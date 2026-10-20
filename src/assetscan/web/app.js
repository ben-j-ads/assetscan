(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var NS = "http://www.w3.org/2000/svg";

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function pct(x, d) { return (x * 100).toFixed(d || 0) + "%"; }

  /* theme */
  var themeBtn = $("theme");
  function setTheme(t) {
    document.documentElement.dataset.theme = t === "dark" ? "dark" : "";
    themeBtn.setAttribute("aria-pressed", t === "dark");
    try { localStorage.setItem("assetscan-theme", t); } catch (e) {}
  }
  setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  themeBtn.addEventListener("click", function () { setTheme(themeBtn.getAttribute("aria-pressed") === "true" ? "light" : "dark"); });

  /* rows */
  var rows = $("rows");
  var CHECKS = [["sound", "without sound"], ["name", "without the name"], ["context", "out of context"], ["consistent", "held constant"], ["instant", "read instantly"]];
  function addRow(v) {
    v = v || {};
    var d = document.createElement("div");
    d.className = "rowwrap";
    var sel = CHECKS.map(function (c) {
      return '<label>' + c[1] + '<select data-check="' + c[0] + '"><option value="">not checked</option><option value="yes">yes</option><option value="no">no</option></select></label>';
    }).join("");
    d.innerHTML =
      '<div class="row">' +
      '<input class="name" type="text" aria-label="asset name" placeholder="e.g. logo mark" value="' + esc(v.name || "") + '">' +
      '<input class="n" type="number" min="1" inputmode="numeric" aria-label="shown to" value="' + (v.n == null ? "" : v.n) + '">' +
      '<input class="brand" type="number" min="0" inputmode="numeric" aria-label="named you" value="' + (v.brand == null ? "" : v.brand) + '">' +
      '<input class="rivals" type="number" min="0" inputmode="numeric" aria-label="named a rival" value="' + (v.rivals == null ? "" : v.rivals) + '">' +
      '<button type="button" class="rm" aria-label="remove asset">×</button></div>' +
      '<details class="audit"><summary>audit this asset (optional)</summary><div class="fields">' + sel +
      '<label>touchpoints it appears in<input class="used" type="number" min="0" inputmode="numeric"></label>' +
      '<label>touchpoints audited<input class="total" type="number" min="0" inputmode="numeric"></label></div></details>';
    d.querySelector(".rm").addEventListener("click", function () { d.remove(); sync(); });
    if (v.checks) Object.keys(v.checks).forEach(function (k) { d.querySelector('[data-check="' + k + '"]').value = v.checks[k]; });
    if (v.used != null) { d.querySelector(".used").value = v.used; d.querySelector(".total").value = v.total; d.querySelector(".audit").open = true; }
    rows.appendChild(d);
    sync();
  }
  function sync() { var rm = rows.querySelectorAll(".rm"); rm.forEach(function (b) { b.disabled = rm.length <= 1; }); }
  $("add-row").addEventListener("click", function () { addRow(); });
  addRow(); addRow();

  $("example").addEventListener("click", function () {
    rows.innerHTML = "";
    [["Lime square logo mark", 400, 248, 38], ["Dark green bottle shape", 400, 140, 190], ["Redaction-bar device", 400, 64, 11],
     ["\"You didn't see this\" tagline", 400, 150, 24], ["Condensed lowercase type", 400, 58, 144]]
      .forEach(function (r) { addRow({ name: r[0], n: r[1], brand: r[2], rivals: r[3] }); });
    $("csv").value = "";
  });
  $("example2").addEventListener("click", function () {
    $("csv").value = "asset,segment,respondents,brand,Rival A,Rival B,check_sound,check_name,check_context,check_consistent,check_instant,touchpoints_used,touchpoints_total\n" +
      "Lime square logo mark,buyers,200,150,8,4,yes,yes,yes,yes,yes,9,10\nLime square logo mark,non-buyers,200,98,14,6,yes,yes,yes,yes,yes,9,10\n" +
      "Dark green bottle shape,buyers,200,90,50,20,,yes,no,no,yes,4,10\nDark green bottle shape,non-buyers,200,50,70,25,,yes,no,no,yes,4,10\n" +
      "Redaction-bar device,buyers,200,40,2,1,no,yes,yes,yes,no,10,10\nRedaction-bar device,non-buyers,200,24,4,2,no,yes,yes,yes,no,10,10";
    $("csv").closest("details").open = true;
  });

  /* submit */
  var errBox = $("form-error");
  function fail(msg) { errBox.textContent = msg; errBox.hidden = false; }
  $("scan-form").addEventListener("submit", function (e) {
    e.preventDefault();
    errBox.hidden = true;
    var body = { fame_cut: $("fame_cut").value, uniq_cut: $("uniq_cut").value, w_fame: $("w_fame").value };
    var csv = $("csv").value.trim();
    if (csv) body.csv = csv;
    else body.assets = Array.prototype.map.call(rows.querySelectorAll(".rowwrap"), function (r) {
      var checks = {};
      r.querySelectorAll("[data-check]").forEach(function (el) { if (el.value) checks[el.dataset.check] = el.value; });
      return { name: r.querySelector(".name").value, n: r.querySelector(".n").value, brand: r.querySelector(".brand").value, rivals: r.querySelector(".rivals").value,
               checks: checks, used: r.querySelector(".used").value, total: r.querySelector(".total").value };
    });
    fetch("/api/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) { if (!x.ok) return fail(x.j.error || "something went wrong"); render(x.j); })
      .catch(function () { fail("couldn't reach the local server. Is assetscan still running?"); });
  });

  /* ---- charts (inline SVG, no libraries) ---- */
  function svg(w, h, inner, label) {
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(label) + '">' + inner + "</svg>";
  }

  function gridChart(res) {
    var W = 640, H = 520, L = 56, R = 16, T = 16, B = 52, pw = W - L - R, ph = H - T - B;
    var X = function (u) { return L + u * pw; }, Y = function (f) { return T + (1 - f) * ph; };
    var s = res.settings, g = "";
    for (var i = 0; i <= 10; i++) {
      var t = i / 10;
      g += '<line class="gridline" x1="' + X(t) + '" y1="' + T + '" x2="' + X(t) + '" y2="' + (T + ph) + '"/>';
      g += '<line class="gridline" x1="' + L + '" y1="' + Y(t) + '" x2="' + (L + pw) + '" y2="' + Y(t) + '"/>';
      if (i % 2 === 0) {
        g += '<text x="' + X(t) + '" y="' + (H - B + 20) + '" text-anchor="middle">' + (t * 100) + '%</text>';
        g += '<text x="' + (L - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + (t * 100) + '%</text>';
      }
    }
    g += '<line class="cut" x1="' + X(s.uniq_cut) + '" y1="' + T + '" x2="' + X(s.uniq_cut) + '" y2="' + (T + ph) + '"/>';
    g += '<line class="cut" x1="' + L + '" y1="' + Y(s.fame_cut) + '" x2="' + (L + pw) + '" y2="' + Y(s.fame_cut) + '"/>';
    g += '<text class="qlabel" x="' + (L + pw - 6) + '" y="' + (T + 16) + '" text-anchor="end">use or lose</text>';
    g += '<text class="qlabel" x="' + (L + 6) + '" y="' + (T + 16) + '">avoid solo use</text>';
    g += '<text class="qlabel" x="' + (L + pw - 6) + '" y="' + (T + ph - 8) + '" text-anchor="end">invest</text>';
    g += '<text class="qlabel" x="' + (L + 6) + '" y="' + (T + ph - 8) + '">test or ignore</text>';
    g += '<text x="' + (L + pw / 2) + '" y="' + (H - 8) + '" text-anchor="middle">uniqueness: of those who named a brand, share who named you</text>';
    g += '<text transform="translate(14 ' + (T + ph / 2) + ') rotate(-90)" text-anchor="middle">fame: share who named you</text>';
    res.assets.forEach(function (a) {
      var x = X(a.uniqueness), y = Y(a.fame);
      g += '<line class="ci" x1="' + X(a.uniqueness_ci[0]) + '" y1="' + y + '" x2="' + X(a.uniqueness_ci[1]) + '" y2="' + y + '"/>';
      g += '<line class="ci" x1="' + x + '" y1="' + Y(a.fame_ci[0]) + '" x2="' + x + '" y2="' + Y(a.fame_ci[1]) + '"/>';
    });
    res.assets.forEach(function (a) {
      var x = X(a.uniqueness), y = Y(a.fame), right = a.uniqueness < 0.72;
      g += '<rect class="pt" x="' + (x - 6) + '" y="' + (y - 6) + '" width="12" height="12"/>';
      g += '<text class="name" x="' + (right ? x + 12 : x - 12) + '" y="' + (right ? y - 9 : y + 22) + '" text-anchor="' + (right ? "start" : "end") + '">' + esc(a.name.length > 26 ? a.name.slice(0, 25) + "…" : a.name) + "</text>";
    });
    return svg(W, H, g, "Fame against uniqueness for each asset, with 95% intervals");
  }

  var SEG = ["var(--lime)", "var(--ink)", "var(--ink-muted)", "var(--rule)"];
  function attributionChart(res) {
    var W = 640, rowH = 44, L = 168, R = 16, T = 8, pw = W - L - R, H = T + res.assets.length * rowH + 28, g = "";
    res.assets.forEach(function (a, i) {
      var y = T + i * rowH, x = L, names = Object.keys(a.shares), tot = a.brand + a.rivals + a.unknown;
      g += '<text class="name" x="' + (L - 10) + '" y="' + (y + 21) + '" text-anchor="end">' + esc(a.name.length > 22 ? a.name.slice(0, 21) + "…" : a.name) + "</text>";
      var parts = [];
      names.forEach(function (nm, j) {
        var cnt = nm === "You" ? a.brand : Math.round(a.shares[nm] * (a.brand + a.rivals));
        parts.push({ nm: nm, cnt: cnt, fill: j === 0 ? SEG[0] : j === 1 ? SEG[1] : SEG[2] });
      });
      parts.push({ nm: "No brand", cnt: a.unknown, fill: "var(--paper-raised)" });
      parts.forEach(function (p) {
        var w = p.cnt / tot * pw;
        if (w <= 0) return;
        g += '<rect x="' + x + '" y="' + (y + 6) + '" width="' + w + '" height="26" fill="' + p.fill + '" stroke="var(--ink)" stroke-width="1.5"><title>' + esc(p.nm) + ": " + p.cnt + " of " + tot + "</title></rect>";
        if (w > 34) g += '<text x="' + (x + w / 2) + '" y="' + (y + 24) + '" text-anchor="middle" style="fill:' + (p.fill === "var(--ink)" || p.fill === "var(--ink-muted)" ? "var(--paper)" : "var(--on-lime)") + ';font-size:12px;font-weight:700">' + Math.round(p.cnt / tot * 100) + "%</text>";
        x += w;
      });
    });
    return svg(W, H, g, "Who gets the credit for each asset");
  }

  function scoreChart(res) {
    var W = 640, rowH = 40, L = 168, R = 24, T = 8, pw = W - L - R, H = T + res.assets.length * rowH + 34, g = "";
    var X = function (s) { return L + s / 100 * pw; };
    [20, 45, 70].forEach(function (b) {
      g += '<line class="cut" x1="' + X(b) + '" y1="' + T + '" x2="' + X(b) + '" y2="' + (H - 30) + '"/><text x="' + X(b) + '" y="' + (H - 12) + '" text-anchor="middle">' + b + "</text>";
    });
    g += '<text x="' + X(0) + '" y="' + (H - 12) + '" text-anchor="middle">0</text><text x="' + X(100) + '" y="' + (H - 12) + '" text-anchor="middle">100</text>';
    res.assets.forEach(function (a, i) {
      var y = T + i * rowH;
      g += '<text class="name" x="' + (L - 10) + '" y="' + (y + 22) + '" text-anchor="end">' + esc(a.name.length > 22 ? a.name.slice(0, 21) + "…" : a.name) + "</text>";
      g += '<rect x="' + X(0) + '" y="' + (y + 8) + '" width="' + Math.max(1, X(a.score) - X(0)) + '" height="20" fill="var(--lime)" stroke="var(--ink)" stroke-width="1.5"/>';
      var cy = y + 18;
      g += '<line class="ci" x1="' + X(a.score_ci[0]) + '" y1="' + cy + '" x2="' + X(a.score_ci[1]) + '" y2="' + cy + '"/>';
      g += '<line class="ci" x1="' + X(a.score_ci[0]) + '" y1="' + (cy - 6) + '" x2="' + X(a.score_ci[0]) + '" y2="' + (cy + 6) + '"/>';
      g += '<line class="ci" x1="' + X(a.score_ci[1]) + '" y1="' + (cy - 6) + '" x2="' + X(a.score_ci[1]) + '" y2="' + (cy + 6) + '"/>';
      g += '<text class="name" x="' + (Math.max(X(a.score), X(a.score_ci[1])) + 8) + '" y="' + (cy + 5) + '">' + a.score.toFixed(0) + "</text>";
    });
    return svg(W, H, g, "Distinctiveness score for each asset with a 95% range");
  }

  function segmentChart(res) {
    var segs = res.summary.segments, W = 640, L = 168, R = 16, T = 8, pw = W - L - R, bh = 14, gap = 4, grp = segs.length * (bh + gap) + 14, H = T + res.assets.length * grp + 12, g = "";
    var X = function (f) { return L + f * pw; }, fills = ["var(--lime)", "var(--ink)", "var(--ink-muted)", "var(--rule)"];
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) { g += '<line class="gridline" x1="' + X(t) + '" y1="' + T + '" x2="' + X(t) + '" y2="' + (H - 12) + '"/>'; });
    res.assets.forEach(function (a, i) {
      var y0 = T + i * grp;
      g += '<text class="name" x="' + (L - 10) + '" y="' + (y0 + 12) + '" text-anchor="end">' + esc(a.name.length > 22 ? a.name.slice(0, 21) + "…" : a.name) + "</text>";
      segs.forEach(function (sg, j) {
        var d = a.segments.filter(function (x) { return x.segment.toLowerCase() === sg.toLowerCase(); })[0];
        if (!d) return;
        var y = y0 + j * (bh + gap);
        g += '<rect x="' + X(0) + '" y="' + y + '" width="' + Math.max(1, d.fame * pw) + '" height="' + bh + '" fill="' + fills[j % 4] + '" stroke="var(--ink)" stroke-width="1.5"><title>' + esc(sg) + ": " + pct(d.fame) + '</title></rect>';
        g += '<text x="' + (X(d.fame) + 6) + '" y="' + (y + 11) + '">' + pct(d.fame) + " " + esc(sg) + "</text>";
      });
    });
    return svg(W, H, g, "Fame by segment for each asset");
  }

  function deployChart(res) {
    var items = res.assets.filter(function (a) { return a.checklist && a.checklist.score != null; });
    var W = 640, H = 460, L = 56, R = 24, T = 16, B = 52, pw = W - L - R, ph = H - T - B, g = "";
    var X = function (v) { return L + v / 100 * pw; }, Y = function (v) { return T + (1 - v / 100) * ph; };
    for (var i = 0; i <= 100; i += 20) {
      g += '<line class="gridline" x1="' + X(i) + '" y1="' + T + '" x2="' + X(i) + '" y2="' + (T + ph) + '"/><line class="gridline" x1="' + L + '" y1="' + Y(i) + '" x2="' + (L + pw) + '" y2="' + Y(i) + '"/>';
      g += '<text x="' + X(i) + '" y="' + (H - B + 20) + '" text-anchor="middle">' + i + '</text><text x="' + (L - 8) + '" y="' + (Y(i) + 4) + '" text-anchor="end">' + i + "</text>";
    }
    g += '<line class="cut" x1="' + X(50) + '" y1="' + T + '" x2="' + X(50) + '" y2="' + (T + ph) + '"/><line class="cut" x1="' + L + '" y1="' + Y(45) + '" x2="' + (L + pw) + '" y2="' + Y(45) + '"/>';
    g += '<text class="qlabel" x="' + (L + pw - 6) + '" y="' + (T + 16) + '" text-anchor="end">known and deployed</text><text class="qlabel" x="' + (L + 6) + '" y="' + (T + 16) + '">known, drifting</text>';
    g += '<text class="qlabel" x="' + (L + pw - 6) + '" y="' + (T + ph - 8) + '" text-anchor="end">deployed, not known yet</text><text class="qlabel" x="' + (L + 6) + '" y="' + (T + ph - 8) + '">neither</text>';
    g += '<text x="' + (L + pw / 2) + '" y="' + (H - 8) + '" text-anchor="middle">execution score from the audit</text><text transform="translate(14 ' + (T + ph / 2) + ') rotate(-90)" text-anchor="middle">distinctiveness score</text>';
    items.forEach(function (a, i) {
      var x = X(a.checklist.score), y = Y(a.score), right = a.checklist.score < 70;
      g += '<rect class="pt" x="' + (x - 6) + '" y="' + (y - 6) + '" width="12" height="12"/><text class="name" x="' + (right ? x + 12 : x - 12) + '" y="' + (i % 2 ? y + 22 : y - 9) + '" text-anchor="' + (right ? "start" : "end") + '">' + esc(a.name.length > 26 ? a.name.slice(0, 25) + "…" : a.name) + "</text>";
    });
    return svg(W, H, g, "Distinctiveness score against execution score");
  }

  function legend(items) {
    return '<div class="legend">' + items.map(function (i) { return '<span><i style="background:' + i[0] + '"></i>' + i[1] + "</span>"; }).join("") + "</div>";
  }

  function auditHtml(a) {
    var c = a.checklist;
    if (!c) return "";
    var mark = { true: "pass", false: "fail", null: "not checked" };
    return '<p class="caption">Audit' + (c.score != null ? ": execution " + c.score.toFixed(0) + "/100" : "") + (c.coverage != null ? ", in " + c.used + " of " + c.total + " touchpoints" : "") + ". " +
      c.items.map(function (i) { return esc(i.label) + " (" + mark[i.result] + ")"; }).join("; ") + ".</p>";
  }
  function segHtml(a) {
    if (!a.segments.length) return "";
    return '<p class="caption">' + a.segments.map(function (x) { return esc(x.segment) + ": fame " + pct(x.fame) + ", uniqueness " + pct(x.uniqueness) + ", score " + x.score.toFixed(0); }).join(" / ") + ".</p>";
  }

  /* ---- result ---- */
  function render(res) {
    var a0 = res.assets[0], s = res.summary, out = $("result");
    var cards = res.assets.map(function (a) {
      var probs = a.quadrant_probs, p = probs[a.quadrant];
      return '<div class="asset-card"><div class="head"><strong>' + esc(a.name) + '</strong><span class="sc">' + a.score.toFixed(0) + '<span class="caption"> / 100, ' + a.score_ci[0].toFixed(0) + " to " + a.score_ci[1].toFixed(0) + '</span></span></div>' +
        '<p><span class="chip ' + (a.quadrant === "use" ? "use" : a.quadrant === "test" ? "test" : "") + '">' + esc(a.quadrant_label) + "</span> " + esc(a.band) + ", " + Math.round(p * 100) + "% sure of this box. Fame " + pct(a.fame) + " (" + pct(a.fame_ci[0]) + " to " + pct(a.fame_ci[1]) + "), uniqueness " + pct(a.uniqueness) + " (" + pct(a.uniqueness_ci[0]) + " to " + pct(a.uniqueness_ci[1]) + "). Sample: " + a.confidence + ".</p>" +
        "<p>" + esc(a.action) + "</p>" + auditHtml(a) + segHtml(a) +
        (a.notes.length ? "<ul>" + a.notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul>" : "") + "</div>";
    }).join("");
    out.innerHTML =
      '<p class="label kicker">best asset: ' + esc(a0.name) + "</p>" +
      '<div class="score-line"><h2 class="verdict"><mark class="hl">' + a0.score.toFixed(0) + '</mark></h2><span class="range">out of 100. 95% range ' + a0.score_ci[0].toFixed(0) + " to " + a0.score_ci[1].toFixed(0) + "</span></div>" +
      '<p class="lead">' + esc(a0.band) + ". " + esc(a0.action) + "</p>" +
      '<div class="summary-cards">' +
      '<div class="card"><p class="label">assets scored</p><p class="n">' + s.assets + "</p></div>" +
      '<div class="card"><p class="label">ownable (70+)</p><p class="n">' + s.ownable + "</p></div>" +
      '<div class="card"><p class="label">average score</p><p class="n">' + s.portfolio_score.toFixed(0) + "</p></div></div>" +
      '<section class="section"><h3>the grid</h3><div class="fig">' + gridChart(res) + '<p class="caption cap">Crosses are 95% intervals. Dashed lines are your thresholds. Further up and right is better.</p></div></section>' +
      '<section class="section"><h3>who gets the credit</h3><div class="fig">' + attributionChart(res) +
      legend([["var(--lime)", "you"], ["var(--ink)", "biggest rival"], ["var(--ink-muted)", "other rivals"], ["var(--paper-raised)", "named no brand"]]) + "</div></section>" +
      '<section class="section"><h3>distinctiveness score</h3><div class="fig">' + scoreChart(res) + '<p class="caption cap">Dashed lines mark the bands: weak 20, building 45, ownable 70. The whisker is the 95% range.</p></div></section>' +
      (s.segments.length ? '<section class="section"><h3>fame by segment</h3><div class="fig">' + segmentChart(res) + '<p class="caption cap">A wide gap between segments means the asset is known to your buyers but not beyond them, or the reverse.</p></div></section>' : "") +
      (res.assets.some(function (a) { return a.checklist && a.checklist.score != null; }) ? '<section class="section"><h3>known against deployed</h3><div class="fig">' + deployChart(res) + '<p class="caption cap">Execution is the share of audit checks passed, averaged with touchpoint coverage. It is shown beside the score, never blended into it.</p></div></section>' : "") +
      '<section class="section"><h3>asset by asset</h3>' + cards + "</section>" +
      '<div class="copy-row"><button type="button" class="link" id="print">print or save as pdf</button></div>';
    out.hidden = false;
    out.scrollIntoView({ behavior: "smooth", block: "start" });
    $("print").addEventListener("click", function () { window.print(); });
  }
})();
