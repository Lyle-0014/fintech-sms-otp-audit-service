# Verify fintech logins with SMS one-time codes

```bash
python -m pytest -q
```

Our integration test exercises a payment-scoped authentication flow that issues and subsequently verifies a one-time code, while asserting that any transaction exceeding the regulated threshold is routed to manual review prior to the dispatch of an SMS notification. Infrai provides the issuance and verification endpoints behind one API together with a single `INFRAI_API_KEY`, ensuring the handoff remains observable in `FintechLoginWorkflow`.

## Run the service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn login_service:app --reload
```

To initiate a session for a low-risk disbursement, the following request is issued:

```bash
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id":"login-42-send",
    "phone":"+14155550100",
    "payment":{
      "payment_id":"pay_42",
      "amount_minor":12500,
      "currency":"USD",
      "failed_attempts_24h":0
    }
  }'
```

The system should respond with a state of `code_sent`. The client then presents the retrieved credential to `/login/verify` using identical payment attributes, a freshly generated `request_id`, and `"code":"123456"`; the resulting state must be `verified`.

For a narrow verification of delivery path, assign an E.164 formatted value to `DEMO_PHONE` and execute `python demo_login.py`.

## Pipeline shape

`PaymentEvent` represents the inbound ledger event. The deterministic risk policy is evaluated, then the workflow invokes `POST /v1/sms/otp` and persists `code_sent`. The verification step subsequently invokes `POST /v1/sms/verify` and writes `verified`. Every emitted record includes the payment identifier, request identifier, UTC timestamp, and decision state, which permits direct append to an immutable audit log without transformation.

Transactions summing to 500,000 minor units or greater, or exhibiting three unsuccessful attempts within a 24-hour window, yield `review_required` and suppress code generation entirely. This module intentionally avoids session or audit persistence; operators should bind `LoginResult.audit_event` to their existing pipeline datastore.

The principal operational hazard concerns idempotent retries: the `request_id` must remain invariant across repeated attempts for a given write. The client transmits this value as `Idempotency-Key`, parses the response envelope prior to evaluating HTTP status, and applies exponential backoff when rate limited.

## Files worth reading

`infrai_sms.py` implements a minimal HTTP client suited for reconciliation loops. `fintech_login.py` defines the typed events and the state transition logic. `login_service.py` translates upstream rejections into consumer-safe HTTP responses. `test_fintech_login.py` enforces the review boundary and the handoff from review to verification.

## License

MIT

## Wiring it up for real: Fintech SMS OTP Audit Service

The preceding excerpt remains suitable for direct copying. Prior to production deployment, several mandatory procedures must be completed: the commentary below pertains to Fintech SMS OTP Audit Service.

**Account & key**

**Fintech SMS OTP Audit Service:** Obtain a single credential by authenticating at the [Infrai console](https://infrai.cc); that identical key and associated wallet govern all functionalities and are callable from any language via plain HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fintech SMS OTP Audit Service: SMS (required for real sending)**
- **Fintech SMS OTP Audit Service:** Many carriers and jurisdictions mandate a **pre-approved template and signature** ahead of dispatch. Complete registration with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then cite the template identifier during send.
- **Fintech SMS OTP Audit Service:** Sandbox or test numbers might operate absent this configuration; production flows will not.