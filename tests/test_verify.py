import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from repopilot.verify import _capture, redact, verify_repository

IMAGE = "python@sha256:" + "a" * 64  # mock identity, never downloaded


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.args = dict(root=self.temp.name, image=IMAGE, approved=True)

    def test_rejects_unapproved_and_arbitrary_commands(self):
        for extra in ({"approved": False}, {"check": "sh -c echo hi"}, {"image": "python:latest"}, {"timeout": True}, {"timeout": 121}):
            with self.subTest(extra=extra), patch("repopilot.verify._capture") as run, self.assertRaises(ValueError):
                verify_repository(**(self.args | extra))
            run.assert_not_called()

    def test_missing_docker_has_no_host_fallback(self):
        with patch("repopilot.verify.shutil.which", return_value=None), patch("repopilot.verify._capture") as run:
            self.assertEqual(verify_repository(**self.args)["status"], "unavailable")
            run.assert_not_called()

    def test_container_policy_and_result_states(self):
        for state, code, expected in (("exited", 0, "passed"), ("exited", 1, "failed"), ("exited", 125, "error"), ("timeout", -9, "timeout"), ("output_limit", -9, "output_limit")):
            with self.subTest(expected=expected), patch("repopilot.verify.shutil.which", return_value="docker"), patch("repopilot.verify._capture", return_value=(state, code, "token=demo-secret")) as run, patch("repopilot.verify.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as clean:
                result = verify_repository(**self.args)
                self.assertEqual(result["status"], expected)
                self.assertNotIn("demo-secret", result["output"])
                command = run.call_args.args[0]
                for flag in ("--pull=never", "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user=65534:65534", "--pids-limit=64"):
                    self.assertIn(flag, command)
                self.assertTrue(any("target=/workspace,readonly" in arg for arg in command))
                self.assertEqual(clean.call_args.args[0][-1], result["container"])
                self.assertFalse(clean.call_args.kwargs["shell"])

    def test_invocation_and_cleanup_failures_are_visible(self):
        with patch("repopilot.verify.shutil.which", return_value="docker"), patch("repopilot.verify._capture", side_effect=OSError("private error")), patch("repopilot.verify.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 10)):
            result = verify_repository(**self.args)
            self.assertEqual(result["status"], "cleanup_failed")
            self.assertNotIn("private error", str(result))

    def test_redacts_credentials_and_private_key(self):
        for value in ("Authorization: Bearer demo", '"password": "demo"', "sk-abcdef", "-----BEGIN PRIVATE KEY-----\ndemo\n-----END PRIVATE KEY-----"):
            self.assertNotIn("demo", redact(value))
            self.assertIn("REDACTED", redact(value))

    def test_capture_timeout_failure_and_output_bound_on_trusted_helpers(self):
        # Fixed test-owned helpers only; no repository or generated code is executed.
        self.assertEqual(_capture([sys.executable, "-c", "raise SystemExit(3)"], 5)[:2], ("exited", 3))
        self.assertEqual(_capture([sys.executable, "-c", "import time; time.sleep(5)"], 0.1)[0], "timeout")
        state, _, output = _capture([sys.executable, "-c", "print('x'*100000)"], 5)
        self.assertEqual(state, "output_limit")
        self.assertLessEqual(len(output), 65536)


if __name__ == "__main__":
    unittest.main()
