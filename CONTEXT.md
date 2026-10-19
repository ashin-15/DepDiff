# MASTER BUILD PROMPT — depdiff

You are a senior software architect, Python engineer, DevSecOps engineer, and open-source maintainer.

Your task is to **design, implement, test, document, and package a complete working MVP of depdiff**, a developer tool for reviewing dependency upgrades and detecting suspicious behavioral changes in software packages.

**Do not stop at planning, scaffolding, or generating documentation. Build the actual working project.**

## 1. Project identity

**Name:** depdiff

**Full name:** Behavioral Dependency Security & Upgrade Review Tool

**Primary category:** Developer Tools & Open Source

**Secondary category:** Systems, Infrastructure & Cybersecurity

**Core question:**

"What changed when this dependency was upgraded, what new capabilities were introduced, and should the developer review those changes before merging?"

depdiff is an open-source CLI that compares two versions of a dependency based on their sensitive capabilities, installation behavior, and dependency metadata.

It should help developers understand dependency upgrades without manually reviewing thousands of lines of code.

It also identifies potential supply-chain security risks that may not yet have a known CVE.

**Important positioning:** This is BOTH a dependency upgrade review tool AND a behavioral supply-chain security analyzer. Neither aspect should be neglected.

It does not claim that a package is malicious or guaranteed safe. It provides explainable evidence for human review.

Read the attached product brief if available and use it as the authoritative specification. Where the brief proposes features beyond the contest MVP, follow the priorities below.

## 2. Development constraints

This project is being built for a buildathon.

**Submission deadline: October 20, 2026, 11:59 PM IST.**

Judges should be able to rebuild and test the application on a clean Linux environment using Docker.

The application must be reproducible, reliable, easy to run, and demonstrable offline.

All implementation work must be performed using OmniRush, in accordance with the competition's AI-tool requirements.

Prioritize a fully tested MVP over advanced features.

### Preferred technology stack

- Python for the CLI and core engine.
- Python standard library wherever practical.
- YAML for detection rules.
- Lightweight static source analysis for JavaScript.
- Docker for reproducible packaging.
- pytest or unittest for automated testing.
- JSON, Markdown, and human-readable terminal reporting.
- Git and GitHub for version control.

Use tree-sitter only if it can be integrated reliably without compromising the contest build.

Minimize dependencies. Pin all external dependencies, provide a lockfile, and ensure Docker builds consistently. Vendor required dependencies if necessary for offline rebuilds.

Do not introduce React, Next.js, databases, Redis, cloud infrastructure, or a web dashboard for the MVP.

## 3. Core CLI

Implement the command:

`depdiff npm <package> <old-version> <new-version>`

Example:

`depdiff npm axios 1.6.0 1.7.0`

For the MVP, the system must work against locally stored package fixtures without an internet connection.

Support a clear offline fixture selection option, and provide working example commands.

If registry retrieval is implemented, verify package integrity and cache downloaded artifacts. Never execute untrusted package code on the host machine.

Support flags for choosing output formats and output destinations.

Provide useful command-line help, validation errors, and nonzero exit codes for actual execution failures. Security verdicts should remain separate from execution failures unless an explicit policy option is configured.

## 4. Required analysis engine

Build a modular analysis pipeline.

### A. Package acquisition and validation

- Identify the package name and both versions.
- Resolve package contents from local fixtures.
- Optionally retrieve tarballs from npm if time permits.
- Read package metadata.
- Never run npm install scripts.
- Reject unsafe archive entries such as path traversal and escaping symlinks.
- Apply reasonable limits to extracted file counts and sizes.
- Keep execution of dependency code completely out of the static analysis pipeline.

### B. Dependency metadata comparison

Compare both versions' `package.json` files.

Detect:

- Newly added installation scripts.
- Removed or modified installation scripts.
- Changes to `preinstall`, `install`, and `postinstall`.
- Added dependencies.
- Removed dependencies.
- Changed dependency version specifications.
- Changes to declared entry points such as `main`, `bin`, and `exports`.

Summarize relevant metadata differences clearly for dependency reviewers.

### C. JavaScript capability analysis

Analyze JavaScript source files using configurable detection rules.

Detect these capability categories:

1. `network` — HTTP/HTTPS, fetch, sockets, DNS.
2. `fs` — filesystem access and file operations.
3. `process` — child process execution, spawning, shell commands.
4. `env` — environment variables and user information.
5. `dynamic-code` — eval, Function constructors, VM execution.
6. `crypto` — cryptographic APIs.
7. `install-script` — lifecycle scripts defined in package metadata.

Each finding should include:

- Capability category.
- Rule identifier.
- Severity.
- Source file and line number.
- Evidence snippet or API pattern.
- Reason why the behavior may deserve review.

Use sensible regular-expression or lightweight source-scanning rules for the first implementation.

Be transparent about false positives, aliases, obfuscation, and limitations of static analysis. Do not falsely claim complete AST accuracy or actual runtime execution.

### D. Capability diff engine

Compare the extracted capabilities of both versions.

Classify capabilities as:

- ADDED
- REMOVED
- UNCHANGED

New capabilities are the primary security-review signal.

Avoid repeatedly alerting users about capabilities already present in the previous version.

However, retain enough evidence to explain the differences and detect changed lifecycle scripts.

### E. Scoring and verdict engine

Implement a configurable, rule-based severity system.

Severity levels:

- HIGH
- MEDIUM
- LOW

Final verdicts:

- `ok`
- `review`
- `block-recommended`

Illustrative default policy:

- Newly introduced process spawning: high risk.
- Newly introduced dynamic-code execution: high risk.
- Newly introduced installation scripts: high risk.
- Newly introduced filesystem and network capabilities together: elevated risk.
- Newly introduced ordinary capabilities: review according to their rule severity.
- No new risky capabilities: `ok`.

Make the scoring deterministic, explainable, and testable.

Do not use an LLM for classification in the MVP.

The verdict is a review recommendation, not proof of safety or maliciousness.

## 5. YAML detection rules

Implement an external YAML-based rule system.

Each rule should define:

- Unique rule ID.
- Detection pattern.
- Capability category.
- Default severity.
- Human-readable description.

Requirements:

- Rules load at runtime.
- Invalid rules produce useful errors.
- Rules are separated from detection engine code.
- Adding a new valid detection rule does not require modifying the core engine.

Ship initial rules covering all seven capability categories, including metadata-based handling for install scripts.

Each rule should have at least one positive and one negative test fixture.

## 6. Reporting system

Implement three usable report formats.

### A. Terminal report

Display:

- Package name.
- Old and new version.
- Overall verdict.
- Added capabilities.
- Removed capabilities.
- Relevant metadata changes.
- Severity.
- Evidence location.
- Explanation for each important finding.

The output should resemble a concise dependency upgrade review.

### B. JSON report

Produce deterministic, machine-readable structured output.

Use stable field names and sorting.

Include package information, capability differences, findings, metadata changes, and the verdict.

### C. Markdown report

Generate a review-friendly Markdown summary suitable for attaching to a dependency-update pull request.

This is an important demonstration feature.

Keep reporting logic separate from analysis logic.

## 7. Architecture

Use a modular structure similar to:

depdiff/
- CLI and argument handling.
- Package acquisition and local fixture handling.
- Metadata analyzer.
- Static capability analyzer.
- YAML rule loader.
- Capability diff engine.
- Severity and verdict engine.
- Terminal reporter.
- JSON reporter.
- Markdown reporter.
- Shared data models and utilities.

Also create:

- tests/
- fixtures/
- rules/
- docs/
- Dockerfile
- Makefile
- README.md
- Dependency lockfile
- .gitignore
- .env.example if configuration requires environment variables
- AGENTS.md or equivalent contributor guidance
- ARCHITECTURE.md

Adjust naming to normal Python packaging conventions.

Avoid unnecessary abstractions, microservices, or overly complex plugin architectures.

## 8. Automated tests

Tests are a mandatory deliverable, not an optional enhancement.

Create meaningful unit and integration tests for:

- Package metadata extraction.
- Install-script additions, removals, and changes.
- Dependency differences.
- Rule loading and rule validation.
- Each capability detection rule.
- Added, removed, and unchanged capability classification.
- Severity scoring.
- Final verdicts.
- JSON serialization.
- Markdown generation.
- Invalid arguments and malformed input.
- Unsafe archive handling.
- Offline execution.

Include at least:

- Two or three suspicious-upgrade fixture scenarios.
- One or two benign-upgrade fixture scenarios.

Use synthetic, harmless files to model potentially malicious behaviors. Never execute malicious samples during testing.

Historical incident reproductions can be added when accurately sourced, but do not label synthetic fixtures as confirmed historical incidents.

All required tests must run without internet access.

Provide one command, ideally:

`make test`

The command must execute the relevant test suite and fail with a nonzero status if tests fail.

## 9. Docker and judge reproducibility

Create a production-appropriate Dockerfile for running the CLI and tests.

Requirements:

- Explicitly pinned Python runtime.
- Reproducible dependency installation.
- No secrets.
- No machine-specific absolute paths.
- No dependency on developer-local configuration.
- Clear working directory.
- Non-root execution where practical.
- Offline execution of the included fixtures and tests.
- Documented build, run, and test commands.

Distinguish between offline runtime/testing and offline image building. If image building needs previously cached base layers or vendored packages, document the requirement and eliminate unnecessary network dependencies.

Verify clean-container behavior rather than assuming local success means the build is portable.

## 10. Demo requirements

Prepare a demonstration that clearly shows depdiff's usefulness.

**Demo A — Suspicious upgrade**

An earlier package version performs ordinary operations.

The updated version introduces process execution, a new postinstall script, or another suspicious capability.

depdiff detects the change, presents evidence, and recommends review or blocking.

**Demo B — Benign upgrade**

A package receives ordinary changes without gaining sensitive capabilities.

depdiff returns `ok` rather than generating unnecessary security alerts.

**Demo C — Pull-request review**

Generate a Markdown report showing the dependency upgrade summary and its security findings.

All demonstrations must be reproducible from the repository with documented commands.

## 11. README and documentation

Create a professional GitHub README covering:

1. The problem depdiff solves.
2. What makes it useful for dependency upgrade reviews.
3. Its supply-chain security value.
4. Features actually implemented.
5. Architecture.
6. Installation.
7. Quick start.
8. Example CLI commands.
9. Sample output.
10. Docker build and execution.
11. Offline testing.
12. Detection rules and extension guidance.
13. Security model and limitations.
14. Planned improvements.

Explain how depdiff complements npm audit, Dependabot, Snyk, and similar tools.

Do not claim capability analysis is entirely new. Highlight depdiff's open-source, version-to-version comparison, local execution, community-editable rules, and evidence-driven reporting.

Avoid fabricated benchmarks, accuracy claims, test results, or incident coverage.

## 12. Implementation phases

Work in the following order.

### PHASE 1 — Foundation

- Inspect the current repository.
- Read the product brief.
- Define the minimal architecture and data models.
- Set up Python packaging and CLI.
- Implement offline fixture loading.
- Implement package.json metadata comparison.
- Add initial tests.

**Deliverable:** A working CLI that compares metadata between two fixtures.

### PHASE 2 — Capability detection

- Implement the YAML rule loader.
- Implement static JavaScript capability detection.
- Add source evidence and line numbers.
- Build capability comparison.
- Add tests for each rule.

**Deliverable:** Real added/removed/unchanged capability results.

### PHASE 3 — Security intelligence

- Implement deterministic severity scoring.
- Implement verdict generation.
- Handle capability combinations.
- Add regression tests.

**Deliverable:** Explainable upgrade review decisions.

### PHASE 4 — Reporting

- Build terminal reporting.
- Build JSON reporting.
- Build Markdown reporting.
- Validate output accuracy and determinism.

**Deliverable:** Three working reporting formats.

### PHASE 5 — Packaging

- Complete Dockerfile.
- Pin dependencies and produce a lockfile.
- Create Makefile.
- Complete README and architecture documentation.
- Validate offline execution.
- Verify clean Linux reproducibility.

**Deliverable:** Judge-ready project.

### PHASE 6 — Final validation

- Run every automated test.
- Run suspicious and benign demo scenarios.
- Generate example reports.
- Inspect the repository for leaked secrets.
- Confirm no absolute machine-specific paths.
- Check that all documented commands work.
- Produce a final implementation and verification report.

**Deliverable:** A reproducible submission with documented evidence.

## 13. Time management and priorities

Because the deadline is close, use the following priority levels.

**P0 — Mandatory**

- Working CLI.
- Offline package fixtures.
- Metadata comparison.
- YAML detection rules.
- Static JavaScript capability detection.
- Capability diffing.
- Severity and verdict calculation.
- Terminal/JSON/Markdown reports.
- Automated tests.
- Dockerfile, pinned dependencies, README.
- Working offline demonstration.

**P1 — Only after P0 is verified**

- npm registry retrieval and local cache.
- Configuration and allowlists.
- Obfuscation indicators.
- Additional detection rules.
- More representative test fixtures.

**P2 — Explicitly postpone**

- GitHub Actions integration.
- PyPI support.
- SARIF integration.
- Dynamic sandbox tracing.
- eBPF.
- Lockfile-wide dependency analysis.
- Web dashboards.
- Hosted services.
- LLM summaries.

Do not sacrifice P0 reliability to implement P1 or P2.

## 14. Agent execution rules

Follow these instructions throughout development.

1. First inspect the existing files rather than replacing working code.
2. Briefly state the immediate implementation plan.
3. Start writing and integrating actual project files.
4. Complete one functional milestone at a time.
5. Execute relevant tests after each milestone.
6. Fix errors instead of merely listing them.
7. Prefer simple, robust solutions over complex ones.
8. Do not leave core features as placeholders, fake implementations, or TODOs.
9. Keep changes focused and maintainable.
10. Never execute downloaded dependency code directly on the host.
11. Never report a feature or test as completed without verifying it.
12. If a command fails, record the failure and fix it before advancing when possible.
13. Maintain a concise milestone checklist and progress record.
14. Use Git commits at meaningful, working checkpoints.
15. Preserve evidence of meaningful OmniRush development sessions for the submission.
16. Document known limitations accurately.

Do not repeatedly ask for approval between milestones unless a decision is genuinely blocking or potentially destructive.

## 15. Acceptance criteria

The MVP is considered complete only when:

- A developer can compare two dependency versions.
- The tool detects new sensitive capabilities.
- It reports actual supporting source locations where available.
- It distinguishes suspicious upgrades from benign upgrades in the test fixtures.
- It produces all three requested report formats.
- Rules are externally configurable through YAML.
- It can be executed and tested offline.
- The Docker configuration is verified.
- The README contains working reproduction steps.
- All required tests pass.
- The project has no dependency on unavailable local credentials or services.

If an acceptance criterion cannot be completed, explicitly identify the limitation instead of marking it complete.

## 16. Final output required

When implementation and testing are finished, generate a `FINAL_BUILD_REPORT.md` containing:

- Implemented features.
- Project architecture.
- File inventory.
- Exact commands to install, run, and test.
- Docker verification.
- Test results and any failures.
- Demo scenarios.
- Known limitations.
- Unimplemented scope.
- Submission readiness checklist.

Also provide a concise summary of the finished system and its most important demonstration command.

## START NOW

Begin by inspecting the workspace and available product brief.

Create a concise implementation plan, then immediately implement PHASE 1.

Continue systematically through the mandatory phases, running tests and resolving failures as you go.

**The objective is not to generate an impressive plan. The objective is to deliver a real, working, tested, open-source developer tool that helps people review dependency upgrades and detect unexpected security-sensitive behavior.**
