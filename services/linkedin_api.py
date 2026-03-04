"""
LinkedIn Posting API Service (Async)

This module provides async LinkedIn posting functionality using the
LinkedIn Community Management API (/rest/posts).

Used by the /api/publish/full route in bot mode.

IMPORTANT - LinkedIn API Compliance:
- Uses LinkedIn's Community Management API (Posts endpoint)
- Requires w_member_social OAuth scope
- Does NOT use browser automation or scraping
- Respects LinkedIn's rate limits

SECURITY NOTES:
- Access tokens are never logged
- Failed responses are logged without exposing tokens
- All API calls use HTTPS with proper authorization headers
"""

import httpx
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

# LinkedIn API configuration
LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_API_VERSION = "202501"  # LinkedIn API versioning (YYYYMM format)


async def post_to_linkedin(
    user_urn: str,
    access_token: str,
    post_content: str,
    image_url: Optional[str] = None,
) -> dict:
    """
    Create a post on LinkedIn using the Community Management API.

    Args:
        user_urn: LinkedIn person URN (without the urn:li:person: prefix)
        access_token: Valid OAuth access token
        post_content: The post text content (max 3000 characters)
        image_url: Optional image URL (not uploaded, just for logging)

    Returns:
        Dict with post ID on success

    Raises:
        Exception: If the post fails with details about the error

    SECURITY:
    - Access token sent only in Authorization header
    - Post visibility is set to PUBLIC
    - No engagement automation
    """
    if not access_token:
        raise ValueError("Missing access_token for LinkedIn posting")
    if not user_urn:
        raise ValueError("Missing user_urn for LinkedIn posting")

    # Build the author URN
    author_urn = f"urn:li:person:{user_urn}" if not user_urn.startswith("urn:") else user_urn

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
    }

    # Build post payload using Community Management API format
    post_data = {
        "author": author_urn,
        "commentary": post_content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
    }

    # Truncate message for logging (don't expose full content)
    preview = post_content[:30].replace("\n", " ")
    logger.info("linkedin_post_started", preview=f"{preview}...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try the Community Management API first (/rest/posts)
        try:
            response = await client.post(
                f"{LINKEDIN_API_BASE}/rest/posts",
                headers=headers,
                json=post_data,
            )

            if response.status_code == 201:
                # Extract post ID from x-restli-id header
                post_id = response.headers.get("x-restli-id", "")
                logger.info("linkedin_post_success", post_id=post_id)
                return {"id": post_id, "success": True}

            # If /rest/posts fails, fall back to legacy /v2/ugcPosts
            if response.status_code in (400, 403, 404, 426):
                logger.warning(
                    "rest_api_failed_trying_legacy",
                    status=response.status_code,
                    response_preview=response.text[:200],
                )
                return await _post_with_ugc_api(client, author_urn, post_content, access_token)

            # Handle specific error codes
            if response.status_code == 401:
                error_text = response.text[:200]
                logger.error("linkedin_post_unauthorized", response_preview=error_text)
                raise PermissionError(
                    f"LinkedIn token expired or invalid. Please reconnect your LinkedIn account. (Status: 401)"
                )

            if response.status_code == 429:
                logger.warning("linkedin_rate_limited")
                raise RuntimeError("LinkedIn rate limit reached. Please wait a few minutes and try again.")

            # Generic failure
            error_text = response.text[:500]
            logger.error(
                "linkedin_post_failed",
                status=response.status_code,
                response_preview=error_text,
            )
            raise RuntimeError(f"LinkedIn API error (status {response.status_code}): {error_text[:200]}")

        except httpx.TimeoutException:
            logger.error("linkedin_post_timeout")
            raise RuntimeError("LinkedIn API request timed out. Please try again.")
        except (PermissionError, RuntimeError, ValueError):
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error("linkedin_post_unexpected_error", error=str(e)[:200])
            raise RuntimeError(f"Unexpected error posting to LinkedIn: {type(e).__name__}")


async def _post_with_ugc_api(
    client: httpx.AsyncClient,
    author_urn: str,
    post_content: str,
    access_token: str,
) -> dict:
    """
    Fallback: Post using the legacy UGC Posts API (/v2/ugcPosts).

    Some LinkedIn apps created before 2024 still use the UGC API.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    post_data = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    response = await client.post(
        f"{LINKEDIN_API_BASE}/v2/ugcPosts",
        headers=headers,
        json=post_data,
    )

    if response.status_code == 201:
        result = response.json()
        post_id = result.get("id", "")
        logger.info("linkedin_ugc_post_success", post_id=post_id)
        return {"id": post_id, "success": True}

    if response.status_code == 401:
        raise PermissionError(
            "LinkedIn token expired or invalid. Please reconnect your LinkedIn account."
        )

    error_text = response.text[:500]
    logger.error(
        "linkedin_ugc_post_failed",
        status=response.status_code,
        response_preview=error_text,
    )
    raise RuntimeError(f"LinkedIn API error (status {response.status_code}): {error_text[:200]}")
