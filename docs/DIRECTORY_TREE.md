# Project Tree

```text
LfSrcHarness/
|-- .ai-collaboration/
|   |-- SCHEME_SELECTION_RECORD.md
|   |-- PROJECT_PLAN.md
|   |-- PROJECT_SUMMARY.md
|   `-- changes/
|-- .github/workflows/ci.yml
|-- CONTRIBUTING.md
|-- LICENSE.md
|-- SECURITY.md
|-- deploy/                    # Compose, Ansible, VM, systemd, K8s, installers
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- ASSUMPTIONS.md
|   |-- DIRECTORY_TREE.md
|   |-- INSTALL.md
|   |-- USAGE.md
|   |-- CHANGELOG.md
|   |-- TEST_REPORT.md
|   |-- THIRD_PARTY.md
|   |-- README.md
|   `-- SPEC.md
|-- package/                   # source, image, wheel, EXE, docs, checksums
|-- plugins/                   # example manifests/adapters
|-- runs/                      # runtime data, excluded from packages
|-- src/lfsrc_harness/          # core Python package and protobuf contract
|-- tests/reports/             # JUnit, coverage XML, HTML coverage
|-- web/                       # React and Vite console
|-- .dockerignore
|-- .gitignore
|-- pyproject.toml
|-- uv.lock
`-- README.md
```

The Agent copy was initially verified against the upstream by file count and SHA-256; its
dashboard was then adapted and private runtime files excluded. The internal tree is not
expanded into this human-facing map.
