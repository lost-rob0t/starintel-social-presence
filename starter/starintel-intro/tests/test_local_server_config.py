"""Hermetic tests: no vendor checkout, Docker daemon, or network needed."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/configure_local_server.py"
SPEC = importlib.util.spec_from_file_location("local_server_config", SCRIPT)
assert SPEC and SPEC.loader
config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(config)

# Tiny source fixtures exercise the hash gate without redistributing server source.
SOURCES = {name: f"fixture for {name}\n" for name in config.SOURCE_HASHES}
SOURCES[".env.example"] = "CREDENTIALS_DIR=./secrets\nSTAR_AUTH_INITIAL_USERNAME=star\n"
SOURCES["docker/star-server-init.lisp"] = "(in-package :star)\n"
HASHES = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in SOURCES.items()}


class LocalServerConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "server"
        self.prepare(self.root)
        self.hash_patch = patch.object(config, "SOURCE_HASHES", HASHES)
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    def prepare(self, root: Path) -> None:
        root.mkdir()
        for name, text in SOURCES.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        (root / "secrets").mkdir(mode=0o700)
        for name in config.BASE_SECRETS:
            target = root / "secrets" / name
            target.write_text("a" * 64 + "\n")
            target.chmod(0o600)
        (root / ".env").write_text(SOURCES[".env.example"])
        (root / ".env").chmod(0o600)

    def snapshot(self) -> dict[str, tuple[int, bytes | str]]:
        result = {}
        for path in self.root.rglob("*"):
            if path.is_symlink():
                value = os.readlink(path)
            elif path.is_file():
                value = path.read_bytes()
            else:
                continue
            result[str(path.relative_to(self.root))] = (path.lstat().st_mode, value)
        return result

    def run_config(self, root: Path | None = None) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            config.configure(root or self.root)
        return output.getvalue()

    def assert_refused_without_changes(self) -> None:
        before = self.snapshot()
        with self.assertRaises((ValueError, OSError)):
            self.run_config()
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / config.LOCAL_DIR).exists())

    def test_unique_persisted_project_and_private_password(self) -> None:
        before = self.snapshot()
        output = self.run_config()
        password = (self.root / "secrets/local_admin_password").read_text().strip()
        self.assertRegex(password, r"^[a-f0-9]{64}$")
        self.assertNotIn(password, output)
        env = (self.root / ".env").read_text()
        self.assertRegex(env, r"\nCOMPOSE_PROJECT_NAME=starintel-local-[a-f0-9]{32}\n$")
        self.assertNotIn(password, env)
        self.assertTrue(env.startswith(SOURCES[".env.example"]))
        for name in (".env", "secrets/local_admin_password", "docker-compose.override.yml"):
            self.assertEqual(stat.S_IMODE((self.root / name).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.root / "secrets").stat().st_mode), 0o700)
        for name, expected in before.items():
            if name != ".env":
                self.assertEqual(self.snapshot()[name], expected)
        second = self.root.parent / "other"
        self.prepare(second)
        self.run_config(second)
        self.assertNotEqual(env, (second / ".env").read_text())
        self.assertNotEqual(password, (second / "secrets/local_admin_password").read_text().strip())

    def test_generated_init_and_override_contract(self) -> None:
        self.run_config()
        init = (self.root / config.LOCAL_DIR / "init.lisp").read_text()
        self.assertTrue(init.startswith(SOURCES["docker/star-server-init.lisp"]))
        self.assertIn('*auth-initial-username* "local-admin"', init)
        self.assertIn('*auth-initial-password* password', init)
        self.assertIn('(error "Local initial administrator password is missing or invalid")', init)
        # Lisp loads as UID 65532; init is nonsecret and world-readable.
        self.assertEqual(stat.S_IMODE((self.root / config.LOCAL_DIR).stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((self.root / config.LOCAL_DIR / "init.lisp").stat().st_mode), 0o644)
        override = (self.root / "docker-compose.override.yml").read_text()
        for text in ('user: "0:0"', 'entrypoint: ["/bin/sh", "-ec"]',
                     'exec /bin/star-server-entrypoint', 'export STAR_LOCAL_INITIAL_PASSWORD',
                     'STAR_SERVER_INIT_FILE: /etc/starintel/init.lisp',
                     'source: ./.starintel-local/init.lisp', 'target: /etc/starintel/init.lisp',
                     'read_only: true', 'create_host_path: false',
                     'file: ./secrets/local_admin_password'):
            self.assertIn(text, override)
        password = (self.root / "secrets/local_admin_password").read_text().strip()
        self.assertNotIn(password, init + override)

    def test_shell_passes_secret_without_output_and_refuses_missing_secret(self) -> None:
        self.run_config()
        command = config.OVERRIDE.split("      - |\n", 1)[1].split("    environment:", 1)[0]
        command = "\n".join(line[8:] for line in command.splitlines()).replace("$$", "$")
        password = self.root / "secrets/local_admin_password"
        command = command.replace("/run/secrets/local_admin_password", str(password))
        # Stand in for the upstream executable: verify inheritance without printing the secret.
        expected = password.read_text().strip()
        command = command.replace("exec /bin/star-server-entrypoint", 'exec /bin/sh -ec \'test "${#STAR_LOCAL_INITIAL_PASSWORD}" -eq 64\'')
        result = subprocess.run(["/bin/sh", "-ec", command], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, "")
        self.assertNotIn(expected, command)
        password.unlink()
        result = subprocess.run(["/bin/sh", "-ec", command], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_existing_override_and_alternate_compose_files_refused(self) -> None:
        for name in ("docker-compose.override.yml", "docker-compose.override.yaml",
                     "compose.yml", "compose.yaml", "compose.override.yml", "compose.override.yaml",
                     "docker-compose.yaml"):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text("user-owned configuration")
                self.assert_refused_without_changes()
                path.unlink()

    def test_existing_generated_paths_and_dangling_symlinks_refused(self) -> None:
        for name in (config.LOCAL_DIR, "docker-compose.override.yml", "secrets/local_admin_password"):
            with self.subTest(name=name):
                path = self.root / name
                path.symlink_to(self.root / "missing-target")
                self.assert_refused_without_changes()
                path.unlink()

    def test_user_env_changes_refused(self) -> None:
        with (self.root / ".env").open("a") as output:
            output.write("COMPOSE_PROJECT_NAME=my-existing-stack\n")
        self.assert_refused_without_changes()

    def test_changed_startup_source_refused(self) -> None:
        (self.root / "source/runtime-lifecycle.lisp").write_text("unsafe lifecycle")
        self.assert_refused_without_changes()

    def test_symlink_inputs_refused(self) -> None:
        for name in (".env", "docker/star-server-init.lisp", "secrets/auth_pepper"):
            with self.subTest(name=name):
                path = self.root / name
                content = path.read_bytes()
                mode = stat.S_IMODE(path.stat().st_mode)
                target = self.root / "outside"
                target.write_bytes(content)
                target.chmod(mode)
                path.unlink()
                path.symlink_to(target)
                self.assert_refused_without_changes()
                path.unlink()
                path.write_bytes(content)
                path.chmod(mode)
                target.unlink()

    def test_root_symlink_refused(self) -> None:
        alias = self.root.parent / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_config(alias)

    def test_public_or_incomplete_preparation_refused(self) -> None:
        (self.root / "secrets/auth_pepper").chmod(0o644)
        self.assert_refused_without_changes()
        (self.root / "secrets/auth_pepper").unlink()
        self.assert_refused_without_changes()

    def test_second_run_refuses_without_changes(self) -> None:
        self.run_config()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.run_config()
        self.assertEqual(before, self.snapshot())

    def test_cli_failure_is_sanitized(self) -> None:
        (self.root / ".env").write_text("user-secret-not-for-output")
        result = subprocess.run([os.sys.executable, str(SCRIPT), str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("user-secret-not-for-output", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
