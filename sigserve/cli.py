"""Admin CLI. Mint an API key with:

    python -m sigserve.cli create-key --name <label>
"""

import argparse

from sigserve.auth import mint_key
from sigserve.db import open_session


def create_key(name: str) -> str:
    with open_session() as session:
        _, plaintext = mint_key(session, name)
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
