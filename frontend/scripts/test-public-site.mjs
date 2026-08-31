import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { createServer, request as httpRequest } from 'node:http'
import { tmpdir } from 'node:os'
import { dirname, extname, join, resolve, sep } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(process.argv[2] || join(frontendRoot, 'dist'))
const publicBase = '/trust-safety-orchestration-agent/'
const screenshotDir = process.env.SAFETYAGENT_E2E_SCREENSHOT_DIR

if (typeof WebSocket !== 'function') {
  throw new Error('The public-site browser test requires Node.js 22 or newer.')
}
if (!existsSync(join(distRoot, 'index.html'))) {
  throw new Error(`Public-site build not found at ${distRoot}. Build it before testing.`)
}
if (screenshotDir) {
  await mkdir(screenshotDir, { recursive: true })
}

async function collectTextFiles(directory) {
  const files = []
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      files.push(...await collectTextFiles(path))
    } else if (['.css', '.html', '.js', '.json', '.svg'].includes(extname(entry.name))) {
      files.push(path)
    }
  }
  return files
}

for (const file of await collectTextFiles(distRoot)) {
  const contents = await readFile(file, 'utf8')
  assert.doesNotMatch(
    contents,
    /execute-api|wss:\/\/|amazonaws\.com/i,
    `Public artifact contains a private cloud endpoint marker: ${file}`,
  )
}

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mp3': 'audio/mpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
}

function findChrome() {
  const candidates = [
    process.env.CHROME_BIN,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean)

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }

  for (const command of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    const found = spawnSync('which', [command], { encoding: 'utf8' })
    if (found.status === 0 && found.stdout.trim()) return found.stdout.trim()
  }

  throw new Error('Chrome or Chromium is required for the public-site browser test.')
}

async function startStaticServer() {
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url || '/', 'http://127.0.0.1')
      let pathname = decodeURIComponent(url.pathname)
      if (pathname === publicBase.slice(0, -1) || pathname === publicBase) {
        pathname = `${publicBase}index.html`
      }
      if (!pathname.startsWith(publicBase)) {
        response.writeHead(404).end('Not found')
        return
      }

      const relativePath = pathname.slice(publicBase.length)
      const filePath = resolve(distRoot, relativePath)
      if (filePath !== distRoot && !filePath.startsWith(`${distRoot}${sep}`)) {
        response.writeHead(403).end('Forbidden')
        return
      }

      const body = await readFile(filePath)
      response.writeHead(200, {
        'cache-control': 'no-store',
        'content-type': contentTypes[extname(filePath)] || 'application/octet-stream',
      })
      if (request.method === 'HEAD') response.end()
      else response.end(body)
    } catch {
      response.writeHead(404).end('Not found')
    }
  })

  await new Promise((resolveListen, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolveListen)
  })
  const address = server.address()
  const port = typeof address === 'object' && address ? address.port : 0
  return { server, origin: `http://127.0.0.1:${port}` }
}

function requestJson(url, method = 'GET') {
  return new Promise((resolveRequest, reject) => {
    const request = httpRequest(url, { method }, (response) => {
      let body = ''
      response.setEncoding('utf8')
      response.on('data', (chunk) => {
        body += chunk
      })
      response.on('end', () => {
        if (!response.statusCode || response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`HTTP ${response.statusCode || 'unknown'}: ${body}`))
          return
        }
        try {
          resolveRequest(JSON.parse(body))
        } catch (error) {
          reject(new Error(`Invalid JSON from ${url}: ${error}`))
        }
      })
    })
    request.setTimeout(2_000, () => {
      request.destroy(new Error(`Timed out requesting ${url}`))
    })
    request.once('error', reject)
    request.end()
  })
}

async function pollJson(url, chrome) {
  let lastError
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (chrome.exitCode !== null) {
      throw new Error(`Chrome exited before DevTools became available (code ${chrome.exitCode}).`)
    }
    try {
      return await requestJson(url)
    } catch (error) {
      lastError = error
    }
    await delay(100)
  }
  throw new Error(`Timed out waiting for Chrome DevTools: ${lastError}`)
}

async function waitForDevToolsUrl(chrome, getOutput) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (chrome.exitCode !== null) {
      throw new Error(`Chrome exited before DevTools became available (code ${chrome.exitCode}).`)
    }
    const match = getOutput().match(/DevTools listening on (ws:\/\/\S+)/)
    if (match) return match[1]
    await delay(100)
  }
  throw new Error('Timed out waiting for Chrome to announce its DevTools endpoint.')
}

class CdpSession {
  constructor(socket) {
    this.socket = socket
    this.nextId = 1
    this.pending = new Map()
    this.listeners = new Map()

    socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data))
      if (message.id) {
        const pending = this.pending.get(message.id)
        if (!pending) return
        this.pending.delete(message.id)
        if (message.error) pending.reject(new Error(message.error.message))
        else pending.resolve(message.result || {})
        return
      }
      const listeners = this.listeners.get(message.method)
      if (!listeners) return
      for (const listener of [...listeners]) listener(message.params || {})
    })
  }

  static async connect(url) {
    const socket = new WebSocket(url)
    await new Promise((resolveOpen, reject) => {
      socket.addEventListener('open', resolveOpen, { once: true })
      socket.addEventListener('error', reject, { once: true })
    })
    return new CdpSession(socket)
  }

  send(method, params = {}) {
    const id = this.nextId
    this.nextId += 1
    return new Promise((resolveResult, reject) => {
      this.pending.set(id, { resolve: resolveResult, reject })
      this.socket.send(JSON.stringify({ id, method, params }))
    })
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) || new Set()
    listeners.add(listener)
    this.listeners.set(method, listeners)
    return () => listeners.delete(listener)
  }

  once(method, timeoutMs = 10_000) {
    return new Promise((resolveEvent, reject) => {
      const timer = setTimeout(() => {
        unsubscribe()
        reject(new Error(`Timed out waiting for Chrome event ${method}`))
      }, timeoutMs)
      const unsubscribe = this.on(method, (params) => {
        clearTimeout(timer)
        unsubscribe()
        resolveEvent(params)
      })
    })
  }

  close() {
    this.socket.close()
  }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  })
  if (result.exceptionDetails) {
    const description = result.exceptionDetails.exception?.description
      || result.exceptionDetails.text
      || 'Browser evaluation failed'
    throw new Error(description)
  }
  return result.result?.value
}

async function waitFor(cdp, expression, description, timeoutMs = 10_000) {
  const deadline = Date.now() + timeoutMs
  let lastError
  while (Date.now() < deadline) {
    try {
      const value = await evaluate(cdp, expression)
      if (value) return value
    } catch (error) {
      lastError = error
    }
    await delay(50)
  }
  throw new Error(`Timed out waiting for ${description}${lastError ? `: ${lastError}` : ''}`)
}

async function click(cdp, selector) {
  const serialized = JSON.stringify(selector)
  const rect = await evaluate(cdp, `(() => {
    const element = document.querySelector(${serialized});
    if (!element) return null;
    element.scrollIntoView({ block: 'center', inline: 'center' });
    const bounds = element.getBoundingClientRect();
    return {
      x: bounds.left + bounds.width / 2,
      y: bounds.top + bounds.height / 2,
      disabled: Boolean(element.disabled),
    };
  })()`)
  assert.ok(rect, `Missing clickable element ${selector}`)
  assert.equal(rect.disabled, false, `Element is disabled: ${selector}`)
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: rect.x,
    y: rect.y,
    button: 'left',
    clickCount: 1,
  })
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: rect.x,
    y: rect.y,
    button: 'left',
    clickCount: 1,
  })
  await delay(60)
}

async function captureScreenshot(cdp, name) {
  if (!screenshotDir) return
  const result = await cdp.send('Page.captureScreenshot', {
    captureBeyondViewport: false,
    format: 'png',
    fromSurface: true,
  })
  await writeFile(join(screenshotDir, name), Buffer.from(result.data, 'base64'))
}

function waitForProcessExit(process, timeoutMs) {
  if (process.exitCode !== null || process.signalCode !== null) {
    return Promise.resolve(true)
  }

  return new Promise((resolveExit) => {
    const onExit = () => {
      clearTimeout(timer)
      resolveExit(true)
    }
    const timer = setTimeout(() => {
      process.off('exit', onExit)
      resolveExit(false)
    }, timeoutMs)
    process.once('exit', onExit)
  })
}

const { server, origin } = await startStaticServer()
const profileDir = await mkdtemp(join(tmpdir(), 'safetyagent-pages-chrome-'))
const chromePath = findChrome()
let chromeOutput = ''
const chromeArgs = [
  '--headless',
  '--disable-background-networking',
  '--disable-component-update',
  '--disable-default-apps',
  '--disable-dev-shm-usage',
  '--disable-extensions',
  '--disable-gpu',
  '--disable-sync',
  '--metrics-recording-only',
  '--mute-audio',
  '--no-default-browser-check',
  '--no-first-run',
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=0',
  `--user-data-dir=${profileDir}`,
  '--window-size=1440,1000',
  'about:blank',
]
if (process.platform === 'linux') chromeArgs.unshift('--no-sandbox')

const chrome = spawn(chromePath, chromeArgs, {
  stdio: ['ignore', 'pipe', 'pipe'],
})
for (const stream of [chrome.stdout, chrome.stderr]) {
  stream.setEncoding('utf8')
  stream.on('data', (chunk) => {
    chromeOutput = `${chromeOutput}${chunk}`.slice(-12_000)
  })
}

let cdp
const browserExceptions = []
const requestedUrls = []
const webSocketUrls = []
const networkFailures = []

try {
  const browserWebSocketUrl = await waitForDevToolsUrl(chrome, () => chromeOutput)
  const devToolsOrigin = `http://${new URL(browserWebSocketUrl).host}`
  await pollJson(`${devToolsOrigin}/json/version`, chrome)
  const target = await requestJson(
    `${devToolsOrigin}/json/new?${encodeURIComponent('about:blank')}`,
    'PUT',
  )
  cdp = await CdpSession.connect(target.webSocketDebuggerUrl)

  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Network.enable')
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }) => {
    browserExceptions.push(
      exceptionDetails?.exception?.description || exceptionDetails?.text || 'Unknown exception',
    )
  })
  cdp.on('Network.requestWillBeSent', ({ request }) => {
    if (request?.url) requestedUrls.push(request.url)
  })
  cdp.on('Network.webSocketCreated', ({ url }) => {
    if (url) webSocketUrls.push(url)
  })
  cdp.on('Network.loadingFailed', ({ errorText, type, blockedReason }) => {
    networkFailures.push({ errorText, type, blockedReason })
  })

  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url: `${origin}${publicBase}` })
  await loaded

  await waitFor(
    cdp,
    `Boolean(document.querySelector('[data-testid="canonical-landing"]'))`,
    'the canonical landing page',
  )
  assert.equal(
    await evaluate(cdp, 'document.title'),
    'SafetyAgent — Trust & Safety Orchestration',
  )
  const landing = await evaluate(cdp, `(() => {
    const mark = document.querySelector('[data-testid="brand-mark"]');
    return {
      copy: document.body.innerText,
      markUrl: mark?.src || '',
      hasArchitecture: Boolean(document.querySelector('[data-testid="architecture-link"]')),
      hasDemo: Boolean(document.querySelector('[data-testid="guided-demo-link"]')),
      hasDashboard: Boolean(document.querySelector('[data-testid="dashboard-link"]')),
    };
  })()`)
  assert.match(landing.copy, /Coordinate trust and safety decisions/)
  assert.match(landing.copy, /Synthetic public demo/i)
  assert.equal(landing.hasArchitecture, true)
  assert.equal(landing.hasDemo, true)
  assert.equal(landing.hasDashboard, true)
  assert.match(landing.markUrl, /\/trust-safety-orchestration-agent\/safetyagent-mark\.svg$/)
  await captureScreenshot(cdp, 'safetyagent-canonical-landing.png')

  await click(cdp, '[data-testid="architecture-link"]')
  await waitFor(
    cdp,
    `location.hash === '#/architecture' && Boolean(document.querySelector('[data-testid="architecture-frame"]'))`,
    'the architecture route',
  )
  await waitFor(
    cdp,
    `(() => {
      const frame = document.querySelector('[data-testid="architecture-frame"]');
      return Boolean(frame?.contentDocument?.getElementById('playBtn'));
    })()`,
    'the interactive architecture iframe',
  )
  const architectureReady = await evaluate(cdp, `(() => {
    const frame = document.querySelector('[data-testid="architecture-frame"]');
    const doc = frame.contentDocument;
    return {
      title: doc.title,
      nodeCount: doc.querySelectorAll('.node').length,
      narrationCount: frame.contentWindow.eval('narrationSteps.length'),
      bgmLoaded: typeof frame.contentWindow.eval('BGMEngine') === 'function',
    };
  })()`)
  assert.match(architectureReady.title, /SafetyAgent Architecture/)
  assert.ok(architectureReady.nodeCount >= 15)
  assert.ok(architectureReady.narrationCount >= 10)
  assert.equal(architectureReady.bgmLoaded, true)

  await evaluate(cdp, `(() => {
    const frame = document.querySelector('[data-testid="architecture-frame"]');
    const win = frame.contentWindow;
    const spoken = [];
    class TestUtterance {
      constructor(text) {
        this.text = String(text);
        this.onend = null;
        this.onerror = null;
      }
    }
    const synthesis = {
      cancel() {},
      speak(utterance) {
        spoken.push(utterance.text);
        win.setTimeout(() => utterance.onend?.({ type: 'end' }), 60);
      },
    };
    Object.defineProperty(win, 'SpeechSynthesisUtterance', {
      configurable: true,
      value: TestUtterance,
    });
    Object.defineProperty(win, 'speechSynthesis', {
      configurable: true,
      value: synthesis,
    });
    Object.defineProperty(win, '__safetyagentSpoken', {
      configurable: true,
      value: spoken,
    });
    win.eval("bgm.start = () => { document.body.dataset.bgmStarted = 'true'; }; bgm.fadeOut = () => { document.body.dataset.bgmStopped = 'true'; };");
    frame.contentDocument.getElementById('playBtn').click();
    return true;
  })()`)
  await waitFor(
    cdp,
    `(() => {
      const frame = document.querySelector('[data-testid="architecture-frame"]');
      const doc = frame.contentDocument;
      return doc.getElementById('narrationBar').classList.contains('visible')
        && frame.contentWindow.__safetyagentSpoken.length > 0
        && doc.querySelectorAll('.node.highlighted').length > 0
        && doc.body.dataset.bgmStarted === 'true';
    })()`,
    'architecture narration, animation, and audio start',
  )
  await captureScreenshot(cdp, 'safetyagent-architecture.png')
  await evaluate(cdp, `(() => {
    const frame = document.querySelector('[data-testid="architecture-frame"]');
    frame.contentDocument.getElementById('playBtn').click();
    return true;
  })()`)

  await click(cdp, '[data-testid="architecture-guided-link"]')
  await waitFor(
    cdp,
    `location.hash === '#/demo' && Boolean(document.querySelector('[data-testid="guided-demo"]'))`,
    'the guided scenario',
  )
  assert.match(await evaluate(cdp, 'document.body.innerText'), /SafetyAgent Illustrative Scenario/)
  for (let step = 1; step <= 6; step += 1) {
    await click(cdp, '[data-testid="demo-next"]')
    await waitFor(
      cdp,
      `document.body.innerText.includes('${step + 1} / 7')`,
      `guided scenario step ${step}`,
    )
  }
  const finalDemo = await evaluate(cdp, `(() => ({
    copy: document.body.innerText,
    nextDisabled: document.querySelector('[data-testid="demo-next"]')?.disabled,
  }))()`)
  assert.match(finalDemo.copy, /Sensitive Case: Always Human/)
  assert.equal(finalDemo.nextDisabled, true)
  await captureScreenshot(cdp, 'safetyagent-guided-scenario.png')

  await evaluate(cdp, `location.hash = '#/app'`)
  await waitFor(
    cdp,
    `document.body.innerText.includes('Trust & Safety Dashboard')
      && document.body.innerText.includes('Synthetic public demo')
      && document.body.innerText.toLowerCase().includes('platform safety score')`,
    'the synthetic operations dashboard',
  )
  await captureScreenshot(cdp, 'safetyagent-dashboard.png')

  const dashboardRoutes = [
    ['#/app/review', 'Review Queue'],
    ['#/app/cases', 'Active Cases'],
    ['#/app/admin', 'Configuration Management'],
    ['#/app/wellbeing', 'Reviewer Wellbeing'],
    ['#/app/getting-started', 'Getting Started'],
  ]
  for (const [hash, expectedText] of dashboardRoutes) {
    await evaluate(cdp, `location.hash = ${JSON.stringify(hash)}`)
    await waitFor(
      cdp,
      `document.body.innerText.includes(${JSON.stringify(expectedText)})`,
      expectedText,
    )
  }

  await evaluate(cdp, `location.hash = '#/app/cases'`)
  await waitFor(
    cdp,
    `Boolean(document.querySelector('a[href^="#/app/cases/"]'))`,
    'a synthetic case link',
  )
  await click(cdp, 'a[href^="#/app/cases/"]')
  await waitFor(
    cdp,
    `document.body.innerText.includes('Profile Metadata')
      && document.body.innerText.includes('Content Visibility')`,
    'synthetic case evidence',
  )

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    deviceScaleFactor: 1,
    height: 844,
    mobile: true,
    screenHeight: 844,
    screenWidth: 390,
    width: 390,
  })
  await evaluate(cdp, `location.hash = '#/'`)
  await waitFor(
    cdp,
    `Boolean(document.querySelector('[data-testid="canonical-landing"]'))`,
    'the mobile landing page',
  )
  const mobile = await evaluate(cdp, `(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    buttonCount: document.querySelectorAll('a[href="#/architecture"], a[href="#/demo"], a[href="#/app"]').length,
  }))()`)
  assert.ok(mobile.scrollWidth <= mobile.innerWidth + 1, `Mobile overflow: ${JSON.stringify(mobile)}`)
  assert.ok(mobile.buttonCount >= 3)
  await captureScreenshot(cdp, 'safetyagent-mobile-landing.png')

  const privateRequests = requestedUrls.filter((url) => {
    if (!url.startsWith('http://') && !url.startsWith('https://')) return false
    const parsed = new URL(url)
    return parsed.origin !== origin || parsed.pathname.includes('/api/')
  })
  assert.deepEqual(privateRequests, [], `Unexpected public-site requests: ${privateRequests.join(', ')}`)
  assert.deepEqual(webSocketUrls, [], `Unexpected WebSocket connections: ${webSocketUrls.join(', ')}`)
  assert.deepEqual(browserExceptions, [], `Browser exceptions: ${browserExceptions.join('\n')}`)
  assert.deepEqual(
    networkFailures.filter(({ errorText }) => errorText !== 'net::ERR_ABORTED'),
    [],
    `Network failures: ${JSON.stringify(networkFailures)}`,
  )
  assert.ok(
    requestedUrls.some((url) => url.endsWith(`${publicBase}narration/bgm-engine.js`)),
    'The architecture background-audio engine was not loaded from the Pages base path.',
  )

  console.log(
    'public site e2e OK: canonical landing, narrated architecture with animation/audio, '
      + '7-step guided scenario, synthetic dashboard routes, case evidence, and mobile layout',
  )
} catch (error) {
  if (cdp) {
    try {
      console.error(
        'Page state:',
        JSON.stringify(
          await evaluate(cdp, `(() => ({
            href: location.href,
            hash: location.hash,
            title: document.title,
            text: document.body?.innerText?.slice(0, 4000) || '',
            html: document.getElementById('root')?.innerHTML?.slice(0, 2000) || '',
          }))()`),
          null,
          2,
        ),
      )
    } catch (diagnosticError) {
      console.error('Unable to capture page state:', diagnosticError)
    }
  }
  console.error('Browser exceptions:', JSON.stringify(browserExceptions, null, 2))
  console.error('Requested URLs:', JSON.stringify(requestedUrls, null, 2))
  console.error('Network failures:', JSON.stringify(networkFailures, null, 2))
  if (chromeOutput) {
    console.error('Chrome output (tail):\n', chromeOutput)
  }
  throw error
} finally {
  cdp?.close()
  if (chrome.exitCode === null && chrome.signalCode === null) {
    chrome.kill('SIGTERM')
  }
  if (!await waitForProcessExit(chrome, 3_000)) {
    chrome.kill('SIGKILL')
    await waitForProcessExit(chrome, 3_000)
  }
  server.close()
  await rm(profileDir, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 100,
  })
}
