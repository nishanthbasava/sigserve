import hashlib
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sigserve.db import get_session
from sigserve.models import ApiKey


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def require_api_key(
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    api_key = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_key(x_api_key)))
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
