const fs = require('fs');
const os = require('os');
const path = require('path');
const { createRequire } = require('module');

function runtimeRoot() {
  return path.resolve(process.env.MODELAGEM_RUNTIME_DIR || path.join(os.homedir(), '.cache', 'modelagem-computacional-grupo'));
}

function moduleRoots() {
  const roots = [process.env.RUNTIME_NODE_MODULES, path.join(runtimeRoot(), 'node', 'node_modules'), path.resolve(__dirname, '..', 'node_modules'), path.resolve(process.cwd(), 'node_modules')];
  if (process.env.MODELAGEM_DISABLE_CODEX_RUNTIME !== '1') roots.push(path.join(os.homedir(), '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules'));
  return [...new Set(roots.filter(Boolean).map((root) => path.resolve(root)))];
}

function nodeModulesRoot() {
  const root = moduleRoots().find((candidate) => fs.existsSync(candidate));
  if (!root) throw new Error('Dependências Node ausentes. Execute scripts/setup_runtime.py para diagnóstico; a instalação isolada exige --install.');
  return root;
}

function runtimeRequire(packageName) {
  if (packageName === 'playwright') {
    const browsers = path.join(runtimeRoot(), 'browsers');
    if (!process.env.PLAYWRIGHT_BROWSERS_PATH && fs.existsSync(browsers)) process.env.PLAYWRIGHT_BROWSERS_PATH = browsers;
  }
  for (const root of moduleRoots()) {
    const entry = path.join(root, packageName);
    if (fs.existsSync(entry)) return require(entry);
  }
  const localRequire = createRequire(path.join(process.cwd(), 'modelagem-runtime.cjs'));
  try { return localRequire(packageName); } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') throw error;
  }
  throw new Error(`Dependência Node ausente: ${packageName}. Execute scripts/setup_runtime.py; não há instalação automática.`);
}

function isExecutable(candidate) {
  if (!candidate) return false;
  try {
    return fs.statSync(candidate).isFile() && (process.platform === 'win32' || (fs.accessSync(candidate, fs.constants.X_OK), true));
  } catch (_) { return false; }
}

function chromeExecutable() {
  if (process.env.CHROME_PATH) {
    if (!isExecutable(process.env.CHROME_PATH)) throw new Error('CHROME_PATH não aponta para um executável válido.');
    return process.env.CHROME_PATH;
  }
  const isolatedBrowsers = path.join(runtimeRoot(), 'browsers');
  if (!process.env.PLAYWRIGHT_BROWSERS_PATH && fs.existsSync(isolatedBrowsers)) process.env.PLAYWRIGHT_BROWSERS_PATH = isolatedBrowsers;
  const { chromium } = runtimeRequire('playwright');
  const bundledChromium = chromium.executablePath();
  if (isExecutable(bundledChromium)) return bundledChromium;
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'),
  ].filter(Boolean);
  const match = candidates.find(isExecutable);
  if (match) return match;
  throw new Error('Chromium/Chrome não localizado. Defina CHROME_PATH ou autorize setup_runtime.py --install para baixar Chromium em cache isolado.');
}

async function launchChromium() {
  // Browser cache must be selected before Playwright initializes its registry.
  const isolatedBrowsers = path.join(runtimeRoot(), 'browsers');
  if (!process.env.PLAYWRIGHT_BROWSERS_PATH && fs.existsSync(isolatedBrowsers)) process.env.PLAYWRIGHT_BROWSERS_PATH = isolatedBrowsers;
  const executablePath = chromeExecutable();
  const { chromium } = runtimeRequire('playwright');
  return chromium.launch({ executablePath, headless: true });
}

async function waitForLocalAssets(page) {
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await Promise.all(
      [...document.images].map((image) => {
        if (image.complete) return Promise.resolve();
        return new Promise((resolve) => {
          image.addEventListener('load', resolve, { once: true });
          image.addEventListener('error', resolve, { once: true });
        });
      })
    );
  });
}

module.exports = { chromeExecutable, launchChromium, moduleRoots, nodeModulesRoot, runtimeRequire, runtimeRoot, waitForLocalAssets };
