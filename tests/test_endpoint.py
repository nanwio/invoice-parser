"""Integration tests for the HTTP endpoints (status codes and validation)."""
import io
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


TEST_SECRET = "test-secret-key-1234567890abcdef"


def _generate_token(username: str = "tester", role: str = "user", days: int = 30) -> str:
    """Generate a JWT token using the test secret."""
    now = datetime.now(timezone.utc)
    payload = {
        "subject": {"username": username, "role": role},
        "exp": now + timedelta(days=days),
        "iat": now,
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture(scope="module", autouse=True)
def _set_secret_env():
    """Force the secret key before the app's settings are imported."""
    previous = os.environ.get("SECRET_KEY")
    os.environ["SECRET_KEY"] = TEST_SECRET
    # Reload settings so the new SECRET_KEY is picked up.
    import importlib
    from src.config import settings as settings_module
    importlib.reload(settings_module)
    yield
    if previous is None:
        os.environ.pop("SECRET_KEY", None)
    else:
        os.environ["SECRET_KEY"] = previous


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """Build a minimal FastAPI app without the heavy PaddleOCR lifespan."""
    # Importing the routers must happen AFTER SECRET_KEY is set.
    from src.api.health import router as health_router
    from src.api.endpoints.upload_and_parse import router as invoice_router

    test_app = FastAPI()
    test_app.include_router(health_router, tags=["Health"])
    test_app.include_router(invoice_router, prefix="/api", tags=["Invoices"])
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_generate_token()}"}


# -------------------------------------------------------------------
# Health endpoint
# -------------------------------------------------------------------

def test_health_endpoint_returns_ok(client: TestClient):
    """RUF-49/RUF-51: /health returns 200 with status, service, version."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "invoice_processing_api"
    assert "version" in body


def test_health_endpoint_does_not_require_auth(client: TestClient):
    """RUF-50: /health is reachable without an Authorization header."""
    response = client.get("/health")
    assert response.status_code == 200


# -------------------------------------------------------------------
# Authentication (CU-04, RUF-40 to RUF-48)
# -------------------------------------------------------------------

def test_upload_without_token_returns_401(client: TestClient):
    """RUF-48: A request without Authorization header is rejected with 401."""
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("dummy.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_with_invalid_token_returns_401(client: TestClient):
    """RUF-48: An invalid JWT token is rejected with 401."""
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("dummy.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_upload_with_expired_token_returns_401(client: TestClient):
    """RUF-43.4: An expired token is rejected with 401."""
    expired = _generate_token(days=-1)
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("dummy.pdf", b"%PDF-1.4", "application/pdf")},
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


# -------------------------------------------------------------------
# Input validation (RUF-03, RUNF-03)
# -------------------------------------------------------------------

def test_upload_unsupported_format_returns_400(client: TestClient, auth_headers):
    """RUF-03: A file with an unsupported MIME type is rejected with 400."""
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("dummy.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Supported types" in response.json()["detail"]


def test_upload_empty_file_returns_400(client: TestClient, auth_headers):
    """RUF-03: An empty file (zero bytes) is rejected with 400."""
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("dummy.pdf", b"", "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_oversized_file_returns_400(client: TestClient, auth_headers):
    """RUNF-03: A file larger than MAX_FILE_SIZE_MB (10 MB) is rejected with 400."""
    oversized = b"%PDF-1.4" + b"A" * (11 * 1024 * 1024)
    response = client.post(
        "/api/v1/invoice/parse",
        files={"file": ("big.pdf", oversized, "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "MB" in response.json()["detail"]


# -------------------------------------------------------------------
# Cache hit path (RUF-37, RUF-38)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_returns_cached_result_when_available(
    client: TestClient, auth_headers, valid_invoice
):
    """RUF-38: A PDF whose hash is in the cache returns the cached invoice."""
    with patch(
        "src.api.endpoints.upload_and_parse.invoice_cache.get_cached_invoice",
        return_value=valid_invoice,
    ):
        response = client.post(
            "/api/v1/invoice/parse",
            files={"file": ("cached.pdf", b"%PDF-1.4 minimal content", "application/pdf")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["processing_results"]["processing_method"] == "cache_hit"
    assert body["invoice"]["parties"]["vendor"]["name"] == valid_invoice.parties.vendor.name
    assert "job_id" in body
