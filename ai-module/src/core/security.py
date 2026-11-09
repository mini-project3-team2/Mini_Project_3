"""Shared authentication dependency for Backend-to-AI routes."""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status


async def require_internal_token(
    request: Request,
    tokens: Annotated[list[str] | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    """Require exactly one matching token; never echo or log credentials."""
    if tokens is None or len(tokens) != 1 or not tokens[0].isascii():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    expected = request.app.state.settings.ai_internal_token
    if not secrets.compare_digest(tokens[0], expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
