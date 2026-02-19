import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from starlette.responses import RedirectResponse
from app.helpers.Database import MongoDB
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.controllers import Auth,Profile, Common, Listings,Operator,Pricelabs, Property,PricelabsAdmin, Export
from app.middleware.JWTVerification import jwt_validator
from app.controllers import BookingAdmin, AirbnbAdmin, CompetitorProperty, CompetitorComparison, FilterPreset, DeploymentCues
from app.models.Operator import OperatorModel
from app.controllers import BookingAdmin, AirbnbAdmin, CompetitorProperty, CompetitorComparison, FilterPreset, ImageCaption
from app.controllers import Booking, Airbnb, TemporaryCompetitor, CueProperties, OnboardingStatus, QueueStatus, AnalyticsCuesPreset, ExcelSchedule, SpeakerProfileOnboarding, Scraper
import logging
from fastapi.middleware.gzip import GZipMiddleware

load_dotenv()

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
app.include_router(Listings.router)
app.include_router(Pricelabs.router)
app.include_router(Operator.router)
app.include_router(Property.router)
app.include_router(BookingAdmin.router)
app.include_router(PricelabsAdmin.router)
app.include_router(Export.router)
app.include_router(AirbnbAdmin.router)
app.include_router(CompetitorProperty.router)
app.include_router(CompetitorComparison.router)
app.include_router(FilterPreset.router)
# app.include_router(BackgroundMapping.router)
app.include_router(DeploymentCues.router)

# app.include_router(BackgroundMapping.router)
app.include_router(ImageCaption.router)
app.include_router(Booking.router)
app.include_router(Airbnb.router)
app.include_router(TemporaryCompetitor.router)
app.include_router(CueProperties.router)
app.include_router(OnboardingStatus.router)
app.include_router(QueueStatus.router)
app.include_router(AnalyticsCuesPreset.router)
app.include_router(ExcelSchedule.router)
app.include_router(SpeakerProfileOnboarding.router)
app.include_router(Scraper.router, dependencies=[Depends(jwt_validator)])


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