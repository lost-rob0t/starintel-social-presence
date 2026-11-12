"""Bootstrap the FIRST administrator on a new local credential store only."""
import argparse
import os
from pathlib import Path


def main() -> None:
    from starintel_client import StarIntelClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner", default="local-operator")
    args = parser.parse_args()
    secret = args.secret_file.read_text().strip()
    if not secret:
        parser.error("bootstrap secret file is empty")
    # Reserve the output before the one-time remote call. Never replace a key.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        with StarIntelClient(os.environ["STAR_SERVER_URL"]) as client:
            client.discover()
            result = client.bootstrap(args.owner, bootstrap_secret=secret)
            output.write(result.api_key + "\n")
            print("Administrator credential:", result.credential.id)


if __name__ == "__main__":
    main()
