// Actual browser screenshots of the running lab; no generated dashboard images.
// Install playwright in a temporary tools directory and expose it via NODE_PATH.
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
let activeBrowser;

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  activeBrowser = browser;
  const page = await browser.newPage({ viewport: { width: 1680, height: 1150 }, deviceScaleFactor: 1 });
  const phase = process.argv[2] || 'baseline';
  await fs.mkdir('screenshots', { recursive: true });
  if (phase === 'details') {
    const { error } = JSON.parse(await fs.readFile('evidence/part7/selected-traces.json', 'utf8'));
    await page.goto('http://localhost:16686/trace/' + error.traceID, { waitUntil: 'networkidle' });
    await page.getByText('chat mock-llm-small', { exact: true }).first().click();
    await page.getByText('Details', { exact: true }).first().click();
    console.log((await page.locator('body').innerText()).slice(0, 7000));
    await page.screenshot({ path: 'screenshots/jaeger-error-trace.png', fullPage: true });
  } else if (phase === 'alerts') {
    await page.goto('http://localhost:9090/alerts', { waitUntil: 'domcontentloaded' });
    await page.getByText('AgentHighErrorRate', { exact: true }).first().waitFor({ timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'screenshots/prometheus-alert-firing.png', fullPage: true });
    console.log((await page.locator('body').innerText()).slice(0, 5000));
  } else {
    if (phase !== 'traces') {
    await page.goto('http://localhost:3000/d/day14-agent-overview/day-14-ai-agent-overview?orgId=1&from=now-5m&to=now&refresh=5s', { waitUntil: 'domcontentloaded' });
    await page.getByText('Day 14 — AI Agent Overview', { exact: true }).first().waitFor({ timeout: 60000 });
    await page.waitForTimeout(7000);
    await page.screenshot({ path: 'screenshots/grafana-dashboard.png', fullPage: true });
    }
    // Jaeger 2.23 exposes streaming OTLP JSON via the v3 query API.
    const query = new URLSearchParams({
      'query.serviceName': 'observable-agent', 'query.searchDepth': '200',
      'query.startTimeMin': new Date(Date.now() - 120000).toISOString(),
      'query.startTimeMax': new Date().toISOString(),
    });
    const response = await fetch('http://localhost:16686/api/v3/traces?' + query);
    if (!response.ok) throw new Error(await response.text());
    const chunks = (await response.text()).trim().split('\n').map(line => JSON.parse(line));
    const byId = new Map();
    for (const chunk of chunks) for (const resource of chunk.result?.resourceSpans || []) {
      for (const scope of resource.scopeSpans || []) for (const span of scope.spans || []) {
        if (!byId.has(span.traceId)) byId.set(span.traceId, { traceID: span.traceId, spans: [] });
        byId.get(span.traceId).spans.push({
          traceID: span.traceId, spanID: span.spanId, operationName: span.name,
          startTime: Number(BigInt(span.startTimeUnixNano) / 1000n),
          duration: Number((BigInt(span.endTimeUnixNano) - BigInt(span.startTimeUnixNano)) / 1000n),
          tags: (span.attributes || []).map(a => ({ key: a.key, value: Object.values(a.value)[0] })),
          error: span.status?.code === 2,
          events: span.events || [],
        });
      }
    }
    const traces = [...byId.values()];
    if (!traces.length) throw new Error('No real Jaeger traces found');
    const duration = t => Math.max(...t.spans.map(s => s.startTime + s.duration)) - Math.min(...t.spans.map(s => s.startTime));
    traces.sort((a, b) => duration(b) - duration(a));
    const slow = traces[0];
    const error = traces.find(t => t.spans.some(s => s.error || s.tags.some(tag => tag.key === 'error' && tag.value === true)));
    if (!error) throw new Error('No error trace found');
    await fs.writeFile('evidence/part7/selected-traces.json', JSON.stringify({ slow, error }, null, 2));
    for (const [kind, trace] of [['slow', slow], ['error', error]]) {
      await page.goto('http://localhost:16686/trace/' + trace.traceID, { waitUntil: 'networkidle' });
      await page.getByText('chat mock-llm-small', { exact: true }).first().waitFor({ timeout: 30000 });
      console.log(kind + ' trace: ' + trace.traceID);
      console.log((await page.locator('body').innerText()).slice(0, 5000));
      const chat = page.getByText('chat mock-llm-small', { exact: true }).first();
      if (await chat.count()) await chat.click();
      if (kind === 'error') {
        await page.getByText('Details', { exact: true }).first().click();
      }
      await page.screenshot({ path: 'screenshots/jaeger-' + kind + '-trace.png', fullPage: true });
    }
  }
  await browser.close();
})().catch(async error => {
  console.error(error);
  if (activeBrowser) await activeBrowser.close();
  process.exitCode = 1;
});
