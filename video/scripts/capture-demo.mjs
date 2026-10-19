import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));
const demoDataPath = fileURLToPath(new URL('../public/demo-data.json', import.meta.url));

function captureReport(packageName, oldVersion, newVersion, format = 'terminal') {
  const args = [
    '-m', 'depdiff', 'npm', packageName, oldVersion, newVersion,
    '--fixtures-dir', 'fixtures',
  ];
  if (format !== 'terminal') {
    args.push('--format', format);
  }

  // Display a portable command even when PYTHON selects a local interpreter.
  const command = ['python3', ...args].join(' ');
  try {
    const content = execFileSync(process.env.PYTHON || 'python3', args, {
      cwd: repositoryRoot,
      shell: false,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONDONTWRITEBYTECODE: '1',
      },
    });
    return { command, content };
  } catch (error) {
    const detail = error.stderr?.toString().trim() || error.message;
    throw new Error(`DepDiff capture failed: ${command}\n${detail}`, { cause: error });
  }
}

function captureUpgrade(packageName, oldVersion, newVersion) {
  const terminal = captureReport(packageName, oldVersion, newVersion);
  const json = captureReport(packageName, oldVersion, newVersion, 'json');
  return {
    command: terminal.command,
    terminal: terminal.content,
    report: JSON.parse(json.content),
  };
}

/** Capture real offline CLI evidence, write stable UTF-8 JSON, and return it.
 * An optional destination lets tests capture without replacing the public data.
 */
export function captureDemo(destination = demoDataPath) {
  const data = {
    suspicious: captureUpgrade('demo-package', '1.0.0', '2.0.0'),
    benign: captureUpgrade('benign-package', '1.0.0', '1.1.0'),
    markdown: captureReport('demo-package', '1.0.0', '2.0.0', 'markdown'),
  };

  // Collect every report before writing, so a failed CLI leaves existing data intact.
  mkdirSync(dirname(destination), { recursive: true });
  writeFileSync(destination, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  return data;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    captureDemo();
    console.log('Captured demo evidence in video/public/demo-data.json');
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
