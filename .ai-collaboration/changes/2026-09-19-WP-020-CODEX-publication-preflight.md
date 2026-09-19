# WP-020 - Public repository and source-only distribution

- Modifier: Codex; collaboration scheme: D; branch: `codex/lfsrc-harness-v1`.
- Scope: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/INSTALL.md`,
  `docs/THIRD_PARTY.md`, `docs/ASSUMPTIONS.md`, `deploy/install.ps1`,
  `deploy/install.sh`, `deploy/windows/*`, tests, `.gitignore`, `.dockerignore`,
  `.ai-collaboration/*` and publication verification.
- Reason / REQ: user requires a new `ZC-kf/LfSrcHarness` public repository with its
  own `main`, separate from the original Agent project. Original code is intended for
  noncommercial lawful use; third-party content retains its own rights.
- Implementation: selected PolyForm Noncommercial 1.0.0 for original Harness code
  and labeled the result source-available rather than OSI open source. The user then
  approved source-only distribution. `agent_bundle/`, generated data and third-party
  tools are excluded. Windows prerequisites download from Microsoft at installation
  time and require a valid Microsoft Authenticode signature. Source-install scripts
  copy an explicit allowlist instead of the entire local directory.
- Verification: local Git root is the LfSrcHarness directory, has no remote and does
  not point at or modify the original Agent project. Gitleaks scans of `src`, `deploy`,
  `docs`, `plugins`, `tests`, `web`, `.github` and `.ai-collaboration` reported zero
  findings. Redacted scan of the local Agent bundle reported 3388 potential findings,
  mostly within copied third-party skill directories; at least one binary exceeds
  GitHub's single-file limit. No secret values were printed or uploaded.
- Status / remaining: publication verification is in progress. Do not report the
  repository or Release as live until remote and download checks pass. Missing-runtime
  installation branches still require a clean Windows VM test; no live public targets
  were contacted by product tests.

## Post-publication CI correction

- Author: Codex; requirement mapping: REQ-014 / REQ-020; same locked scheme D.
- Scope: `deploy/docker-compose.yml`, `tests/test_deploy.py`, deployment docs and
  this record. No original Agent or third-party source changed.
- Evidence: GitHub CI run #1 passed Python (Windows/Linux), web and deployment
  jobs, but container smoke failed. API traceback ended at SQLite opening
  `/opt/lfsrc/runs/state.sqlite3`. Compose bind-mounted the checkout's `runs/`
  directory over the image directory already owned by the non-root service user.
  The Linux checkout directory is not writable by that container user.
- Fix: use a Compose-managed `runs-data` volume by default, preserving non-root
  execution. A regression test checks all runtime services use the named volume.
- Verification: focused deployment tests and Compose config pass locally;
  post-fix GitHub container smoke and Release verification remain pending.
