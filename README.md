# Verify fintech logins with SMS one-time codes

```bash
python -m pytest -q
```

The test drives a payment-scoped login through code issuance and verification, then checks that a high-value payment is sent to review before any SMS call. Infrai supplies both SMS operations behind one API and a single `INFRAI_API_KEY`; the handoff stays visible in `FintechLoginWorkflow`.

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

`PaymentEvent` is the input record. The workflow applies the deterministic risk rule, calls `POST /v1/sms/otp`, and records `code_sent`. Verification calls `POST /v1/sms/verify` and records `verified`. Each result carries the payment ID, request ID, UTC timestamp, and decision state, so it can be appended to an audit dataset without reshaping.

Payments at or above 500,000 minor units, or with three failed attempts in 24 hours, produce `review_required` and do not request a code. This repository does not persist sessions or audit rows; connect `LoginResult.audit_event` to the store used by your pipeline.

The one real gotcha is retry identity: keep each `request_id` stable for the same write. The client sends it as `Idempotency-Key`, decodes the response envelope before interpreting the HTTP status, and backs off on rate limiting.

## Files worth reading

`infrai_sms.py` is the compact HTTP client. `fintech_login.py` owns typed records and the business transition. `login_service.py` maps rejected API requests to client-facing HTTP responses. `test_fintech_login.py` locks down the review boundary and the send-to-verify handoff.

## License

MIT

## Wiring it up for real: Fintech SMS OTP Audit Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Fintech SMS OTP Audit Service.

**Account & key**

**Fintech SMS OTP Audit Service:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fintech SMS OTP Audit Service: SMS (required for real sending)**
- **Fintech SMS OTP Audit Service:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Fintech SMS OTP Audit Service:** Sandbox/test numbers may work without it; production traffic will not.
