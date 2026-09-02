#!/usr/bin/env node
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { launchChromium, runtimeRequire, waitForLocalAssets } = require('./node_runtime.cjs');

function parseArgs(argv) {
  const positional = [];
  let manifest = null;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--manifest') manifest = argv[++index];
    else positional.push(argv[index]);
  }
  if (positional.length !== 2 || !manifest) throw new Error('Uso: node build_deck_pdf.cjs index.html apresentacao.pdf --manifest manifesto.json');
  return { source: path.resolve(positional[0]), destination: path.resolve(positional[1]), manifest: manifest && path.resolve(manifest) };
}

function allBundleFiles(root, destination) {
  const result = [];
  function visit(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(absolute);
      else if (absolute !== destination && path.extname(entry.name).toLowerCase() !== '.pdf') result.push(absolute);
    }
  }
  visit(root);
  return result.sort((a, b) => path.relative(root, a).localeCompare(path.relative(root, b)));
}

function bundleHash(root, destination) {
  const hash = crypto.createHash('sha256');
  for (const file of allBundleFiles(root, destination)) {
    hash.update(path.relative(root, file));
    hash.update(Buffer.from([0]));
    hash.update(fs.readFileSync(file));
    hash.update(Buffer.from([0]));
  }
  return hash.digest('hex');
}

function updateManifest(manifestPath, destination, digest) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const expected = manifest.slides || [];
  const packageRoot = path.resolve(manifest.project.package_root);
  const expectedPdf = manifest.artifacts.presentation.pdf;
  const expectedDestination = path.resolve(packageRoot, expectedPdf);
  if (expectedDestination !== destination) throw new Error(`Destino PDF diverge do manifesto: ${expectedPdf}`);
  manifest.provenance ||= {};
  manifest.provenance.presentation_bundle_sha256_at_pdf_generation = digest;
  manifest.provenance.generated_pdf_sha256 ||= {};
  manifest.provenance.generated_pdf_sha256[expectedPdf] = crypto.createHash('sha256').update(fs.readFileSync(destination)).digest('hex');
  manifest.provenance.presentation_slide_count_at_pdf_generation = expected.length;
  const temporary = `${manifestPath}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, manifestPath);
}

async function main() {
  const { source, destination, manifest } = parseArgs(process.argv.slice(2));
  if (!fs.existsSync(source)) throw new Error(`Deck inexistente: ${source}`);
  const root = path.dirname(source);
  const bundleFiles = allBundleFiles(root, destination);
  const placeholderFiles = bundleFiles.filter((file) => ['.html', '.css', '.js', '.json', '.svg', '.txt'].includes(path.extname(file).toLowerCase()));
  const unresolved = placeholderFiles.filter((file) => /\{\{[A-Z0-9_]+\}\}/.test(fs.readFileSync(file, 'utf8')));
  if (unresolved.length) throw new Error(`O bundle ainda contém placeholders: ${unresolved.map((file) => path.relative(root, file)).join(', ')}`);

  const { PDFDocument } = runtimeRequire('pdf-lib');
  const browser = await launchChromium();
  let slides;
  let temporaryPdf = null;
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
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
    await page.goto(pathToFileURL(source).href, { waitUntil: 'networkidle' });
    await waitForLocalAssets(page);
    await page.emulateMedia({ media: 'print' });
    slides = await page.evaluate(() => {
      const items = [...document.querySelectorAll('.slide')];
      const brokenImages = [...document.images].filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.src);
      const entries = items.map((slide, index) => {
        const bounds = slide.getBoundingClientRect();
        const overflow = [...slide.querySelectorAll('*')].filter((element) => {
          const style = getComputedStyle(element);
          if (style.display === 'none' || style.visibility === 'hidden') return false;
          const rect = element.getBoundingClientRect();
          return rect.left < bounds.left - 1 || rect.top < bounds.top - 1 || rect.right > bounds.right + 1 || rect.bottom > bounds.bottom + 1;
        }).slice(0, 8).map((element) => element.tagName + (element.className ? `.${String(element.className).replace(/\s+/g, '.')}` : ''));
        return {
          id: slide.dataset.slideId,
          ownerBlockId: slide.dataset.ownerBlockId,
          title: slide.querySelector('h1,h2')?.textContent?.trim() || '',
          ordinal: index + 1,
          overflow,
        };
      });
      const katexErrors = [...document.querySelectorAll('.katex-error')].map((node) => node.textContent?.trim() || 'erro KaTeX');
      const rawLatex = [...document.querySelectorAll('[data-latex]')].filter((node) => !node.querySelector('.katex')).map((node) => node.dataset.latex || node.textContent || '');
      return { entries, brokenImages, katexErrors, rawLatex };
    });
    if (runtimeErrors.length) throw new Error(`Erros JavaScript: ${runtimeErrors.join(' | ')}`);
    if (blockedRequests.length) throw new Error(`Recursos remotos bloqueados: ${blockedRequests.join(', ')}`);
    if (!slides.entries.length) throw new Error('Nenhum .slide encontrado.');
    if (slides.brokenImages.length) throw new Error(`Imagens quebradas: ${slides.brokenImages.join(', ')}`);
    if (slides.katexErrors.length || slides.rawLatex.length) throw new Error(`Fórmulas não renderizadas: ${[...slides.katexErrors, ...slides.rawLatex].join(' | ')}`);
    const bad = slides.entries.filter((slide) => !slide.id || !slide.ownerBlockId || slide.overflow.length);
    if (bad.length) throw new Error(`Slides inválidos/overflow: ${JSON.stringify(bad)}`);

    if (manifest) {
      const data = JSON.parse(fs.readFileSync(manifest, 'utf8'));
      const expected = (data.slides || []).slice().sort((a, b) => a.ordinal - b.ordinal).map((slide) => ({ id: slide.id, ownerBlockId: slide.owner_block_id || slide.ownerBlockId, title: slide.title }));
      const actual = slides.entries.map(({ id, ownerBlockId, title }) => ({ id, ownerBlockId, title }));
      if (JSON.stringify(expected) !== JSON.stringify(actual)) throw new Error('IDs ou responsáveis do HTML divergem do manifesto.');
    }

    fs.mkdirSync(path.dirname(destination), { recursive: true });
    temporaryPdf = path.join(path.dirname(destination), `.${path.basename(destination)}.tmp-${process.pid}.pdf`);
    await page.pdf({ path: temporaryPdf, printBackground: true, preferCSSPageSize: true, margin: { top: '0', right: '0', bottom: '0', left: '0' } });
    const pdf = await PDFDocument.load(fs.readFileSync(temporaryPdf));
    if (pdf.getPageCount() !== slides.entries.length) {
      throw new Error(`HTML possui ${slides.entries.length} slides e o PDF possui ${pdf.getPageCount()} páginas.`);
    }
    fs.renameSync(temporaryPdf, destination);
    temporaryPdf = null;
  } finally {
    await browser.close();
    if (temporaryPdf && fs.existsSync(temporaryPdf)) fs.rmSync(temporaryPdf, { force: true });
  }

  const digest = bundleHash(root, destination);
  updateManifest(manifest, destination, digest);
  console.log(JSON.stringify({ output: destination, slides: slides.entries.length, bundle_sha256: digest }));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
