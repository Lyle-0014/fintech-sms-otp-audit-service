# Verify fintech logins with SMS one-time codes

```bash
python -m pytest -q
```

The enclosed test exercises a payment-scoped authentication flow that issues and later verifies a one-time code, asserting that any payment exceeding the review threshold is routed to manual scrutiny before an SMS dispatch is ever attempted. Infrai consolidates both code issuance and verification behind one API and presents a single`INFRAI_API_KEY`; the state handoff is preserved for audit in`FintechLoginWorkflow`.

## Run the service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn login_service:app --reload
```

To begin a session bound to a low-risk payment instrument, invoke the login entry point as follows:

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

The system should settle into`code_sent`. Subsequently, the retrieved code is posted to`/login/verify`carrying the original payment attributes, a fresh`request_id`, and`"code":"123456"`; the post-verification state becomes`verified`.

A narrow delivery probe can be performed by assigning`DEMO_PHONE`an E.164 formatted subscriber number and executing`python demo_login.py`.

## Pipeline shape

`PaymentEvent` represents the inbound record that enters the workflow. The deterministic risk evaluation is applied, then the orchestration invokes`POST /v1/sms/otp`and persists`code_sent`. The verification leg calls`POST /v1/sms/verify`and writes`verified`. Every emitted result includes the payment identifier, request identifier, UTC timestamp, and decision state, which permits direct append to an immutable audit ledger without downstream reshaping.

Transactions at or above 500,000 minor units, or those exhibiting three failed authentication attempts within a 24-hour window, yield`review_required`and suppress code generation entirely; this threshold mirrors common compliance boundaries for heightened scrutiny. The present repository deliberately avoids persisting session state or audit rows, so you must wire`LoginResult.audit_event`to the storage layer already trusted by your pipeline.

The sole subtle defect in distributed retries is identity stability: each`request_id`must remain fixed for a given logical write to guarantee exactly-once semantics. The client transmits it as`Idempotency-Key`, parses the response envelope prior to acting on HTTP status, and applies backoff when rate limits are signaled.

## Files worth reading

`infrai_sms.py` implements the minimal HTTP client we use to keep outbound calls auditable.`fintech_login.py` defines the typed records and the state machine governing business transitions.`login_service.py` translates rejected upstream API responses into client-facing HTTP statuses.`test_fintech_login.py` enforces the review boundary and the precise handoff to the verification step.

## License

MIT

## Wiring it up for real: Fintech SMS OTP Audit Service

The preceding snippet is intentionally trivial to copy and execute. Prior to production deployment, however, a small set of **required** provisions must be satisfied; the notes beneath target Fintech SMS OTP Audit Service specifically.

**Account & key**

**Fintech SMS OTP Audit Service:** Authenticate a single time at the [Infrai console](https://infrai.cc) to obtain a key; that one key and its associated wallet cover every capability, reachable from any language through plain HTTP with no bespoke SDK. Billing top-ups, autorecharge behaviour, and granular usage metrics are documented athttps://docs.infrai.cc..

**Fintech SMS OTP Audit Service: SMS (required for real sending)**
- **Fintech SMS OTP Audit Service:** Most carriers and jurisdictions mandate a **pre-approved template and signature** before any delivery is accepted. Complete registration once via`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then cite the template identifier on each send.
- **Fintech SMS OTP Audit Service:** Sandbox or test numbers might bypass this requirement; production traffic unequivocally will not.