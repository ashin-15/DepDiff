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
    await page.screenshot({ path: path.join(output, 'desktop.png') });
    await page.screenshot({ path: path.join(output, 'desktop-full.png'), fullPage: true });
    // Axe uses injected styles internally, so audit without the production CSP.
    const auditPage = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
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
    await mobile.screenshot({ path: path.join(output, 'mobile.png') });
    await mobile.screenshot({ path: path.join(output, 'mobile-full.png'), fullPage: true });
    await mobile.locator('.menu-toggle').click();
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'true');
    await mobile.keyboard.press('Escape');
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');
    await mobile.locator('.menu-toggle').click();
    await mobile.locator('#mobile-nav a[href="#use-cases"]').click();
    assert.equal(await mobile.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');
    assert.equal(new URL(mobile.url()).hash, '#use-cases');
    await mobile.locator('[data-format="json"]').click();
    await checkWidth(mobile);
    await mobile.setViewportSize({ width: 320, height: 740 });
    await checkWidth(mobile);
    await mobile.setViewportSize({ width: 768, height: 1024 });
    await checkWidth(mobile);

    const mobileAudit = await browser.newPage({ viewport: { width: 390, height: 844 } });
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
    await noJs.close();
    assert.deepEqual(externalRequests, [], 'The showcase must make no third-party requests');
    assert.deepEqual(errors, [], 'The page must have no JavaScript or CSP console errors');
    assert.deepEqual(accessibilityFailures, [], 'Desktop and mobile must have no automated WCAG A/AA violations');
    console.log('PASS: real reports, findings, all formats, download, scenarios, keyboard, capability explorer, copy, setup, FAQ, mobile menu, responsive widths, reduced motion, failure/retry, no-JS, CSP, and no external requests.');
    console.log(`Screenshots and accessibility results: ${path.relative(root, output)}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
