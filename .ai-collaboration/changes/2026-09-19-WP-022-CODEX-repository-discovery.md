# WP-022 - Repository About and installer discovery

- Modifier: Codex; scheme: D; base: `690c58d` on `main`.
- Requirement: REQ-022; the user wants “凛枫SRC Harness” in GitHub About,
  an Agent introduction, and obvious download/install entry points.
- Write scope: `README.md`, `docs/INSTALL.md`,
  `.ai-collaboration/PROJECT_PLAN.md`,
  `.ai-collaboration/PROJECT_SUMMARY.md`, this record, and GitHub repository
  About metadata. No product code, installer binary, Agent bundle, or icon edit.
- Approach: link the current verified preview Release assets directly from the
  top of README; show Linux/Kali/Ubuntu/Debian clone-and-install commands;
  state accurately that the Linux distribution uses `install.sh`, not a DEB/RPM.
  Use concise, non-exaggerated About copy and point its website to the Release.
- Acceptance: GitHub About visibly shows “凛枫SRC Harness” and an accurate
  Agent/Harness introduction, with its website pointed at Releases. The public
  README first screen exposes direct `v0.1.1-preview.3` Windows EXE, source
  archive, checksum file, and Linux command block. All three linked assets
  appeared on the published Release page; the Windows asset was downloaded
  from GitHub and matched the locally tested SHA-256.
