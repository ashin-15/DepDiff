# depdiff

**Behavioral Dependency Security & Upgrade Review Tool**

depdiff compares two versions of an npm dependency and explains what changed
in package metadata and statically visible JavaScript capabilities. It is built
for a practical review question:

> What changed in this dependency upgrade, what new capabilities appeared, and
> should a developer review those changes before merging?

depdiff is both an upgrade-review tool and a supply-chain security analyzer. It
does not claim that a package is malicious or guaranteed safe. It produces
deterministic evidence and a review recommendation for a human maintainer.

## Why use it

Vulnerability databases and update bots answer important questions, but they do
not always show behavioral differences between two package versions. depdiff
adds a local, version-to-version view of:

- lifecycle installation scripts;
- dependency and entry-point metadata changes;
- newly visible network, filesystem, process, environment, dynamic-code, and
  cryptographic capabilities;
- exact source locations, line numbers, evidence snippets, and review reasons.

It complements `npm audit`, Dependabot, Snyk, and similar tools. Those tools can
identify known advisories, outdated packages, or broader dependency risk.
depdiff focuses on explainable behavioral deltas, including changes that do not
yet have a known CVE. It is not a replacement for those tools.

## Implemented MVP

- Python 3.11 CLI: `depdiff npm <package> <old-version> <new-version>`.
- Offline directory fixtures with package name/version validation.
- Safe fixture path checks, file-count and size limits, and safe tar archive
  extraction helpers that reject traversal, links, and special files.
- `package.json` comparison for lifecycle scripts, dependency sections, and
  `main`, `bin`, and `exports` entry points.
- External YAML rules loaded at runtime without executing package code.
- Read-only regular-expression scanning of `.js`, `.mjs`, `.cjs`, and `.jsx`.
- Findings with category, rule ID, severity, file, line, evidence, and reason.
- Added, removed, and unchanged capability classification.
- Deterministic scoring and `ok`, `review`, or `block-recommended` verdicts.
- Terminal, JSON, and Markdown reports.
- Standard-library-only tests and a Docker image definition.

## Rebuild from a clean Linux machine

The Docker workflow is the canonical rebuild path when the host does not have
Python or the project tools installed. From the root of a clean checkout:

```console
$ docker build --tag depdiff:local .
$ docker run --rm --entrypoint python depdiff:local \
    -m unittest discover --start-directory /app/tests --verbose
$ docker run --rm depdiff:local npm demo-package 1.0.0 2.0.0 \
    --fixtures-dir /app/fixtures
```

The image build uses the pinned Python `3.11.2` Bookworm base image and installs
the local package with no package index. The initial build needs access to that
base image, either from a local Docker cache or the container registry. After
the image is available, the test and demo commands are offline.

## Quick start

The repository pins Python with `.python-version` and uses no third-party
runtime or test dependencies. `requirements.lock` is intentionally an empty
lockfile because the project uses only the Python standard library. From the
repository root:

```console
$ make test
$ make demo-suspicious
$ make demo-benign
$ make demo-markdown
```

The most useful demonstration command is:

```console
$ python3 -m depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures
```

The synthetic upgrade introduces a `postinstall` script, filesystem access,
and child-process execution. The output includes evidence and recommends
`block-recommended`. The fixture is harmless and is never executed.

The benign scenario remains `ok`:

```console
$ python3 -m depdiff npm benign-package 1.0.0 1.1.0 --fixtures-dir fixtures
```

## Installation

For local development, running `python3 -m depdiff` does not require an
installation. To install the console command into a virtual environment:

```console
$ python3 -m venv .venv
$ .venv/bin/python -m pip install --no-index --no-deps .
$ .venv/bin/depdiff --help
```

The required local runtime is exactly Python `3.11.2`, as recorded in
`.python-version` and `pyproject.toml`. The `.env.example` file contains only
non-secret process defaults; depdiff does not require an `.env` file, API key,
database, or other external service.

The project-local PEP 517 backend has no build requirements, so this command
does not need a package index. The same package can be built and installed in a
clean Python 3.11.2 environment.

## CLI and reports

```console
$ depdiff npm --help
$ depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures
$ depdiff npm demo-package 1.0.0 2.0.0 \
    --fixtures-dir fixtures --format json --output reports/review.json
$ depdiff npm demo-package 1.0.0 2.0.0 \
    --fixtures-dir fixtures --format markdown --output reports/review.md
```

Options:

- `--fixtures-dir PATH`: local root containing `npm/<package>/<version>`;
- `--rules PATH`: replace the shipped rules with a local YAML rule file;
- `--format terminal|json|markdown`: choose the report format;
- `--output PATH`: write the report to a file, creating parent directories.

Execution failures, such as a missing fixture or invalid rule file, return a
nonzero exit code. A security verdict is printed as report data and does not
itself turn a successful analysis into an execution failure.

The JSON report has stable field names and ordering. Markdown is suitable for
attaching to a dependency-update pull request. Terminal output is intentionally
concise but includes evidence locations and assessment reasons.

## Offline fixture layout

```text
fixtures/
└── npm/
    └── <package-name>/
        └── <version>/
            ├── package.json
            └── source files
```

Scoped npm names use two path components, for example
`fixtures/npm/@scope/name/1.0.0/package.json`. The loader validates that the
metadata name and version match the requested fixture. It rejects traversal,
escaping paths, symlinks, oversized metadata, malformed JSON, and fixture
trees over configured file/size limits.

The implementation never runs `npm install`, lifecycle scripts, JavaScript,
imports, subprocesses, or downloaded package code. It makes no network request.

## Rules and static analysis

Default rules are in [`rules/default.yaml`](rules/default.yaml). The loader
supports a deliberately small, reviewable YAML subset with:

```yaml
version: 1
rules:
  - id: custom-network
    capability: network
    severity: MEDIUM
    pattern: '\\brequest\\s*\\('
    description: 'Finds a custom request call.'
    reason: 'Network access deserves review.'
```

Each rule requires a unique `id`, `capability`, `severity`, `pattern`, and
`description`. Optional `reason`, `source`, and regex `flags` are supported.
`source` is `javascript` by default or `metadata` for lifecycle entries. The
seven shipped capability categories are `network`, `fs`, `process`, `env`,
`dynamic-code`, `crypto`, and `install-script`.

The scanner is intentionally lightweight regular-expression analysis. It can
produce false positives in comments, strings, aliases, generated code, or
unusual formatting, and can miss obfuscation, dynamic API selection, and
runtime-only behavior. It is not an AST or runtime sandbox.

## Architecture

```text
CLI
  -> FixtureStore and metadata validation
  -> YAML RuleSet
  -> read-only JavaScript and lifecycle scanning
  -> metadata and capability diffing
  -> deterministic scoring/verdict
  -> terminal, JSON, or Markdown reporter
```

Details and extension points are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Docker

The Dockerfile uses the pinned `python:3.11.2-slim-bookworm` base image, installs
the local package without an index, and runs as a non-root user:

```console
$ docker build --tag depdiff:local .
$ docker run --rm depdiff:local npm demo-package 1.0.0 2.0.0 \
    --fixtures-dir /app/fixtures
$ docker run --rm depdiff:local --help
$ docker run --rm --entrypoint python depdiff:local \
    -m unittest discover --start-directory /app/tests --verbose
```

The image build needs the pinned base image available locally or access to the
container registry for that base layer. Runtime analysis and the full test
suite use only files included in this repository and require no network. The
`.dockerignore` file excludes Git metadata, local virtual environments,
generated reports, caches, and `.env` files from the build context.

## Testing and reproducibility

Run the one project test command:

```console
$ make test
```

The suite covers metadata parsing and diffs, rule validation, positive and
negative capability fixtures, capability classification, scoring, all report
formats, CLI failures, offline execution, safe archive handling, and
reproducible wheel builds. Tests use synthetic harmless samples and do not
execute them.

## Security model and limitations

depdiff is evidence for human review. `ok` means that the configured static
analysis found no newly introduced capability signal under the default policy;
it is not a guarantee of safety. `review` and `block-recommended` are policy
recommendations, not proof of maliciousness.

The MVP does not retrieve npm registry packages, inspect lockfile-wide graphs,
perform dynamic tracing, run a sandbox, or prove semantic equivalence. Tar
archive validation is available for safe static materialization, but no package
archive is installed or executed.

## Planned improvements

Possible follow-on work includes verified npm registry retrieval and caching,
more AST-aware analysis, obfuscation indicators, allowlists, SARIF output,
lockfile-wide comparison, and CI integrations. These are intentionally outside
the current offline MVP.

## License

MIT. See the project metadata for the current package version.
