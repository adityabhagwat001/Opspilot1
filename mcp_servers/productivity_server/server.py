"""
OpsPilot Custom FastMCP Server: Email & Calendar Integration.
Connects to authorized Email (Gmail / Enterprise Mail Store) and Calendar (Google Calendar / Enterprise Calendar).
Enforces mandatory human approval before any draft, send, or calendar mutation.
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
from sqlalchemy import String, Text, DateTime, Boolean, select, insert

mcp = FastMCP("opspilot-productivity-server")

APPROVAL_SECRET = os.getenv("OPSPILOT_APPROVAL_SECRET", "opspilot_trusted_approval_boundary_secret_key_32chars")
MAIL_DB_URL = os.getenv("OPS_DATABASE_URL", "sqlite+aiosqlite:///./operational_data.db")

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

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
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db(self):
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

def verify_approval_token(tool_name: str, args: Dict[str, Any], approval_token: str) -> bool:
    if not approval_token:
        return False
    try:
        parts = approval_token.split(".")
        if len(parts) != 3:
            return False
        timestamp_str, token_action_hash, signature = parts
        token_time = int(timestamp_str)
        now = int(utc_now().timestamp())
        if now - token_time > 900 or token_time - now > 60:
            return False

        canonical = f"{tool_name}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False

# =========================================================================
# EMAIL READ TOOLS
# =========================================================================

@mcp.tool()
async def list_messages(max_results: int = 10, include_drafts: bool = False) -> Dict[str, Any]:
    """
    List operational emails in the inbox.
    """
    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        query = select(EmailMessage)
        if not include_drafts:
            query = query.where(EmailMessage.is_draft == False)
        query = query.order_by(EmailMessage.created_at.desc()).limit(max_results)
        result = await session.execute(query)
        messages = result.scalars().all()

        return {
            "count": len(messages),
            "messages": [
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
        }

@mcp.tool()
async def search_messages(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search operational emails matching keywords in subject or body.
    """
    await prod_store.init_db()
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

        return {
            "search_query": query,
            "count": len(messages),
            "matches": [
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
        }

@mcp.tool()
async def get_message(message_id: str) -> Dict[str, Any]:
    """
    Get the complete content, sender, recipient, and body of an email message.
    """
    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        stmt = select(EmailMessage).where(EmailMessage.id == message_id)
        result = await session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return {"error": f"Message '{message_id}' not found"}
        
        return {
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

@mcp.tool()
async def get_unread_messages(max_results: int = 10) -> Dict[str, Any]:
    """
    Get all currently unread operational messages.
    """
    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        stmt = (
            select(EmailMessage)
            .where(EmailMessage.is_unread == True, EmailMessage.is_draft == False)
            .order_by(EmailMessage.created_at.desc())
            .limit(max_results)
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()

        return {
            "unread_count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "subject": m.subject,
                    "snippet": m.body[:150],
                    "created_at": m.created_at.isoformat() + "Z"
                }
                for m in messages
            ]
        }

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
        return {
            "status": "APPROVAL_REQUIRED",
            "error": "WRITE_APPROVAL_REQUIRED: Creating an email draft requires explicit human approval.",
            "tool_name": "create_email_draft",
            "proposed_parameters": call_args
        }

    await prod_store.init_db()
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

    return {
        "status": "SUCCESS",
        "action": "created_email_draft",
        "draft_id": draft_id,
        "recipient": recipient,
        "subject": subject,
        "created_at": utc_now().isoformat() + "Z"
    }

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
        return {
            "status": "APPROVAL_REQUIRED",
            "error": "WRITE_APPROVAL_REQUIRED: Sending external emails modifies company communications and requires explicit human approval.",
            "tool_name": "send_email",
            "proposed_parameters": call_args
        }

    await prod_store.init_db()
    msg_id = f"MSG-{uuid.uuid4().hex[:6].upper()}"
    sent_msg = EmailMessage(
        id=msg_id,
        sender="ops-assistant@enterprise.internal",
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

    return {
        "status": "SUCCESS",
        "action": "sent_email",
        "message_id": msg_id,
        "recipient": recipient,
        "subject": subject,
        "sent_at": utc_now().isoformat() + "Z",
        "delivered": True
    }

# =========================================================================
# CALENDAR READ TOOLS
# =========================================================================

@mcp.tool()
async def list_calendars() -> Dict[str, Any]:
    """
    List connected calendars (primary operations, oncall rotation, release calendar).
    """
    return {
        "calendars": [
            {"id": "primary", "summary": "Operations Team Primary Calendar", "timeZone": "UTC", "primary": True},
            {"id": "oncall-rotation", "summary": "DevOps On-Call Schedule", "timeZone": "UTC", "primary": False},
            {"id": "releases", "summary": "Production Release Calendar", "timeZone": "UTC", "primary": False}
        ]
    }

@mcp.tool()
async def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None
) -> Dict[str, Any]:
    """
    List upcoming calendar events.
    """
    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        query = select(CalendarEvent).where(
            CalendarEvent.calendar_id == calendar_id,
            CalendarEvent.status != "cancelled"
        ).order_by(CalendarEvent.start_time.asc())
        
        result = await session.execute(query)
        events = result.scalars().all()

        return {
            "calendar_id": calendar_id,
            "count": len(events),
            "events": [
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
        }

@mcp.tool()
async def get_event(event_id: str) -> Dict[str, Any]:
    """
    Get details of a specific calendar event.
    """
    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
        result = await session.execute(stmt)
        e = result.scalar_one_or_none()
        if not e:
            return {"error": f"Event '{event_id}' not found"}

        return {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "start_time": e.start_time.isoformat() + "Z",
            "end_time": e.end_time.isoformat() + "Z",
            "attendees": json.loads(e.attendees or "[]"),
            "status": e.status
        }

@mcp.tool()
async def check_availability(start_time: str, end_time: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """
    Check availability and conflicts for a proposed meeting slot.
    Format: ISO-8601 strings, e.g. '2026-10-14T15:00:00'
    """
    await prod_store.init_db()
    try:
        req_start = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
        req_end = datetime.datetime.fromisoformat(end_time.replace("Z", ""))
    except Exception as ex:
        return {"error": f"Invalid datetime format: {str(ex)}. Expected ISO-8601."}

    async with prod_store.session_factory() as session:
        # Check overlaps
        stmt = select(CalendarEvent).where(
            CalendarEvent.calendar_id == calendar_id,
            CalendarEvent.status != "cancelled",
            CalendarEvent.start_time < req_end,
            CalendarEvent.end_time > req_start
        )
        res = await session.execute(stmt)
        conflicts = res.scalars().all()

        is_available = len(conflicts) == 0
        return {
            "requested_slot": {"start": start_time, "end": end_time},
            "is_available": is_available,
            "conflict_count": len(conflicts),
            "conflicts": [
                {"id": c.id, "title": c.title, "start": c.start_time.isoformat(), "end": c.end_time.isoformat()}
                for c in conflicts
            ]
        }

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
        "attendees": attendees or [],
        "description": description or "",
        "calendar_id": calendar_id
    }

    if not verify_approval_token("create_calendar_event", call_args, approval_token):
        return {
            "status": "APPROVAL_REQUIRED",
            "error": "WRITE_APPROVAL_REQUIRED: Scheduling a new calendar meeting requires explicit human approval.",
            "tool_name": "create_calendar_event",
            "proposed_parameters": call_args
        }

    try:
        start_dt = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
        end_dt = datetime.datetime.fromisoformat(end_time.replace("Z", ""))
    except Exception as ex:
        return {"status": "ERROR", "error": f"Invalid start or end datetime format: {str(ex)}"}

    await prod_store.init_db()
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

    return {
        "status": "SUCCESS",
        "action": "created_calendar_event",
        "event_id": event_id,
        "title": title,
        "start_time": start_dt.isoformat() + "Z",
        "end_time": end_dt.isoformat() + "Z",
        "attendees": attendees or [],
        "calendar_id": calendar_id
    }

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
        return {
            "status": "APPROVAL_REQUIRED",
            "error": "WRITE_APPROVAL_REQUIRED: Updating calendar events requires human approval.",
            "tool_name": "update_calendar_event",
            "proposed_parameters": call_args
        }

    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
        res = await session.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            return {"status": "ERROR", "error": f"Event '{event_id}' not found"}

        if title: event.title = title
        if start_time: event.start_time = datetime.datetime.fromisoformat(start_time.replace("Z", ""))
        if end_time: event.end_time = datetime.datetime.fromisoformat(end_time.replace("Z", ""))

        await session.commit()

    return {
        "status": "SUCCESS",
        "action": "updated_calendar_event",
        "event_id": event_id
    }

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
        return {
            "status": "APPROVAL_REQUIRED",
            "error": "WRITE_APPROVAL_REQUIRED: Cancelling an event requires explicit human approval.",
            "tool_name": "cancel_calendar_event",
            "proposed_parameters": call_args
        }

    await prod_store.init_db()
    async with prod_store.session_factory() as session:
        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
        res = await session.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            return {"status": "ERROR", "error": f"Event '{event_id}' not found"}

        event.status = "cancelled"
        await session.commit()

    return {
        "status": "SUCCESS",
        "action": "cancelled_calendar_event",
        "event_id": event_id,
        "status_state": "cancelled"
    }

if __name__ == "__main__":
    mcp.run()
