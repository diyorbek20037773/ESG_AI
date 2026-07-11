// Initialize GLightbox
document.addEventListener('DOMContentLoaded', function () {
  if (typeof GLightbox !== 'undefined') {
    GLightbox({});
  }

  // ── Theme (Dark / Light Mode) ──────────────────────────────────
  // Anti-FOUC script in <head> already set data-bs-theme before render.
  // Here we just wire up the toggle button and sync aria-label.
  (function () {
    const STORAGE_KEY = 'novdai-theme';
    const html        = document.documentElement;

    function syncBtn(theme) {
      const btn = document.getElementById('theme-toggle-btn');
      if (!btn) return;
      const isDark = theme === 'dark';
      btn.setAttribute(
        'aria-label',
        isDark ? 'Kunduzgi rejimga o\'tish' : 'Tungi rejimga o\'tish'
      );
    }

    function setTheme(theme) {
      // Add transition class → smooth color switch
      html.classList.add('theme-switching');
      html.setAttribute('data-bs-theme', theme);
      localStorage.setItem(STORAGE_KEY, theme);
      syncBtn(theme);
      // Remove after transition ends
      setTimeout(function () { html.classList.remove('theme-switching'); }, 320);
    }

    // Sync button on page load (theme already applied by anti-FOUC)
    syncBtn(html.getAttribute('data-bs-theme') || 'light');

    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      btn.addEventListener('click', function () {
        const current = html.getAttribute('data-bs-theme') || 'light';
        setTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // Respect OS-level changes (e.g. system auto mode switches at night)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      // Only follow OS if user has NOT manually saved a preference
      if (!localStorage.getItem(STORAGE_KEY)) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });
  })();

  // Language switcher: strip language prefix from "next" so translate_url works correctly
  const langForm = document.getElementById('lang-switch-form');
  if (langForm) {
    const nextInput = langForm.querySelector('input[name="next"]');
    if (nextInput) {
      let path = window.location.pathname;
      // Strip non-default language prefixes (en, ru)
      const nonDefaultLangs = ['en', 'ru'];
      for (const lang of nonDefaultLangs) {
        if (path.startsWith('/' + lang + '/')) {
          path = path.slice(lang.length + 1) || '/';
          break;
        } else if (path === '/' + lang) {
          path = '/';
          break;
        }
      }
      nextInput.value = path;
    }
  }

  // Custom language dropdown
  const langBtn  = document.getElementById('lang-dropdown-btn');
  const langMenu = document.getElementById('lang-dropdown-menu');
  const langInput = document.getElementById('lang-hidden-input');

  if (langBtn && langMenu) {
    langBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      const isOpen = langMenu.classList.contains('open');
      langMenu.classList.toggle('open', !isOpen);
      langBtn.classList.toggle('open', !isOpen);
      langBtn.setAttribute('aria-expanded', String(!isOpen));
    });

    langMenu.querySelectorAll('.lang-dropdown-item').forEach(function (item) {
      item.addEventListener('click', function () {
        if (langInput) langInput.value = this.dataset.lang;
        if (langForm) langForm.submit();
      });
    });

    document.addEventListener('click', function () {
      langMenu.classList.remove('open');
      langBtn.classList.remove('open');
      langBtn.setAttribute('aria-expanded', 'false');
    });

    langMenu.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  // Hero verdict ring gauges: animate conic fill (--r) + number count-up
  (function () {
    var rings = document.querySelectorAll('.nv-fv-score i[data-ring]');
    if (!rings.length) return;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    rings.forEach(function (el, idx) {
      var target = parseInt(el.getAttribute('data-ring'), 10) || 0;
      var numEl  = el.parentElement.querySelector('b');
      if (reduce) { el.style.setProperty('--r', target); if (numEl) numEl.textContent = target; return; }
      var start = null, dur = 1300, delay = 500 + idx * 160;
      function step(ts) {
        if (!start) start = ts;
        var t = ts - start - delay;
        if (t < 0) { requestAnimationFrame(step); return; }
        var pr = Math.min(t / dur, 1);
        var e  = 1 - Math.pow(1 - pr, 3);
        var v  = e * target;
        el.style.setProperty('--r', v.toFixed(1));
        if (numEl) numEl.textContent = Math.round(v);
        if (pr < 1) requestAnimationFrame(step);
      }
      if (numEl) numEl.textContent = 0;
      requestAnimationFrame(step);
    });
  })();

  // Hero stat count-up (fires once on load)
  (function () {
    var nums = document.querySelectorAll('[data-countup]');
    if (!nums.length) return;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    nums.forEach(function (el) {
      var target = parseInt(el.getAttribute('data-countup'), 10) || 0;
      if (reduce) { el.textContent = target; return; }
      var start = null, dur = 1100;
      function step(ts) {
        if (!start) start = ts;
        var pr = Math.min((ts - start) / dur, 1);
        var e  = 1 - Math.pow(1 - pr, 3);
        el.textContent = Math.round(e * target);
        if (pr < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  })();

  // Custom cursor follower
  (function () {
    if (!window.matchMedia('(pointer: fine)').matches) return;

    const dot  = document.getElementById('cursor-dot');
    const ring = document.getElementById('cursor-ring');
    if (!dot || !ring) return;

    let mX = 0, mY = 0;
    let rX = 0, rY = 0;
    let rafId;

    document.addEventListener('mousemove', function (e) {
      mX = e.clientX;
      mY = e.clientY;
      dot.style.left    = mX + 'px';
      dot.style.top     = mY + 'px';
      dot.style.opacity = '1';
      ring.style.opacity = '1';
    });

    document.addEventListener('mouseleave', function () {
      dot.style.opacity  = '0';
      ring.style.opacity = '0';
    });

    document.addEventListener('mousedown', function () {
      dot.classList.add('is-clicking');
      ring.classList.add('is-clicking');
    });
    document.addEventListener('mouseup', function () {
      dot.classList.remove('is-clicking');
      ring.classList.remove('is-clicking');
    });

    // Hover state on interactive elements
    var hoverTargets = 'a, button, [role="button"], .card-lift, .lang-dropdown-item, .social-link, .play-btn';
    document.querySelectorAll(hoverTargets).forEach(function (el) {
      el.addEventListener('mouseenter', function () {
        dot.classList.add('is-hovered');
        ring.classList.add('is-hovered');
      });
      el.addEventListener('mouseleave', function () {
        dot.classList.remove('is-hovered');
        ring.classList.remove('is-hovered');
      });
    });

    // Ring follows with spring lag via rAF
    function animateRing() {
      rX += (mX - rX) * 0.1;
      rY += (mY - rY) * 0.1;
      ring.style.left = rX + 'px';
      ring.style.top  = rY + 'px';
      rafId = requestAnimationFrame(animateRing);
    }
    rafId = requestAnimationFrame(animateRing);
  })();

  // Smooth Scroll — index sahifasida bo'lsa anchor scroll,
  // boshqa sahifada bo'lsa to'liq URL ga navigatsiya qiladi.
  document.querySelectorAll('.nav-link[href*="#"]').forEach(link => {
    link.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      const hashIdx = href.indexOf('#');
      if (hashIdx === -1) return;

      const hash     = href.slice(hashIdx);      // '#hero'
      const pathPart = href.slice(0, hashIdx);   // '/uz/' yoki ''

      // Agar link joriy sahifani ko'rsatsa — smooth scroll
      const onSamePage = !pathPart || pathPart === window.location.pathname;
      if (onSamePage) {
        const target = document.querySelector(hash);
        if (target) {
          e.preventDefault();
          window.scrollTo({ top: target.offsetTop - 80, behavior: 'smooth' });
        }
      }
      // else: brauzer to'liq URLga navigatsiya qiladi
    });
  });

  // Active link on scroll — 'url#id' va '#id' shakllarini ham tushunadi
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  window.addEventListener('scroll', () => {
    let scrollPos = window.scrollY + 100;
    sections.forEach(sec => {
      if (scrollPos >= sec.offsetTop && scrollPos < sec.offsetTop + sec.offsetHeight) {
        navLinks.forEach(link => {
          link.classList.remove('active');
          const href = link.getAttribute('href') || '';
          if (href.endsWith('#' + sec.id)) {
            link.classList.add('active');
          }
        });
      }
    });
  });
});
