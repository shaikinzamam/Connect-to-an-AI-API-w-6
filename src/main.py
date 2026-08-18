"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.routes.triage import router as triage_router

load_dotenv()

app = FastAPI(title="AI Support Message Triage API", version="1.0.0")
app.include_router(triage_router)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return the assignment's required 400 response with field names."""

    errors = []
    for error in exc.errors():
        location = [str(item) for item in error.get("loc", ()) if item != "body"]
        errors.append(
            {
                "field": ".".join(location) or "request_body",
                "message": error.get("msg", "Invalid value"),
            }
        )
    return JSONResponse(status_code=400, content={"detail": "Invalid request", "errors": errors})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
