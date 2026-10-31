/* Insights page charts (Chart.js). Data comes from the json_script block. */
(function () {
  if (!window.Chart) return;
  const d = JSON.parse(document.getElementById('insights-data').textContent);
  const dark = document.documentElement.classList.contains('dark');
  Chart.defaults.color = dark ? '#cbd5e1' : '#475569';
  Chart.defaults.borderColor = dark ? '#334155' : '#e2e8f0';
  Chart.defaults.maintainAspectRatio = false;
  const P = ['#6366f1', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9', '#84cc16', '#ec4899', '#64748b'];
  const mk = (id, cfg) => new Chart(document.getElementById(id), cfg);
  mk('c-months', { type: 'bar', data: { labels: d.deadlines_by_month.labels, datasets: [{ data: d.deadlines_by_month.values, backgroundColor: P[0] }] }, options: { plugins: { legend: { display: false } } } });
  mk('c-domain', { type: 'bar', data: { labels: d.by_domain.map(x => x[0]), datasets: [{ data: d.by_domain.map(x => x[1]), backgroundColor: P[1] }] }, options: { indexAxis: 'y', plugins: { legend: { display: false } } } });
  mk('c-rank', { type: 'bar', data: { labels: d.core_distribution.map(x => 'CORE ' + x[0]).concat(d.quartile_distribution.map(x => x[0])), datasets: [{ data: d.core_distribution.map(x => x[1]).concat(d.quartile_distribution.map(x => x[1])), backgroundColor: d.core_distribution.map(() => P[0]).concat(d.quartile_distribution.map(() => P[2])) }] }, options: { plugins: { legend: { display: false } } } });
  mk('c-scatter', { type: 'scatter', data: { datasets: [{ data: d.scatter, backgroundColor: P[4] }] }, options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => `${c.raw.label}: ${c.raw.x}% accepted, h5 ${c.raw.y}` } } }, scales: { x: { title: { display: true, text: 'Acceptance rate (%)' } }, y: { title: { display: true, text: 'h5-index' } } } } });
  mk('c-if', { type: 'bar', data: { labels: d.top_impact.map(x => x[0]), datasets: [{ data: d.top_impact.map(x => x[1]), backgroundColor: P[2] }] }, options: { indexAxis: 'y', plugins: { legend: { display: false } } } });
  mk('c-cont', { type: 'doughnut', data: { labels: d.by_continent.map(x => x[0]), datasets: [{ data: d.by_continent.map(x => x[1]), backgroundColor: P }] } });
})();
