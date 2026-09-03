from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    payment_id: str = Field(min_length=1)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    failed_attempts_24h: int = Field(ge=0)


class OtpRequest(BaseModel):
    request_id: str = Field(min_length=1)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    payment: PaymentEvent


class OtpVerification(BaseModel):
    request_id: str = Field(min_length=1)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    code: str = Field(pattern=r"^\d{4,8}$")
    payment: PaymentEvent


class LoginState(str, Enum):
    CODE_SENT = "code_sent"
    VERIFIED = "verified"
    REVIEW_REQUIRED = "review_required"


class LoginResult(BaseModel):
    request_id: str
    payment_id: str
    state: LoginState
    audit_event: dict[str, Any]


class SmsOtpGateway(Protocol):
    def request_otp(self, phone: str, *, request_id: str) -> Mapping[str, Any]:
        pass

    def verify_otp(
        self, phone: str, code: str, *, request_id: str
    ) -> Mapping[str, Any]:
        pass


class FintechLoginWorkflow:
    def __init__(self, sms: SmsOtpGateway, *, review_threshold_minor: int = 500_000):
        self.sms = sms
        self.review_threshold_minor = review_threshold_minor

    def _requires_review(self, payment: PaymentEvent) -> bool:
        return (
            payment.amount_minor >= self.review_threshold_minor
            or payment.failed_attempts_24h >= 3
        )

    def _result(self, request_id: str, payment: PaymentEvent, state: LoginState) -> LoginResult:
        return LoginResult(
            request_id=request_id,
            payment_id=payment.payment_id,
            state=state,
            audit_event={
                "event": "fintech_login_decision",
                "request_id": request_id,
                "payment_id": payment.payment_id,
                "state": state.value,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def send_code(self, command: OtpRequest) -> LoginResult:
        if self._requires_review(command.payment):
            return self._result(command.request_id, command.payment, LoginState.REVIEW_REQUIRED)
        self.sms.request_otp(command.phone, request_id=command.request_id)
        return self._result(command.request_id, command.payment, LoginState.CODE_SENT)

    def verify_code(self, command: OtpVerification) -> LoginResult:
        if self._requires_review(command.payment):
            return self._result(command.request_id, command.payment, LoginState.REVIEW_REQUIRED)
        self.sms.verify_otp(command.phone, command.code, request_id=command.request_id)
        return self._result(command.request_id, command.payment, LoginState.VERIFIED)
