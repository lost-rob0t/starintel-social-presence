"""Create a short-lived scoped key; save the one-time secret in a NEW private file."""
import argparse
import os
from pathlib import Path

def save_secret(path: Path, value: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(value + "\n")


def main() -> None:
    from starintel_client import StarIntelClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; refusing to issue another key")
    if not args.output.parent.is_dir():
        parser.error("create the private output directory first")
    with StarIntelClient(os.environ["STAR_SERVER_URL"], api_key=os.environ["STARINTEL_API_KEY"]) as client:
        client.discover()
        key = client.create_credential(args.owner, "api_client", args.scope, expires_in_seconds=3600)
        save_secret(args.output, key.api_key)
        print("Saved a one-time key to", args.output)
        print("Credential metadata:", key.credential)


if __name__ == "__main__":
    main()
