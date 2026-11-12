"""Offline tests: no server, credentials, downloads or vendor checkouts required."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StarterTests(unittest.TestCase):
    def test_sources_are_commit_pinned_to_forgejo(self):
        sources = json.loads((ROOT / "sources.json").read_text())
        self.assertEqual(set(sources), {"starintel-mcp", "starintel-client", "starintel-server"})
        for source in sources.values():
            self.assertRegex(source["commit"], r"^[a-f0-9]{40}$")
            self.assertTrue(source["url"].startswith("ssh://forgejo@git.starintel.actor/"))

    def test_configurations_use_absolute_paths_and_no_secret(self):
        module = load_script("mcp_config")
        config = module.configuration("opencode")
        server = config["mcp"]["servers"]["starintel"]
        self.assertEqual(server["type"], "local")
        self.assertEqual(server["command"][-1], "serve")
        self.assertTrue(Path(server["command"][0]).is_absolute())
        self.assertTrue(Path(server["environment"]["STARINTEL_WORKSPACE"]).is_absolute())
        self.assertNotIn("TOKEN", json.dumps(config))
        claude = module.configuration("claude")["mcpServers"]["starintel"]
        self.assertEqual([claude["command"], *claude["args"]], server["command"])

    def test_default_has_no_live_host(self):
        config = json.loads((ROOT / "config/workspace-local.json").read_text())
        self.assertEqual(config, {"ingestHosts": {"local": {"local": True}}})

    def test_prepare_server_creates_all_private_secrets_and_refuses_reuse(self):
        module = load_script("prepare_server")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docker-compose.yml").write_text("services: {}")
            (root / ".env.example").write_text("STAR_SERVER_BIND_ADDRESS=127.0.0.1\n")
            with redirect_stdout(io.StringIO()):
                module.prepare(root)
            secret_dir = root / "secrets"
            self.assertEqual(stat.S_IMODE(secret_dir.stat().st_mode), 0o700)
            self.assertEqual({p.name for p in secret_dir.iterdir()}, {
                "couchdb_password", "couchdb_secret", "erlang_cookie",
                "rabbitmq_password", "valkey_password", "auth_pepper", "auth_bootstrap_secret",
            })
            before = {p.name: p.read_bytes() for p in secret_dir.iterdir()}
            self.assertEqual(len(set(before.values())), 7)
            for path in secret_dir.iterdir():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((root / ".env").stat().st_mode), 0o600)
            with self.assertRaisesRegex(ValueError, "nothing was changed"):
                module.prepare(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in secret_dir.iterdir()})

    def test_prepare_refuses_existing_env_before_creating_secret_directory(self):
        module = load_script("prepare_server")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docker-compose.yml").write_text("services: {}")
            (root / ".env").write_text("user-owned")
            with self.assertRaises(ValueError):
                module.prepare(root)
            self.assertFalse((root / "secrets").exists())
            self.assertEqual((root / ".env").read_text(), "user-owned")

    def test_key_output_is_private_and_never_overwrites(self):
        module = load_script("issue_key")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key"
            module.save_secret(path, "synthetic-test-value")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                module.save_secret(path, "replacement")
            self.assertEqual(path.read_text(), "synthetic-test-value\n")

    def test_modified_vendor_is_not_reset(self):
        module = load_script("fetch_sources")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vendor/tool").mkdir(parents=True)
            with patch.object(module, "ROOT", root), patch.object(module.subprocess, "run") as run:
                with patch.object(module.subprocess, "check_output", side_effect=["a" * 40 + "\n", " M user-file"]):
                    with self.assertRaisesRegex(SystemExit, "left unchanged"):
                        module.fetch("tool", {"commit": "a" * 40, "url": "unused"})
                run.assert_not_called()

    def test_existing_wrong_revision_is_not_checked_out(self):
        module = load_script("fetch_sources")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vendor/tool").mkdir(parents=True)
            with patch.object(module, "ROOT", root), patch.object(module.subprocess, "run") as run:
                with patch.object(module.subprocess, "check_output", side_effect=["b" * 40, ""]):
                    with self.assertRaises(SystemExit):
                        module.fetch("tool", {"commit": "a" * 40, "url": "unused"})
                run.assert_not_called()

    def test_batch_preview_does_not_connect_or_need_a_key(self):
        module = load_script("publish_batch")
        client = MagicMock()
        modules = {
            "starintel_client": SimpleNamespace(StarIntelClient=client),
            "starintel_canonical": SimpleNamespace(parse_json=json.loads, stringify_json=json.dumps),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.jsonl"
            path.write_text('{"id":"synthetic"}\n')
            with patch.dict(sys.modules, modules), patch.object(sys, "argv", ["publish_batch", str(path)]):
                with patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()) as output:
                    module.main()
            client.assert_not_called()
            self.assertIn("No network request", output.getvalue())

    def test_context_discovers_before_authentication_and_omits_key(self):
        module = load_script("api_context")
        client = MagicMock()
        instance = client.return_value.__enter__.return_value
        instance.discover.return_value.operation_ids = ("auth.context.get",)
        instance.auth_context.return_value = SimpleNamespace(data={"owner": "training"}, correlation_id="example-correlation")
        modules = {
            "starintel_client": SimpleNamespace(StarIntelClient=client),
            "starintel_canonical": SimpleNamespace(stringify_json=json.dumps),
        }
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {
            "STAR_SERVER_URL": "https://example.invalid", "STARINTEL_API_KEY": "never-print-this",
        }), redirect_stdout(io.StringIO()) as output:
            module.main()
        self.assertEqual([call[0] for call in instance.method_calls], ["discover", "auth_context"])
        self.assertNotIn("never-print-this", output.getvalue())

    def test_bootstrap_reserves_private_output_and_omits_secrets(self):
        module = load_script("bootstrap")
        client = MagicMock()
        instance = client.return_value.__enter__.return_value
        instance.bootstrap.return_value = SimpleNamespace(
            api_key="synthetic-one-time-key", credential=SimpleNamespace(id="test-credential-id"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "bootstrap-secret"
            secret.write_text("synthetic-bootstrap-secret\n")
            output_path = root / "admin-key"
            argv = ["bootstrap", "--secret-file", str(secret), "--output", str(output_path)]
            with patch.dict(sys.modules, {"starintel_client": SimpleNamespace(StarIntelClient=client)}):
                with patch.object(sys, "argv", argv), patch.dict(os.environ, {"STAR_SERVER_URL": "http://127.0.0.1:5000"}):
                    with redirect_stdout(io.StringIO()) as output:
                        module.main()
                    self.assertEqual(output_path.read_text(), "synthetic-one-time-key\n")
                    self.assertEqual(stat.S_IMODE(output_path.stat().st_mode), 0o600)
                    self.assertNotIn("synthetic", output.getvalue())
                    self.assertEqual(instance.bootstrap.call_count, 1)
                    with self.assertRaises(FileExistsError):
                        module.main()
                    self.assertEqual(instance.bootstrap.call_count, 1)

    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(ROOT / "scripts/setup.sh"), str(ROOT / "scripts/local-demo.sh"), str(ROOT / "bin/starintel")], check=True)


if __name__ == "__main__":
    unittest.main()
