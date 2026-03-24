"""
Paystack Payment Service

Handles Paystack-backed subscription payments:
- Initializing hosted checkout transactions for subscriptions
- Verifying and processing Paystack webhooks
- Persisting subscription lifecycle state into the local database

Notes:
- We keep the public API surface largely compatible with the previous payments
  module so the rest of the app can migrate with minimal churn.
- Paystack does not offer a hosted billing portal, so subscription
  self-service is intentionally limited unless a custom management URL is set.
"""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import httpx
import structlog

from services.db import get_database

logger = structlog.get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

PAYSTACK_API_BASE_URL = os.getenv("PAYSTACK_API_BASE_URL", "https://api.paystack.co")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET") or PAYSTACK_SECRET_KEY
PAYSTACK_SUCCESS_URL = os.getenv("PAYSTACK_SUCCESS_URL", "http://localhost:3000/dashboard?payment=success")
PAYSTACK_CANCEL_URL = os.getenv("PAYSTACK_CANCEL_URL", "http://localhost:3000/pricing")
PAYSTACK_MANAGE_SUBSCRIPTION_URL = os.getenv("PAYSTACK_MANAGE_SUBSCRIPTION_URL")
PAYSTACK_HTTP_TIMEOUT = float(os.getenv("PAYSTACK_HTTP_TIMEOUT", "20"))

if not PAYSTACK_SECRET_KEY:
    logger.warning("PAYSTACK_SECRET_KEY not set - payment features disabled")


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class PaymentServiceError(Exception):
    """Base exception for payment service errors."""


class PaystackNotConfiguredError(PaymentServiceError):
    """Raised when Paystack keys are not configured."""


class WebhookVerificationError(PaymentServiceError):
    """Raised when webhook signature verification fails."""


class CustomerNotFoundError(PaymentServiceError):
    """Raised when a customer/subscription record cannot be found."""


class SubscriptionError(PaymentServiceError):
    """Raised when subscription operations fail."""


class SubscriptionManagementUnavailableError(PaymentServiceError):
    """Raised when self-service subscription management is unavailable."""


# =============================================================================
# DATA CLASSES
# =============================================================================

class SubscriptionStatus(str, Enum):
    """Normalized subscription statuses used by the app."""

    ACTIVE = "active"
    NON_RENEWING = "non_renewing"
    ATTENTION = "attention"
    CANCELED = "canceled"
    COMPLETE = "complete"
    DISABLED = "disabled"
    INACTIVE = "inactive"


@dataclass
class CheckoutSessionResult:
    """Result of initializing a hosted checkout session."""

    session_id: str
    checkout_url: str


@dataclass
class SubscriptionInfo:
    """Subscription information for a user."""

    user_id: str
    paystack_customer_code: Optional[str]
    paystack_subscription_code: Optional[str]
    plan_id: Optional[str]
    status: SubscriptionStatus
    current_period_end: Optional[int]
    cancel_at_period_end: bool


# =============================================================================
# PAYSTACK HELPERS
# =============================================================================

def _ensure_paystack_configured() -> None:
    """Ensure Paystack is properly configured."""

    if not PAYSTACK_SECRET_KEY:
        raise PaystackNotConfiguredError(
            "PAYSTACK_SECRET_KEY environment variable is not set. "
            "Payment features are disabled."
        )


def _paystack_headers() -> Dict[str, str]:
    _ensure_paystack_configured()
    return {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def _paystack_request(
    method: str,
    endpoint: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a Paystack API request and return the `data` envelope."""

    try:
        async with httpx.AsyncClient(
            base_url=PAYSTACK_API_BASE_URL,
            timeout=PAYSTACK_HTTP_TIMEOUT,
        ) as client:
            response = await client.request(
                method,
                endpoint,
                json=payload,
                params=params,
                headers=_paystack_headers(),
            )
    except httpx.HTTPError as exc:
        logger.error("paystack_request_failed", endpoint=endpoint, error=str(exc))
        raise PaymentServiceError(f"Paystack request failed: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("paystack_invalid_json", endpoint=endpoint, status_code=response.status_code)
        raise PaymentServiceError("Paystack returned an invalid response") from exc

    if not response.is_success:
        message = body.get("message") if isinstance(body, dict) else response.text
        raise PaymentServiceError(f"Paystack API error ({response.status_code}): {message}")

    if isinstance(body, dict) and body.get("status") is False:
        raise PaymentServiceError(body.get("message", "Paystack request was rejected"))

    return body.get("data", {}) if isinstance(body, dict) else {}


def _normalize_status(status: Optional[str]) -> SubscriptionStatus:
    normalized = (status or "inactive").strip().lower().replace("-", "_")
    mapping = {
        "active": SubscriptionStatus.ACTIVE,
        "non_renewing": SubscriptionStatus.NON_RENEWING,
        "attention": SubscriptionStatus.ATTENTION,
        "canceled": SubscriptionStatus.CANCELED,
        "cancelled": SubscriptionStatus.CANCELED,
        "complete": SubscriptionStatus.COMPLETE,
        "completed": SubscriptionStatus.COMPLETE,
        "disabled": SubscriptionStatus.DISABLED,
        "inactive": SubscriptionStatus.INACTIVE,
    }
    return mapping.get(normalized, SubscriptionStatus.INACTIVE)


def _status_to_tier(status: SubscriptionStatus) -> str:
    return "pro" if status in {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.NON_RENEWING,
        SubscriptionStatus.ATTENTION,
    } else "free"


def _parse_timestamp(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            try:
                return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
            except ValueError:
                return None
    return None


def _extract_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    metadata = data.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _extract_customer_code(data: Dict[str, Any]) -> Optional[str]:
    customer = data.get("customer")
    if isinstance(customer, dict):
        return customer.get("customer_code") or customer.get("code")
    return data.get("customer_code") or customer


def _extract_plan_code(data: Dict[str, Any]) -> Optional[str]:
    plan = data.get("plan") or data.get("plan_object")
    if isinstance(plan, dict):
        return plan.get("plan_code") or plan.get("code") or plan.get("id")
    return data.get("plan_code") or plan


def _extract_subscription_code(data: Dict[str, Any]) -> Optional[str]:
    subscription = data.get("subscription")
    if isinstance(subscription, dict):
        return subscription.get("subscription_code") or subscription.get("code")
    return data.get("subscription_code") or subscription


def _extract_authorization_code(data: Dict[str, Any]) -> Optional[str]:
    authorization = data.get("authorization")
    if isinstance(authorization, dict):
        return authorization.get("authorization_code")
    return data.get("authorization_code")


async def _find_user_id_by_customer_code(customer_code: Optional[str]) -> Optional[str]:
    if not customer_code:
        return None

    db = get_database()
    row = await db.fetch_one(
        query="SELECT user_id FROM subscriptions WHERE paystack_customer_code = :customer_code",
        values={"customer_code": customer_code},
    )
    return row["user_id"] if row else None


async def _find_user_id_by_subscription_code(subscription_code: Optional[str]) -> Optional[str]:
    if not subscription_code:
        return None

    db = get_database()
    row = await db.fetch_one(
        query="SELECT user_id FROM subscriptions WHERE paystack_subscription_code = :subscription_code",
        values={"subscription_code": subscription_code},
    )
    return row["user_id"] if row else None


async def _get_existing_subscription_row(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_database()
    row = await db.fetch_one(
        query="""
            SELECT plan_id, current_period_start, current_period_end,
                   paystack_customer_code, paystack_subscription_code,
                   paystack_email_token, paystack_authorization_code
            FROM subscriptions
            WHERE user_id = :user_id
        """,
        values={"user_id": user_id},
    )
    return dict(row) if row else None


async def _upsert_subscription_record(
    *,
    user_id: str,
    plan_id: Optional[str],
    status: SubscriptionStatus,
    current_period_start: Optional[int] = None,
    current_period_end: Optional[int] = None,
    paystack_customer_code: Optional[str] = None,
    paystack_subscription_code: Optional[str] = None,
    paystack_email_token: Optional[str] = None,
    paystack_authorization_code: Optional[str] = None,
) -> None:
    """Persist subscription state and synchronize the user's tier."""

    db = get_database()
    now = int(time.time())
    tier = _status_to_tier(status)
    cancel_at_period_end = 1 if status in {
        SubscriptionStatus.NON_RENEWING,
        SubscriptionStatus.CANCELED,
        SubscriptionStatus.COMPLETE,
        SubscriptionStatus.DISABLED,
    } else 0

    await db.execute(
        query="""
            INSERT INTO subscriptions (
                user_id,
                plan_id,
                status,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
                created_at,
                updated_at,
                paystack_customer_code,
                paystack_subscription_code,
                paystack_email_token,
                paystack_authorization_code
            ) VALUES (
                :user_id,
                :plan_id,
                :status,
                :current_period_start,
                :current_period_end,
                :cancel_at_period_end,
                :created_at,
                :updated_at,
                :paystack_customer_code,
                :paystack_subscription_code,
                :paystack_email_token,
                :paystack_authorization_code
            )
            ON CONFLICT (user_id) DO UPDATE SET
                plan_id = COALESCE(:plan_id, subscriptions.plan_id),
                status = :status,
                current_period_start = COALESCE(:current_period_start, subscriptions.current_period_start),
                current_period_end = COALESCE(:current_period_end, subscriptions.current_period_end),
                cancel_at_period_end = :cancel_at_period_end,
                updated_at = :updated_at,
                paystack_customer_code = COALESCE(:paystack_customer_code, subscriptions.paystack_customer_code),
                paystack_subscription_code = COALESCE(:paystack_subscription_code, subscriptions.paystack_subscription_code),
                paystack_email_token = COALESCE(:paystack_email_token, subscriptions.paystack_email_token),
                paystack_authorization_code = COALESCE(:paystack_authorization_code, subscriptions.paystack_authorization_code)
        """,
        values={
            "user_id": user_id,
            "plan_id": plan_id,
            "status": status.value,
            "current_period_start": current_period_start,
            "current_period_end": current_period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "created_at": now,
            "updated_at": now,
            "paystack_customer_code": paystack_customer_code,
            "paystack_subscription_code": paystack_subscription_code,
            "paystack_email_token": paystack_email_token,
            "paystack_authorization_code": paystack_authorization_code,
        },
    )

    await db.execute(
        query="""
            UPDATE user_settings
            SET subscription_tier = :tier,
                subscription_status = :status,
                subscription_expires_at = :expires_at,
                updated_at = :updated_at
            WHERE user_id = :user_id
        """,
        values={
            "tier": tier,
            "status": status.value,
            "expires_at": current_period_end,
            "updated_at": now,
            "user_id": user_id,
        },
    )

    logger.info(
        "subscription_record_updated",
        user_id=user_id,
        status=status.value,
        tier=tier,
        plan_id=plan_id,
    )


# =============================================================================
# CHECKOUT SESSION
# =============================================================================

async def create_checkout_session(
    user_id: str,
    price_id: Optional[str] = None,
    amount_kobo: Optional[int] = None,
    email: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> CheckoutSessionResult:
    """
    Initialize a Paystack hosted checkout transaction for a subscription plan.

    `price_id` is treated as the Paystack plan code to minimize API churn in the
    rest of the application. For testing, `amount_kobo` can be sent as a fallback
    when plan-level amount validation fails.
    """

    _ensure_paystack_configured()

    if not email:
        raise PaymentServiceError("Customer email is required for Paystack checkout")

    if not price_id and not amount_kobo:
        raise PaymentServiceError("Provide either a plan code or amount_kobo")

    reference = f"paystack_{user_id[:12]}_{int(time.time())}"
    callback_url = success_url or PAYSTACK_SUCCESS_URL

    log = logger.bind(user_id=user_id, plan_code=price_id, amount_kobo=amount_kobo, reference=reference)
    log.info("initializing_paystack_checkout")

    payload: Dict[str, Any] = {
        "email": email,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {
            "user_id": user_id,
            "provider": "paystack",
            "plan_id": price_id,
            "cancel_url": cancel_url or PAYSTACK_CANCEL_URL,
        },
    }

    if price_id:
        payload["plan"] = price_id

    if amount_kobo:
        payload["amount"] = int(amount_kobo)

    data = await _paystack_request(
        "POST",
        "/transaction/initialize",
        payload=payload,
    )

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=price_id,
        status=SubscriptionStatus.INACTIVE,
    )

    return CheckoutSessionResult(
        session_id=data.get("reference") or reference,
        checkout_url=data.get("authorization_url", ""),
    )


# =============================================================================
# WEBHOOK HANDLING
# =============================================================================

def verify_webhook_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Verify a Paystack webhook signature and return the parsed event body."""

    if not PAYSTACK_WEBHOOK_SECRET:
        raise WebhookVerificationError(
            "PAYSTACK_WEBHOOK_SECRET (or PAYSTACK_SECRET_KEY) is not configured."
        )

    expected = hmac.new(
        PAYSTACK_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()

    if not sig_header or not hmac.compare_digest(expected, sig_header):
        raise WebhookVerificationError("Invalid Paystack webhook signature")

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise WebhookVerificationError("Invalid webhook payload") from exc

    logger.debug("webhook_signature_verified", event_type=event.get("event"))
    return event


async def handle_webhook(payload: bytes, sig_header: str) -> Tuple[bool, str]:
    """Process a Paystack webhook event."""

    event = verify_webhook_signature(payload, sig_header)
    event_type = event.get("event", "")
    event_data = event.get("data") or {}

    log = logger.bind(event_type=event_type)
    log.info("processing_paystack_webhook")

    try:
        if event_type == "charge.success":
            await _handle_charge_success(event_data)
            return True, "Charge processed successfully"

        if event_type == "subscription.create":
            await _handle_subscription_created(event_data)
            return True, "Subscription created"

        if event_type == "subscription.not_renew":
            await _handle_subscription_non_renewing(event_data)
            return True, "Subscription marked as non-renewing"

        if event_type == "subscription.disable":
            await _handle_subscription_disabled(event_data)
            return True, "Subscription disabled"

        if event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(event_data)
            return True, "Payment failure recorded"

        log.debug("webhook_event_ignored", reason="unhandled_event_type")
        return True, f"Event type {event_type} ignored"

    except Exception as exc:
        log.error("webhook_processing_failed", error=str(exc), exc_info=True)
        raise PaymentServiceError(f"Webhook processing failed: {exc}") from exc


async def _handle_charge_success(data: Dict[str, Any]) -> None:
    metadata = _extract_metadata(data)
    user_id = metadata.get("user_id") or await _find_user_id_by_customer_code(_extract_customer_code(data))
    if not user_id:
        logger.warning("charge_success_missing_user_id")
        return

    existing = await _get_existing_subscription_row(user_id)
    plan_code = _extract_plan_code(data) or metadata.get("plan_id") or (existing or {}).get("plan_id")

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=plan_code,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=_parse_timestamp(data.get("paid_at") or data.get("paidAt") or data.get("created_at")),
        current_period_end=_parse_timestamp(data.get("next_payment_date")),
        paystack_customer_code=_extract_customer_code(data) or (existing or {}).get("paystack_customer_code"),
        paystack_subscription_code=_extract_subscription_code(data) or (existing or {}).get("paystack_subscription_code"),
        paystack_email_token=data.get("email_token") or (existing or {}).get("paystack_email_token"),
        paystack_authorization_code=_extract_authorization_code(data) or (existing or {}).get("paystack_authorization_code"),
    )


async def _handle_subscription_created(data: Dict[str, Any]) -> None:
    customer_code = _extract_customer_code(data)
    user_id = _extract_metadata(data).get("user_id") or await _find_user_id_by_customer_code(customer_code)
    if not user_id:
        logger.warning("subscription_created_missing_user_id", customer_code=customer_code)
        return

    existing = await _get_existing_subscription_row(user_id)

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=_extract_plan_code(data) or (existing or {}).get("plan_id"),
        status=_normalize_status(data.get("status") or "active"),
        current_period_start=_parse_timestamp(data.get("created_at") or data.get("createdAt")),
        current_period_end=_parse_timestamp(data.get("next_payment_date")),
        paystack_customer_code=customer_code or (existing or {}).get("paystack_customer_code"),
        paystack_subscription_code=_extract_subscription_code(data) or (existing or {}).get("paystack_subscription_code"),
        paystack_email_token=data.get("email_token") or (existing or {}).get("paystack_email_token"),
        paystack_authorization_code=_extract_authorization_code(data) or (existing or {}).get("paystack_authorization_code"),
    )


async def _handle_subscription_non_renewing(data: Dict[str, Any]) -> None:
    subscription_code = _extract_subscription_code(data)
    user_id = _extract_metadata(data).get("user_id") or await _find_user_id_by_subscription_code(subscription_code)
    if not user_id:
        logger.warning("subscription_non_renewing_missing_user_id", subscription_code=subscription_code)
        return

    existing = await _get_existing_subscription_row(user_id)

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=_extract_plan_code(data) or (existing or {}).get("plan_id"),
        status=SubscriptionStatus.NON_RENEWING,
        current_period_end=_parse_timestamp(data.get("next_payment_date")) or (existing or {}).get("current_period_end"),
        paystack_customer_code=_extract_customer_code(data) or (existing or {}).get("paystack_customer_code"),
        paystack_subscription_code=subscription_code or (existing or {}).get("paystack_subscription_code"),
        paystack_email_token=data.get("email_token") or (existing or {}).get("paystack_email_token"),
        paystack_authorization_code=_extract_authorization_code(data) or (existing or {}).get("paystack_authorization_code"),
    )


async def _handle_subscription_disabled(data: Dict[str, Any]) -> None:
    subscription_code = _extract_subscription_code(data)
    user_id = _extract_metadata(data).get("user_id") or await _find_user_id_by_subscription_code(subscription_code)
    if not user_id:
        logger.warning("subscription_disabled_missing_user_id", subscription_code=subscription_code)
        return

    existing = await _get_existing_subscription_row(user_id)

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=_extract_plan_code(data) or (existing or {}).get("plan_id"),
        status=SubscriptionStatus.DISABLED,
        current_period_end=_parse_timestamp(data.get("next_payment_date")) or (existing or {}).get("current_period_end"),
        paystack_customer_code=_extract_customer_code(data) or (existing or {}).get("paystack_customer_code"),
        paystack_subscription_code=subscription_code or (existing or {}).get("paystack_subscription_code"),
        paystack_email_token=data.get("email_token") or (existing or {}).get("paystack_email_token"),
        paystack_authorization_code=_extract_authorization_code(data) or (existing or {}).get("paystack_authorization_code"),
    )


async def _handle_invoice_payment_failed(data: Dict[str, Any]) -> None:
    subscription_code = _extract_subscription_code(data)
    user_id = _extract_metadata(data).get("user_id") or await _find_user_id_by_subscription_code(subscription_code)
    if not user_id:
        logger.warning("invoice_payment_failed_missing_user_id", subscription_code=subscription_code)
        return

    existing = await _get_existing_subscription_row(user_id)

    await _upsert_subscription_record(
        user_id=user_id,
        plan_id=_extract_plan_code(data) or (existing or {}).get("plan_id"),
        status=SubscriptionStatus.ATTENTION,
        current_period_end=_parse_timestamp(data.get("next_payment_date")) or (existing or {}).get("current_period_end"),
        paystack_customer_code=_extract_customer_code(data) or (existing or {}).get("paystack_customer_code"),
        paystack_subscription_code=subscription_code or (existing or {}).get("paystack_subscription_code"),
        paystack_email_token=data.get("email_token") or (existing or {}).get("paystack_email_token"),
        paystack_authorization_code=_extract_authorization_code(data) or (existing or {}).get("paystack_authorization_code"),
    )


# =============================================================================
# SUBSCRIPTION QUERIES
# =============================================================================

async def get_subscription_info(user_id: str) -> Optional[SubscriptionInfo]:
    """Get subscription information for a user."""

    db = get_database()
    result = await db.fetch_one(
        query="""
            SELECT user_id,
                   paystack_customer_code,
                   paystack_subscription_code,
                   plan_id,
                   status,
                   current_period_end,
                   cancel_at_period_end
            FROM subscriptions
            WHERE user_id = :user_id
        """,
        values={"user_id": user_id},
    )

    if not result:
        return None

    row = dict(result)

    return SubscriptionInfo(
        user_id=row["user_id"],
        paystack_customer_code=row.get("paystack_customer_code"),
        paystack_subscription_code=row.get("paystack_subscription_code"),
        plan_id=row.get("plan_id"),
        status=_normalize_status(row.get("status")),
        current_period_end=row.get("current_period_end"),
        cancel_at_period_end=bool(row.get("cancel_at_period_end")),
    )


async def create_billing_portal_session(user_id: str, return_url: str) -> str:
    """
    Return a custom subscription-management URL if configured.

    Paystack does not offer a hosted billing portal. If you want a
    self-service management experience, provide `PAYSTACK_MANAGE_SUBSCRIPTION_URL`
    pointing to your own page or flow.
    """

    if PAYSTACK_MANAGE_SUBSCRIPTION_URL:
        return PAYSTACK_MANAGE_SUBSCRIPTION_URL.format(
            user_id=user_id,
            return_url=return_url,
        )

    raise SubscriptionManagementUnavailableError(
        "Paystack does not provide a hosted billing portal. Configure a custom "
        "PAYSTACK_MANAGE_SUBSCRIPTION_URL or manage subscriptions manually."
    )
