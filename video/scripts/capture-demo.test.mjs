import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { captureDemo } from './capture-demo.mjs';

const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));
const videoRoot = fileURLToPath(new URL('../', import.meta.url));
const publicDataPath = fileURLToPath(new URL('../public/demo-data.json', import.meta.url));
const suspiciousCommand = 'python3 -m depdiff npm demo-package 1.0.0 2.0.0 --fixtures-dir fixtures';
const benignCommand = 'python3 -m depdiff npm benign-package 1.0.0 1.1.0 --fixtures-dir fixtures';
const disclaimer = 'This is an explainable review recommendation, not proof of maliciousness or safety.';
const expectedFindings = [
  {
    capability: 'fs',
    evidence: "fs.readFileSync('/etc/hostname', 'utf8');",
    line: 5,
    reason: 'Filesystem access can read or modify files outside the package source tree.',
    rule_id: 'fs-file-operation',
    severity: 'MEDIUM',
    source_file: 'lib/index.js',
  },
  {
    capability: 'install-script',
    evidence: 'scripts.postinstall: node scripts/setup.js',
    line: 10,
    reason: 'Lifecycle scripts run during package installation and can perform actions before a reviewer runs the package.',
    rule_id: 'install-script-lifecycle',
    severity: 'HIGH',
    source_file: 'package.json',
  },
  {
    capability: 'process',
    evidence: "exec('echo setup');",
    line: 6,
    reason: 'Process execution can invoke shell commands and affect the host outside the JavaScript runtime.',
    rule_id: 'process-child-process',
    severity: 'HIGH',
    source_file: 'lib/index.js',
  },
];

let temporaryDirectory;
let firstPath;
let secondPath;
let first;
let second;

before(() => {
  temporaryDirectory = mkdtempSync(join(tmpdir(), 'depdiff-demo-'));
  firstPath = join(temporaryDirectory, 'first', 'demo-data.json');
  secondPath = join(temporaryDirectory, 'second', 'demo-data.json');
  first = captureDemo(firstPath);
  second = captureDemo(secondPath);
});

after(() => {
  if (temporaryDirectory) {
    rmSync(temporaryDirectory, { recursive: true, force: true });
  }
});

test('two captures are byte-identical and match the public UTF-8 artifact', () => {
  const bytes = readFileSync(firstPath);
  assert.deepEqual(bytes, readFileSync(secondPath));
  assert.deepEqual(bytes, readFileSync(publicDataPath));
  assert.deepEqual(first, second);
  assert.deepEqual(JSON.parse(bytes.toString('utf8')), first);
  assert.equal(bytes.toString('utf8'), `${JSON.stringify(first, null, 2)}\n`);

  assert.deepEqual(Object.keys(first), ['suspicious', 'benign', 'markdown']);
  for (const entry of [first.suspicious, first.benign]) {
    assert.deepEqual(Object.keys(entry), ['command', 'terminal', 'report']);
  }
  assert.deepEqual(Object.keys(first.markdown), ['command', 'content']);
  assert.equal(first.suspicious.command, suspiciousCommand);
  assert.equal(first.benign.command, benignCommand);
  assert.equal(first.markdown.command, `${suspiciousCommand} --format markdown`);

  const serialized = bytes.toString('utf8');
  assert.ok(!serialized.includes(repositoryRoot));
  assert.ok(!serialized.includes(videoRoot));
  assert.ok(!serialized.includes(temporaryDirectory));
  assert.doesNotMatch(serialized, /\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
});

test('suspicious evidence retains the actual score, capabilities, locations, and metadata', () => {
  const { report, terminal } = first.suspicious;
  assert.deepEqual(report.package, {
    name: 'demo-package', old_version: '1.0.0', new_version: '2.0.0',
  });
  assert.deepEqual(report.assessment, {
    reasons: [
      'Added fs capability with 1 evidence finding(s).',
      'Added install-script capability with 1 evidence finding(s).',
      'Added process capability with 1 evidence finding(s).',
    ],
    score: 8,
    severity: 'HIGH',
    verdict: 'block-recommended',
  });
  assert.deepEqual(report.capabilities.old, { capabilities: [], findings: [] });
  assert.deepEqual(report.capabilities.new, {
    capabilities: ['fs', 'install-script', 'process'],
    findings: expectedFindings,
  });
  const added = expectedFindings.map((finding) => ({
    capability: finding.capability,
    change: 'ADDED',
    findings: [finding],
    new_findings: [finding],
    old_findings: [],
  }));
  assert.deepEqual(report.capabilities.diff, {
    added, changes: added, removed: [], unchanged: [],
  });
  assert.deepEqual(report.metadata_diff.lifecycle_scripts, [{
    area: 'lifecycle-script',
    change: 'added',
    name: 'postinstall',
    new_value: 'node scripts/setup.js',
    old_value: null,
  }]);
  assert.equal(report.metadata_diff.changes.length, 6);
  assert.ok(terminal.includes('Verdict: block-recommended\nRisk score: 8\n'));
  for (const finding of expectedFindings) {
    assert.ok(terminal.includes(`${finding.source_file}:${finding.line}:`));
    assert.ok(terminal.includes(`evidence: ${finding.evidence}`));
  }
  assert.ok(terminal.includes(disclaimer));
});

test('benign evidence reports ok with zero score and no added capability signals', () => {
  const { report, terminal } = first.benign;
  assert.deepEqual(report.package, {
    name: 'benign-package', old_version: '1.0.0', new_version: '1.1.0',
  });
  assert.deepEqual(report.assessment, {
    reasons: ['No new capability evidence or modified lifecycle scripts were found.'],
    score: 0,
    severity: null,
    verdict: 'ok',
  });
  assert.deepEqual(report.capabilities, {
    diff: { added: [], changes: [], removed: [], unchanged: [] },
    new: { capabilities: [], findings: [] },
    old: { capabilities: [], findings: [] },
  });
  assert.deepEqual(report.metadata_diff, {
    changes: [], dependencies: [], entry_points: [], lifecycle_scripts: [],
  });
  assert.ok(terminal.includes('Verdict: ok\nRisk score: 0\n'));
  assert.ok(terminal.includes('New capability evidence:\n- none\n'));
  assert.ok(terminal.includes(disclaimer));
});

test('Markdown contains the real review, capability table, and source evidence', () => {
  const { content } = first.markdown;
  assert.ok(content.startsWith('# depdiff review: `demo-package` 1.0.0 -> 2.0.0\n'));
  assert.ok(content.includes('**Verdict:** `block-recommended`'));
  assert.ok(content.includes('**Risk score:** `8`'));
  assert.ok(content.includes('**Highest new severity:** `HIGH`'));
  assert.ok(content.includes('## Metadata changes'));
  assert.ok(content.includes('`lifecycle-script:postinstall` (new `node scripts/setup.js`)'));
  for (const finding of expectedFindings) {
    assert.ok(content.includes(`| \`${finding.capability}\` | **ADDED** | 1 |`));
    assert.ok(content.includes(`\`${finding.source_file}:${finding.line}\``));
    assert.ok(content.includes(`Evidence: \`${finding.evidence}\``));
  }
  assert.ok(content.includes('## Assessment'));
  assert.ok(content.includes(disclaimer));
  assert.ok(content.endsWith('\n'));
});

test('every captured output matches its runnable real CLI command', () => {
  function run(command) {
    const [python, ...args] = command.split(' ');
    assert.equal(python, 'python3');
    return execFileSync(process.env.PYTHON || python, args, {
      cwd: repositoryRoot,
      shell: false,
      encoding: 'utf8',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1' },
    });
  }

  for (const entry of [first.suspicious, first.benign]) {
    assert.equal(entry.terminal, run(entry.command));
    assert.deepEqual(entry.report, JSON.parse(run(`${entry.command} --format json`)));
  }
  assert.equal(first.markdown.content, run(first.markdown.command));
});

test('the script regenerates identical bytes from the repository root and video directory', () => {
  const expected = readFileSync(firstPath);
  for (const [cwd, script] of [
    [repositoryRoot, 'video/scripts/capture-demo.mjs'],
    [videoRoot, 'scripts/capture-demo.mjs'],
  ]) {
    execFileSync(process.execPath, [script], { cwd, shell: false });
    assert.deepEqual(readFileSync(publicDataPath), expected);
  }
});

test('PYTHON is honored and a failed capture preserves existing data', () => {
  const previousPython = process.env.PYTHON;
  const existing = readFileSync(firstPath);
  const missingDestination = join(temporaryDirectory, 'missing.json');
  try {
    process.env.PYTHON = join(temporaryDirectory, 'missing python');
    assert.throws(() => captureDemo(firstPath), /DepDiff capture failed:/);
    assert.deepEqual(readFileSync(firstPath), existing);
    assert.throws(() => captureDemo(missingDestination), /DepDiff capture failed:/);
    assert.equal(existsSync(missingDestination), false);
  } finally {
    if (previousPython === undefined) {
      delete process.env.PYTHON;
    } else {
      process.env.PYTHON = previousPython;
    }
  }
});
