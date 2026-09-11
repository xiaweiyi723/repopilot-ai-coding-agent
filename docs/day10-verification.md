# Day 10 — Opt-in container verification adapter

## Problem and implementation

A coding assistant must not execute model-generated shell text on the host. `verify.py` exposes two fixed check IDs: `unittest` and `ruff`. It invokes Docker with an argument list and `shell=False`; there is no arbitrary command field and no host-execution fallback. The host/UI must obtain explicit approval and choose the root and trusted image. Do not expose the approval boolean as an agent-controlled tool argument.

The Docker command requests no network, a read-only root filesystem and checkout mount, a non-root user, all capabilities dropped, no new privileges, 64 PIDs, 256 MiB memory including swap, one CPU and a 64 MiB noexec/nosuid temporary filesystem. It overrides the image entrypoint with Python, disables healthchecks and daemon log storage, and uses `--pull=never`. Image references must include a SHA-256 digest. These controls follow the [official Docker run reference](https://docs.docker.com/engine/containers/run/); they reduce exposure but are not a proof against container escape or a compromised daemon/image.

## Setup and usage

Prerequisites: a trusted local Linux-container Docker engine and a reviewed, preloaded image containing Python and the project's test dependencies. The `ruff` check additionally requires Ruff inside that image. This adapter does not install dependencies, pull images or create credentials. Pinning a digest ensures identity, not trust.

Prepare a disposable checkout with no secrets, credentials, nested mounts or unrelated personal files. The entire checkout is readable by tests. Do not mount a home directory, production workspace or Docker socket. On Windows, configure Docker Desktop file sharing yourself; the daemon must see the same host path. Remote Docker contexts are unsupported.

```bash
python -m repopilot.verify /path/to/disposable-checkout --check unittest --image YOUR_REVIEWED_IMAGE@sha256:YOUR_64_HEX_DIGEST --timeout 30 --approve-execution
```

The image string is a placeholder, not a downloadable example. The Python equivalent is `verify_repository(root, check="unittest", image=trusted_digest_reference, approved=True)`. Without approval, input is rejected. `ruff` uses isolated configuration and no cache; unittest discovers `tests/`, with `PYTHONPATH=/workspace/src`. Checks requiring writes inside the checkout fail under the read-only mount; temporary test data should use `/tmp`.

## Results and cleanup

JSON reports `passed`, `failed`, `error`, `timeout`, `output_limit`, `unavailable`, or `cleanup_failed`. CLI exit 0 is reserved for `passed`; runtime failures exit 1 and invalid inputs exit 2. `executed` is null on timeout/overflow because container startup may not have completed; it is not proof that tests ran. A zero check exit code is not evidence of correct test coverage.

Retained combined stdout/stderr is capped at 64 KiB. The reader drains the pipe, while the controller kills the Docker CLI on timeout or overflow and attempts removal of its unique `repopilot-verify-...` container. Cleanup is attempted after normal exits and failures, with a separate 10-second bound. A failed removal overrides the top-level status and includes the previous check status; the named container may need manual inspection. Killing the CLI alone is not treated as container cleanup. Docker timeout configuration is 1–120 seconds, plus bounded process/reader shutdown and cleanup overhead.

Common token/password/authorization assignments, familiar token prefixes and private-key blocks are redacted before output is returned. Terminal control characters are stripped. This is best-effort pattern redaction, not a general data-loss-prevention boundary: encoded, unusual or partially truncated secrets can escape detection. Never rely on redaction to make a secret-containing checkout safe.

## Validation evidence

`python -m unittest discover -s tests -v`: 43 tests ran, 42 passed, one existing Windows symlink privilege skip. Six new tests cover approval and allowlist rejection, missing Docker without fallback, hardened Docker argv, successful/failed/infrastructure/timeout/output-limit states, cleanup failure and credential redaction. The capture test really starts three fixed test-owned Python helpers to exercise nonzero exit, timeout and output limits. It does not execute untrusted repository code on the host.

Docker was not installed in the development environment. Container policy tests use mocks; **no live container isolation, image compatibility or end-to-end sandbox success is claimed**. To complete environment acceptance, run a tiny reviewed fixture in a preloaded image, check pass/fail/timeout paths, verify `/workspace` rejects writes and networking is disabled, and confirm each named container is removed. This remains a manual environment check, not a hidden success assertion.

## Integration and next risk

Day 9 diffs are not applied automatically. Review and apply a proposal to a separate disposable checkout yourself, then explicitly authorize a check on that checkout. The adapter verifies its current contents; it does not claim to have validated an unapplied proposal. The next project stage can expose these results in a UI without granting an LLM control over approval, image selection or shell arguments.
