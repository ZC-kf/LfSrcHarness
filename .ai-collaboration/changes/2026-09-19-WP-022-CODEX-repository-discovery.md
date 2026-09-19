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
- Acceptance: public About text and link visible; README first screen exposes
  Windows EXE, source tarball, SHA-256 file, and Linux command block; public
  links resolve to the current Release. Tests and final state pending.
