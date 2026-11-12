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
        self.assertEqual(server["environment"]["STARINTEL_INGEST_HOSTS"], "")
        self.assertNotIn("TOKEN", json.dumps(config))
        claude = module.configuration("claude")["mcpServers"]["starintel"]
        self.assertEqual([claude["command"], *claude["args"]], server["command"])
        self.assertEqual(claude["env"], server["environment"])

    def test_launcher_clears_inherited_hosts_and_preserves_connected_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            launcher = root / "bin/starintel"
            launcher.write_bytes((ROOT / "bin/starintel").read_bytes())
            (root / ".venv/bin").mkdir(parents=True)
            (root / ".venv/bin/python").symlink_to(sys.executable)
            (root / "vendor/starintel-mcp/bin").mkdir(parents=True)
            (root / "vendor/starintel-mcp/bin/starintel-mcp").write_text(
                "import json, os\nprint(json.dumps(dict(os.environ)))\n"
            )
            workspace = root / "reviewed-workspace"
            workspace.mkdir()
            host_file = workspace / "starintel-mcp.json"
            connected = (ROOT / "config/workspace-connected.json.example").read_bytes()
            host_file.write_bytes(connected)
            result = subprocess.run(["bash", str(launcher), "ingest", "hosts"], check=True,
                                    capture_output=True, text=True, env={**os.environ,
                                        "STARINTEL_WORKSPACE": str(workspace),
                                        "STARINTEL_INGEST_HOSTS": '{"unreviewed": {"url": "https://example.invalid"}}',
                                    })
            environment = json.loads(result.stdout)
            self.assertNotIn("STARINTEL_INGEST_HOSTS", environment)
            self.assertEqual(environment["STARINTEL_WORKSPACE"], str(workspace))
            self.assertEqual(host_file.read_bytes(), connected)

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
            self.assertEqual((root / ".env").read_bytes(), (root / ".env.example").read_bytes())
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

    def test_prepare_refuses_dangling_symlinks_before_creating_files(self):
        module = load_script("prepare_server")
        for name in (".env", "secrets"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "docker-compose.yml").write_text("services: {}")
                (root / name).symlink_to(root / "missing")
                with self.assertRaisesRegex(ValueError, "nothing was changed"):
                    module.prepare(root)
                self.assertTrue((root / name).is_symlink())
                self.assertFalse((root / "missing").exists())
                self.assertEqual({p.name for p in root.iterdir()}, {"docker-compose.yml", name})

    def test_prepare_env_exclusive_creation_rejects_racing_symlink(self):
        module = load_script("prepare_server")
        real_open = os.open
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docker-compose.yml").write_text("services: {}")
            (root / ".env.example").write_text("EXAMPLE=value\n")
            target = root / "outside"

            def race(path, flags, mode):
                self.assertEqual(Path(path), root / ".env")
                self.assertEqual(mode, 0o600)
                (root / ".env").symlink_to(target)
                return real_open(path, flags, mode)

            with patch.object(module.os, "open", side_effect=race):
                with self.assertRaises(FileExistsError):
                    module.prepare(root)
            self.assertFalse(target.exists())
            self.assertTrue((root / ".env").is_symlink())

    def test_key_output_is_reserved_private_before_issuance_and_never_overwrites(self):
        module = load_script("issue_key")
        client = MagicMock()
        instance = client.return_value.__enter__.return_value
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key"

            def issue(*args, **kwargs):
                self.assertEqual(path.read_bytes(), b"")
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                return SimpleNamespace(api_key="never-print-this", credential=SimpleNamespace(id="recovery-id"))

            instance.create_credential.side_effect = issue
            with patch.dict(sys.modules, {"starintel_client": SimpleNamespace(StarIntelClient=client)}), patch.dict(os.environ, {
                "STAR_SERVER_URL": "https://example.invalid", "STARINTEL_API_KEY": "admin-secret",
            }), patch.object(sys, "argv", ["issue_key", "--owner", "learner", "--scope", "actors:read", "--output", str(path)]):
                with redirect_stdout(io.StringIO()) as output:
                    module.main()
                self.assertEqual(path.read_text(), "never-print-this\n")
                self.assertIn("recovery-id", output.getvalue())
                self.assertNotIn("never-print-this", output.getvalue())
                self.assertNotIn("admin-secret", output.getvalue())
                with self.assertRaises(FileExistsError):
                    module.main()
                instance.create_credential.assert_called_once_with("learner", "api_client", ["actors:read"], expires_in_seconds=3600)

    def test_key_unusable_output_never_calls_api(self):
        module = load_script("issue_key")
        for kind in ("existing", "dangling", "unwritable"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "key"
                if kind == "existing":
                    path.write_text("user-owned")
                elif kind == "dangling":
                    path.symlink_to(Path(directory) / "missing")
                client = MagicMock()
                real_open = os.open
                with patch.dict(sys.modules, {"starintel_client": SimpleNamespace(StarIntelClient=client)}), patch.object(sys, "argv", [
                    "issue_key", "--owner", "learner", "--scope", "actors:read", "--output", str(path),
                ]), patch.object(module.os, "open", side_effect=PermissionError("not writable") if kind == "unwritable" else real_open):
                    with self.assertRaises(OSError):
                        module.main()
                client.assert_not_called()
                if kind == "existing":
                    self.assertEqual(path.read_text(), "user-owned")
                elif kind == "dangling":
                    self.assertTrue(path.is_symlink())
                    self.assertFalse(path.exists())

    def test_key_write_failure_prints_recovery_id_before_write_without_secret(self):
        module = load_script("issue_key")
        client = MagicMock()
        instance = client.return_value.__enter__.return_value
        instance.create_credential.return_value = SimpleNamespace(
            api_key="never-print-this", credential=SimpleNamespace(id="revoke-this-id"),
        )
        real_fdopen = os.fdopen
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            path = Path(directory) / "key"

            def fail_write(descriptor, mode):
                stream = real_fdopen(descriptor, mode)
                wrapper = MagicMock(wraps=stream)
                wrapper.__enter__.return_value = wrapper
                wrapper.__exit__.side_effect = lambda *args: stream.close()

                def write(value):
                    self.assertIn("revoke-this-id", output.getvalue())
                    raise OSError("disk full")

                wrapper.write.side_effect = write
                return wrapper

            with patch.dict(sys.modules, {"starintel_client": SimpleNamespace(StarIntelClient=client)}), patch.dict(os.environ, {
                "STAR_SERVER_URL": "https://example.invalid", "STARINTEL_API_KEY": "admin-secret",
            }), patch.object(sys, "argv", ["issue_key", "--owner", "learner", "--scope", "actors:read", "--output", str(path)]), patch.object(module.os, "fdopen", side_effect=fail_write):
                with self.assertRaisesRegex(OSError, "disk full"):
                    module.main()
            instance.create_credential.assert_called_once()
            self.assertIn("revoke-this-id", output.getvalue())
            self.assertNotIn("never-print-this", output.getvalue())
            self.assertNotIn("admin-secret", output.getvalue())
            self.assertNotIn("Saved", output.getvalue())

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
