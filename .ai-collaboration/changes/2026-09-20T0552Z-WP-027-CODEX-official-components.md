# WP-027 — install-time official component preflight (partial)

- Writer: Codex (`AI_OWNER: CODEX`), `COLLABORATION_SCHEME: D`, protocol 5.1.
- Baseline: `f272f34`; plan version advanced from 7 to 8 for the user's revised installation requirement.
- Scope: `deploy/windows/OfficialComponents.ps1`, `deploy/windows/LfSrcHarness.iss`,
  `tests/test_official_components.py`, `docs/INSTALL.md`, `docs/ASSUMPTIONS.md`,
  `.ai-collaboration/PROJECT_PLAN.md`, this record, and `PROJECT_SUMMARY.md`.
- Requirement map: REQ-027 / WP-027. Existing installations are reused; missing
  supported components are downloaded from publisher-controlled HTTPS URLs into
  the selected installation's `tools/downloads`, Authenticode-checked, handed to
  vendor installers with Windows UAC, then detected again. Setup stops with a
  repair hint when a required component is declined or remains unavailable.
- Implementation choice: retain the existing Inno installer; invoke a separate
  PowerShell component preflight after the desktop self-test. This limits the
  installer change and permits a no-network check mode. Vendor installation may
  require system locations; no forced relocation or security-software changes.
- TDD evidence: new check-mode tests failed first because the script did not
  exist. Install-mode tests failed first because the mode was not implemented.
- Verification: `pytest tests/test_official_components.py tests/test_installer.py -q`
  passed (9 passed, 2 Linux-only skipped); full `pytest -q` passed
  (112 passed, 2 Linux-only skipped; 2 dependency deprecation warnings);
  `ruff check src tests` passed; Inno Setup 7.1 `/Q` compile exited 0.
- Local artifact: `package/LfSrcHarness-Windows-Setup-v0.1.1-preview.4.exe`,
  35,109,909 bytes, SHA-256
  `5649F73A5DAB45A2171F0A933A7420182F06C97D332B291505F605B9BC557A87`.
- Remaining work: missing-component download, signature, UAC and re-detection
  paths have not been run on a clean Windows VM; Linux component provisioning
  (WP-028) and audited public Agent packaging (WP-029) are not implemented.
  This local installer is not a complete Agent release and must not be uploaded
  or described as such. GitHub release and public documentation still point to
  preview.3. Generated `build/pyinstaller-work/` remains an untracked local cache.
