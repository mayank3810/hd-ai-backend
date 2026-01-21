from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from typing import Dict, Any

def jwt_validator(
    auth: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> Dict[str, Any]:
    secret_key: str = os.getenv("JWT_SECRET"),
    algorithm: str = "RS256",
    token = auth.credentials
    try:
        payload = jwt.decode(token, secret_key)
        return payload

    except JWTError as e:
        print(e)
        raise HTTPException(status_code=401, detail="Invalid or expired token.")