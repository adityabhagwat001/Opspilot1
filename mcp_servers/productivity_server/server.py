"""
OpsPilot Custom FastMCP Server: Email & Calendar Integration.
Connects to authorized Email (Gmail / Enterprise Mail Store) and Calendar (Google Calendar / Enterprise Calendar).
Enforces mandatory human approval before any draft, send, or calendar mutation.
Returns standardized, typed envelopes for all tools.
"""

import os
import sys
import hmac
import hashlib
import json
import uuid
import datetime
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Boolean, select

# Add parent directory to path so imports work seamlessly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import asyncio
import logging
from envelope import create_success_envelope, create_error_envelope
from dotenv import load_dotenv

logger = logging.getLogger("opspilot.productivity_server")

mcp = FastMCP("opspilot-productivity-server")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DEFAULT_DB_FILE = os.path.join(PROJECT_ROOT, "operational_data.db").replace("\\", "/")
MAIL_DB_URL = os.getenv("OPS_DATABASE_URL", f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}")
APPROVAL_SECRET = os.getenv("OPSPILOT_APPROVAL_SECRET", "opspilot_trusted_approval_boundary_secret_key_32chars")

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

class ProductivityBase(DeclarativeBase):
    pass

class EmailMessage(ProductivityBase):
    __tablename__ = "productivity_emails"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sender: Mapped[str] = mapped_column(String(150), nullable=False)
    recipient: Mapped[str] = mapped_column(String(150), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_unread: Mapped[bool] = mapped_column(Boolean, default=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class CalendarEvent(ProductivityBase):
    __tablename__ = "productivity_calendar_events"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    attendees: Mapped[str] = mapped_column(Text, default="[]")  # JSON encoded list of emails
    calendar_id: Mapped[str] = mapped_column(String(50), default="primary")
    status: Mapped[str] = mapped_column(String(30), default="confirmed")  # confirmed, cancelled
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)

class ProductivityStore:
    def __init__(self, db_url: str):
        if "postgresql" in db_url:
            from sqlalchemy.pool import NullPool
            self.engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
        else:
            self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db(self):
        """
        Explicit administrative initialization & seeding for operational mailbox and calendar.
        Called only by administrative scripts, never by read tools.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(ProductivityBase.metadata.create_all)
        
        async with self.session_factory() as session:
            count = await session.scalar(select(EmailMessage).limit(1))
            if count is None:
                await self._seed(session)

    async def _seed(self, session: AsyncSession):
        now = utc_now()
        emails = [
            EmailMessage(
                id="MSG-801",
                sender="alert-manager@enterprise.internal",
                recipient="ops-oncall@enterprise.internal",
                subject="CRITICAL: Deployment pipeline stalled on canary stage",
                body="Automated canary deployment for auth-service v2.4.1 failed health checks with 4.2% error rate. Rollback requested.",
                is_unread=True,
                is_draft=False,
                thread_id="TH-101",
                created_at=now - datetime.timedelta(hours=2)
            ),
            EmailMessage(
                id="MSG-802",
                sender="cto@enterprise.internal",
                recipient="engineering-leads@enterprise.internal",
                subject="Operational incident update and postmortem review",
                body="Please ensure postmortem reviews for today's auth service latency spike are scheduled before Friday 4 PM.",
                is_unread=True,
                is_draft=False,
                thread_id="TH-102",
                created_at=now - datetime.timedelta(hours=5)
            ),
            EmailMessage(
                id="MSG-803",
                sender="infra-bot@enterprise.internal",
                recipient="ops@enterprise.internal",
                subject="Scheduled maintenance window: Redis Cluster Upgrade",
                body="Notice: Secondary Redis node upgrade scheduled for Sunday at 02:00 UTC. Expected downtime under 60 seconds.",
                is_unread=False,
                is_draft=False,
                thread_id="TH-103",
                created_at=now - datetime.timedelta(days=1)
            ),
        ]
        session.add_all(emails)

        tomorrow = now.date() + datetime.timedelta(days=1)
        events = [
            CalendarEvent(
                id="EVT-901",
                title="Daily Operations Standup",
                description="Daily operational review of active incidents and CI/CD status.",
                start_time=datetime.datetime.combine(tomorrow, datetime.time(10, 0)),
                end_time=datetime.datetime.combine(tomorrow, datetime.time(10, 30)),
                attendees=json.dumps(["ops-team@enterprise.internal", "oncall@enterprise.internal"]),
                calendar_id="primary",
                status="confirmed"
            ),
            CalendarEvent(
                id="EVT-902",
                title="Incident INC-101 Postmortem Review",
                description="Root cause analysis of auth service connection pool exhaustion.",
                start_time=datetime.datetime.combine(tomorrow, datetime.time(15, 0)),
                end_time=datetime.datetime.combine(tomorrow, datetime.time(16, 0)),
                attendees=json.dumps(["aditya.b@enterprise.internal", "cto@enterprise.internal", "eng-leads@enterprise.internal"]),
                calendar_id="primary",
                status="confirmed"
            ),
        ]
        session.add_all(events)
        await session.commit()

prod_store = ProductivityStore(MAIL_DB_URL)

def compute_action_hash(tool_name: str, arguments: Dict[str, Any]) -> str:
    clean_args = {k: v for k, v in arguments.items() if k not in ("approval_token", "workspace_id")}
    canonical = f"{tool_name}:{json.dumps(clean_args, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def verify_approval_token(
    tool_name: str,
    args: Dict[str, Any],
    approval_token: str,
    workspace_id: str = "default-ops"
) -> bool:
    """
    Verifies that the approval token was cryptographically signed by the OpsPilot backend
    for this EXACT tool, workspace, and CANONICAL arguments payload.
    The LLM cannot forge this token.
    """
    if not approval_token:
        return False
    try:
        parts = approval_token.split(".")
        if len(parts) != 4:
            return False
        nonce, timestamp_str, token_action_hash, signature = parts
        
        token_time = int(timestamp_str)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if now - token_time > 900 or token_time - now > 60:
            return False

        actual_hash = compute_action_hash(tool_name, args)
        if not hmac.compare_digest(actual_hash, token_action_hash):
            # Check with None values stripped in case caller omitted optional parameters
            stripped_args = {k: v for k, v in args.items() if v is not None}
            stripped_hash = compute_action_hash(tool_name, stripped_args)
            if not hmac.compare_digest(stripped_hash, token_action_hash):
                return False

        canonical = f"{tool_name}:{workspace_id}:{nonce}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False

# =========================================================================
# EMAIL READ TOOLS (Authorized operational queries - ZERO DDL / Seeding)
# =========================================================================

@mcp.tool()
async def list_messages(max_results: int = 10, include_drafts: bool = False) -> Dict[str, Any]:
    """
    List operational emails in the inbox.
    """
    try:
        async with prod_store.session_factory() as session:
            query = select(EmailMessage)
            if not include_drafts:
                query = query.where(EmailMessage.is_draft == False)
            query = query.order_by(EmailMessage.created_at.desc()).limit(max_results)
            result = await session.execute(query)
            messages = result.scalars().all()

            cleaned = [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "recipient": m.recipient,
                    "subject": m.subject,
                    "snippet": m.body[:150] + ("..." if len(m.body) > 150 else ""),
                    "is_unread": m.is_unread,
                    "is_draft": m.is_draft,
                    "created_at": m.created_at.isoformat() + "Z"
                }
                for m in messages
            ]
            return create_success_envelope(
                system="email",
                tool="list_messages",
                data={"count": len(cleaned), "messages": cleaned},
                resource_ids_urls=[m["id"] for m in cleaned]
            )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="list_messages",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def search_messages(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search operational emails matching keywords in subject or body.
    """
    try:
        async with prod_store.session_factory() as session:
            q_str = f"%{query.lower()}%"
            stmt = (
                select(EmailMessage)
                .where((EmailMessage.subject.ilike(q_str)) | (EmailMessage.body.ilike(q_str)))
                .order_by(EmailMessage.created_at.desc())
                .limit(max_results)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()

            cleaned = [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "subject": m.subject,
                    "snippet": m.body[:200],
                    "is_unread": m.is_unread,
                    "created_at": m.created_at.isoformat() + "Z"
                }
                for m in messages
            ]
            return create_success_envelope(
                system="email",
                tool="search_messages",
                data={"search_query": query, "count": len(cleaned), "matches": cleaned},
                resource_ids_urls=[m["id"] for m in cleaned]
            )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="search_messages",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_message(message_id: str) -> Dict[str, Any]:
    """
    Get the complete content, sender, recipient, and body of an email message.
    """
    try:
        async with prod_store.session_factory() as session:
            stmt = select(EmailMessage).where(EmailMessage.id == message_id)
            result = await session.execute(stmt)
            m = result.scalar_one_or_none()
            if not m:
                return create_error_envelope(
                    system="email",
                    tool="get_message",
                    error=f"Message '{message_id}' not found",
                    error_category="NOT_FOUND"
                )
            
            cleaned = {
                "id": m.id,
                "sender": m.sender,
                "recipient": m.recipient,
                "subject": m.subject,
                "body": m.body,
                "is_unread": m.is_unread,
                "is_draft": m.is_draft,
                "thread_id": m.thread_id,
                "created_at": m.created_at.isoformat() + "Z"
            }
            return create_success_envelope(
                system="email",
                tool="get_message",
                data=cleaned,
                resource_ids_urls=[m.id]
            )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="get_message",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_unread_messages(max_results: int = 10) -> Dict[str, Any]:
    """
    Get all currently unread operational messages.
    """
    try:
        async with prod_store.session_factory() as session:
            stmt = (
                select(EmailMessage)
                .where(EmailMessage.is_unread == True, EmailMessage.is_draft == False)
                .order_by(EmailMessage.created_at.desc())
                .limit(max_results)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()

            cleaned = [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "subject": m.subject,
                    "snippet": m.body[:150],
                    "created_at": m.created_at.isoformat() + "Z"
                }
                for m in messages
            ]
            return create_success_envelope(
                system="email",
                tool="get_unread_messages",
                data={"unread_count": len(cleaned), "messages": cleaned},
                resource_ids_urls=[m["id"] for m in cleaned]
            )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="get_unread_messages",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

# =========================================================================
# EMAIL WRITE TOOLS (MANDATORY APPROVAL GATE)
# =========================================================================

@mcp.tool()
async def create_email_draft(
    recipient: str,
    subject: str,
    body: str,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Create an email draft in the mailbox.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {"recipient": recipient, "subject": subject, "body": body}

    if not verify_approval_token("create_email_draft", call_args, approval_token):
        return create_error_envelope(
            system="email",
            tool="create_email_draft",
            error="WRITE_APPROVAL_REQUIRED: Creating an email draft requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    try:
        draft_id = f"DFT-{uuid.uuid4().hex[:6].upper()}"
        draft = EmailMessage(
            id=draft_id,
            sender="ops-assistant@enterprise.internal",
            recipient=recipient,
            subject=subject,
            body=body,
            is_unread=False,
            is_draft=True,
            created_at=utc_now()
        )

        async with prod_store.session_factory() as session:
            session.add(draft)
            await session.commit()

        return create_success_envelope(
            system="email",
            tool="create_email_draft",
            is_write=True,
            data={
                "status": "SUCCESS",
                "action": "created_email_draft",
                "draft_id": draft_id,
                "recipient": recipient,
                "subject": subject,
                "created_at": utc_now().isoformat() + "Z"
            },
            resource_ids_urls=[draft_id]
        )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="create_email_draft",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

@mcp.tool()
async def send_email(
    recipient: str,
    subject: str,
    body: str,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [CRITICAL WRITE OPERATION - REQUIRES APPROVAL]
    Actually send an email message to a recipient.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {"recipient": recipient, "subject": subject, "body": body}

    if not verify_approval_token("send_email", call_args, approval_token):
        return create_error_envelope(
            system="email",
            tool="send_email",
            error="WRITE_APPROVAL_REQUIRED: Sending external emails modifies company communications and requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    try:
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_from = os.getenv("SMTP_FROM_EMAIL", smtp_user or "ops-assistant@enterprise.internal").strip()

        # If live SMTP credentials are configured, dispatch real email
        is_live_smtp = bool(smtp_user and smtp_pass and not os.getenv("PYTEST_CURRENT_TEST"))
        if is_live_smtp:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            def _dispatch():
                msg = MIMEMultipart()
                msg["From"] = smtp_from
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.send_message(msg)

            await asyncio.to_thread(_dispatch)
            logger.info(f"Live SMTP email sent successfully to {recipient} via {smtp_host}")

        msg_id = f"MSG-{uuid.uuid4().hex[:6].upper()}"
        sent_msg = EmailMessage(
            id=msg_id,
            sender=smtp_from if is_live_smtp else "ops-assistant@enterprise.internal",
            recipient=recipient,
            subject=subject,
            body=body,
            is_unread=False,
            is_draft=False,
            created_at=utc_now()
        )

        async with prod_store.session_factory() as session:
            session.add(sent_msg)
            await session.commit()

        return create_success_envelope(
            system="email",
            tool="send_email",
            is_write=True,
            data={
                "status": "SUCCESS",
                "action": "sent_email",
                "message_id": msg_id,
                "recipient": recipient,
                "subject": subject,
                "sent_at": utc_now().isoformat() + "Z",
                "delivered": True,
                "delivery_mode": "live_smtp" if is_live_smtp else "operational_store"
            },
            resource_ids_urls=[msg_id]
        )
    except Exception as ex:
        return create_error_envelope(
            system="email",
            tool="send_email",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

# =========================================================================
# CALENDAR READ TOOLS
# =========================================================================

@mcp.tool()
async def list_calendars() -> Dict[str, Any]:
    """
    List connected calendars (primary operations, oncall rotation, release calendar).
    """
    calendars = [
        {"id": "primary", "summary": "Operations Team Primary Calendar", "timeZone": "UTC", "primary": True},
        {"id": "oncall-rotation", "summary": "DevOps On-Call Schedule", "timeZone": "UTC", "primary": False},
        {"id": "releases", "summary": "Production Release Calendar", "timeZone": "UTC", "primary": False}
    ]
    return create_success_envelope(
        system="calendar",
        tool="list_calendars",
        data={"calendars": calendars},
        resource_ids_urls=[c["id"] for c in calendars]
    )

@mcp.tool()
async def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None
) -> Dict[str, Any]:
    """
    List upcoming calendar events.
    """
    try:
        async with prod_store.session_factory() as session:
            query = select(CalendarEvent).where(
                CalendarEvent.calendar_id == calendar_id,
                CalendarEvent.status != "cancelled"
            ).order_by(CalendarEvent.start_time.asc())
            
            result = await session.execute(query)
            events = result.scalars().all()

            cleaned = [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "start_time": e.start_time.isoformat() + "Z",
                    "end_time": e.end_time.isoformat() + "Z",
                    "attendees": json.loads(e.attendees or "[]"),
                    "status": e.status
                }
                for e in events
            ]
            return create_success_envelope(
                system="calendar",
                tool="list_events",
                data={"calendar_id": calendar_id, "count": len(cleaned), "events": cleaned},
                resource_ids_urls=[e["id"] for e in cleaned]
            )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="list_events",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def get_event(event_id: str) -> Dict[str, Any]:
    """
    Get details of a specific calendar event.
    """
    try:
        async with prod_store.session_factory() as session:
            stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
            result = await session.execute(stmt)
            e = result.scalar_one_or_none()
            if not e:
                return create_error_envelope(
                    system="calendar",
                    tool="get_event",
                    error=f"Event '{event_id}' not found",
                    error_category="NOT_FOUND"
                )

            cleaned = {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "start_time": e.start_time.isoformat() + "Z",
                "end_time": e.end_time.isoformat() + "Z",
                "attendees": json.loads(e.attendees or "[]"),
                "status": e.status
            }
            return create_success_envelope(
                system="calendar",
                tool="get_event",
                data=cleaned,
                resource_ids_urls=[e.id]
            )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="get_event",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

@mcp.tool()
async def check_availability(start_time: str, end_time: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """
    Check availability and conflicts for a proposed meeting slot.
    Format: ISO-8601 strings, e.g. '2026-10-14T15:00:00Z'
    """
    try:
        req_start = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
        req_end = datetime.datetime.fromisoformat(end_time.replace("Z", ""))
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="check_availability",
            error=f"Invalid datetime format: {str(ex)}. Expected ISO-8601.",
            error_category="VALIDATION"
        )

    try:
        async with prod_store.session_factory() as session:
            stmt = select(CalendarEvent).where(
                CalendarEvent.calendar_id == calendar_id,
                CalendarEvent.status != "cancelled",
                CalendarEvent.start_time < req_end,
                CalendarEvent.end_time > req_start
            )
            res = await session.execute(stmt)
            conflicts = res.scalars().all()

            is_available = len(conflicts) == 0
            conflict_data = [
                {"id": c.id, "title": c.title, "start": c.start_time.isoformat() + "Z", "end": c.end_time.isoformat() + "Z"}
                for c in conflicts
            ]
            return create_success_envelope(
                system="calendar",
                tool="check_availability",
                data={
                    "requested_slot": {"start": start_time, "end": end_time},
                    "is_available": is_available,
                    "conflict_count": len(conflicts),
                    "conflicts": conflict_data
                },
                resource_ids_urls=[c["id"] for c in conflict_data]
            )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="check_availability",
            error=str(ex),
            error_category="PROVIDER_ERROR"
        )

# =========================================================================
# CALENDAR WRITE TOOLS (MANDATORY APPROVAL GATE)
# =========================================================================

@mcp.tool()
async def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    calendar_id: str = "primary",
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Schedule a meeting / event on the calendar.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "attendees": attendees if attendees is not None else [],
        "description": description,
        "calendar_id": calendar_id
    }

    if not verify_approval_token("create_calendar_event", call_args, approval_token):
        return create_error_envelope(
            system="calendar",
            tool="create_calendar_event",
            error="WRITE_APPROVAL_REQUIRED: Scheduling a new calendar meeting requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    try:
        start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
        end_dt = datetime.datetime.fromisoformat(end_time.replace("Z", ""))
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="create_calendar_event",
            error=f"Invalid start or end datetime format: {str(ex)}",
            error_category="VALIDATION",
            is_write=True
        )

    try:
        event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        new_event = CalendarEvent(
            id=event_id,
            title=title,
            description=description,
            start_time=start_dt,
            end_time=end_dt,
            attendees=json.dumps(attendees or []),
            calendar_id=calendar_id,
            status="confirmed",
            created_at=utc_now()
        )

        async with prod_store.session_factory() as session:
            session.add(new_event)
            await session.commit()

        return create_success_envelope(
            system="calendar",
            tool="create_calendar_event",
            is_write=True,
            data={
                "status": "SUCCESS",
                "action": "created_calendar_event",
                "event_id": event_id,
                "title": title,
                "start_time": start_dt.isoformat() + "Z",
                "end_time": end_dt.isoformat() + "Z",
                "attendees": attendees or [],
                "calendar_id": calendar_id
            },
            resource_ids_urls=[event_id]
        )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="create_calendar_event",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

@mcp.tool()
async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Update an existing calendar event.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {"event_id": event_id, "title": title, "start_time": start_time, "end_time": end_time}

    if not verify_approval_token("update_calendar_event", call_args, approval_token):
        return create_error_envelope(
            system="calendar",
            tool="update_calendar_event",
            error="WRITE_APPROVAL_REQUIRED: Updating calendar events requires human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    try:
        async with prod_store.session_factory() as session:
            stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
            res = await session.execute(stmt)
            event = res.scalar_one_or_none()
            if not event:
                return create_error_envelope(
                    system="calendar",
                    tool="update_calendar_event",
                    error=f"Event '{event_id}' not found",
                    error_category="NOT_FOUND",
                    is_write=True
                )

            if title: event.title = title
            if start_time: event.start_time = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
            if end_time: event.end_time = datetime.datetime.fromisoformat(end_time.replace("Z", ""))

            await session.commit()

        return create_success_envelope(
            system="calendar",
            tool="update_calendar_event",
            is_write=True,
            data={
                "status": "SUCCESS",
                "action": "updated_calendar_event",
                "event_id": event_id
            },
            resource_ids_urls=[event_id]
        )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="update_calendar_event",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

@mcp.tool()
async def cancel_calendar_event(
    event_id: str,
    approval_token: str = ""
) -> Dict[str, Any]:
    """
    [WRITE OPERATION - REQUIRES APPROVAL]
    Cancel a scheduled calendar event.
    Requires cryptographic approval_token from the OpsPilot backend approval boundary.
    """
    call_args = {"event_id": event_id}

    if not verify_approval_token("cancel_calendar_event", call_args, approval_token):
        return create_error_envelope(
            system="calendar",
            tool="cancel_calendar_event",
            error="WRITE_APPROVAL_REQUIRED: Cancelling an event requires explicit human approval.",
            error_category="APPROVAL_REQUIRED",
            is_write=True
        )

    try:
        async with prod_store.session_factory() as session:
            stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
            res = await session.execute(stmt)
            event = res.scalar_one_or_none()
            if not event:
                return create_error_envelope(
                    system="calendar",
                    tool="cancel_calendar_event",
                    error=f"Event '{event_id}' not found",
                    error_category="NOT_FOUND",
                    is_write=True
                )

            event.status = "cancelled"
            await session.commit()

        return create_success_envelope(
            system="calendar",
            tool="cancel_calendar_event",
            is_write=True,
            data={
                "status": "SUCCESS",
                "action": "cancelled_calendar_event",
                "event_id": event_id,
                "status_state": "cancelled"
            },
            resource_ids_urls=[event_id]
        )
    except Exception as ex:
        return create_error_envelope(
            system="calendar",
            tool="cancel_calendar_event",
            error=str(ex),
            error_category="PROVIDER_ERROR",
            is_write=True
        )

if __name__ == "__main__":
    mcp.run()
