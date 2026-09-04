"""Create a user. There is no public signup — this LE-facing tool is admin-only.

    uv run python scripts/create_user.py --email a@x.gov --name "A" --role officer --password '…'
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from app.db.engine import create_all  # noqa: E402
from app.domain.account_store import SqlAccountStore  # noqa: E402
from app.domain.accounts import AccountService, Role  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(prog="create_user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    parser.add_argument("--unit", default=None)
    parser.add_argument("--password", default=None, help="omit to be prompted")
    args = parser.parse_args()

    password = args.password or getpass.getpass("password: ")
    create_all()
    account = AccountService(SqlAccountStore()).create_user(
        email=args.email,
        full_name=args.name,
        role=Role(args.role),
        password=password,
        unit=args.unit,
    )
    print(f"created {account.email} ({account.role.value}) id={account.id}")


if __name__ == "__main__":
    main()
