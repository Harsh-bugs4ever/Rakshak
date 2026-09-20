const assert = require('node:assert/strict');
const { mkdir } = require('node:fs/promises');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || undefined });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = process.env.APP_URL || 'http://localhost:3001';
    await page.goto(base + '/emergency');
    await page.getByRole('button', { name: 'Not sure', exact: true }).click();
    await page.getByRole('heading', { name: 'Person is not breathing', exact: true }).waitFor();
    await page.reload();
    assert.equal(await page.getByRole('button', { name: 'Not sure', exact: true }).getAttribute('aria-pressed'), 'true');
    await page.getByText('Emergency and Aftermath screens saved for offline use.').waitFor({ timeout: 30000 });
    assert.equal(await page.locator('a[href="tel:108"]').count(), 1);
    await mkdir('artifacts', { recursive: true });
    await page.screenshot({ path: 'artifacts/emergency-mobile.png', fullPage: true });
    await page.getByRole('link', { name: 'Aftermath The road ahead' }).click();
    await page.getByRole('checkbox').first().check();
    await page.reload();
    assert.equal(await page.getByRole('checkbox').first().isChecked(), true);
    await page.getByRole('searchbox').fill('zzzznomatch');
    await page.getByText('No matching answer.', { exact: false }).waitFor();
    await page.getByRole('searchbox').fill('MLC');
    await page.locator('.faq-results details').first().waitFor();
    await page.screenshot({ path: 'artifacts/aftermath-mobile.png', fullPage: true });
    await context.setOffline(true);
    await page.reload();
    assert.equal(await page.getByRole('checkbox').first().isChecked(), true);
    await page.getByRole('link', { name: 'Emergency First minutes' }).click();
    await page.getByRole('heading', { name: 'Person is not breathing', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Yes', exact: true }).click();
    await page.getByRole('heading', { name: 'Person is breathing but injured', exact: true }).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: 'artifacts/emergency-desktop-dark.png', fullPage: true });
    assert.deepEqual(errors, []);
    console.log('Browser smoke passed: triage, persistence, FAQ search, offline reload and navigation, mobile overflow.');
    await context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
