from __future__ import annotations

from fastapi import FastAPI, HTTPException

from fintech_login import FintechLoginWorkflow, LoginResult, OtpRequest, OtpVerification
from infrai_sms import InfraiError, InfraiSmsClient


app = FastAPI(title="Fintech SMS login")


def workflow() -> FintechLoginWorkflow:
    return FintechLoginWorkflow(InfraiSmsClient())


@app.post("/login/code", response_model=LoginResult)
def send_login_code(command: OtpRequest) -> LoginResult:
    try:
        return workflow().send_code(command)
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/login/verify", response_model=LoginResult)
def verify_login_code(command: OtpVerification) -> LoginResult:
    try:
        return workflow().verify_code(command)
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

