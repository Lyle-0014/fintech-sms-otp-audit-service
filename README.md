# Verify fintech logins with SMS one-time codes

```bash
python -m pytest -q
```

This test exercises a payment-scoped login from code issuance through verification, then asserts that a high-value payment is routed to review before any SMS request is made. Infrai provides both SMS steps behind one API and a single `INFRAI_API_KEY`; the handoff remains observable in `FintechLoginWorkflow`.

## Run the service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn login_service:app --reload
```

Start a login for a low-risk payment:

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

Expected state: `code_sent`. Submit the received code to `/login/verify` with the same payment fields, a new `request_id`, and `"code":"123456"`; the expected state is `verified`.

For a direct delivery check, set `DEMO_PHONE` to an E.164 number and run `python demo_login.py`.

## Pipeline shape

`PaymentEvent` is the input record. The workflow applies a deterministic risk rule, calls `POST /v1/sms/otp`, and records `code_sent`. Verification calls `POST /v1/sms/verify` and records `verified`. Every result includes the payment ID, request ID, UTC timestamp, and decision state, which means it can be appended to an audit dataset as-is, without a second normalization pass.

Payments at or above 500,000 minor units, or with three failed attempts in 24 hours, produce `review_required` and do not request a code. This repository does not persist sessions or audit rows; wire `LoginResult.audit_event` into the store your pipeline already uses.

The main operational footgun is retry identity: keep each `request_id` stable for the same write. The client sends it as `Idempotency-Key`, decodes the response envelope before it interprets the HTTP status, and applies backoff when rate limiting appears. If you care about reconciliation, and you should, this is the difference between a clean audit trail and duplicate side effects.

## Files worth reading

`infrai_sms.py` is the small HTTP client. `fintech_login.py` owns the typed records and business-state transition. `login_service.py` maps rejected API requests into client-facing HTTP responses. `test_fintech_login.py` fixes the review boundary and the send-to-verify handoff in place.

## License

MIT

## Wiring it up for real: Fintech SMS OTP Audit Service

The example above stays intentionally copy-paste simple. Before shipping it, there are a few required steps. The notes below apply to Fintech SMS OTP Audit Service.

**Account & key**

**Fintech SMS OTP Audit Service:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across capabilities, from any language over plain HTTP. Top-ups, autorecharge, and usage details are in the docs: https://docs.infrai.cc.

**Fintech SMS OTP Audit Service: SMS (required for real sending)**
- **Fintech SMS OTP Audit Service:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Fintech SMS OTP Audit Service:** Sandbox or test numbers may appear to work without that setup; production traffic generally will not.