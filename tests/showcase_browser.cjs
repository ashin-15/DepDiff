/* Optional browser checks. See docs/showcase.md for the pinned test-tool setup. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const base = process.env.SHOWCASE_URL || 'http://localhost:4173';
const output = path.join(root, 'reports/showcase-browser');
const expected = require('../showcase/data/reports.json');
const vercel = require('../vercel.json');
const securityHeaders = Object.fromEntries(vercel.headers[0].headers.map(({ key, value }) => [key, value]));
const accessibilityFailures = [];

async function visible(page, selector) {
  await page.locator(selector).waitFor({ state: 'visible' });
}

async function checkWidth(page) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Page must not overflow horizontally');
}

async function checkTypography(page) {
  const groups = [
    { minimum: 1, selector: '.hero-description, #evidence-reason, #verdict-description, .demo-disclaimer, .section-heading > p:last-child, .capability-detail p, .feature-notes p, .workflow-steps p, .use-case-list p, .start-copy > p:not(.section-index), .faq-list details p, .closing p, .footer-note' },
    { minimum: .875, selector: '.scenario-tabs button, #demo-command, .finding-name, .evidence-line code, #raw-output, .format-tabs button, .text-button, .desktop-nav, .header-github, .button, .capability-options button, .quickstart-tabs button, .setup-step pre, .pipeline code, .cap-code code, .site-footer nav, .inline-link' },
    { minimum: .75, selector: '.severity, .pane-label, .pane-label > span, .micro-label, .score small, .principles span, .step-detail, .section-index, .setup-step > span, .version-tag, .window-chrome, .hero-note, .source-annotation, .line-number' },
  ];
  const result = await page.evaluate((checks) => {
    const rootSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
    return {
      rootSize,
      failures: checks.flatMap(({ minimum, selector }) => [...document.querySelectorAll(selector)]
        .filter((element) => element.getClientRects().length)
        .flatMap((element) => {
          const size = parseFloat(getComputedStyle(element).fontSize);
          return size + .01 < minimum * rootSize
            ? [`${element.id || element.className}: ${size}px, expected at least ${minimum * rootSize}px`]
            : [];
        })),
    };
  }, groups);
  assert(result.rootSize >= 16, 'The site must not shrink the browser’s default font size');
  assert.deepEqual(result.failures, [], 'Text must keep a readable, preference-relative type scale');
}

async function assertScenarioSettled(page, id) {
  await page.waitForFunction((expectedId) => {
    const content = document.querySelector('#demo-content');
    const selected = document.querySelector('.scenario-tabs button[aria-pressed="true"]');
    return content && !content.hidden && content.dataset.transition === 'idle'
      && content.getAttribute('aria-busy') === 'false' && selected?.dataset.scenario === expectedId;
  }, id);
}

async function audit(page, label) {
  if (!process.env.AXE_MODULE) return;
  // Only the locally installed testing tool is injected, never a site dependency.
  const script = require.resolve(process.env.AXE_MODULE);
  await page.addScriptTag({ path: script });
  const results = await page.evaluate(async () => window.axe.run(document, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
  }));
  await fs.writeFile(path.join(output, `accessibility-${label}.json`), JSON.stringify(results.violations, null, 2));
  accessibilityFailures.push(...results.violations.map((violation) => `${label}: ${violation.id}: ${violation.nodes.map((node) => node.target).join(', ')}`));
}

async function main() {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const errors = [];
  const externalRequests = [];
  await context.route('**/*', async (route) => {
    const request = route.request();
    if (!request.url().startsWith(base)) {
      externalRequests.push(request.url());
      return route.abort();
    }
    if (request.isNavigationRequest()) {
      const response = await route.fetch();
      return route.fulfill({ response, headers: { ...response.headers(), ...securityHeaders } });
    }
    return route.continue();
  });
  const page = await context.newPage();
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  try {
    await page.goto(base);
    await visible(page, '#demo-content');
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('#report-score').textContent(), '8');
    assert.equal(await page.locator('#verdict-title').textContent(), 'Block recommended');
    await checkWidth(page);
    await checkTypography(page);
    await page.screenshot({ path: path.join(output, 'desktop.png') });
    await page.screenshot({ path: path.join(output, 'desktop-full.png'), fullPage: true });
    await page.locator('#demo').screenshot({ path: path.join(output, 'desktop-demo.png') });
    // Axe uses injected styles internally, so audit without the production CSP.
    const auditPage = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    await auditPage.emulateMedia({ reducedMotion: 'reduce' });
    await auditPage.goto(base);
    await visible(auditPage, '#demo-content');
    await audit(auditPage, 'desktop');
    await auditPage.close();

    await page.locator('[data-finding="fs"]').click();
    assert.match(await page.locator('#evidence-code').textContent(), /readFileSync/);
    assert.equal(await page.locator('#evidence-location').textContent(), 'lib/index.js:5');
    for (const format of ['terminal', 'json', 'markdown']) {
      await page.locator(`[data-format="${format}"]`).click();
      const text = await page.locator('#raw-output').textContent();
      if (format === 'json') assert.deepEqual(JSON.parse(text), expected.scenarios[0].report);
      else assert.equal(text, expected.scenarios[0][format]);
      await checkTypography(page);
    }
    const downloadEvent = page.waitForEvent('download');
    await page.locator('#download-report').click();
    const download = await downloadEvent;
    assert.equal(download.suggestedFilename(), 'depdiff-suspicious.md');
    assert.equal(await fs.readFile(await download.path(), 'utf8'), expected.scenarios[0].markdown);
    await page.locator('[data-format="visual"]').click();

    await page.locator('[data-scenario="benign"]').click();
    assert.equal(await page.locator('#report-score').textContent(), '0');
    assert.equal(await page.locator('.finding-button').count(), 0);
    assert.match(await page.locator('.empty-findings').textContent(), /No new capability/);
    await page.locator('[data-scenario="review"]').click();
    assert.equal(await page.locator('#change-count').textContent(), '3 removed');
    assert.equal(await page.locator('#report-score').textContent(), '0');
    assert.match(await page.locator('#evidence-change').textContent(), /removed/);
    await page.locator('[data-scenario="suspicious"]').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#report-package').textContent(), 'benign-package');

    for (const category of ['network', 'fs', 'process', 'env', 'dynamic-code', 'crypto', 'install-script']) {
      await page.locator(`[data-capability="${category}"]`).click();
      assert.equal(await page.locator(`[data-capability="${category}"]`).getAttribute('aria-pressed'), 'true');
      assert((await page.locator('#cap-code').textContent()).length > 0);
    }
    await page.locator('[data-setup="docker"]').click();
    assert.match(await page.locator('#setup-command').textContent(), /docker build/);
    await page.locator('[data-setup="python"]').click();
    assert.match(await page.locator('#setup-command').textContent(), /python3 -m depdiff/);
    await page.locator('[data-copy-target="setup-command"]').click();
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), (await page.locator('#setup-command').textContent()).trim());
    await page.locator('.faq-list summary').first().click();
    assert.equal(await page.locator('.faq-list details').first().getAttribute('open'), '');

    const mobile = await context.newPage();
    await mobile.setViewportSize({ width: 390, height: 844 });
    await mobile.emulateMedia({ reducedMotion: 'reduce' });
    await mobile.goto(base);
    await visible(mobile, '#demo-content');
    await mobile.evaluate(() => document.fonts.ready);
    await checkWidth(mobile);
    await checkTypography(mobile);
    const reducedMotion = await mobile.evaluate(() => ({
      scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
      buttonTransitionDuration: getComputedStyle(document.querySelector('.button')).transitionDuration,
      menuBarTransitionDuration: getComputedStyle(document.querySelector('.menu-toggle > span')).transitionDuration,
      travelDotDisplay: getComputedStyle(document.querySelector('.travel-dot')).display,
    }));
    assert.equal(reducedMotion.scrollBehavior, 'auto');
    assert.equal(reducedMotion.buttonTransitionDuration, '0s');
    assert.equal(reducedMotion.menuBarTransitionDuration, '0s');
    assert.equal(reducedMotion.travelDotDisplay, 'none');
    await mobile.waitForFunction(() => Number(document.querySelector('#scroll-progress').dataset.progress) <= 0.001);
    assert.equal(await mobile.locator('.site-header').getAttribute('data-scrolled'), 'false');
    const maxScroll = await mobile.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    assert(maxScroll > 0);
    await mobile.evaluate((position) => window.scrollTo(0, position), maxScroll / 2);
    await mobile.waitForFunction(() => Number(document.querySelector('#scroll-progress').dataset.progress) > 0);
    assert.equal(await mobile.locator('.site-header').getAttribute('data-scrolled'), 'true');
    const middleProgress = Number(await mobile.locator('#scroll-progress').getAttribute('data-progress'));
    assert(middleProgress > 0 && middleProgress < 1);
    await mobile.evaluate(() => window.scrollTo(0, 0));
    await mobile.waitForFunction(() => Number(document.querySelector('#scroll-progress').dataset.progress) <= 0.001);
    await mobile.screenshot({ path: path.join(output, 'mobile.png') });
    await mobile.screenshot({ path: path.join(output, 'mobile-full.png'), fullPage: true });
    await mobile.locator('#demo').screenshot({ path: path.join(output, 'mobile-demo.png') });
    await mobile.locator('.menu-toggle').click();
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'true');
    await mobile.keyboard.press('Escape');
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');
    await mobile.locator('.menu-toggle').click();
    await mobile.locator('#mobile-nav a[href="#use-cases"]').click();
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');
    assert.equal(new URL(mobile.url()).hash, '#use-cases');
    await mobile.locator('[data-format="json"]').click();
    await mobile.locator('[data-scenario="review"]').click();
    await assertScenarioSettled(mobile, 'review');
    await checkWidth(mobile);
    await mobile.setViewportSize({ width: 320, height: 740 });
    await checkWidth(mobile);
    await mobile.setViewportSize({ width: 768, height: 1024 });
    await checkWidth(mobile);

    // Reflow rather than shrinking type, including a doubled browser text preference.
    for (const fontSize of ['100%', '200%']) {
      await mobile.evaluate((size) => { document.documentElement.style.fontSize = size; }, fontSize);
      for (const width of [320, 390, 768, 1440]) {
        await mobile.setViewportSize({ width, height: 1024 });
        for (const scenario of ['suspicious', 'benign', 'review']) {
          await mobile.locator(`[data-scenario="${scenario}"]`).click();
          await mobile.locator('[data-format="visual"]').click();
          await checkWidth(mobile);
          await checkTypography(mobile);
        }
        await mobile.locator('[data-format="json"]').click();
        await checkWidth(mobile);
        await checkTypography(mobile);
      }
    }

    const mobileAudit = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await mobileAudit.emulateMedia({ reducedMotion: 'reduce' });
    await mobileAudit.goto(base);
    await visible(mobileAudit, '#demo-content');
    await audit(mobileAudit, 'mobile');
    await mobileAudit.close();

    const failure = await browser.newPage();
    const block = (route) => route.fulfill({ status: 503, body: 'Unavailable' });
    await failure.route('**/data/reports.json', block);
    await failure.goto(base);
    await visible(failure, '#demo-error');
    assert(await failure.locator('#demo-content').isHidden());
    await failure.unroute('**/data/reports.json', block);
    await failure.locator('#retry-demo').click();
    await visible(failure, '#demo-content');
    await failure.close();

    const noJs = await browser.newPage({ javaScriptEnabled: false });
    await noJs.goto(base);
    assert(await noJs.locator('h1').isVisible());
    assert(await noJs.locator('noscript').isVisible());
    assert(await noJs.locator('#get-started').textContent());
    assert(await noJs.locator('#demo-loading').isVisible());
    assert.match(await noJs.locator('#demo-loading').textContent(), /requires JavaScript/);
    assert(await noJs.locator('#demo-content').isHidden());
    assert(await noJs.locator('button[data-scenario="suspicious"]').isDisabled());
    await noJs.locator('.hero-actions a[href="#demo"]').click();
    assert.equal(new URL(noJs.url()).hash, '#demo');
    await noJs.close();
    assert.deepEqual(externalRequests, [], 'The showcase must make no third-party requests');
    assert.deepEqual(errors, [], 'The page must have no JavaScript or CSP console errors');
    assert.deepEqual(accessibilityFailures, [], 'Desktop and mobile must have no automated WCAG A/AA violations');
    console.log('PASS: real reports, findings, all formats, download, scenarios, keyboard, capability explorer, copy, setup, FAQ, mobile menu, readable typography, responsive widths at default and 200% text size, reduced motion, failure/retry, no-JS, CSP, and no external requests.');
    console.log(`Screenshots and accessibility results: ${path.relative(root, output)}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
