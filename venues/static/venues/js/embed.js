// Live countdown for the embeddable deadline widget (/embed/venue/<slug>/). No dependencies.
(function () {
  "use strict";
  var pad = function (n) { return String(n).padStart(2, "0"); };
  var el = document.querySelector("[data-countdown]");
  var aoe = document.querySelector("[data-aoe]");
  if (aoe) {
    var at = new Date(aoe.getAttribute("data-aoe"));
    var shifted = new Date(at.getTime() - 12 * 3600 * 1000);
    aoe.textContent = shifted.toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric", year: "numeric" }) +
      " " + pad(shifted.getUTCHours()) + ":" + pad(shifted.getUTCMinutes()) + " AoE";
  }
  if (!el) return;
  var target = new Date(el.getAttribute("data-countdown")).getTime();
  function tick() {
    var ms = target - Date.now();
    if (ms <= 0) { el.textContent = "Closed"; return; }
    var s = Math.floor(ms / 1000);
    var d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    el.textContent = d + "d " + pad(h) + "h " + pad(m) + "m " + pad(s % 60) + "s";
    el.classList.toggle("urgent", ms < 7 * 86400 * 1000);
    setTimeout(tick, 1000);
  }
  tick();
})();
