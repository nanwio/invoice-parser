"""
JWT token generator for the invoice processing API.

Usage examples:
    python scripts/generate_token.py --username cliente_acme
    python scripts/generate_token.py --username admin1 --role admin --days 30
    python scripts/generate_token.py --username pruebas --days 1

The secret key is read from the SECRET_KEY (or JWT_SECRET_KEY) environment
variable, matching the value used by the API to validate incoming tokens.
"""
import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import jwt
from dotenv import load_dotenv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a JWT access token for a client of the invoice processing API.",
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Identifier of the client the token is issued to.",
    )
    parser.add_argument(
        "--role",
        default="user",
        choices=["user", "admin"],
        help="Role granted to the client (default: user).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Validity period of the token in days (default: 30).",
    )
    return parser


def main() -> int:
    load_dotenv()

    args = build_parser().parse_args()

    secret_key = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        print(
            "ERROR: SECRET_KEY (or JWT_SECRET_KEY) is not configured. "
            "Set it in your environment or .env file before generating tokens.",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(timezone.utc)
    payload = {
        "subject": {"username": args.username, "role": args.role},
        "exp": now + timedelta(days=args.days),
        "iat": now,
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")

    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
