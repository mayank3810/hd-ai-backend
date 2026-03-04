import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from starlette.responses import RedirectResponse
from app.helpers.Database import MongoDB
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.controllers import Auth,Profile, Common
from app.middleware.JWTVerification import jwt_validator
from app.controllers import SpeakerProfileOnboarding, SpeakerOptions, Scraper, UrlScraperRapidAPI, Opportunity
import logging
from fastapi.middleware.gzip import GZipMiddleware

load_dotenv()

# Configure logging for URL scraper and LLM extraction
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
for name in ("app.helpers.RapidAPIScraper", "app.helpers.SpeakingOpportunityExtractor", "app.services.UrlScraperRapidAPI"):
    logging.getLogger(name).setLevel(logging.INFO)

app = FastAPI(
    title="HD AI",
    description="HD AI Backend API's",
    version='1.0.0',
    docs_url="/api-docs",
    redoc_url="/api-redoc"
)

# Middleware
app.add_middleware(GlobalErrorHandlingMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
add_cors_middleware(app)

# Routes
app.include_router(Auth.router)
app.include_router(Profile.router,dependencies=[Depends(jwt_validator)])
app.include_router(Common.router,dependencies=[Depends(jwt_validator)])
app.include_router(SpeakerProfileOnboarding.router)
app.include_router(SpeakerOptions.router)
app.include_router(Scraper.router, dependencies=[Depends(jwt_validator)])
app.include_router(UrlScraperRapidAPI.router, dependencies=[Depends(jwt_validator)])
app.include_router(Opportunity.router, dependencies=[Depends(jwt_validator)])


@app.on_event("startup")
async def startup_event():
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    # Connect async MongoDB (Motor)
    MongoDB.connect(connection_string)
    print("MongoDB connected (async with Motor)")
   

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup resources on shutdown"""
    from app.dependencies import cleanup_resources
    cleanup_resources()
    if MongoDB.client:
        MongoDB.client.close()
    print("App shutdown complete - resources cleaned up")

@app.get("/")
def api_docs():
    return RedirectResponse(url="/api-docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)