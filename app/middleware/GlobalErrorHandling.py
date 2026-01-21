from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import traceback

class GlobalErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            print(f"Unhandled exception: {e}")
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"data": None, "error":str(e),"success": False}
            )