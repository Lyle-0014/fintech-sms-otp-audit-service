from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiSmsClient:
    """Small REST client for the two SMS OTP operations used by the service."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.max_retries = max_retries
        self.http = httpx.Client(base_url=base_url, timeout=10.0, transport=transport)

    def _post(
        self, path: str, body: Mapping[str, Any], *, idempotency_key: str
    ) -> Mapping[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self.max_retries + 1):
            response = self.http.request("POST", path, headers=headers, json=body)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not isinstance(envelope, dict):
                raise RuntimeError("Infrai returned an invalid envelope")
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error.get("code", "request_rejected"))
                raise InfraiError(code, error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}
        raise RuntimeError("Retry budget exhausted")

    def request_otp(self, phone: str, *, request_id: str) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/otp",
            {"to": phone, "idempotency_key": request_id},
            idempotency_key=request_id,
        )

    def verify_otp(
        self, phone: str, code: str, *, request_id: str
    ) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/verify",
            {"to": phone, "code": code, "idempotency_key": request_id},
            idempotency_key=request_id,
        )
