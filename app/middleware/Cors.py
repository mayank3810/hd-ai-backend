from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*","http://localhost:4444/"],  # Can restrict to specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )