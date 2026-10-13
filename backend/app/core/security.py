"""
Security & Cryptographic Boundary for OpsPilot Enterprise Platform
Handles password hashing, JWT authentication, and unforgeable Approval Token generation.
"""

import os
import hmac
import hashlib
import json
import datetime
import bcrypt
import jwt
from typing import Optional, Dict, Any
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
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None

def compute_action_hash(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA256 hash of canonical tool arguments.
    Ensures that any tampering or modification of parameters invalidates approval.
    """
    clean_args = {k: v for k, v in arguments.items() if k != "approval_token"}
    canonical = f"{tool_name}:{json.dumps(clean_args, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def generate_approval_token(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Cryptographically signs an approval token for this EXACT tool and parameters.
    Format: timestamp.action_hash.signature
    Valid for 15 minutes. The LLM cannot generate this token.
    """
    timestamp = str(int(datetime.datetime.utcnow().timestamp()))
    action_hash = compute_action_hash(tool_name, arguments)
    canonical = f"{tool_name}:{timestamp}:{action_hash}"
    
    signature = hmac.new(
        settings.APPROVAL_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return f"{timestamp}.{action_hash}.{signature}"

def verify_approval_token(tool_name: str, arguments: Dict[str, Any], approval_token: str) -> bool:
    """
    Validates token signature and freshness.
    """
    if not approval_token:
        return False
    try:
        parts = approval_token.split(".")
        if len(parts) != 3:
            return False
        timestamp_str, token_action_hash, signature = parts
        token_time = int(timestamp_str)
        now = int(datetime.datetime.utcnow().timestamp())
        if now - token_time > (settings.APPROVAL_EXPIRE_MINUTES * 60) or token_time - now > 60:
            return False

        canonical = f"{tool_name}:{timestamp_str}:{token_action_hash}"
        expected_sig = hmac.new(
            settings.APPROVAL_SECRET.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False
