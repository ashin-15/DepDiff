const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = { scenarios: [], scenario: null, format: 'visual', finding: null };
let toastTimeout;
let loading = false;
let renderVersion = 0;
let scrollFrame;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

function replayClass(element, className) {
  if (!element) return;
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
}

function clamp(value, minimum = 0, maximum = 1) {
  return Math.min(maximum, Math.max(minimum, value));
}

function notify(message) {
  clearTimeout(toastTimeout);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  toastTimeout = setTimeout(() => { $('#toast').hidden = true; }, 4000);
}

function setPressed(selector, attribute, value) {
  $$(selector).forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset[attribute] === value));
  });
}

function reportText(format = state.format) {
  if (!state.scenario) return '';
  if (format === 'terminal') return state.scenario.terminal;
  if (format === 'markdown') return state.scenario.markdown;
  return `${JSON.stringify(state.scenario.report, null, 2)}\n`;
}

function renderFormat() {
  const visual = state.format === 'visual';
  $('#visual-report').hidden = !visual;
  $('#raw-report').hidden = visual;
  $('#raw-output').textContent = visual ? '' : reportText();
  $('#raw-report').setAttribute('aria-label', `${state.format} report`);
  $('#raw-report').scrollTop = 0;
  $('#download-format').textContent = visual ? 'JSON' : state.format === 'markdown' ? 'Markdown' : state.format === 'json' ? 'JSON' : 'TXT';
  setPressed('[data-format]', 'format', state.format);
}

function renderEvidence(change) {
  state.finding = change?.capability ?? null;
  $$('.finding-button').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.finding === state.finding));
  });
  const finding = change?.findings[0];
  if (!finding) {
    $('#evidence-location').textContent = 'No new capability findings';
    $('#evidence-rule').textContent = 'Default policy';
    $('#evidence-change').textContent = 'No new static capability signal';
    $('#evidence-line').textContent = '✓';
    $('#evidence-code').textContent = 'No sensitive capability category was added.';
    $('#evidence-reason').textContent = 'This comparison did not introduce a capability signal under the configured rules. An ok verdict is not a guarantee of safety; static analysis has limits.';
    replayClass($('#evidence-line'), 'is-fresh');
    return;
  }
  $('#evidence-location').textContent = `${finding.source_file}:${finding.line}`;
  $('#evidence-rule').textContent = finding.rule_id;
  const changes = { ADDED: '+ Newly introduced capability', REMOVED: '− Capability removed from this version', UNCHANGED: '= Previously present capability' };
  $('#evidence-change').textContent = changes[change.change];
  $('#evidence-line').textContent = finding.line;
  $('#evidence-code').textContent = finding.evidence;
  $('#evidence-reason').textContent = finding.reason;
  replayClass($('#evidence-line'), 'is-fresh');
}

function renderFindings(report) {
  const diff = report.capabilities.diff;
  const changes = [...diff.changes];
  const order = ['install-script', 'process', 'fs', 'network', 'env', 'dynamic-code', 'crypto'];
  changes.sort((a, b) => order.indexOf(a.capability) - order.indexOf(b.capability));
  const counts = [
    [diff.added.length, 'added'], [diff.removed.length, 'removed'], [diff.unchanged.length, 'unchanged'],
  ].filter(([count]) => count).map(([count, label]) => `${count} ${label}`);
  $('#change-count').textContent = counts.join(' / ') || '0 added';
  const list = $('#finding-list');
  list.replaceChildren();
  changes.forEach((change, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'finding-button finding-enter';
    button.dataset.finding = change.capability;
    button.dataset.findingIndex = String(index);
    button.setAttribute('aria-pressed', 'false');
    const sign = document.createElement('span');
    sign.className = `finding-sign${change.change === 'REMOVED' ? ' removed' : ''}`;
    sign.textContent = change.change === 'ADDED' ? '+' : change.change === 'REMOVED' ? '−' : '=';
    sign.setAttribute('aria-hidden', 'true');
    const name = document.createElement('span');
    name.className = 'finding-name';
    name.textContent = change.capability;
    const severity = change.findings.some((item) => item.severity === 'HIGH') ? 'HIGH'
      : change.findings.some((item) => item.severity === 'MEDIUM') ? 'MEDIUM' : 'LOW';
    const badge = document.createElement('span');
    badge.className = `severity ${severity.toLowerCase()}`;
    badge.textContent = severity;
    button.append(sign, name, badge);
    button.setAttribute('aria-label', `${change.capability}, ${change.change.toLowerCase()}, ${severity.toLowerCase()} severity`);
    button.addEventListener('click', () => renderEvidence(change));
    list.append(button);
  });
  if (!changes.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-findings';
    empty.textContent = '✓ No new capability signals. An ordinary upgrade, with no new static findings.';
    list.append(empty);
  }
  const selected = changes.find((change) => change.capability === 'process') ?? changes[0];
  renderEvidence(selected);
}

function selectScenario(id) {
  const scenario = state.scenarios.find((item) => item.id === id);
  if (!scenario) return;
  const content = $('#demo-content');
  const version = ++renderVersion;
  content.classList.add('is-switching');
  content.dataset.transition = 'switching';
  content.setAttribute('aria-busy', 'true');
  state.scenario = scenario;
  const report = scenario.report;
  setPressed('[data-scenario]', 'scenario', id);
  $('#demo-command').textContent = scenario.command;
  $('#report-package').textContent = report.package.name;
  $('#report-versions').textContent = `${report.package.old_version} → ${report.package.new_version}`;
  $('#report-score').textContent = report.assessment.score;
  const verdict = report.assessment.verdict;
  const descriptions = {
    'block-recommended': ['Block recommended', 'New capabilities deserve a closer look before merging.'],
    review: ['Review recommended', 'Inspect the new evidence before accepting this change.'],
    ok: ['No new capability signal', 'No new signal under this policy. Not a guarantee of safety.'],
  };
  const [title, description] = descriptions[verdict];
  $('#verdict-title').textContent = title;
  $('#verdict-description').textContent = description;
  $('#verdict-bar').classList.toggle('is-ok', verdict === 'ok');
  $('.verdict-symbol').textContent = verdict === 'ok' ? '✓' : '!';
  const count = report.metadata_diff.changes.length;
  $('#metadata-summary').textContent = `+ ${count} metadata change${count === 1 ? '' : 's'} in the full report`;
  renderFindings(report);
  renderFormat();
  replayClass($('#verdict-bar'), 'is-fresh');
  replayClass($('#report-score'), 'is-fresh');
  requestAnimationFrame(() => {
    if (version !== renderVersion) return;
    content.classList.remove('is-switching');
    content.dataset.transition = 'idle';
    content.setAttribute('aria-busy', 'false');
  });
}

async function loadReports() {
  if (loading) return;
  loading = true;
  $('#demo-loading').textContent = 'Loading the saved comparison…';
  $('#demo-loading').hidden = false;
  $('#demo-error').hidden = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch('./data/reports.json', { signal: controller.signal });
    if (!response.ok) throw new Error('Report unavailable');
    const data = await response.json();
    if (data.schema_version !== 1 || !['suspicious', 'benign', 'review'].every((id) =>
      data.scenarios?.some((scenario) => scenario.id === id && scenario.report?.capabilities?.diff && scenario.report?.assessment && typeof scenario.terminal === 'string' && typeof scenario.markdown === 'string'))) {
      throw new Error('Unsupported report data');
    }
    state.scenarios = data.scenarios;
    selectScenario('suspicious');
    $('#demo-content').hidden = false;
    $$('[data-scenario]').forEach((button) => { button.disabled = false; });
  } catch {
    $('#demo-content').hidden = true;
    $('#demo-error').hidden = false;
  } finally {
    clearTimeout(timeout);
    loading = false;
    $('#demo-loading').hidden = true;
    scheduleScrollUI();
  }
}

$$('[data-scenario]').forEach((button) => {
  button.addEventListener('click', () => selectScenario(button.dataset.scenario));
});
$$('[data-format]').forEach((button) => {
  button.addEventListener('click', () => {
    state.format = button.dataset.format;
    renderFormat();
  });
});
$('#retry-demo').addEventListener('click', loadReports);

$('#download-report').addEventListener('click', () => {
  if (!state.scenario) return;
  const format = state.format === 'visual' ? 'json' : state.format;
  const extension = { json: 'json', terminal: 'txt', markdown: 'md' }[format];
  const mime = { json: 'application/json', terminal: 'text/plain', markdown: 'text/markdown' }[format];
  const url = URL.createObjectURL(new Blob([reportText(format)], { type: `${mime};charset=utf-8` }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `depdiff-${state.scenario.id}.${extension}`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

$$('[data-copy-target]').forEach((button) => {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    try {
      await navigator.clipboard.writeText(target.textContent.trim());
      notify('Command copied. Run it from your local checkout.');
    } catch {
      const range = document.createRange();
      range.selectNodeContents(target);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      notify('Clipboard unavailable. The command is selected for you to copy.');
    }
  });
});

const capabilities = {
  network: {
    title: 'A package that can reach the network.',
    description: 'Fetch, HTTP clients, sockets, TLS, and DNS calls can retrieve remote content or send package and host data.',
    code: 'fetch(endpoint);', rule: 'network-fetch', severity: 'MEDIUM',
  },
  fs: {
    title: 'A package that can touch your files.',
    description: 'Filesystem APIs can read or modify files outside the package source tree, not just the files you expected it to use.',
    code: 'fs.readFileSync(path);', rule: 'fs-file-operation', severity: 'MEDIUM',
  },
  process: {
    title: 'A package that can start another process.',
    description: 'Child-process APIs can invoke shell commands and affect the host beyond the JavaScript runtime.',
    code: 'child_process.exec(command);', rule: 'process-child-process', severity: 'HIGH',
  },
  env: {
    title: 'A package that can read its environment.',
    description: 'Environment variables can contain credentials, tokens, paths, and machine-specific information. New access deserves context.',
    code: 'process.env.CONFIG_PATH', rule: 'env-process', severity: 'MEDIUM',
  },
  'dynamic-code': {
    title: 'A package that can turn data into code.',
    description: 'Evaluation and VM APIs can execute dynamically selected code that is not visible in the surrounding source.',
    code: 'eval(source);', rule: 'dynamic-code-evaluation', severity: 'HIGH',
  },
  crypto: {
    title: 'A package that can transform sensitive data.',
    description: 'Cryptographic APIs can protect data, but can also conceal or transform behavior. Their presence alone is not suspicious.',
    code: "crypto.createHash('sha256');", rule: 'crypto-node-api', severity: 'LOW',
  },
  'install-script': {
    title: 'A package with a new installation hook.',
    description: 'Preinstall, install, and postinstall scripts can act during package installation, before a reviewer runs the package.',
    code: '"postinstall": "node setup.js"', rule: 'install-script-lifecycle', severity: 'HIGH',
  },
};

$$('[data-capability]').forEach((button) => {
  button.addEventListener('click', () => {
    const category = button.dataset.capability;
    const capability = capabilities[category];
    if (!capability) return;
    const detail = $('.capability-detail');
    detail.classList.add('is-changing');
    setPressed('[data-capability]', 'capability', category);
    $('#cap-title').textContent = capability.title;
    $('#cap-description').textContent = capability.description;
    $('#cap-code').textContent = capability.code;
    $('#cap-rule').textContent = capability.rule;
    $('#cap-severity').textContent = capability.severity;
    $('#cap-severity').className = `severity ${capability.severity.toLowerCase()}`;
    replayClass($('#cap-code').parentElement, 'is-fresh');
    requestAnimationFrame(() => detail.classList.remove('is-changing'));
  });
});

const exampleArgs = 'npm demo-package 1.0.0 2.0.0';
const continuation = ' \\\n  ';
const setupCommands = {
  python: {
    requirement: 'PYTHON 3.11.2', label: '02 / COMPARE THE FIXTURES',
    command: `python3 -m depdiff ${exampleArgs}${continuation}--fixtures-dir fixtures`,
    share: `python3 -m depdiff ${exampleArgs}${continuation}--fixtures-dir fixtures --format markdown${continuation}--output reports/review.md`,
  },
  docker: {
    requirement: 'DOCKER', label: '02 / BUILD & COMPARE',
    command: `docker build --tag depdiff:local .\ndocker run --rm depdiff:local ${exampleArgs}${continuation}--fixtures-dir /app/fixtures`,
    share: `docker run --rm depdiff:local ${exampleArgs}${continuation}--fixtures-dir /app/fixtures --format markdown${continuation}> review.md`,
  },
};
$$('[data-setup]').forEach((button) => {
  button.addEventListener('click', () => {
    const method = button.dataset.setup;
    const setup = setupCommands[method];
    setPressed('[data-setup]', 'setup', method);
    $('#setup-command').textContent = setup.command;
    $('#share-command').textContent = setup.share;
    $('#setup-label').textContent = setup.label;
    $('#setup-requirement').textContent = setup.requirement;
  });
});

const revealGroups = [
  '.principles > div',
  '#features .feature-notes > article',
  '#how-it-works .workflow-steps > li',
  '#use-cases .use-case-list > article',
];
const revealTargets = [
  '.demo-caption', '#demo .review-window', '.demo-disclaimer',
  '#features .section-heading', '#features .capability-layout > *',
  '#how-it-works .section-heading', '#how-it-works .pipeline',
  '#use-cases .use-cases-heading', '#get-started > *',
  '.faq-section > *', '.closing .wrap', ...revealGroups,
];

function setupScrollReveals() {
  const targets = [...new Set(revealTargets.flatMap((selector) => $$(selector)))];
  revealGroups.forEach((selector) => {
    $$(selector).forEach((element, index) => element.dataset.revealOrder = String(index + 1));
  });
  targets.forEach((element) => { element.dataset.reveal = ''; });
  document.documentElement.classList.add('motion-ready');
  const show = (element) => element.classList.add('is-visible');
  if (reducedMotion.matches || !('IntersectionObserver' in window)) {
    targets.forEach(show);
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      show(entry.target);
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 });
  targets.forEach((element) => observer.observe(element));
}

function updateScrollUI() {
  const progress = clamp((window.scrollY || window.pageYOffset) / Math.max(1, document.documentElement.scrollHeight - innerHeight));
  const progressBar = $('#scroll-progress');
  progressBar.dataset.progress = progress.toFixed(3);
  progressBar.style.setProperty('--scroll-progress', progress.toFixed(3));
  $('.site-header').dataset.scrolled = String(window.scrollY > 24);

  const activeLine = innerHeight * 0.28;
  const sectionIds = ['features', 'how-it-works', 'use-cases', 'get-started'];
  let activeSection = '';
  sectionIds.forEach((id) => {
    const section = document.getElementById(id);
    const bounds = section.getBoundingClientRect();
    if (bounds.top <= activeLine && bounds.bottom > activeLine) activeSection = id;
  });
  $$('.desktop-nav a, #mobile-nav a').forEach((link) => {
    const isActive = link.getAttribute('href') === `#${activeSection}`;
    link.dataset.active = String(isActive);
    if (isActive) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });

  const workflow = $('#how-it-works .workflow-steps');
  const workflowBounds = $('#how-it-works').getBoundingClientRect();
  const workflowProgress = clamp((innerHeight * 0.76 - workflowBounds.top) / (workflowBounds.height + innerHeight * 0.38));
  workflow.style.setProperty('--workflow-progress', workflowProgress.toFixed(3));
  workflow.dataset.progress = workflowProgress.toFixed(3);
  const activeStep = Math.min(2, Math.max(0, Math.floor(workflowProgress * 3.2)));
  $$('#how-it-works .workflow-steps > li').forEach((step, index) => {
    step.dataset.active = String(index <= activeStep && workflowProgress > 0.04);
  });
}

function scheduleScrollUI() {
  if (scrollFrame) return;
  scrollFrame = requestAnimationFrame(() => {
    scrollFrame = undefined;
    updateScrollUI();
  });
}

setupScrollReveals();
window.addEventListener('scroll', scheduleScrollUI, { passive: true });
window.addEventListener('resize', scheduleScrollUI, { passive: true });
updateScrollUI();

const menuButton = $('.menu-toggle');
const menu = $('#mobile-nav');
function closeMenu(returnFocus = false) {
  menu.hidden = true;
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-label', 'Open navigation');
  if (returnFocus) menuButton.focus();
}
menuButton.addEventListener('click', () => {
  const open = menu.hidden;
  menu.hidden = !open;
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
});
$$('#mobile-nav a').forEach((link) => link.addEventListener('click', () => closeMenu()));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !menu.hidden) closeMenu(true);
});
document.addEventListener('click', (event) => {
  if (!menu.hidden && !menu.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
});
matchMedia('(min-width: 701px)').addEventListener('change', (event) => {
  if (event.matches) closeMenu();
});

$$('[role="group"]').forEach((group) => {
  group.addEventListener('keydown', (event) => {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const buttons = [...group.querySelectorAll('button:not(:disabled)')];
    const index = buttons.indexOf(document.activeElement);
    if (index === -1) return;
    event.preventDefault();
    let next = index;
    if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = buttons.length - 1;
    else next = (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next].focus();
    buttons[next].click();
  });
});

loadReports();
