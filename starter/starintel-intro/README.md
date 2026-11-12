# StarIntel intro

A safe starting checkout for **local learning**, MCP clients, CLI workflows,
and authenticated server access. Start offline; remote publication is explicit.
No real data, API keys, provider accounts, or running server are included.

## 1. Install the tools

You need Git, Python **3.12+** with `venv` and pip, and an authorized Forgejo
account with its SSH key configured. MCP repository access may require an
invitation; an API key does not grant source access. On Linux/macOS:

```sh
bash scripts/setup.sh
bash scripts/local-demo.sh
```

Setup downloads the exact source commits in `sources.json` from Forgejo and
installs the maintained HTTP client plus MCP's schema dependency. It does not
start Docker, enable actors, or submit data. The local demo creates `intro-demo`,
writes a synthetic note, reads/searches it, uses a saved view, appends a revision,
shows history, and exports JSONL. A second run must use another operation name:
`bash scripts/local-demo.sh intro-demo-2`.

The upstream MCP launcher runs **from its checkout** so its vendored schema and
hint files remain available. Do not copy only its Python package elsewhere.

## 2. Explore the local CLI

```sh
bash bin/starintel --help
bash bin/starintel op list
bash bin/starintel op show intro-demo
bash bin/starintel hints --dtype document
bash bin/starintel target list --op intro-demo
bash bin/starintel ingest hosts
bash bin/starintel web
```

Open `http://127.0.0.1:8777` for the optional local web UI; Ctrl-C stops it.
It is not the server API or an HTTP MCP endpoint. Local records live under
`workspace/operations/<operation>/db/<dataset>/<dtype>/documents.ndjson`.
The synthetic note uses the canonical `document` dtype and `rawContent` field;
there is no canonical `note` dtype.
Back up the entire workspace, including operation metadata and views. History
is append-only; a tombstone is not erasure of historical sensitive content.

## 3. Configure MCP

Print configuration using absolute paths, then merge the `starintel` entry into
your client's existing configuration. Do not overwrite unrelated settings.

```sh
python3 scripts/mcp_config.py opencode
python3 scripts/mcp_config.py claude
```

OpenCode **V2** uses `mcp.servers`, not the older direct `mcp` map. Check with
`opencode mcp list` or `/mcps`; saving configuration triggers a reload. Claude's
configuration uses `mcpServers`. The server speaks **stdio**, so configure a local
command ending in `serve`, not an HTTPS URL. No API key is needed for local tools.

Try: “Use StarIntel to list operations, then search notes in intro-demo. Do not
ingest anything remotely.” Local tools can still modify/delete local records;
review client permissions and do not give an untrusted agent a sensitive workspace.

## 4. Use your server API key

Get the server URL and a scoped API key from your administrator. Never paste a
key into chat, a command argument, a screenshot, or a tracked config. In Bash:

```sh
export STAR_SERVER_URL='http://127.0.0.1:5000'
read -r -s -p 'API key: ' STARINTEL_API_KEY
echo
export STARINTEL_API_KEY
.venv/bin/python scripts/api_context.py
```

A successful auth-context request proves authentication; `/health` alone does
not. `401` means invalid/expired/revoked credentials; `403` means a valid key lacks
the requested scope or dataset grant. Discovery fetches `/client-manifest.json`
and `/openapi.json`; operations absent from the registry are unavailable. Keep
correlation IDs for support, never authorization headers.

Variable names differ between maintained tools:

| Tool | Server URL | Credential |
|---|---|---|
| These Python examples / `sa-*` | `STAR_SERVER_URL` / `--server URL` | `STARINTEL_API_KEY` |
| MCP remote ingest | `STAR_SERVER_URL` or host config | `STAR_SERVER_TOKEN` by default |
| `star-cli` | `STAR_SERVER_URL` | `STAR_SERVER_TOKEN` or `STAR_SERVER_API_KEY` |

Only alias the key when intentionally using that tool:
`export STAR_SERVER_TOKEN="$STARINTEL_API_KEY"`.

### Administrator: issue a learning key

With your administrator key currently loaded, this writes the one-time secret
to a new ignored file (0600), not terminal output:

```sh
install -d -m 0700 secrets
.venv/bin/python scripts/issue_key.py --owner intro-discovery \
  --scope actors:read --output secrets/discovery-key
export STARINTEL_API_KEY="$(cat secrets/discovery-key)"
.venv/bin/python scripts/api_context.py
```

The learning key expires after one hour. `actors:read` grants discovery only,
not document writes or target execution. Request only capabilities your task
needs. Keep administrator credentials separate, retain credential IDs, and
rotate/revoke through the maintained client's credential lifecycle methods.

### Publish a reviewed export

The demo's export command reports a JSONL batch path. First inspect and count it:

```sh
.venv/bin/python scripts/publish_batch.py /absolute/path/to/export.jsonl
# Only with a write-authorized key and an approved destination:
.venv/bin/python scripts/publish_batch.py /absolute/path/to/export.jsonl --submit
```

This uses the discovery-driven HTTP client and preserves exact JSON numbers.
An ingest receipt is not proof of downstream indexing or actor completion.
For bulk responses inspect `failed` as well as `succeeded`; for async jobs follow
the job status defined by the returned contract before claiming persistence.

The pinned MCP version's own `ingest submit` defaults to **live** and constructs
a fixed bulk URL. This starter config exposes only `local` by default, so an
unqualified ingest fails rather than publishing accidentally. To intentionally
enable it, review `config/workspace-connected.json.example`, edit the URL, then
install it as `workspace/starintel-mcp.json`, export `STAR_SERVER_TOKEN`, and run:

```sh
bash bin/starintel ingest hosts
bash bin/starintel ingest submit intro-demo training --host live --dry-run
# Explicit remote write, only if your deployment supports the pinned MCP bulk contract:
bash bin/starintel ingest submit intro-demo training --host live
```

Prefer `publish_batch.py` when registry-driven interoperability is required.
The MCP child must inherit credentials from the process launching it; changing
variables in an unrelated terminal will not update an already-running process.

## 5. Full local server installation (optional)

Linux with Nix flakes, Docker Engine, Compose v2, curl and jq is the reference
path. Image builds need network access, free disk and time; no resource sizing
or ARM support is promised here. Use a fresh machine/project without conflicting
ports, not an existing production deployment.

```sh
python3 scripts/fetch_sources.py starintel-server
python3 scripts/prepare_server.py vendor/starintel-server
cd vendor/starintel-server
docker compose config --quiet
nix run .#load-images
docker compose up --detach --wait
docker compose ps
curl --fail http://127.0.0.1:5000/health
```

The helper creates **all seven required base-stack secrets**, including auth
pepper and bootstrap secret missing from older upstream quickstarts. It refuses
existing `.env` or secret directories rather than rotating credentials silently.
It starts no services. Keep loopback bindings; do not expose CouchDB, RabbitMQ,
Valkey, or this development-shaped API to the Internet.

For a brand-new credential store, return to the starter root and bootstrap an
administrator through the maintained Python client:

```sh
cd ../..
export STAR_SERVER_URL=http://127.0.0.1:5000
install -d -m 0700 secrets
.venv/bin/python scripts/bootstrap.py \
  --secret-file vendor/starintel-server/secrets/auth_bootstrap_secret \
  --output secrets/admin-key
export STARINTEL_API_KEY="$(cat secrets/admin-key)"
.venv/bin/python scripts/api_context.py
```

Bootstrap reserves a new 0600 output file before requesting the one-time key.
If the call fails, inspect the error and possibly empty file before retrying.
On `bootstrap_complete`, use the existing administrator; never delete the auth DB.
Do not rely on the historical `star:intel` initial user. The pinned Compose
model does not forward every initial-user variable in `.env.example`; configure
passwords through the actual auth API before using user login.

Verify discovery and `scripts/api_context.py` before installing actors. The base
stack contains CouchDB, Clouseau, RabbitMQ, Valkey, Star Server and a telemetry
sidecar; telemetry is off by default. The optional `actors` profile is not the
full Pro actor fleet. Pro actors require a separately authorized fleet checkout,
its runtime dependencies/provider credentials, and broker/registry configuration.
See the docs site's Pro actors tutorial; never start all collectors blindly.

From `vendor/starintel-server`, stop while retaining data: `docker compose down`.
Restart: `docker compose up --detach --wait`. **Do not add `--volumes`** unless you intend
to destroy stored data. Back up volumes and file secrets before upgrades; keep
the auth pepper with the credential store or issued keys may become unusable.
On startup failure inspect `docker compose ps` and `docker compose logs
--tail=100 star-server couchdb rabbitmq`; redact secrets before sharing logs.

## Troubleshooting and checks

- Missing Python module: rerun setup with Python 3.12+ and use `.venv/bin/python`.
- Missing schema: retain the full pinned MCP checkout under `vendor/`.
- Empty local search: check operation, dataset and `STARINTEL_WORKSPACE`; remote
  server search is not the MCP workspace search.
- Missing `live` host: deliberate safe default, not a reason to disable auth.
- A local target is not dispatched work. Remote ingest, scheduling and an online
  registered worker are separate requirements.
- Port conflict: change the local bind ports in server `.env`, then use the same
  API URL in client configuration.
- `star-cli` exit codes: 4 authentication, 5 authorization, 2 validation,
  3 not found, 6 conflict, 7 transport.

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/setup.sh scripts/local-demo.sh bin/starintel
```

Offline checks need neither a server nor credentials. Upstream live collection,
remote writes, Docker image builds and end-to-end indexing require separate
operator-run checks; passing local tests does not prove those services work.
