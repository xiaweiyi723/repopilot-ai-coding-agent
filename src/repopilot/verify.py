"""Opt-in Docker verification; never falls back to host execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from uuid import uuid4

CHECKS = {
    "unittest": ("-B", "-m", "unittest", "discover", "-s", "tests", "-v"),
    "ruff": ("-B", "-m", "ruff", "check", "--isolated", "--no-cache", "src", "tests"),
}
MAX_OUTPUT = 64 * 1024


def redact(text: str) -> str:
    """Best-effort common credential redaction, not arbitrary secret detection."""
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)", "[REDACTED KEY]", text)
    text = re.sub(r"(?im)\b(authorization|api[_-]?key|token|password|secret)\b[\"']?\s*[:=]\s*[^\r\n]+", r"\1=[REDACTED]", text)
    text = re.sub(r"\b(?:gh[pousr]_|github_pat_|sk-)[A-Za-z0-9_-]+", "[REDACTED]", text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _capture(argv, timeout):
    """Bound retained output while draining a pipe; kill CLI on timeout/overflow."""
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, shell=False)
    output = bytearray()
    overflow = threading.Event()

    def drain():
        while True:
            block = process.stdout.read(4096)
            if not block:
                break
            available = MAX_OUTPUT - len(output)
            output.extend(block[:available])
            if len(block) > available:
                overflow.set()

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    status = "exited"
    try:
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() >= deadline:
                status = "output_limit" if overflow.is_set() else "timeout"
                process.kill()
                break
            time.sleep(0.02)
        process.wait(timeout=5)
        reader.join(timeout=5)
        if overflow.is_set():
            status = "output_limit"
        return status, process.returncode, bytes(output).decode("utf-8", errors="replace")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if not reader.is_alive():
            process.stdout.close()


def verify_repository(root, *, check="unittest", image, timeout=30, approved=False):
    """Run a fixed check in a preloaded, trusted digest-pinned Linux image.

    Mount a disposable, secret-free checkout. Approval is a host/UI decision,
    not a field that should be exposed to an untrusted model tool call.
    """
    root = Path(root).resolve()
    if not root.is_dir() or any(c in str(root) for c in ',\r\n"'):
        raise ValueError("root must be an existing directory without mount delimiters")
    if check not in CHECKS:
        raise ValueError("unknown check; only unittest and ruff are allowed")
    if not isinstance(image, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:-]*@sha256:[0-9a-f]{64}", image):
        raise ValueError("a trusted digest-pinned image is required")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("timeout must be an integer between 1 and 120 seconds")
    if approved is not True:
        raise ValueError("explicit execution approval is required")
    docker = shutil.which("docker")
    if not docker:
        return {"status": "unavailable", "executed": False, "output": "Docker unavailable; no host fallback.", "cleanup": "not_needed"}
    name = "repopilot-verify-" + uuid4().hex
    argv = [docker, "run", "--name", name, "--pull=never", "--network=none",
            "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--user=65534:65534", "--pids-limit=64", "--memory=256m", "--memory-swap=256m",
            "--cpus=1", "--log-driver=none", "--no-healthcheck",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--mount", f"type=bind,source={root},target=/workspace,readonly",
            "--workdir=/workspace", "--env=PYTHONPATH=/workspace/src", "--env=HOME=/tmp",
            "--entrypoint=python", image, *CHECKS[check]]
    result = {"check": check, "container": name, "image": image, "executed": False,
              "status": "error", "output": "", "exit_code": None, "cleanup": "failed"}
    try:
        state, code, output = _capture(argv, timeout)
        result.update(exit_code=code, output=redact(output), executed=(code not in (125, 126, 127)) if state == "exited" else None)
        result["status"] = state if state != "exited" else ("passed" if code == 0 else "error" if code in (125, 126, 127) else "failed")
    except (OSError, subprocess.SubprocessError):
        result["output"] = "Docker invocation failed; no host fallback."
    finally:
        try:
            clean = subprocess.run([docker, "rm", "-f", name], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   shell=False, timeout=10)
            result["cleanup"] = "removed" if clean.returncode == 0 else "failed"
        except (OSError, subprocess.SubprocessError):
            pass
    if result["cleanup"] == "failed":
        result["check_status"] = result["status"]
        result["status"] = "cleanup_failed"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--check", choices=CHECKS, default="unittest")
    parser.add_argument("--image", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--approve-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify_repository(args.root, check=args.check, image=args.image,
                                   timeout=args.timeout, approved=args.approve_execution)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
