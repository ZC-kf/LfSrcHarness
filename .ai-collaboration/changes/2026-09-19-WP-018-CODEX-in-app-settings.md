# WP-018 - In-app model and scope settings

- Modifier: Codex; collaboration scheme: D; branch: `codex/lfsrc-harness-v1`.
- Scope: `src/lfsrc_harness/desktop_settings.py`, `src/lfsrc_harness/providers.py`,
  `src/lfsrc_harness/api.py`, `web/src/App.tsx`, `web/src/styles.css`, provider/API/UI
  tests, and related assumptions.
- Reason / REQ: REQ-018 requires cloud vendors, local model endpoints and relay gateways
  to be configured inside the software, including optional API keys.
- Implementation: provider metadata is stored in user data, secrets in the OS credential
  vault; read APIs return only `has_api_key`. The UI can save, remove and test provider
  connections and edit the authorization scope without hand-editing project files.
- Verification: 98 Python tests and 5 React tests passed; Vite build, Ruff and strict
  mypy passed. No live external vendor request was made during acceptance.
- Remaining: provider-specific production interoperability and broader task-management
  UI flows remain unverified; no offline model weights are bundled by user decision.
