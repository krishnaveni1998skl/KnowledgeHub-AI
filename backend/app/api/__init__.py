from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.auth import router as auth_router, get_current_user, get_current_user_optional, require_roles

__all__ = [
    "health_router",
    "documents_router",
    "search_router",
    "auth_router",
    "get_current_user",
    "get_current_user_optional",
    "require_roles",
]

