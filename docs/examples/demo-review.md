# depdiff review: `demo-package` 1.0.0 -> 2.0.0

**Verdict:** `block-recommended`<br>
**Risk score:** `8`<br>
**Highest new severity:** `HIGH`

> This is an explainable review recommendation, not proof of maliciousness or safety.

## Capability changes

| Capability | Status | Evidence count |
| --- | --- | ---: |
| `fs` | **ADDED** | 1 |
| `install-script` | **ADDED** | 1 |
| `process` | **ADDED** | 1 |

## Metadata changes

- **modified** `dependency:dependencies:chalk` (old `^4.1.0`; new `^5.0.0`)
- **removed** `dependency:dependencies:debug` (old `^4.3.0`)
- **added** `dependency:dependencies:left-pad` (new `^1.3.0`)
- **added** `entry-point:bin` (new `{"demo":"bin/demo.js"}`)
- **modified** `entry-point:main` (old `index.js`; new `lib/index.js`)
- **added** `lifecycle-script:postinstall` (new `node scripts/setup.js`)

## New capability evidence

- **MEDIUM** `fs` via `fs-file-operation` at `lib/index.js:5` - Filesystem access can read or modify files outside the package source tree.

  Evidence: `fs.readFileSync('/etc/hostname', 'utf8');`
- **HIGH** `install-script` via `install-script-lifecycle` at `package.json:10` - Lifecycle scripts run during package installation and can perform actions before a reviewer runs the package.

  Evidence: `scripts.postinstall: node scripts/setup.js`
- **HIGH** `process` via `process-child-process` at `lib/index.js:6` - Process execution can invoke shell commands and affect the host outside the JavaScript runtime.

  Evidence: `exec('echo setup');`

## Assessment

- Added fs capability with 1 evidence finding(s).
- Added install-script capability with 1 evidence finding(s).
- Added process capability with 1 evidence finding(s).
