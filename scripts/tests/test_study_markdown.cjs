const assert = require('node:assert/strict');
const test = require('node:test');
const { prepareMarkdown, restoreMath } = require('../build_study_pdf.cjs');
const { runtimeRequire } = require('../node_runtime.cjs');
const { marked } = runtimeRequire('marked');
const katex = require('../../assets/vendor/katex/katex.min.js');

function render(source) {
  const prepared = prepareMarkdown(source, katex);
  return restoreMath(marked.parse(prepared.markdown, { gfm: true }), prepared.math);
}

test('fala sugerida becomes a real Markdown blockquote', () => {
  const html = render('## Fala sugerida\n\n> Explicamos o resultado.\n> Sem antecipar a conclusão.\n');
  assert.match(html, /<blockquote>\s*<p>Explicamos o resultado/);
  assert.doesNotMatch(html, /&gt; Explicamos/);
});

test('raw scripts and source HTML remain inert inside and outside a quote', () => {
  const html = render('> <script>globalThis.compromised=true</script>\n\n<img src="x" onerror="alert(1)">\n');
  assert.match(html, /<blockquote>/);
  assert.match(html, /&lt;script(?:>|&gt;)/);
  assert.doesNotMatch(html, /<script\b|<img\b/i);
});

test('quotes preserve inline math and escaped code', () => {
  const html = render('> Resíduo: \\(r=V-\\hat V\\).\n\n`<script>noop()</script>`\n');
  assert.match(html, /<blockquote>[\s\S]*class="katex"/);
  assert.match(html, /<code>&lt;script&gt;noop\(\)&lt;\/script&gt;<\/code>/);
  assert.doesNotMatch(html, /<script\b/i);
});
