"""
Authentication Routes
Handles OAuth flows for LinkedIn and GitHub.

SECURITY NOTES:
- OAuth tokens are stored encrypted in backend_tokens.db
- User IDs are validated via Clerk JWT
- State parameter prevents CSRF attacks
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

# =============================================================================
# ROUTER SETUP
# =============================================================================
router = APIRouter(prefix="/auth", tags=["Authentication"])

# GitHub OAuth configuration — kept for reference but OAuth routes moved to github.py
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')

# =============================================================================
# SERVICE IMPORTS (with graceful fallbacks)
# =============================================================================
try:
    from services.user_settings import get_user_settings, save_user_settings
except ImportError:
    get_user_settings = None
    save_user_settings = None

import structlog
logger = structlog.get_logger(__name__)


# =============================================================================
# REQUEST MODELS
# =============================================================================
class DisconnectRequest(BaseModel):
    """Request model for disconnect endpoints."""
    user_id: str


class AuthRefreshRequest(BaseModel):
    user_id: str


# =============================================================================
# LINKEDIN OAUTH ENDPOINTS
# =============================================================================
# NOTE: LinkedIn OAuth /start and /callback are handled by routes/linkedin.py
# (linkedin_auth_router) which has proper redirect URL validation and env-based
# callback URLs. The endpoints below are REMOVED to avoid duplicate route
# conflicts where the insecure version takes priority.


# =============================================================================
# GITHUB OAUTH ENDPOINTS
# =============================================================================
# NOTE: GitHub OAuth /start and /callback are handled by routes/github.py
# (github_auth_router) which has proper redirect URL validation.
# The endpoints below are REMOVED to avoid duplicate route conflicts
# and the open redirect vulnerability in the old /start endpoint.


# =============================================================================
# AUTH UTILITY ENDPOINTS
# =============================================================================
@router.post("/refresh")
async def refresh_auth(req: AuthRefreshRequest):
    """Check if user has valid LinkedIn connection.
    
    Checks the accounts table (where OAuth tokens are actually stored)
    for a valid LinkedIn connection, with user_settings as a fallback.
    """
    try:
        # Primary check: accounts table (where tokens are actually stored)
        try:
            from services.token_store import get_token_by_user_id
            token_data = await get_token_by_user_id(req.user_id)
            if token_data and token_data.get("access_token"):
                return {
                    "access_token": "valid",
                    "user_urn": token_data.get("linkedin_user_urn", ""),
                    "authenticated": True
                }
        except Exception as e:
            logger.warning("auth_refresh_token_check_failed", error=str(e))

        # Fallback: direct DB query in case token_store import fails
        try:
            from services.db import get_database
            db = get_database()
            row = await db.fetch_one(
                "SELECT access_token, linkedin_user_urn FROM accounts WHERE user_id = $1",
                [req.user_id]
            )
            if row:
                row_dict = dict(row)
                if row_dict.get("access_token"):
                    return {
                        "access_token": "valid",
                        "user_urn": row_dict.get("linkedin_user_urn", ""),
                        "authenticated": True
                    }
        except Exception as e:
            logger.warning("auth_refresh_db_fallback_failed", error=str(e))

        # Legacy fallback: user_settings (for users with per-user LinkedIn credentials)
        if get_user_settings:
            settings = await get_user_settings(req.user_id)
            if settings and settings.get("linkedin_user_urn"):
                return {
                    "access_token": "valid",
                    "user_urn": settings.get("linkedin_user_urn"),
                    "authenticated": True
                }

        return {"access_token": None, "authenticated": False}
    except Exception as e:
        logger.error("auth_refresh_error", error=str(e))
        return {"error": str(e), "authenticated": False}
