import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from starlette.responses import RedirectResponse
from app.helpers.Database import MongoDB
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.controllers import Auth
from app.middleware.JWTVerification import jwt_validator
from app.middleware.ConditionalGZip import ConditionalGZipMiddleware



load_dotenv()

app = FastAPI(
    title="HD AI Backend",
    description="HD AI Backend API's",
    version='1.0.0',
    docs_url="/api-docs",
    redoc_url="/api-redoc"
)

# Middleware
app.add_middleware(GlobalErrorHandlingMiddleware)
app.add_middleware(
    ConditionalGZipMiddleware, 
    minimum_size=1000,
    exclude_paths=[
    ]
)
add_cors_middleware(app)

# Routes
app.include_router(Auth.router)

@app.on_event("startup")
async def startup_event():
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    MongoDB.connect(connection_string)
    MongoDB.sync_connect(connection_string)


    print("mongodb connected")

@app.on_event("shutdown") 
async def shutdown_event():
    print("app shutdown")

@app.get("/")
def api_docs():
    return RedirectResponse(url="/api-docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)