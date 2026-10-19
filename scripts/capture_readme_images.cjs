/* Uses the optional, pinned Playwright setup in docs/showcase.md. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const base = process.env.SHOWCASE_URL || 'http://localhost:4173';
const output = path.join(root, 'docs/images');

async function main() {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      colorScheme: 'dark',
    });
    const errors = [];
    const externalRequests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/*', (route) => {
      if (new URL(route.request().url()).origin !== new URL(base).origin) {
        externalRequests.push(route.request().url());
        return route.abort();
      }
      return route.continue();
    });
    const response = await page.goto(base);
    assert.equal(response.status(), 200, 'Serve the repository showcase before capturing images');
    await page.locator('#demo-content').waitFor({ state: 'visible' });
    await page.evaluate(() => document.fonts.ready);

    assert.equal(await page.locator('#report-score').textContent(), '8');
    await page.locator('#demo').screenshot({
      path: path.join(output, 'suspicious-upgrade.png'), animations: 'disabled',
    });

    await page.locator('[data-scenario="benign"]').click();
    assert.equal(await page.locator('#report-score').textContent(), '0');
    await page.locator('#demo').screenshot({
      path: path.join(output, 'benign-upgrade.png'), animations: 'disabled',
    });

    await page.locator('[data-capability="process"]').click();
    await page.locator('.capability-explorer').screenshot({
      path: path.join(output, 'capability-explorer.png'), animations: 'disabled',
    });
    assert.deepEqual(externalRequests, [], 'README images must use only repository assets');
    assert.deepEqual(errors, [], 'Do not capture a broken showcase');
    console.log(`Captured three README images in ${path.relative(root, output)}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
