"""Auth Port — authentication handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class AuthResult:
    ok: bool
    status: int = 200
    message: str = ""


@runtime_checkable
class AuthHandler(Protocol):
    """Port: request authentication."""

    async def authenticate(self, request: Any) -> AuthResult: ...
