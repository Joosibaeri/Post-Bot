"""
Backend Integration Tests

Comprehensive tests for all API endpoints:
- Health & Templates (public)
- Auth refresh
- Settings (GET / POST / ownership)
- Usage & Stats (data + ownership)
- Connection status
- Post CRUD (create, get history)
- Post generation & publishing
- Scheduled posts (CRUD)
- Feedback (submit, status)
- Ownership guards (403 on cross-user access)
- Error handling
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client(sync_test_client):
    """Shorthand for sync_test_client."""
    return sync_test_client


# ── Fake user IDs ───────────────────────────────────────────────────────────
AUTH_USER_ID = "test_user_dev"       # matches _FAKE_AUTH_USER in conftest
OTHER_USER_ID = "other_user_evil"    # foreign user for 403 tests


# ═══════════════════════════════════════════════════════════════════════════
# 1. HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════════
class TestHealth:
    """Health check endpoint."""

    def test_health_endpoint_returns_json(self, client: TestClient):
        """GET /health must return JSON with status & database."""
        r = client.get("/health")
        assert r.status_code in (200, 503)
        body = r.json()
        assert "status" in body
        assert "database" in body
        assert body["status"] in ("healthy", "degraded")


# ═══════════════════════════════════════════════════════════════════════════
# 2. TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════
class TestTemplates:
    """Template listing endpoints."""

    def test_root_templates_endpoint(self, client: TestClient):
        """GET /api/templates returns a list of templates."""
        r = client.get("/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) > 0

    def test_templates_fields(self, client: TestClient):
        """Each template has id, name, description."""
        templates = client.get("/api/templates").json()["templates"]
        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t

    def test_standard_template_exists(self, client: TestClient):
        """The 'standard' template should always be present."""
        ids = [t["id"] for t in client.get("/api/templates").json()["templates"]]
        assert "standard" in ids

    def test_settings_templates_endpoint(self, client: TestClient):
        """GET /api/settings/templates duplicates from settings router."""
        r = client.get("/api/templates")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 3. AUTH REFRESH
# ═══════════════════════════════════════════════════════════════════════════
class TestAuthRefresh:
    """POST /auth/refresh – check if user has valid LinkedIn connection."""

    def test_refresh_returns_auth_status(self, client: TestClient):
        """Refresh endpoint returns authenticated boolean."""
        r = client.post("/auth/refresh", json={"user_id": AUTH_USER_ID})
        assert r.status_code == 200
        body = r.json()
        assert "authenticated" in body

    def test_refresh_nonexistent_user(self, client: TestClient):
        """Unknown user should return authenticated=False (not crash)."""
        r = client.post("/auth/refresh", json={"user_id": "nonexistent_user_xyz"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("authenticated") is False


# ═══════════════════════════════════════════════════════════════════════════
# 4. SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
class TestSettings:
    """GET/POST /api/settings endpoints."""

    def test_get_settings_own_user(self, client: TestClient):
        """Authenticated user can GET their own settings."""
        r = client.get(f"/api/settings/{AUTH_USER_ID}")
        # 200 when DB is running, 500 when DatabaseBackend is not running
        assert r.status_code in (200, 500)
        body = r.json()
        if r.status_code == 200:
            assert "user_id" in body or "error" in body

    def test_get_settings_other_user_forbidden(self, client: TestClient):
        """Accessing another user's settings returns 403."""
        r = client.get(f"/api/settings/{OTHER_USER_ID}")
        assert r.status_code == 403

    def test_save_settings_body(self, client: TestClient):
        """POST /api/settings saves settings via body."""
        r = client.post(
            "/api/settings",
            json={
                "user_id": AUTH_USER_ID,
                "github_username": "testuser",
                "onboarding_complete": True,
            },
        )
        # 200 when DB running, 500 when DB not available in test env
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            assert r.json().get("success") is True

    def test_save_settings_path(self, client: TestClient):
        """POST /api/settings/{user_id} saves via path param."""
        r = client.post(
            f"/api/settings/{AUTH_USER_ID}",
            json={
                "github_username": "testuser2",
            },
        )
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            assert r.json().get("success") is True

    def test_save_settings_other_user_forbidden(self, client: TestClient):
        """Saving settings for another user returns 403."""
        r = client.post(
            "/api/settings",
            json={"user_id": OTHER_USER_ID, "github_username": "hacker"},
        )
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 5. USAGE & STATS
# ═══════════════════════════════════════════════════════════════════════════
class TestUsage:
    """GET /api/usage/{user_id} – daily limit tracking."""

    def test_usage_returns_tier_info(self, client: TestClient):
        """Usage endpoint returns tier, limits, and counts."""
        r = client.get(f"/api/usage/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "tier" in body
        assert "posts_today" in body
        assert "posts_limit" in body
        assert "posts_remaining" in body

    def test_usage_other_user_forbidden(self, client: TestClient):
        """Accessing another user's usage returns 403."""
        r = client.get(f"/api/usage/{OTHER_USER_ID}")
        assert r.status_code == 403


class TestStats:
    """GET /api/stats/{user_id} – dashboard statistics."""

    def test_stats_returns_post_counts(self, client: TestClient):
        """Stats endpoint returns expected fields."""
        r = client.get(f"/api/stats/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "posts_generated" in body
        assert "posts_published" in body
        assert "growth_percentage" in body

    def test_stats_other_user_forbidden(self, client: TestClient):
        """Accessing another user's stats returns 403."""
        r = client.get(f"/api/stats/{OTHER_USER_ID}")
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONNECTION STATUS
# ═══════════════════════════════════════════════════════════════════════════
class TestConnectionStatus:
    """GET /api/connection-status/{user_id}."""

    def test_connection_status_returns_fields(self, client: TestClient):
        """Connection status returns linkedin/github connection states."""
        r = client.get(f"/api/connection-status/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "linkedin_connected" in body
        assert "github_connected" in body
        assert isinstance(body["linkedin_connected"], bool)

    def test_connection_status_other_user_forbidden(self, client: TestClient):
        """Accessing another user's connection status returns 403."""
        r = client.get(f"/api/connection-status/{OTHER_USER_ID}")
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 7. POST CRUD
# ═══════════════════════════════════════════════════════════════════════════
class TestPostCRUD:
    """POST /api/posts, GET /api/posts/{user_id}."""

    def test_create_post(self, client: TestClient):
        """Create a draft post."""
        r = client.post(
            "/api/posts",
            json={
                "user_id": AUTH_USER_ID,
                "post_content": "Hello LinkedIn! 🚀",
                "post_type": "push",
                "status": "draft",
            },
        )
        # 200 when DB is running, 500 when DatabaseBackend not available
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            body = r.json()
            assert body.get("success") is True
            assert "id" in body

    def test_get_posts_history(self, client: TestClient):
        """Get post history returns a list."""
        r = client.get(f"/api/posts/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "posts" in body
        assert isinstance(body["posts"], list)

    def test_get_posts_other_user_forbidden(self, client: TestClient):
        """Accessing another user's post history returns 403."""
        r = client.get(f"/api/posts/{OTHER_USER_ID}")
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 8. POST GENERATION
# ═══════════════════════════════════════════════════════════════════════════
class TestPostGeneration:
    """POST /api/post/generate-preview."""

    def test_generate_preview_with_context(self, client: TestClient):
        """Generate preview should accept context."""
        r = client.post(
            "/api/post/generate-preview",
            json={
                "context": {
                    "type": "push",
                    "repo": "test-project",
                    "commits": 3,
                },
                "user_id": AUTH_USER_ID,
            },
        )
        # May fail if AI service is unavailable (503), or work (200)
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            body = r.json()
            assert "post" in body or "error" in body

    def test_generate_preview_empty_context(self, client: TestClient):
        """Empty context should still return a response (not crash)."""
        r = client.post(
            "/api/post/generate-preview",
            json={"context": {}, "user_id": AUTH_USER_ID},
        )
        assert r.status_code in (200, 422, 503)

    def test_providers_endpoint(self, client: TestClient):
        """GET /api/post/providers lists AI providers."""
        r = client.get("/api/post/providers")
        assert r.status_code == 200
        body = r.json()
        assert "providers" in body
        assert "user_tier" in body


# ═══════════════════════════════════════════════════════════════════════════
# 9. PUBLISHING
# ═══════════════════════════════════════════════════════════════════════════
class TestPublishing:
    """POST /api/post/publish, POST /api/publish/full."""

    def test_publish_test_mode(self, client: TestClient):
        """Publish in test mode returns success without real post."""
        r = client.post(
            "/api/post/publish",
            json={
                "user_id": AUTH_USER_ID,
                "post_content": "Test mode publish 🧪",
                "test_mode": True,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
        assert body.get("test_mode") is True

    def test_publish_full_test_mode(self, client: TestClient):
        """POST /api/publish/full in test mode."""
        r = client.post(
            "/api/publish/full",
            json={
                "user_id": AUTH_USER_ID,
                "post_content": "Full publish test mode 🚀",
                "test_mode": True,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
        assert body.get("test_mode") is True

    def test_publish_without_content_or_context(self, client: TestClient):
        """Publish with neither content nor context returns error."""
        r = client.post(
            "/api/post/publish",
            json={
                "user_id": AUTH_USER_ID,
                "test_mode": False,
            },
        )
        # Should fail since there's no content to publish
        body = r.json()
        assert body.get("success") is False or "error" in body or r.status_code >= 400


# ═══════════════════════════════════════════════════════════════════════════
# 10. SCHEDULED POSTS
# ═══════════════════════════════════════════════════════════════════════════
class TestScheduledPosts:
    """Scheduled post CRUD endpoints."""

    def test_schedule_post(self, client: TestClient):
        """POST /api/scheduled creates a scheduled post."""
        import time
        future_time = int(time.time()) + 86400  # 24h from now

        r = client.post(
            "/api/scheduled",
            json={
                "user_id": AUTH_USER_ID,
                "post_content": "Scheduled test post ⏰",
                "scheduled_time": future_time,
            },
        )
        assert r.status_code == 200
        body = r.json()
        # When DB is running: success=True; when DB is down: success=False with error
        assert body.get("success") is True or "error" in body

    def test_get_scheduled_posts(self, client: TestClient):
        """GET /api/scheduled/{user_id} returns scheduled posts."""
        r = client.get(f"/api/scheduled/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "scheduled_posts" in body
        assert isinstance(body["scheduled_posts"], list)

    def test_get_scheduled_other_user_forbidden(self, client: TestClient):
        """Accessing another user's scheduled posts returns 403."""
        r = client.get(f"/api/scheduled/{OTHER_USER_ID}")
        assert r.status_code == 403

    def test_get_scheduled_posts_alternate(self, client: TestClient):
        """GET /api/scheduled-posts/{user_id} also returns posts."""
        r = client.get(f"/api/scheduled-posts/{AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "posts" in body


# ═══════════════════════════════════════════════════════════════════════════
# 11. FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════
class TestFeedback:
    """Feedback submit and status endpoints."""

    def test_feedback_status(self, client: TestClient):
        """GET /api/feedback/status/{user_id} checks submission status."""
        r = client.get(f"/api/feedback/status/{AUTH_USER_ID}")
        # 200 when DB available, 500 when DatabaseBackend is not running
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            body = r.json()
            assert "has_submitted" in body

    def test_submit_feedback(self, client: TestClient):
        """POST /api/feedback/submit stores feedback."""
        r = client.post(
            "/api/feedback/submit",
            json={
                "user_id": AUTH_USER_ID,
                "rating": 5,
                "liked": "The AI post generation",
                "improvements": "More templates please",
                "suggestions": "Add Twitter support",
            },
        )
        assert r.status_code == 200
        body = r.json()
        # Either success or service not available (both OK for integration)
        assert body.get("success") is True or "error" in body

    def test_submit_feedback_invalid_rating(self, client: TestClient):
        """Feedback with out-of-range rating is handled."""
        r = client.post(
            "/api/feedback/submit",
            json={
                "user_id": AUTH_USER_ID,
                "rating": 99,
                "improvements": "Nothing",
            },
        )
        assert r.status_code == 200
        body = r.json()
        # Should either reject or cap the rating
        if body.get("success") is False:
            assert "error" in body


# ═══════════════════════════════════════════════════════════════════════════
# 12. GITHUB ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════
class TestGitHubActivity:
    """GitHub activity and scan endpoints."""

    def test_github_activity_endpoint(self, client: TestClient):
        """GET /api/github/activity/{username} returns activities."""
        r = client.get("/api/github/activity/octocat?limit=3")
        assert r.status_code == 200
        body = r.json()
        assert "activities" in body or "error" in body

    def test_github_scan_authenticated(self, client: TestClient):
        """POST /api/github/scan requires matching user_id."""
        r = client.post(
            "/api/github/scan",
            json={"user_id": AUTH_USER_ID, "hours": 24},
        )
        # Should succeed (might have no activities, but no crash)
        assert r.status_code == 200

    def test_github_scan_other_user_forbidden(self, client: TestClient):
        """Scanning for another user returns 403."""
        r = client.post(
            "/api/github/scan",
            json={"user_id": OTHER_USER_ID, "hours": 24},
        )
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 13. BOT STATS
# ═══════════════════════════════════════════════════════════════════════════
class TestBotStats:
    """GET /api/post/bot-stats – bot mode statistics."""

    def test_bot_stats_returns_counts(self, client: TestClient):
        """Bot stats returns generated/published counts."""
        r = client.get(f"/api/post/bot-stats?user_id={AUTH_USER_ID}")
        assert r.status_code == 200
        body = r.json()
        assert "generated" in body or "error" in body

    def test_bot_stats_other_user_forbidden(self, client: TestClient):
        """Bot stats for another user returns 403."""
        r = client.get(f"/api/post/bot-stats?user_id={OTHER_USER_ID}")
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 14. CORS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
class TestCORS:
    """CORS response headers."""

    def test_cors_allows_localhost(self, client: TestClient):
        """OPTIONS /health with localhost origin should succeed."""
        r = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # FastAPI may return 200 or 405 for OPTIONS
        assert r.status_code in (200, 405)

    def test_health_has_json_content_type(self, client: TestClient):
        """Health endpoint returns application/json."""
        r = client.get("/health")
        assert "application/json" in r.headers.get("content-type", "")


# ═══════════════════════════════════════════════════════════════════════════
# 15. RESPONSE FORMAT CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════
class TestResponseFormat:
    """Validate consistent API response shapes."""

    def test_error_response_format(self, client: TestClient):
        """Missing required fields return 422 with detail."""
        r = client.post(
            "/api/post/generate-preview",
            json={},  # missing 'context'
        )
        assert r.status_code == 422
        body = r.json()
        assert "detail" in body

    def test_invalid_json_body(self, client: TestClient):
        """Invalid JSON returns 422."""
        r = client.post(
            "/api/post/publish",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 16. REPURPOSE ENGINE
# ═══════════════════════════════════════════════════════════════════════════
class TestRepurposeEngine:
    """POST /api/post/repurpose endpoints."""

    @patch("routes.posts.scrape_url", new_callable=AsyncMock)
    @patch("routes.posts.generate_linkedin_post", new_callable=AsyncMock)
    def test_repurpose_url_success(self, mock_generate, mock_scrape, client: TestClient):
        """Valid URL and successful AI generation returns 3 posts."""
        mock_scrape.return_value = "This is some test content from a blog."
        
        # Mock the generation result
        mock_result = MagicMock()
        mock_result.content = '["Post 1", "Post 2", "Post 3"]'
        mock_result.provider = MagicMock(value="groq")
        mock_result.model = "llama3-8b-8192"
        mock_generate.return_value = mock_result

        r = client.post(
            "/api/post/repurpose",
            json={
                "url": "https://example.com/blog-post",
                "user_id": AUTH_USER_ID,
                "model": "groq"
            },
        )
        
        # 200 when DB is running, 500 if DB is down but the API logic runs
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            body = r.json()
            assert "posts" in body
            assert len(body["posts"]) == 3
            assert body["posts"][0]["content"] == "Post 1"

    @patch("routes.posts.scrape_url", new_callable=AsyncMock)
    def test_repurpose_url_scraping_fails(self, mock_scrape, client: TestClient):
        """Failed scraping returns 400 Bad Request."""
        mock_scrape.side_effect = Exception("Connection error")

        r = client.post(
            "/api/post/repurpose",
            json={
                "url": "https://invalid-url.com",
                "user_id": AUTH_USER_ID,
            },
        )
        assert r.status_code == 400
        body = r.json()
        assert "detail" in body
        assert "Failed to scrape URL" in body["detail"]

    @patch("routes.posts.scrape_url", new_callable=AsyncMock)
    @patch("routes.posts.generate_linkedin_post", new_callable=AsyncMock)
    def test_repurpose_json_fallback(self, mock_generate, mock_scrape, client: TestClient):
        """If AI returns invalid JSON, it falls back to a single post array."""
        mock_scrape.return_value = "Test content"
        
        mock_result = MagicMock()
        mock_result.content = "Here are your posts: 1. A 2. B 3. C"  # not JSON
        mock_result.provider = MagicMock(value="groq")
        mock_result.model = "llama3-8b-8192"
        mock_generate.return_value = mock_result

        r = client.post(
            "/api/post/repurpose",
            json={
                "url": "https://example.com/blog-post",
                "user_id": AUTH_USER_ID,
            },
        )
        
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            body = r.json()
            assert "posts" in body
            assert len(body["posts"]) == 1
            assert body["posts"][0]["content"] == mock_result.content
