/* VenuePulse client logic (loaded before Alpine): stores, components, shortcuts and HTMX glue. */
(function () {
  'use strict';

  // ------------------------------------------------------------------ utilities
  const safe = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };
  const pad = (n) => String(n).padStart(2, '0');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const BROWSER_TZ = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch (e) { return 'UTC'; } })();
  const COMMON_TZ = ['UTC', 'America/Los_Angeles', 'America/Denver', 'America/Chicago', 'America/New_York', 'America/Sao_Paulo',
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Athens', 'Africa/Cairo', 'Africa/Johannesburg', 'Asia/Dubai',
    'Asia/Kolkata', 'Asia/Dhaka', 'Asia/Bangkok', 'Asia/Singapore', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Tokyo',
    'Australia/Sydney', 'Pacific/Auckland'];

  function validZone(zone) {
    try { new Intl.DateTimeFormat('en-US', { timeZone: zone }); return true; } catch (e) { return false; }
  }

  const formatters = {};
  function fmtZone(ms, zone) {
    const key = zone || 'local';
    if (!formatters[key]) {
      const opts = { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' };
      if (zone) opts.timeZone = zone;
      try { formatters[key] = new Intl.DateTimeFormat(undefined, opts); } catch (e) { formatters[key] = new Intl.DateTimeFormat(undefined, { ...opts, timeZone: undefined }); }
    }
    return formatters[key].format(new Date(ms));
  }

  // "Anywhere on Earth" = UTC-12: shift the instant and read it back with UTC getters.
  function fmtAoE(ms) {
    const d = new Date(ms - 12 * 3600 * 1000);
    return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} AoE`;
  }

  const rtf = (() => { try { return new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }); } catch (e) { return null; } })();
  function relative(ms, now) {
    const diff = ms - now;
    const abs = Math.abs(diff);
    const units = [['day', 86400000], ['hour', 3600000], ['minute', 60000]];
    for (const [unit, size] of units) {
      if (abs >= size || unit === 'minute') {
        const value = Math.round(diff / size);
        return rtf ? rtf.format(value, unit) : `${value} ${unit}s`;
      }
    }
    return '';
  }

  function csrfHeaders() {
    try { return JSON.parse(document.body.getAttribute('hx-headers') || '{}'); } catch (e) { return {}; }
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      ta.remove(); return ok;
    }
  }

  window.VenuePulse = { fmtAoE, fmtZone, relative, copyText };

  // ------------------------------------------------------------------ Alpine
  document.addEventListener('alpine:init', () => {
    const toast = (msg, type) => Alpine.store('toast').show(msg, type);

    Alpine.store('clock', { now: Date.now() });
    setInterval(() => { Alpine.store('clock').now = Date.now(); }, 1000);

    Alpine.store('tz', {
      zone: (() => {
        const fromProfile = document.body.dataset.userTz;
        const saved = safe.get('vp-tz');
        for (const z of [fromProfile, saved, BROWSER_TZ]) if (z && validZone(z)) return z;
        return 'UTC';
      })(),
      _options: null,
      options() {
        if (!this._options) {
          let list = [];
          try { list = Intl.supportedValuesOf('timeZone'); } catch (e) { list = COMMON_TZ; }
          this._options = Array.from(new Set(['UTC', BROWSER_TZ, this.zone, ...list]));
        }
        return this._options;
      },
      set(zone) {
        if (!validZone(zone)) return;
        this.zone = zone;
        safe.set('vp-tz', zone);
        const url = document.body.dataset.tzUrl;
        if (document.body.dataset.authenticated === '1' && url) {
          fetch(url, { method: 'POST', headers: { ...csrfHeaders(), 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'timezone=' + encodeURIComponent(zone) })
            .then((r) => toast(r.ok ? `Times now shown in ${zone}` : 'Could not save your timezone', r.ok ? 'success' : 'error'))
            .catch(() => toast('Could not save your timezone', 'error'));
        } else {
          toast(`Times now shown in ${zone}`);
        }
      },
    });

    const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    Alpine.store('theme', {
      mode: ['light', 'dark', 'system'].includes(safe.get('vp-theme')) ? safe.get('vp-theme') : 'system',
      dark: document.documentElement.classList.contains('dark'),
      init() { if (media) media.addEventListener('change', () => { if (this.mode === 'system') this.apply(); }); },
      apply() {
        this.dark = this.mode === 'dark' || (this.mode === 'system' && !!media && media.matches);
        document.documentElement.classList.toggle('dark', this.dark);
      },
      set(mode) { this.mode = mode; safe.set('vp-theme', mode); this.apply(); },
      toggle() { this.set(this.dark ? 'light' : 'dark'); },
    });

    Alpine.store('toast', {
      msg: '', type: 'info', visible: false, timer: null,
      show(msg, type) {
        this.msg = msg; this.type = type || 'info'; this.visible = true;
        clearTimeout(this.timer);
        this.timer = setTimeout(() => { this.visible = false; }, this.type === 'error' ? 5000 : 2600);
      },
    });

    Alpine.store('shortcuts', { open: false });

    Alpine.store('compare', {
      items: [], open: false, max: 4,
      init() {
        try { this.items = JSON.parse(safe.get('vp-compare') || '[]').filter((i) => i && i.slug); } catch (e) { this.items = []; }
      },
      has(slug) { return this.items.some((i) => i.slug === slug); },
      save() { safe.set('vp-compare', JSON.stringify(this.items)); },
      toggle(slug, acronym) {
        if (this.has(slug)) {
          this.items = this.items.filter((i) => i.slug !== slug);
          toast(`Removed ${acronym} from comparison`);
        } else if (this.items.length < this.max) {
          this.items.push({ slug, acronym });
          toast(`Added ${acronym} to comparison (${this.items.length}/${this.max})`);
        } else {
          toast(`You can compare up to ${this.max} venues — remove one first`, 'error');
          return;
        }
        this.save();
        if (this.open) this.load();
      },
      clear() { this.items = []; this.save(); if (this.open) this.load(); },
      url() { return '/compare/?' + this.items.map((i) => 's=' + encodeURIComponent(i.slug)).join('&'); },
      async copyLink() { if (await copyText(location.origin + this.url())) toast('Comparison link copied'); },
      show() { this.open = true; this.load(); },
      load() { htmx.ajax('GET', this.url(), { target: '#compare-body', swap: 'innerHTML' }); },
    });

    Alpine.data('countdown', (iso) => {
      const target = new Date(iso).getTime();
      return {
        target,
        aoe: fmtAoE(target),
        get local() { return fmtZone(this.target, Alpine.store('tz').zone); },
        get relative() { return relative(this.target, Alpine.store('clock').now); },
        get diff() { return Math.max(0, this.target - Alpine.store('clock').now); },
        get done() { return this.target <= Alpine.store('clock').now; },
        get d() { return Math.floor(this.diff / 86400000); },
        get h() { return pad(Math.floor(this.diff / 3600000) % 24); },
        get m() { return pad(Math.floor(this.diff / 60000) % 60); },
        get s() { return pad(Math.floor(this.diff / 1000) % 60); },
        get urgent() { return !this.done && this.diff < 7 * 86400000; },
      };
    });

    // A timestamp rendered in the viewer's chosen timezone: <span x-data="when('…')" x-text="text"></span>
    Alpine.data('when', (iso) => ({
      t: new Date(iso).getTime(),
      get text() { return fmtZone(this.t, Alpine.store('tz').zone); },
    }));

    Alpine.data('dismissible', (key) => ({
      hidden: safe.get('vp-dismiss-' + key) === '1',
      dismiss() { this.hidden = true; safe.set('vp-dismiss-' + key, '1'); },
    }));

    // Filter sidebar helper: table header sorting, chips, IF slider label, saved searches.
    Alpine.data('listPage', (minIf) => ({
      minIf, filtersOpen: false,
      form() { return document.getElementById('filters'); },
      submit() { htmx.trigger(this.form(), 'change'); },
      setSort(key, defaultDir) {
        const f = this.form();
        const dir = f.elements.dir;
        if (f.elements.sort.value === key) dir.value = dir.value === 'asc' ? 'desc' : 'asc';
        else { f.elements.sort.value = key; dir.value = defaultDir; }
        this.submit();
      },
      setView(view) {
        this.form().elements.view.value = view;
        this.submit();
      },
      closingWithin(days) {
        const f = this.form();
        for (const el of f.elements) if (el.name === 'status') el.checked = el.value === '';
        f.elements.within.value = days;
        this.submit();
        const top = document.getElementById('results-top');
        if (top) top.scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
      removeFilter(name, value) {
        for (const el of this.form().elements) {
          if (el.name !== name) continue;
          if (el.type === 'checkbox') { if (value == null || el.value === value) el.checked = false; }
          else if (el.type === 'radio') { el.checked = el.value === ''; }
          else if (el.type === 'range') { el.value = 0; this.minIf = 0; }
          else if (el.tagName === 'SELECT' && el.multiple) { for (const o of el.options) if (value == null || o.value === value) o.selected = false; }
          else el.value = '';
        }
        this.submit();
      },
      saveSearch() {
        const name = document.getElementById('ss-name').value.trim();
        if (!name) { toast('Give the search a name', 'error'); return; }
        const params = new URLSearchParams(new FormData(this.form()));
        for (const [k, v] of [...params.entries()]) if (!v || k === 'csrfmiddlewaretoken' || (k === 'min_if' && v === '0')) params.delete(k);
        const sf = document.getElementById('save-search-form');
        sf.elements.name.value = name;
        sf.elements.querystring.value = params.toString();
        sf.elements.alert.value = document.getElementById('ss-alert').checked ? 'on' : '';
        sf.submit();
      },
      reset() {
        const f = this.form();
        for (const el of f.elements) {
          if (el.type === 'checkbox') el.checked = false;
          else if (el.type === 'radio') el.checked = el.value === '';
          else if (el.type === 'range') el.value = 0;
          else if (el.tagName === 'SELECT' && el.name !== 'sort') el.selectedIndex = 0;
          else if (el.type === 'search' || el.type === 'text') el.value = '';
        }
        this.minIf = 0;
        this.submit();
      },
    }));

    const PAGES = [
      { acronym: 'Explore venues', name: 'Search & filter every venue', url: '/', flag: '🔎', type: 'Page' },
      { acronym: 'Recommend', name: 'Find venues for my paper', url: '/recommend/', flag: '✨', type: 'Page' },
      { acronym: 'Deadline planner', name: 'When will my paper be ready?', url: '/plan/', flag: '🗓️', type: 'Page' },
      { acronym: 'Insights', name: 'Charts & statistics', url: '/insights/', flag: '📊', type: 'Page' },
      { acronym: 'My targets', name: 'Starred venues', url: '/targets/', flag: '⭐', type: 'Page' },
      { acronym: 'Dashboard', name: 'Your deadlines & submissions', url: '/accounts/', flag: '🏠', type: 'Page' },
      { acronym: 'Tracker', name: 'My submissions board', url: '/tracker/', flag: '📌', type: 'Page' },
      { acronym: 'Deadline radar', name: 'Recent date changes', url: '/community/changes/', flag: '📡', type: 'Page' },
      { acronym: 'API docs', name: 'JSON API & feeds', url: '/api/docs/', flag: '🧩', type: 'Page' },
      { acronym: 'Toggle dark mode', name: 'Switch between light and dark', action: 'theme', flag: '🌓', type: 'Action', url: '' },
      { acronym: 'Open comparison', name: 'Show the compare drawer', action: 'compare', flag: '⚖️', type: 'Action', url: '' },
      { acronym: 'Keyboard shortcuts', name: 'Show all shortcuts', action: 'shortcuts', flag: '⌨️', type: 'Action', url: '' },
    ];

    Alpine.data('palette', () => ({
      open: false, q: '', results: [], idx: 0, seq: 0,
      show() {
        this.open = true; this.q = ''; this.results = PAGES; this.idx = 0;
        this.$nextTick(() => this.$refs.input.focus());
      },
      move(d) { this.idx = Math.max(0, Math.min(this.results.length - 1, this.idx + d)); },
      run(r) {
        this.open = false;
        if (r.action === 'theme') Alpine.store('theme').toggle();
        else if (r.action === 'compare') Alpine.store('compare').show();
        else if (r.action === 'shortcuts') Alpine.store('shortcuts').open = true;
      },
      go() {
        const r = this.results[this.idx];
        if (!r) return;
        if (r.action) this.run(r); else window.location.href = r.url;
      },
      async search() {
        const q = this.q.trim().toLowerCase();
        const seq = ++this.seq;
        const pages = PAGES.filter((p) => !q || (p.acronym + ' ' + p.name).toLowerCase().includes(q));
        if (!q) { this.results = pages; this.idx = 0; return; }
        try {
          const res = await fetch('/api/suggest/?q=' + encodeURIComponent(q), { headers: { Accept: 'application/json' } });
          const venues = res.ok ? (await res.json()).results : [];
          if (seq !== this.seq) return; // a newer keystroke won
          this.results = [...venues, ...pages];
        } catch (e) {
          if (seq === this.seq) this.results = pages;
        }
        this.idx = 0;
      },
    }));

    Alpine.data('copier', () => ({
      copied: false,
      async copy(text) {
        if (await copyText(text)) { this.copied = true; toast('Copied to clipboard'); setTimeout(() => { this.copied = false; }, 1800); }
        else toast('Copy failed — select the text manually', 'error');
      },
    }));

    Alpine.data('sharer', (url, title) => ({
      async share() {
        const full = new URL(url, location.origin).toString();
        if (navigator.share) {
          try { await navigator.share({ title, url: full }); return; } catch (e) { if (e && e.name === 'AbortError') return; }
        }
        if (await copyText(full)) toast('Link copied to clipboard');
      },
    }));
  });

  // ------------------------------------------------------------------ keyboard shortcuts
  let pendingG = 0;
  const GO = { h: '/', t: '/targets/', r: '/recommend/', d: '/accounts/', k: '/tracker/', i: '/insights/', p: '/plan/' };
  document.addEventListener('keydown', (e) => {
    const el = e.target;
    const typing = el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      window.dispatchEvent(new CustomEvent('open-palette'));
      return;
    }
    if (typing || e.ctrlKey || e.metaKey || e.altKey || !window.Alpine) return;
    if (pendingG && Date.now() - pendingG < 1200 && GO[e.key]) {
      pendingG = 0; window.location.href = GO[e.key]; return;
    }
    pendingG = 0;
    if (e.key === 'g') { pendingG = Date.now(); return; }
    if (e.key === '/') {
      const q = document.getElementById('q');
      e.preventDefault();
      if (q) q.focus(); else window.dispatchEvent(new CustomEvent('open-palette'));
    } else if (e.key === '?') {
      Alpine.store('shortcuts').open = true;
    } else if (e.key === 'c') {
      Alpine.store('compare').show();
    } else if (e.key === 'd') {
      Alpine.store('theme').toggle();
    }
  });

  // ------------------------------------------------------------------ HTMX glue
  function showToast(msg, type) {
    if (window.Alpine && Alpine.store('toast')) Alpine.store('toast').show(msg, type);
  }
  // Server-sent toasts: HX-Trigger: {"toast": {"message": "...", "type": "success"}}
  document.addEventListener('toast', (e) => {
    const d = e.detail || {};
    if (d.message) showToast(d.message, d.type);
  });
  document.addEventListener('htmx:responseError', (e) => {
    const xhr = e.detail.xhr;
    let msg = 'Something went wrong. Please try again.';
    if (xhr.status === 429) msg = 'Too many requests — please slow down.';
    else if (xhr.status === 403) msg = 'Your session may have expired. Reload the page and try again.';
    else if (xhr.status === 404) msg = 'That item no longer exists.';
    showToast(msg, 'error');
  });
  document.addEventListener('htmx:sendError', () => showToast('You appear to be offline. Check your connection.', 'error'));

  // Keep shareable URLs clean: drop empty filters and defaults from the explore form's GET requests.
  const DEFAULTS = { view: 'grid', sort: 'deadline', min_if: '0' };
  document.addEventListener('htmx:configRequest', (e) => {
    if (!e.detail.elt || e.detail.elt.id !== 'filters') return;
    const fd = e.detail.formData;
    const params = e.detail.parameters;
    const keys = fd ? [...new Set([...fd.keys()])] : Object.keys(params);
    for (const k of keys) {
      const values = fd ? fd.getAll(k) : [].concat(params[k]);
      const meaningful = values.filter((v) => v !== '' && v !== DEFAULTS[k]);
      if (!meaningful.length) {
        if (fd) fd.delete(k);
        if (params && k in params) delete params[k];
      }
    }
  });
  // Screen-reader friendly busy state on swap targets.
  document.addEventListener('htmx:beforeRequest', (e) => { if (e.detail.target) e.detail.target.setAttribute('aria-busy', 'true'); });
  document.addEventListener('htmx:afterRequest', (e) => { if (e.detail.target) e.detail.target.setAttribute('aria-busy', 'false'); });
  document.addEventListener('htmx:timeout', () => showToast('The server took too long to respond.', 'error'));
})();
