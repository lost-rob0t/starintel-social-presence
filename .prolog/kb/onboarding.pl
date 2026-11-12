% Verified against pinned MCP 6157f070 and client ad48cfc4 during docs overhaul.
onboarding_template('starter/starintel-intro').
onboarding_check(offline, 'python3 -m unittest discover -s starter/starintel-intro/tests -v').
onboarding_dtype(synthetic_note, document, rawContent).
onboarding_runtime(mcp, local_workspace, 'STARINTEL_WORKSPACE').
onboarding_runtime(python_client_examples, server_http, 'STARINTEL_API_KEY').
onboarding_runtime(mcp_ingest, server_http, 'STAR_SERVER_TOKEN').
onboarding_runtime(star_cli, server_http, 'STAR_SERVER_TOKEN').
onboarding_safety(default_ingest_hosts, local_only).
onboarding_safety(remote_publication, explicit_submit).
onboarding_boundary(local_target, not_remote_dispatch).
onboarding_boundary(mcp_web_ui, not_http_mcp_endpoint).
onboarding_server_secret(auth_pepper).
onboarding_server_secret(auth_bootstrap_secret).
