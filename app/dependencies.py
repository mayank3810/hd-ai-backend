"""
Singleton dependencies for resource management.
Prevents creating multiple heavy resources on every API request.
"""
from functools import lru_cache
from typing import Optional, TYPE_CHECKING
import os


# Global singletons - Services
_auth_service = None




def get_auth_service():
    """Get singleton AuthService instance"""
    global _auth_service
    if _auth_service is None:
        from app.services.Auth import AuthService
        _auth_service = AuthService()
    return _auth_service



def cleanup_resources():
    """
    Cleanup all singleton resources. Call this on application shutdown.
    """
    global _auth_service
    # Reset services
    _auth_service = None

