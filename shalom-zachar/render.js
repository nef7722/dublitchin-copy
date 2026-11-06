// Renders index.html to a high-resolution PNG + JPG (2400x3200).
// Usage: node render.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1600 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const el = await page.$('#poster');
  await el.screenshot({ path: path.join(__dirname, 'shalom-zachar.png') });
  await el.screenshot({ path: path.join(__dirname, 'shalom-zachar.jpg'), type: 'jpeg', quality: 92 });
  await browser.close();
})();
