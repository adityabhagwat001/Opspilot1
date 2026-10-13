"""
Security & Cryptographic Boundary for OpsPilot Enterprise Platform
Handles password hashing, JWT authentication, and unforgeable Approval Token generation with single-use nonce consumption.
"""

import os
import uuid
import hmac
import hashlib
import json
import datetime
import bcrypt
import jwt
from typing import Optional, Dict, Any, Callable
from app.core.config import settings

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None

def compute_action_hash(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA256 hash of canonical tool arguments.
    Excludes ephemeral tokens, strictly sorts keys.
    Any tampering or modification of parameters invalidates approval.
    """
    clean_args = {k: v for k, v in arguments.items() if k not in ("approval_token", "workspace_id")}
    canonical = f"{tool_name}:{json.dumps(clean_args, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def generate_approval_token(
    tool_name: str,
    arguments: Dict[str, Any],
    workspace_id: str = "default-ops",
    nonce: Optional[str] = None
) -> str:
    """
    Cryptographically signs an approval token for this EXACT tool, workspace, and parameters.
    Format: nonce.timestamp.action_hash.signature
    Valid for 15 minutes. The LLM cannot generate this token.
    """
    token_nonce = nonce or str(uuid.uuid4())
    timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))
    action_hash = compute_action_hash(tool_name, arguments)
    canonical = f"{tool_name}:{workspace_id}:{token_nonce}:{timestamp}:{action_hash}"
    
    signature = hmac.new(
        settings.APPROVAL_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return f"{token_nonce}.{timestamp}.{action_hash}.{signature}"

def verify_approval_token(
    tool_name: str,
    arguments: Dict[str, Any],
    approval_token: str,
    workspace_id: str = "default-ops",
    consumed_nonces: Optional[set] = None
) -> bool:
    """
    Validates token signature, freshness, parameter integrity, and prevents replay attacks.
    """
    if not approval_token:
        return False
    try:
        parts = approval_token.split(".")
        if len(parts) != 4:
            return False
        nonce, timestamp_str, token_action_hash, signature = parts

        # 1. Check expiration (15 minutes)
        token_time = int(timestamp_str)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        if now - token_time > (settings.APPROVAL_EXPIRE_MINUTES * 60) or token_time - now > 60:
            return False

        # 2. Check parameter hash integrity: actual arguments MUST match token hash!
        actual_hash = compute_action_hash(tool_name, arguments)
        if not hmac.compare_digest(actual_hash, token_action_hash):
            return False

        # 3. Check HMAC signature with tool, workspace, nonce, timestamp, and hash
        canonical = f"{tool_name}:{workspace_id}:{nonce}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            settings.APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return False

        # 4. Check single-use consumption if tracking set provided
        if consumed_nonces is not None:
            if nonce in consumed_nonces:
                return False  # Replay attack blocked!
            consumed_nonces.add(nonce)

        return True
    except Exception:
        return False
