"""Explicitly publish an exported JSONL batch using registry discovery, not MCP's fixed route."""
import argparse
import os
from pathlib import Path

def main() -> None:
    from starintel_client import StarIntelClient
    from starintel_canonical import parse_json, stringify_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--submit", action="store_true", help="Perform a remote write; otherwise only count records")
    args = parser.parse_args()
    documents = [parse_json(line) for line in args.batch.read_text().splitlines() if line.strip()]
    print(f"Batch contains {len(documents)} documents")
    if not args.submit:
        print("No network request made. Add --submit only after reviewing the batch and destination.")
        return
    with StarIntelClient(os.environ["STAR_SERVER_URL"], api_key=os.environ["STARINTEL_API_KEY"]) as client:
        client.discover()
        response = client.publish_documents_bulk(documents)
        print(stringify_json(response.data))
        print("Correlation:", response.correlation_id)


if __name__ == "__main__":
    main()
