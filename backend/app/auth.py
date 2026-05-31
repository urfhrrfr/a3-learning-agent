from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import Header, HTTPException

from .agents import now
from .storage import load_records, save_record


JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRE_MINUTES = 60 * 24 * 7


def registration_mode() -> str:
    mode = os.getenv("AUTH_REGISTRATION_MODE", "single").strip().lower()
    return mode if mode in {"single", "open", "disabled"} else "single"


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret:
        return secret
    return "a3-dev-secret-change-before-deploy"


def jwt_expire_minutes() -> int:
    raw = os.getenv("JWT_EXPIRE_MINUTES", str(DEFAULT_EXPIRE_MINUTES)).strip()
    try:
        return max(5, int(raw))
    except ValueError:
        return DEFAULT_EXPIRE_MINUTES


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str) -> str:
    digest = hmac.new(jwt_secret().encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64_encode(digest)


def _user_record_id(username: str) -> str:
    return f"user_{username.lower()}"


def list_users() -> list[dict]:
    return sorted(load_records("user"), key=lambda item: item.get("created_at", ""))


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
        "created_at": user.get("created_at", ""),
        "last_login_at": user.get("last_login_at", ""),
    }


def auth_status() -> dict:
    return {
        "registration_mode": registration_mode(),
        "has_user": bool(list_users()),
    }


def find_user_by_username(username: str) -> dict | None:
    normalized = username.strip().lower()
    return next((user for user in list_users() if user.get("username", "").lower() == normalized), None)


def find_user_by_id(user_id: str) -> dict | None:
    return next((user for user in list_users() if user.get("id") == user_id), None)


def create_user(username: str, password: str, display_name: str = "") -> dict:
    normalized_username = username.strip().lower()
    if len(normalized_username) < 3:
        raise HTTPException(status_code=400, detail="username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")

    mode = registration_mode()
    existing_users = list_users()
    if mode == "disabled":
        raise HTTPException(status_code=403, detail="registration is disabled")
    if mode == "single" and existing_users:
        raise HTTPException(status_code=403, detail="registration is closed after the first user")
    if find_user_by_username(normalized_username):
        raise HTTPException(status_code=409, detail="username already exists")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = {
        "id": f"user_{uuid4().hex[:12]}",
        "username": normalized_username,
        "password_hash": password_hash,
        "display_name": display_name.strip() or normalized_username,
        "created_at": now(),
        "last_login_at": "",
    }
    save_record("user", _user_record_id(normalized_username), user)
    return user


def authenticate_user(username: str, password: str) -> dict | None:
    user = find_user_by_username(username)
    if not user:
        return None
    password_hash = str(user.get("password_hash", "")).encode("utf-8")
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash):
        return None
    user["last_login_at"] = now()
    save_record("user", _user_record_id(user["username"]), user)
    return user


def create_access_token(user: dict) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=jwt_expire_minutes())
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": int(expires_at.timestamp()),
    }
    encoded_header = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{encoded_header}.{encoded_payload}"
    return f"{message}.{_sign(message)}"


def verify_access_token(token: str) -> dict:
    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    message = f"{encoded_header}.{encoded_payload}"
    if not hmac.compare_digest(_sign(message), signature):
        raise HTTPException(status_code=401, detail="invalid token")

    try:
        payload = json.loads(_b64_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=401, detail="token expired")

    user = find_user_by_id(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    return verify_access_token(authorization.split(" ", 1)[1].strip())
