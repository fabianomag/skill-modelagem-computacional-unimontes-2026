#!/usr/bin/env node
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { pathToFileURL } = require('url');
const { launchChromium, runtimeRequire, waitForLocalAssets } = require('./node_runtime.cjs');

const SKILL_DIR = path.resolve(__dirname, '..');
const KATEX_DIR = path.join(SKILL_DIR, 'assets', 'vendor', 'katex');

function usage() {
  console.error('Uso: node build_study_pdf.cjs FONTE.md DESTINO.pdf [--manifest manifesto.json]');
}

function parseArgs(argv) {
  const positional = [];
  let manifest = null;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--manifest') manifest = argv[++index];
    else positional.push(argv[index]);
  }
  if (positional.length !== 2) return null;
  return { source: path.resolve(positional[0]), destination: path.resolve(positional[1]), manifest: manifest && path.resolve(manifest) };
}

function fileHash(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function updateManifest(manifestPath, source, destination) {
  if (!manifestPath) return;
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const packageRoot = path.resolve(manifest.project.package_root);
  const relative = path.relative(packageRoot, destination).split(path.sep).join('/');
  if (!relative || relative.startsWith('../') || path.isAbsolute(relative)) throw new Error('O PDF de estudo deve ficar dentro do pacote do manifesto.');
  manifest.provenance ||= {};
  manifest.provenance.generated_pdf_sha256 ||= {};
  manifest.provenance.generated_pdf_sha256[relative] = fileHash(destination);
  manifest.provenance.study_sources ||= {};
  manifest.provenance.study_sources[relative] = { source_path: source, source_sha256: fileHash(source) };
  const temporary = `${manifestPath}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, manifestPath);
}

function prepareMarkdown(source, katex) {
  const protectedCode = [];
  const protectedMath = [];
  let text = source.replace(/```[\s\S]*?```|`[^`\n]+`/g, (match) => {
    const token = `@@MODELAGEM_CODE_${protectedCode.length}@@`;
    protectedCode.push(match);
    return token;
  });

  function equation(expression, displayMode) {
    try {
      const rendered = katex.renderToString(expression.trim(), {
        displayMode,
        throwOnError: true,
        strict: 'error',
        output: 'htmlAndMathml',
      });
      const html = displayMode ? `<div class="math-display">${rendered}</div>` : `<span class="math-inline">${rendered}</span>`;
      const token = `@@MODELAGEM_MATH_${displayMode ? 'D' : 'I'}_${protectedMath.length}@@`;
      protectedMath.push({ token, html, displayMode });
      return token;
    } catch (error) {
      throw new Error(`Fórmula inválida: ${expression}\n${error.message}`);
    }
  }

  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, body) => equation(body, true));
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, body) => equation(body, true));
  text = text.replace(/\\\(([^\n]*?)\\\)/g, (_, body) => equation(body, false));
  text = text.replace(/(^|[^$])\$([^$\n]+?)\$(?!\$)/g, (_, prefix, body) => `${prefix}${equation(body, false)}`);
  // Escaping '<' disables source HTML. Keep '>' so Markdown blockquotes retain
  // their meaning; a closing bracket alone cannot open an HTML tag.
  text = text.replace(/</g, '&lt;');
  text = text.replace(/@@MODELAGEM_CODE_(\d+)@@/g, (_, index) => protectedCode[Number(index)]);
  return { markdown: text, math: protectedMath };
}

function restoreMath(html, entries) {
  let result = html;
  for (const entry of entries) {
    if (entry.displayMode) {
      const paragraph = new RegExp(`<p>\\s*${entry.token}\\s*</p>`, 'g');
      result = result.replace(paragraph, entry.html);
    }
    result = result.replaceAll(entry.token, entry.html);
  }
  return result;
}

function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args) {
    usage();
    process.exit(2);
  }
  const { source, destination, manifest } = args;
  if (!fs.existsSync(source)) throw new Error(`Fonte inexistente: ${source}`);
  if (source === destination) throw new Error('A saída não pode sobrescrever a fonte.');

  const { marked } = runtimeRequire('marked');
  const { PDFDocument } = runtimeRequire('pdf-lib');
  const katex = require(path.join(KATEX_DIR, 'katex.min.js'));
  const markdown = fs.readFileSync(source, 'utf8');
  if (/\{\{[^}]+\}\}/.test(markdown)) throw new Error('A fonte ainda contém placeholders {{...}}.');
  const prepared = prepareMarkdown(markdown, katex);
  const body = restoreMath(marked.parse(prepared.markdown, { gfm: true, breaks: false }), prepared.math);
  const cssUrl = pathToFileURL(path.join(SKILL_DIR, 'assets', 'study-print.css')).href;
  const katexCssUrl = pathToFileURL(path.join(KATEX_DIR, 'katex.min.css')).href;
  const sourceBaseUrl = pathToFileURL(`${path.dirname(source)}${path.sep}`).href;
  const title = (markdown.match(/^#\s+(.+)$/m) || [null, 'Material de estudo'])[1];
  const html = `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title><base href="${sourceBaseUrl}">
<link rel="stylesheet" href="${katexCssUrl}"><link rel="stylesheet" href="${cssUrl}">
</head><body><main>${body}</main></body></html>`;

  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'modelagem-study-'));
  const htmlPath = path.join(temporary, 'document.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  let browser = null;
  let temporaryPdf = null;
  try {
    browser = await launchChromium();
    const page = await browser.newPage();
    const runtimeErrors = [];
    const blockedRequests = [];
    page.on('pageerror', (error) => runtimeErrors.push(error.message));
    page.on('console', (message) => {
      if (message.type() === 'error') runtimeErrors.push(message.text());
    });
    await page.route('**/*', async (route) => {
      const url = route.request().url();
      if (/^(?:file|data|blob|about):/i.test(url)) await route.continue();
      else { blockedRequests.push(url); await route.abort(); }
    });
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });
    await waitForLocalAssets(page);
    await page.emulateMedia({ media: 'print' });
    const audit = await page.evaluate(() => {
      const brokenImages = [...document.images].filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.src);
      const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
      const clipped = [...document.querySelectorAll('table, pre, .math-display, img, svg')].filter((element) => {
        const style = getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        return element.scrollWidth > element.clientWidth + 2 || element.scrollHeight > element.clientHeight + 2;
      }).slice(0, 8).map((element) => element.tagName + (element.className ? `.${String(element.className).replace(/\s+/g, '.')}` : ''));
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const raw = [];
      while (walker.nextNode()) {
        const parent = walker.currentNode.parentElement;
        if (parent?.closest('pre, code, .katex')) continue;
        const value = walker.currentNode.nodeValue || '';
        if (/\\(?:text|hat|frac|sum|begin)\b|\\\[|\\\]/.test(value)) raw.push(value.trim());
      }
      const katexErrors = [...document.querySelectorAll('.katex-error')].map((node) => node.textContent?.trim() || 'erro KaTeX');
      return { brokenImages, overflow, clipped, raw, katexErrors };
    });
    if (runtimeErrors.length) throw new Error(`Erros JavaScript: ${runtimeErrors.join(' | ')}`);
    if (blockedRequests.length) throw new Error(`Recursos remotos bloqueados: ${blockedRequests.join(', ')}`);
    if (audit.brokenImages.length) throw new Error(`Imagens quebradas: ${audit.brokenImages.join(', ')}`);
    if (audit.overflow) throw new Error('O documento possui overflow horizontal.');
    if (audit.clipped.length) throw new Error(`Conteúdo internamente cortado: ${audit.clipped.join(', ')}`);
    if (audit.katexErrors.length) throw new Error(`Erros KaTeX: ${audit.katexErrors.join(' | ')}`);
    if (audit.raw.length) throw new Error(`LaTeX cru detectado: ${audit.raw.slice(0, 3).join(' | ')}`);
    temporaryPdf = path.join(path.dirname(destination), `.${path.basename(destination)}.tmp-${process.pid}.pdf`);
    await page.pdf({
      path: temporaryPdf,
      format: 'A4',
      printBackground: true,
      preferCSSPageSize: true,
      margin: { top: '0', right: '0', bottom: '0', left: '0' },
    });
    const pdf = await PDFDocument.load(fs.readFileSync(temporaryPdf));
    if (pdf.getPageCount() < 1) throw new Error('O PDF não possui páginas.');
    fs.renameSync(temporaryPdf, destination);
    temporaryPdf = null;
    updateManifest(manifest, source, destination);
    console.log(JSON.stringify({ output: destination, pages: pdf.getPageCount() }));
  } finally {
    if (browser) await browser.close();
    if (temporaryPdf && fs.existsSync(temporaryPdf)) fs.rmSync(temporaryPdf, { force: true });
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exit(1);
  });
}

module.exports = { prepareMarkdown, restoreMath };
