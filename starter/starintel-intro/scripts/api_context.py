"""Authenticate and inspect granted capabilities through the maintained client."""
import os

def main() -> None:
    from starintel_client import StarIntelClient
    from starintel_canonical import stringify_json

    with StarIntelClient(os.environ["STAR_SERVER_URL"], api_key=os.environ["STARINTEL_API_KEY"]) as client:
        manifest = client.discover()
        print("Contract operations:", ", ".join(manifest.operation_ids))
        result = client.auth_context()
        print(stringify_json(result.data))
        print("Correlation:", result.correlation_id)


if __name__ == "__main__":
    main()
