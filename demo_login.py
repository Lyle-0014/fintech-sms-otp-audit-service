from __future__ import annotations

import json
import os

from fintech_login import FintechLoginWorkflow, OtpRequest, PaymentEvent
from infrai_sms import InfraiSmsClient


phone = os.environ.get("DEMO_PHONE")
if not phone:
    raise SystemExit("DEMO_PHONE is required")

command = OtpRequest(
    request_id="demo-payment-login-001",
    phone=phone,
    payment=PaymentEvent(
        payment_id="pay_demo_001",
        amount_minor=12_500,
        currency="USD",
        failed_attempts_24h=0,
    ),
)
result = FintechLoginWorkflow(InfraiSmsClient()).send_code(command)
print(json.dumps(result.model_dump(mode="json"), indent=2))

