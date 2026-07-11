/* NovdAI dashboard — interactions (vanilla, no deps) */
(function () {
  'use strict';
  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Theme toggle ─────────────────────────────────────── */
  var KEY = 'novdai-theme';
  var themeBtn = document.getElementById('nv-theme-btn');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-bs-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    // re-run gauges/bars so arc colors (theme tokens) stay crisp
    animate();
  });

  /* ── Mobile drawer ────────────────────────────────────── */
  var app = document.getElementById('nv-app');
  document.querySelectorAll('[data-nv-open]').forEach(function (b) {
    b.addEventListener('click', function () { app.classList.add('drawer-open'); });
  });
  document.querySelectorAll('[data-nv-close]').forEach(function (b) {
    b.addEventListener('click', function () { app.classList.remove('drawer-open'); });
  });

  /* ── Language dropdown ────────────────────────────────── */
  var lang = document.getElementById('nv-lang');
  var langBtn = document.getElementById('nv-lang-btn');
  if (langBtn) langBtn.addEventListener('click', function (e) {
    e.stopPropagation(); lang.classList.toggle('open');
  });
  document.addEventListener('click', function () { if (lang) lang.classList.remove('open'); });
  document.querySelectorAll('.nv-lang-item').forEach(function (it) {
    it.addEventListener('click', function () {
      var input = document.getElementById('nv-lang-input');
      input.value = it.getAttribute('data-lang');
      document.getElementById('nv-lang-form').submit();
    });
  });

  /* ── Count-up + gauges + bars ─────────────────────────── */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var suffix = el.getAttribute('data-suffix') || '';
    if (reduce) { el.textContent = target + suffix; return; }
    var start = performance.now(), dur = 900;
    function step(now) {
      var p = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function setGauge(el) {
    var val = parseFloat(el.getAttribute('data-gauge')) || 0;
    var arc = el.querySelector('.nv-gauge-arc');
    if (!arc) return;
    var r = arc.r.baseVal.value, c = 2 * Math.PI * r;
    arc.style.strokeDasharray = c;
    arc.style.strokeDashoffset = c;
    var stroke = val >= 70 ? 'var(--nv-good)' : val >= 45 ? 'var(--nv-warn)' : 'var(--nv-bad)';
    arc.style.stroke = 'var(--nv-emerald)';
    // reveal after a tick so the transition runs
    requestAnimationFrame(function () {
      arc.style.strokeDashoffset = reduce ? (c * (1 - val / 100)) : (c * (1 - val / 100));
    });
    var lbl = el.querySelector('.nv-gauge-val');
    if (lbl) countUp(lbl);
  }

  function setBar(el) {
    var val = parseFloat(el.getAttribute('data-bar')) || 0;
    var fill = el.querySelector('span');
    var color = el.getAttribute('data-bar-color') || 'var(--nv-emerald)';
    if (fill) { fill.style.background = color; requestAnimationFrame(function () { fill.style.width = val + '%'; }); }
  }

  function animate() {
    document.querySelectorAll('[data-gauge]').forEach(setGauge);
    document.querySelectorAll('[data-bar]').forEach(setBar);
  }

  document.querySelectorAll('[data-count]').forEach(countUp);
  animate();

  /* ── Staggered rise ───────────────────────────────────── */
  if (!reduce) document.querySelectorAll('[data-rise]').forEach(function (el, i) {
    el.classList.add('nv-rise');
    el.style.animationDelay = (i * 55) + 'ms';
  });

  /* ── File upload (drag/drop + list) ───────────────────── */
  var drop = document.getElementById('nv-drop');
  var input = document.getElementById('nv-docs');
  var list = document.getElementById('nv-file-list');
  if (drop && input) {
    drop.addEventListener('click', function () { input.click(); });
    ['dragover', 'dragenter'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('drag'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('drag'); });
    });
    drop.addEventListener('drop', function (e) { input.files = e.dataTransfer.files; renderFiles(); });
    input.addEventListener('change', renderFiles);
    function renderFiles() {
      if (!list) return;
      list.innerHTML = '';
      Array.prototype.forEach.call(input.files, function (f) {
        var li = document.createElement('li');
        li.innerHTML = '<i class="ti ti-file-text"></i>' + f.name;
        list.appendChild(li);
      });
    }
  }

  /* ── Submit spinner ───────────────────────────────────── */
  var form = document.getElementById('nv-analyze-form');
  if (form) form.addEventListener('submit', function () {
    var btn = form.querySelector('[data-submit]');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader-2 nv-spin"></i>' + (btn.getAttribute('data-loading') || 'Analysing...'); }
  });
})();
