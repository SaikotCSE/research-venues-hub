/* VenuePulse client logic: live clock, countdowns, compare drawer, theme, filter helpers. */
(function () {
  const safe = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } },
  };
  const pad = (n) => String(n).padStart(2, '0');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  // "Anywhere on Earth" = UTC-12: shift the instant and read it back with UTC getters.
  function fmtAoE(ms) {
    const d = new Date(ms - 12 * 3600 * 1000);
    return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} AoE`;
  }
  function fmtLocal(ms) {
    return new Date(ms).toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
    });
  }
  window.VenuePulse = { fmtAoE, fmtLocal };

  document.addEventListener('alpine:init', () => {
    Alpine.store('clock', { now: Date.now() });
    setInterval(() => { Alpine.store('clock').now = Date.now(); }, 1000);

    Alpine.data('countdown', (iso) => {
      const target = new Date(iso).getTime();
      return {
        target,
        local: fmtLocal(target),
        aoe: fmtAoE(target),
        get diff() { return Math.max(0, this.target - Alpine.store('clock').now); },
        get done() { return this.target <= Alpine.store('clock').now; },
        get d() { return Math.floor(this.diff / 86400000); },
        get h() { return pad(Math.floor(this.diff / 3600000) % 24); },
        get m() { return pad(Math.floor(this.diff / 60000) % 60); },
        get s() { return pad(Math.floor(this.diff / 1000) % 60); },
        get urgent() { return !this.done && this.diff < 7 * 86400000; },
      };
    });

    Alpine.store('theme', {
      dark: document.documentElement.classList.contains('dark'),
      toggle() {
        this.dark = !this.dark;
        document.documentElement.classList.toggle('dark', this.dark);
        safe.set('vp-theme', this.dark ? 'dark' : 'light');
      },
    });

    Alpine.store('compare', {
      items: [], open: false, max: 4,
      init() {
        try { this.items = JSON.parse(safe.get('vp-compare') || '[]'); } catch (e) { this.items = []; }
      },
      has(slug) { return this.items.some((i) => i.slug === slug); },
      toggle(slug, acronym) {
        if (this.has(slug)) this.items = this.items.filter((i) => i.slug !== slug);
        else if (this.items.length < this.max) this.items.push({ slug, acronym });
        else { Alpine.store('toast').show(`You can compare up to ${this.max} venues`); return; }
        safe.set('vp-compare', JSON.stringify(this.items));
        if (this.open) this.load();
      },
      clear() { this.items = []; safe.set('vp-compare', '[]'); if (this.open) this.load(); },
      show() { this.open = true; this.load(); },
      load() {
        const q = this.items.map((i) => 's=' + encodeURIComponent(i.slug)).join('&');
        htmx.ajax('GET', '/compare/?' + q, { target: '#compare-body', swap: 'innerHTML' });
      },
    });

    Alpine.store('toast', {
      msg: '', visible: false, timer: null,
      show(msg) { this.msg = msg; this.visible = true; clearTimeout(this.timer); this.timer = setTimeout(() => { this.visible = false; }, 2200); },
    });

    // Filter sidebar helper: table header sorting + live IF slider label.
    Alpine.data('listPage', (minIf) => ({
      minIf, filtersOpen: false,
      setSort(key, defaultDir) {
        const f = document.getElementById('filters');
        const dir = f.elements['dir'];
        if (f.elements['sort'].value === key) dir.value = dir.value === 'asc' ? 'desc' : 'asc';
        else { f.elements['sort'].value = key; dir.value = defaultDir; }
        htmx.trigger(f, 'change');
      },
      reset() {
        const f = document.getElementById('filters');
        f.reset();
        f.querySelectorAll('input[type=checkbox]').forEach((c) => { c.checked = false; });
        f.querySelectorAll('select').forEach((s) => { s.selectedIndex = 0; });
        f.elements['q'].value = '';
        f.elements['min_if'].value = 0; this.minIf = 0;
        htmx.trigger(f, 'change');
      },
    }));

    Alpine.data('copier', () => ({
      copied: false,
      async copy(text) {
        try { await navigator.clipboard.writeText(text); }
        catch (e) {
          const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta);
          ta.select(); document.execCommand('copy'); ta.remove();
        }
        this.copied = true; setTimeout(() => { this.copied = false; }, 1800);
      },
    }));
  });

  function icons() { if (window.lucide) window.lucide.createIcons(); }
  document.addEventListener('DOMContentLoaded', icons);
  document.body && document.body.addEventListener('htmx:afterSettle', icons);
  document.addEventListener('htmx:afterSettle', icons);
})();
