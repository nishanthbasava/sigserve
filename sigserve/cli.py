"""Admin CLI. Mint an API key with:

    python -m sigserve.cli create-key --name <label>
"""

import argparse
import secrets

from sigserve.auth import hash_key
from sigserve.db import open_session
from sigserve.models import ApiKey


def create_key(name: str) -> str:
    plaintext = f"sgs_{secrets.token_urlsafe(32)}"
    with open_session() as session:
        session.add(ApiKey(name=name, key_hash=hash_key(plaintext)))
        session.commit()
    return plaintext


def main() -> None:
    parser = argparse.ArgumentParser(prog="sigserve")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-key", help="Mint a new API key")
    create.add_argument("--name", required=True, help="Label identifying the key's owner")
    args = parser.parse_args()

    if args.command == "create-key":
        plaintext = create_key(args.name)
        print("API key (store it now; only its hash is kept):")
        print(plaintext)


if __name__ == "__main__":
    main()
