from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
import gzip
from typing import List


class ConditionalGZipMiddleware(BaseHTTPMiddleware):
    """
    GZip middleware that excludes streaming endpoints to prevent buffering.
    For excluded paths, responses pass through without compression.
    For other paths, applies GZip compression similar to FastAPI's GZipMiddleware.
    """
    def __init__(self, app, minimum_size: int = 1000, exclude_paths: List[str] = None):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(self, request: Request, call_next):
        # Check if the path should be excluded from GZip compression
        path = request.url.path
        
        # Check if path matches any excluded pattern
        should_exclude = any(
            path.startswith(excluded_path) for excluded_path in self.exclude_paths
        )
        
        if should_exclude:
            # Skip GZip compression for this path (important for streaming)
            return await call_next(request)
        
        # For non-excluded paths, apply GZip compression
        response = await call_next(request)
        
        # Don't compress streaming responses or if already compressed
        if isinstance(response, StreamingResponse):
            return response
        
        if response.headers.get("content-encoding") == "gzip":
            return response
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response
        
        # Check content type - only compress certain types
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/xhtml+xml",
        ]
        if not any(ct in content_type for ct in compressible_types):
            return response
        
        # Get response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Check minimum size
        if len(response_body) < self.minimum_size:
            # Return uncompressed response
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Compress the response
        compressed_body = gzip.compress(response_body, compresslevel=6)
        
        # Create new response with compressed body
        headers = dict(response.headers)
        headers["content-encoding"] = "gzip"
        headers["content-length"] = str(len(compressed_body))
        headers.setdefault("vary", "Accept-Encoding")
        
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
