"""
Feedback Routes
Handles user feedback submission and status checking.

This module supports the beta feedback popup that collects user ratings
and improvement suggestions.
"""

import os
import time
import uuid
import requests
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from services.db import get_database

# =============================================================================
# ROUTER SETUP
# =============================================================================
router = APIRouter(prefix="/api/feedback", tags=["Feedback"])
logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ISSUES_OWNER = os.getenv("GITHUB_ISSUES_OWNER", os.getenv("GITHUB_USERNAME", "cliff-de-tech"))
GITHUB_ISSUES_REPO = os.getenv("GITHUB_ISSUES_REPO", "Post-Bot")
GITHUB_ISSUE_TIMEOUT = int(os.getenv("GITHUB_ISSUE_TIMEOUT", "15"))

# =============================================================================
# SERVICE IMPORTS
# =============================================================================
try:
    from services.feedback import (
        save_feedback,
        has_user_submitted_feedback,
        get_all_feedback,
    )
except ImportError:
    save_feedback = None
    has_user_submitted_feedback = None
    get_all_feedback = None

try:
    from services.email_service import EmailService
    email_service = EmailService()
except ImportError:
    email_service = None


# =============================================================================
# REQUEST MODELS
# =============================================================================
class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    user_id: str
    rating: int  # 1-5 stars - validated by Field
    liked: Optional[str] = None
    improvements: str  # Required
    suggestions: Optional[str] = None
    
    class Config:
        @staticmethod
        def json_schema_extra(schema: dict) -> None:
            schema['properties']['rating']['minimum'] = 1
            schema['properties']['rating']['maximum'] = 5


class BugReportRequest(BaseModel):
    """Request model for dashboard bug reports."""
    bug_title: str
    bug_description: str
    user_email: EmailStr


def _create_github_issue(title: str, description: str, email: str, ticket_id: str) -> dict:
    """Create a GitHub issue for a submitted bug report."""
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=503, detail="Bug reporting is temporarily unavailable (GitHub token not configured)")

    issue_title = f"[Bug] {title}"
    issue_body = (
        "## Bug Report\n\n"
        f"**Reporter email:** {email}\n"
        f"**Internal ticket ID:** {ticket_id}\n\n"
        "### Description\n"
        f"{description}\n"
    )

    response = requests.post(
        f"{GITHUB_API}/repos/{GITHUB_ISSUES_OWNER}/{GITHUB_ISSUES_REPO}/issues",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        json={
            "title": issue_title,
            "body": issue_body,
            "labels": ["bug", "from-dashboard"],
        },
        timeout=GITHUB_ISSUE_TIMEOUT,
    )

    if response.status_code != 201:
        try:
            err_msg = response.json().get("message", "Failed to create GitHub issue")
        except Exception:
            err_msg = "Failed to create GitHub issue"
        logger.error("github_issue_create_failed", extra={"status_code": response.status_code, "message": err_msg})
        raise HTTPException(status_code=502, detail=f"GitHub issue creation failed: {err_msg}")

    return response.json()


@router.post("", status_code=status.HTTP_201_CREATED)
async def report_bug(req: BugReportRequest):
    """Submit a bug report from the dashboard modal and create a GitHub issue."""
    db = get_database()

    title = req.bug_title.strip()
    description = req.bug_description.strip()
    email = req.user_email.strip()

    if not title:
        raise HTTPException(status_code=400, detail="Bug title is required")
    if not description:
        raise HTTPException(status_code=400, detail="Bug description is required")

    ticket_id = str(uuid.uuid4())

    # Primary action: create GitHub issue in Post-Bot repository.
    issue = _create_github_issue(title=title, description=description, email=email, ticket_id=ticket_id)
    issue_number = issue.get("number")
    issue_url = issue.get("html_url")

    try:
        await db.execute(
            """
            INSERT INTO tickets (id, name, email, subject, body, recipient, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            [
                ticket_id,
                "Dashboard User",
                email,
                f"Bug Report: {title}",
                description,
                "engineering",
                "open",
                int(time.time()),
            ],
        )
    except Exception as exc:
        logger.warning("bug_report_ticket_insert_failed", extra={"ticket_id": ticket_id, "error": str(exc)})

    return {
        "success": True,
        "ticket_id": ticket_id,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "message": "Bug report submitted and GitHub issue created successfully",
    }


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.post("/submit")
async def submit_feedback(req: FeedbackRequest):
    """Submit user feedback (stored in SQLite and optionally emailed)."""
    if not save_feedback:
        return {"error": "Feedback service not available"}
    
    try:
        # Validate rating range
        if req.rating < 1 or req.rating > 5:
            return {"success": False, "error": "Rating must be between 1 and 5"}
        
        # Save to database
        result = await save_feedback(
            user_id=req.user_id,
            rating=req.rating,
            liked=req.liked,
            improvements=req.improvements,
            suggestions=req.suggestions
        )
        
        # Also send email notification if email service available
        if email_service and result.get('success'):
            try:
                email_body = f"""
New Beta Feedback Received!

User ID: {req.user_id}
Rating: {'⭐' * req.rating}
Liked: {req.liked or 'Not provided'}
Improvements: {req.improvements}
Suggestions: {req.suggestions or 'None'}
                """
                email_service.send_email(
                    to_email=os.getenv('ADMIN_EMAIL', 'admin@example.com'),
                    subject=f"[LinkedIn Bot] New Feedback - {req.rating}⭐",
                    body=email_body
                )
            except Exception as e:
                print(f"Failed to send feedback email: {e}")
        
        return result
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return {"success": False, "error": str(e)}


@router.get("/status/{user_id}")
async def get_feedback_status(user_id: str):
    """Check if user has already submitted feedback."""
    if not has_user_submitted_feedback:
        return {"has_submitted": False}
    
    try:
        return {"has_submitted": await has_user_submitted_feedback(user_id)}
    except Exception as e:
        print(f"Error checking feedback status: {e}")
        return {"has_submitted": False}
