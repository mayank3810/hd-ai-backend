from jose import jwt, JWTError
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key: str = None, algorithm: str = "HS256"):
        super().__init__(app)
        self.secret_key = secret_key or os.getenv("JWT_SECRET", "defaultsecret")
        self.algorithm = algorithm

    async def dispatch(self, request: Request, call_next):
        
        public_routes = ["/login", "/register"]  # Add paths that don't require auth
        if request.url.path in public_routes:
            return await call_next(request)

        # Validate Authorization header
        authorization: str = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header is missing or invalid."},
            )

        token = authorization.split("Bearer ")[1]

        try:
            # Decode and validate the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Optional: Add the user info to the request state for use in endpoints
            request.state.user = payload
        except JWTError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token."},
            )

        return await call_next(request)