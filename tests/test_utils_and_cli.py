"""Tests for utility modules and command-line tools."""
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone

import jwt
import pytest

from src.utils.document_utils import document_utils


# -------------------------------------------------------------------
# DocumentUtilities: SHA-256 hashing (RUF-35)
# -------------------------------------------------------------------

def test_sha256_hash_matches_hashlib_reference():
    """The hash returned by the utility must match the standard hashlib computation."""
    payload = b"%PDF-1.4 dummy invoice content"
    expected = hashlib.sha256(payload).hexdigest()

    assert document_utils.calculate_file_hash(payload) == expected


def test_sha256_hash_is_deterministic():
    """The same input must produce the same hash on different invocations."""
    payload = b"deterministic-payload"
    first = document_utils.calculate_file_hash(payload)
    second = document_utils.calculate_file_hash(payload)

    assert first == second


def test_sha256_hash_changes_for_different_inputs():
    """Different inputs must produce different hashes."""
    h1 = document_utils.calculate_file_hash(b"content-A")
    h2 = document_utils.calculate_file_hash(b"content-B")

    assert h1 != h2


def test_sha256_hash_has_expected_length():
    """SHA-256 produces a 64-character hexadecimal digest."""
    h = document_utils.calculate_file_hash(b"x")
    assert len(h) == 64
    int(h, 16)  # Must be valid hexadecimal.


# -------------------------------------------------------------------
# CLI tool: scripts/generate_token.py (RUF-45 a RUF-47)
# -------------------------------------------------------------------

SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "generate_token.py",
)


def _run_cli(env: dict, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Execute the token generation script with the given environment and arguments."""
    return subprocess.run(
        [sys.executable, SCRIPT_PATH, *args],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_generates_valid_token_with_required_arg():
    """RUF-45/RUF-46: The CLI emits a valid JWT when --username is provided."""
    env = os.environ.copy()
    env["SECRET_KEY"] = "cli-test-secret"

    result = _run_cli(env, "--username", "cliente_test")

    assert result.returncode == 0
    token = result.stdout.strip()
    decoded = jwt.decode(token, "cli-test-secret", algorithms=["HS256"])
    assert decoded["subject"]["username"] == "cliente_test"
    assert decoded["subject"]["role"] == "user"  # Default role.


def test_cli_respects_role_and_days_arguments():
    """RUF-46.2/RUF-46.3: --role and --days are reflected in the token payload."""
    env = os.environ.copy()
    env["SECRET_KEY"] = "cli-test-secret"

    result = _run_cli(env, "--username", "admin1", "--role", "admin", "--days", "7")

    assert result.returncode == 0
    decoded = jwt.decode(result.stdout.strip(), "cli-test-secret", algorithms=["HS256"])
    assert decoded["subject"]["role"] == "admin"

    now = datetime.now(timezone.utc).timestamp()
    expected_exp = now + 7 * 24 * 3600
    assert abs(decoded["exp"] - expected_exp) < 60  # Within 1 minute.


def test_cli_fails_when_secret_key_missing(monkeypatch, capsys):
    """RUF-47: Without SECRET_KEY in the environment, the script exits with error.

    The script's ``main()`` function is invoked directly, monkeypatching
    ``load_dotenv`` so the project's ``.env`` is not loaded.
    """
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["generate_token.py", "--username", "cualquiera"])

    # Import the script as a module after manipulating sys.argv and patching dotenv.
    import importlib.util
    spec = importlib.util.spec_from_file_location("generate_token", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    spec.loader.exec_module(module)

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "SECRET_KEY" in captured.err
