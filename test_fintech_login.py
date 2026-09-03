from typing import Any, Mapping

from fintech_login import (
    FintechLoginWorkflow,
    LoginState,
    OtpRequest,
    OtpVerification,
    PaymentEvent,
)


class RecordingSms:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def request_otp(self, phone: str, *, request_id: str) -> Mapping[str, Any]:
        self.calls.append(("otp", request_id))
        return {"id": "sms_1"}

    def verify_otp(self, phone: str, code: str, *, request_id: str) -> Mapping[str, Any]:
        self.calls.append(("verify", request_id))
        return {"verified": True}


def payment(amount_minor: int = 25_00, failures: int = 0) -> PaymentEvent:
    return PaymentEvent(
        payment_id="pay_42",
        amount_minor=amount_minor,
        currency="USD",
        failed_attempts_24h=failures,
    )


def test_low_risk_payment_crosses_send_and_verify_handoff() -> None:
    sms = RecordingSms()
    flow = FintechLoginWorkflow(sms)

    sent = flow.send_code(
        OtpRequest(request_id="login-42-send", phone="+14155550100", payment=payment())
    )
    verified = flow.verify_code(
        OtpVerification(
            request_id="login-42-verify",
            phone="+14155550100",
            code="123456",
            payment=payment(),
        )
    )

    assert sent.state is LoginState.CODE_SENT
    assert verified.state is LoginState.VERIFIED
    assert sms.calls == [("otp", "login-42-send"), ("verify", "login-42-verify")]


def test_risky_payment_is_routed_to_review_before_sms() -> None:
    sms = RecordingSms()
    flow = FintechLoginWorkflow(sms)

    result = flow.send_code(
        OtpRequest(
            request_id="login-risk-7",
            phone="+14155550100",
            payment=payment(amount_minor=900_000),
        )
    )

    assert result.state is LoginState.REVIEW_REQUIRED
    assert result.audit_event["payment_id"] == "pay_42"
    assert sms.calls == []

