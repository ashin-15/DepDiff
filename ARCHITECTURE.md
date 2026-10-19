# depdiff architecture

depdiff is a local, read-only analysis pipeline. It never imports or executes
package code. Each stage produces immutable data models so the CLI and report
formats remain separate from analysis logic.

## Pipeline

```text
CLI arguments
    -> FixtureStore
        -> path, symlink, size, and package.json validation
    -> RuleSet
        -> external YAML parsing and regex validation
    -> scan_package(old), scan_package(new)
        -> JavaScript text findings
        -> lifecycle metadata findings
    -> compare_metadata
    -> compare_capabilities
    -> assess_upgrade
    -> terminal/json/markdown reporter
```

## Modules

- `depdiff/cli.py`: public command parsing, default selection, clean error
  handling, and output destinations.
- `depdiff/fixtures.py`: local fixture resolution, directory limits, and safe
  tar extraction helpers. It does not install packages.
- `depdiff/metadata.py`: strict `package.json` parsing and comparison of
  lifecycle scripts, dependency sections, and entry points.
- `depdiff/rules.py`: constrained YAML rule parser, schema validation, and
  regular-expression compilation.
- `depdiff/capabilities.py`: read-only source scanning and category-level
  capability comparison.
- `depdiff/analysis.py`: orchestration for one old/new upgrade pair.
- `depdiff/scoring.py`: deterministic review recommendation policy.
- `depdiff/reporters.py`: terminal, JSON, and Markdown rendering.
- `depdiff/models.py`: immutable metadata, finding, diff, assessment, and
  aggregate analysis models.
- `depdiff/build_backend.py`: project-local dependency-free wheel backend.

## Fixture contract

The CLI expects:

```text
<fixtures-dir>/npm/<package>/<version>/package.json
```

Scoped package names use two components, such as `@scope/name`. The requested
package and version must exactly match the fields in `package.json`. Directory
fixtures are resolved inside the configured root and symlinks are rejected.
The selected tree is checked against file-count and total-size limits.

`extract_safe_tarball()` is available for archive materialization. It rejects
absolute paths, `..` traversal, backslashes, symlinks, hardlinks, special files,
member-count limits, and total-size limits. It writes bytes only for regular
files and directories. No extracted file is executed.

## Metadata model

`PackageMetadata` retains only fields relevant to upgrade review:

- `scripts`, with special comparison for `preinstall`, `install`, and
  `postinstall`;
- `dependencies`, `optionalDependencies`, `peerDependencies`, and
  `devDependencies`;
- `main`, `bin`, and `exports` entry points.

Changes are represented as added, removed, or modified values. JSON object
ordering is preserved for `exports` because conditional export order can affect
Node.js resolution.

## Rule and scanner model

Rules are external and contain an ID, category, severity, regex pattern, and
description. JavaScript rules match source one line at a time. Metadata rules
match normalized lifecycle keys and report the corresponding `package.json`
line. Every finding contains:

```text
capability, rule_id, severity, source_file, line, evidence, reason
```

The scanner supports `.js`, `.mjs`, `.cjs`, and `.jsx`. Findings are sorted by
capability, path, line, rule, severity, evidence, and reason. Capability diffing
is category-based: a category present in both versions is `UNCHANGED` even if
its evidence moved, while old and new evidence remain available.

This is intentionally not an AST or runtime analysis. Comments, strings,
aliases, generated code, unusual formatting, obfuscation, and dynamic API
selection can cause false positives or missed findings.

## Scoring policy

New evidence contributes deterministic weights: LOW=1, MEDIUM=2, HIGH=3.
New `process`, `dynamic-code`, or `install-script` capabilities, or any new
HIGH finding, produce `block-recommended`. New ordinary findings produce
`review`. Newly introduced `fs` and `network` together add an elevated review
signal. Modified lifecycle scripts produce `review` even when the lifecycle
category existed before. If no new capability or modified lifecycle signal is
present, the recommendation is `ok`.

The score and reasons are visible in every report. Existing capabilities are
not repeatedly scored as new risk.

## Packaging and reproducibility

The project pins Python 3.11.2 and has no third-party dependency. The local PEP
517 backend builds a pure-Python wheel with normalized timestamps and includes
the external default rules. `Dockerfile` uses a pinned Debian-based Python
image, installs from the local source with `--no-index`, and runs the CLI as a
non-root user. The Docker base image itself must be cached locally or fetched
when an image is first built.
