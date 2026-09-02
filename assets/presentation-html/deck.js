(() => {
  const meta = window.MODELAGEM_DECK || { slides: [] };
  const stage = document.getElementById('stage');

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  function safeHtml(value) {
    const template = document.createElement('template');
    template.innerHTML = String(value ?? '');
    template.content.querySelectorAll('script, iframe, object, embed').forEach((node) => node.remove());
    template.content.querySelectorAll('*').forEach((node) => {
      [...node.attributes].forEach((attribute) => {
        const name = attribute.name.toLowerCase();
        const raw = attribute.value.trim();
        if (name.startsWith('on')) node.removeAttribute(attribute.name);
        if ((name === 'src' || name === 'href') && /^(?:https?:)?\/\//i.test(raw)) node.removeAttribute(attribute.name);
      });
    });
    return template.innerHTML;
  }

  function renderMetrics(items = []) {
    return `<div class="metrics metrics-${Math.min(Math.max(items.length, 1), 4)}">${items.map((item) => `
      <article class="metric" data-term-id="${escapeHtml(item.termId)}">
        <strong>${escapeHtml(item.value)}</strong>
        <b>${escapeHtml(item.label)}</b>
        <span>${escapeHtml(item.definition)}</span>
      </article>`).join('')}</div>`;
  }

  function renderEvidence(items = []) {
    return `<div class="evidence-list">${items.map((item, index) => `
      <div><span>${String(index + 1).padStart(2, '0')}</span><b>${escapeHtml(item.label)}</b><p>${escapeHtml(item.text)}</p></div>`).join('')}</div>`;
  }

  function renderFlow(items = []) {
    return `<div class="flow flow-${Math.min(Math.max(items.length, 1), 5)}">${items.map((item, index) => `
      ${index ? '<i aria-hidden="true">→</i>' : ''}
      <div><span>${String(index + 1).padStart(2, '0')}</span><b>${escapeHtml(item.label)}</b><small>${escapeHtml(item.meaning)}</small></div>`).join('')}</div>`;
  }

  function renderComparison(items = []) {
    return `<div class="model-compare model-count-${Math.min(Math.max(items.length, 1), 3)}">${items.map((item, index) => `
      <article class="model model-${index + 1}"><span>${escapeHtml(item.label)}</span><strong${item.formulaLatex ? ` data-latex="${escapeHtml(item.formulaLatex)}"` : ''}>${escapeHtml(item.formula || item.formulaLatex)}</strong><p>${escapeHtml(item.reading)}</p></article>`).join('')}</div>`;
  }

  function renderMath() {
    document.querySelectorAll('[data-latex]').forEach((node) => {
      const expression = node.dataset.latex;
      if (!expression) return;
      if (!window.katex) throw new Error('KaTeX local não foi carregado.');
      window.katex.render(expression, node, { throwOnError: true, strict: 'error', displayMode: node.dataset.display === 'true' });
    });
  }

  function commonHeader(slide) {
    return `<header class="slide-header"><p class="eyebrow">${escapeHtml(slide.eyebrow || 'MODELAGEM')}</p><h2>${escapeHtml(slide.title)}</h2></header>`;
  }

  function renderLayout(slide) {
    const body = safeHtml(slide.bodyHtml);
    if (slide.layout === 'cover') {
      return `<div class="course-mark"><strong>${escapeHtml(meta.course || 'Modelagem Computacional')}</strong><span>${escapeHtml(meta.identification || '')}</span></div>
        <div class="cover-copy"><p class="eyebrow">${escapeHtml(slide.eyebrow || '')}</p><h1>${escapeHtml(slide.title || meta.title)}</h1><p class="lead">${escapeHtml(slide.lead || '')}</p></div>
        <footer class="cover-footer"><span>${(meta.team || []).slice(0, 3).map(escapeHtml).join(' · ')}</span><span>${(meta.team || []).slice(3).map(escapeHtml).join(' · ')}</span></footer>`;
    }
    if (slide.layout === 'metrics') {
      return `${commonHeader(slide)}${renderMetrics(slide.metrics)}<p class="takeaway">${escapeHtml(slide.takeaway)}</p>`;
    }
    if (slide.layout === 'flow') {
      return `${commonHeader(slide)}${renderFlow(slide.steps)}${slide.comparison ? renderComparison(slide.comparison) : body}`;
    }
    if (slide.layout === 'comparison') {
      return `${commonHeader(slide)}${renderComparison(slide.items)}${body ? `<div class="supporting-copy">${body}</div>` : ''}`;
    }
    if (slide.layout === 'visual') {
      return `${commonHeader(slide)}<div class="split split-visual"><figure class="visual-frame">${safeHtml(slide.visualHtml)}<figcaption>${escapeHtml(slide.caption)}</figcaption></figure>${renderEvidence(slide.evidence)}</div>`;
    }
    if (slide.layout === 'two-column') {
      return `${commonHeader(slide)}<div class="split split-equal"><div class="content-panel">${safeHtml(slide.leftHtml)}</div><div class="content-panel">${safeHtml(slide.rightHtml)}</div></div>`;
    }
    if (slide.layout === 'decision') {
      return `${commonHeader(slide)}<div class="decision-statement"><span>${escapeHtml(slide.resultLabel || 'RESULTADO')}</span><strong>${escapeHtml(slide.resultValue)}</strong></div><p class="lead decision-lead">${escapeHtml(slide.lead)}</p><div class="limit-callout"><b>Limite científico</b><span>${escapeHtml(slide.limit)}</span></div>`;
    }
    return `${commonHeader(slide)}<div class="content-body">${body}</div>`;
  }

  function buildSlides() {
    if (!Array.isArray(meta.slides) || !meta.slides.length) {
      throw new Error('deck-data.js não contém slides. Gere-o a partir do manifesto.');
    }
    document.title = meta.title ? `${meta.title} — Modelagem Computacional` : 'Apresentação — Modelagem Computacional';
    stage.replaceChildren();
    meta.slides.forEach((slide, index) => {
      const section = document.createElement('section');
      section.className = `slide slide-${slide.layout || 'content'}${index === 0 ? ' is-active' : ''}`;
      section.dataset.slideId = slide.id;
      section.dataset.ownerBlockId = slide.ownerBlockId;
      section.setAttribute('aria-label', slide.title || `Slide ${index + 1}`);
      section.innerHTML = renderLayout(slide);
      stage.appendChild(section);
    });
    renderMath();
  }

  buildSlides();
  const slides = [...document.querySelectorAll('.slide')];
  const count = slides.length;
  const params = new URLSearchParams(window.location.search);
  const isEmbed = params.get('embed') === '1';
  const requested = Number(params.get('slide') || window.location.hash.replace('#', ''));
  let current = Number.isFinite(requested) && requested > 0 ? Math.min(count - 1, requested - 1) : 0;
  let presenterWindow = null;

  if (isEmbed) document.body.classList.add('embed');
  const total = document.getElementById('total-number');
  if (total) total.textContent = String(count).padStart(2, '0');

  function slideState() {
    const element = slides[current];
    return { type: 'modelagem-deck-state', current, count, slideId: element?.dataset.slideId, ownerBlockId: element?.dataset.ownerBlockId };
  }

  function render(options = {}) {
    slides.forEach((slide, index) => slide.classList.toggle('is-active', index === current));
    const number = document.getElementById('current-number');
    const progress = document.getElementById('progress-bar');
    if (number) number.textContent = String(current + 1).padStart(2, '0');
    if (progress) progress.style.width = `${((current + 1) / count) * 100}%`;
    document.body.dataset.slide = String(current + 1);
    if (!isEmbed && options.updateUrl !== false) history.replaceState(null, '', `#${current + 1}`);
    const state = slideState();
    if (presenterWindow && !presenterWindow.closed) presenterWindow.postMessage(state, '*');
    if (window.opener && !window.opener.closed) window.opener.postMessage(state, '*');
    if (window.parent && window.parent !== window) window.parent.postMessage(state, '*');
  }

  function goTo(index) { current = Math.max(0, Math.min(count - 1, Number(index) || 0)); render(); }
  function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
    else document.exitFullscreen?.();
  }
  function openPresenter() {
    if (isEmbed) return;
    presenterWindow = window.open('presenter.html', 'modelagem-presenter', 'popup=yes,width=1500,height=920,resizable=yes');
  }

  window.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const key = event.key.toLowerCase();
    if (['arrowright', 'arrowdown', 'pagedown', ' '].includes(key)) { event.preventDefault(); goTo(current + 1); }
    else if (['arrowleft', 'arrowup', 'pageup'].includes(key)) { event.preventDefault(); goTo(current - 1); }
    else if (key === 'home') { event.preventDefault(); goTo(0); }
    else if (key === 'end') { event.preventDefault(); goTo(count - 1); }
    else if (key === 'f') { event.preventDefault(); toggleFullscreen(); }
    else if (key === 'p') { event.preventDefault(); openPresenter(); }
  });

  window.addEventListener('message', (event) => {
    const message = event.data || {};
    if (message.type === 'modelagem-presenter-ready' && presenterWindow && !presenterWindow.closed) {
      presenterWindow.postMessage(slideState(), '*');
      return;
    }
    if (message.type !== 'modelagem-presenter-command') return;
    if (message.command === 'next') goTo(current + 1);
    if (message.command === 'previous') goTo(current - 1);
    if (message.command === 'goto') goTo(message.index);
    if (message.command === 'fullscreen') toggleFullscreen();
  });

  window.DeckAPI = { goTo, openPresenter, toggleFullscreen, getState: slideState };
  render({ updateUrl: !isEmbed });
})();
