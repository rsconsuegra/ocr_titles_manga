import { createRequire } from "node:module";
import { parseArgs } from "node:util";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const {
  values: { url, output, width, height },
} = parseArgs({
  options: {
    url: { type: "string", default: "http://localhost:5173" },
    output: { type: "string", default: "uploads/screenshot.png" },
    width: { type: "string", default: "1280" },
    height: { type: "string", default: "720" },
  },
});

const viewport = {
  width: parseInt(width, 10),
  height: parseInt(height, 10),
};

mkdirSync(dirname(output), { recursive: true });

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport });
  console.log(`Navigating to ${url} ...`);
  await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: output, fullPage: false });
  console.log(`Screenshot saved to ${output}`);
} catch (err) {
  console.error(`Failed to capture screenshot: ${err.message}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
}
