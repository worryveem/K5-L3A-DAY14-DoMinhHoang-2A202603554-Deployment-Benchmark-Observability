// Export real Railway CLI metadata and actual public HTTP results as PNG evidence.
// dashboard.png is a CLI status report, not a capture of Railway's authenticated web console.
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const escape = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

async function renderReport(page, name, title, note, content) {
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><title>${escape(title)}</title>
  <style>body{font:17px/1.6 system-ui;margin:48px;color:#172334;background:#f5f7fa}
  main{max-width:1320px;margin:auto;background:white;padding:32px;border:1px solid #d5dce5}
  h1{font-size:28px;margin:0 0 12px}p{color:#49576b}pre{white-space:pre-wrap;overflow-wrap:anywhere;
  font:16px/1.5 Consolas,monospace;padding:24px;background:#edf2f7;border:1px solid #d5dce5}</style>
  <main><h1>${escape(title)}</h1><p>${escape(note)}</p><pre>${escape(content)}</pre></main></html>`;
  const target = path.resolve('evidence/part6/' + name + '.html');
  await fs.writeFile(target, html);
  await page.goto(pathToFileURL(target).href);
  await page.screenshot({ path: 'screenshots/' + name + '.png', fullPage: true });
}

(async () => {
  const metadata = JSON.parse(await fs.readFile('evidence/part6/railway-deployment.json', 'utf8'));
  const checks = JSON.parse(await fs.readFile('evidence/part6/public-api.json', 'utf8'));
  if (!checks.passed || metadata.services.some(service => service.status !== 'SUCCESS')) {
    throw new Error('Deployment evidence must be successful before capture');
  }
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 }, deviceScaleFactor: 1 });
    const statusText = [
      '$ railway service list --json',
      'Project: ' + metadata.project_name,
      'Environment: ' + metadata.environment,
      'Public URL: ' + metadata.public_url,
      'Railway project: ' + metadata.dashboard_url,
      'Captured: ' + metadata.captured_at,
      '',
      ...metadata.services.map(service => `${service.name}: ${service.status}\n  service_id: ${service.id}\n  deployment_id: ${service.deployment_id}\n  running replicas: ${service.replicas?.running}`),
    ].join('\n');
    await renderReport(page, 'dashboard', 'Railway deployment status — CLI snapshot',
      'Source: actual railway service list output saved in railway-deployment.json. Secret values excluded.', statusText);
    await page.goto(metadata.public_url + '/docs', { waitUntil: 'domcontentloaded' });
    await page.getByText('Production AI Agent', { exact: false }).first().waitFor({ timeout: 30000 });
    await page.screenshot({ path: 'screenshots/running.png', fullPage: true });
    const transcript = ['Public URL: ' + checks.public_url, 'Executed: ' + checks.executed_at, ''];
    for (const check of checks.checks) {
      transcript.push(`${check.method} ${check.path} | API key: ${check.authenticated ? '[REDACTED]' : 'absent'} | HTTP ${check.status}`);
      transcript.push(JSON.stringify(check.body, null, 2), '');
    }
    await renderReport(page, 'test', 'Public deployment — actual HTTP verification',
      'Source: live public requests saved in public-api.json. All four required checks passed.', transcript.join('\n'));
  } finally {
    await browser.close();
  }
  console.log('Saved deployment status export, live Swagger UI, and actual HTTP result screenshots.');
})().catch(error => { console.error(error); process.exitCode = 1; });
