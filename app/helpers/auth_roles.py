"""JWT / user role checks shared across controllers."""

from typing import Optional

# Roles that may perform admin-only API actions (list users, speaker profile admin views, etc.)
_ADMIN_ROLE_VALUES = frozenset({"admin", "super_admin"})


def is_admin_role(user_type: Optional[str]) -> bool:
    """True if user_type is admin or super_admin."""
    return user_type in _ADMIN_ROLE_VALUES
