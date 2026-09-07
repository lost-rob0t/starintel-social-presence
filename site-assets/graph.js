/* StarIntel org-roam graph workspace.
   Vanilla canvas force-directed graph; no external dependencies. */
(function () {
  "use strict";

  var canvas = document.getElementById("graph-canvas");
  if (!canvas) return;
  var wrap = canvas.parentElement;
  var tooltip = document.getElementById("graph-tooltip");
  var statsEl = document.getElementById("graph-stats");

  var SECTIONS = {
    blog: { color: "#f5cf58" },
    docs: { color: "#8fb573" },
    portfolio: { color: "#9fc6e8" },
  };

  var nodes = [];
  var edges = [];
  var visible = new Set();
  var hovered = null;
  var dragged = null;
  var alpha = 1;

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = wrap.clientWidth;
    var h = wrap.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function radius(n) {
    var base = n.section === "docs" ? 6 : 7;
    return base + Math.min(7, n.degree * 1.1);
  }

  function computeDegrees() {
    var deg = {};
    edges.forEach(function (e) {
      deg[e.source] = (deg[e.source] || 0) + 1;
      deg[e.target] = (deg[e.target] || 0) + 1;
    });
    nodes.forEach(function (n) { n.degree = deg[n.id] || 0; });
  }

  function applyFilters() {
    var checks = document.querySelectorAll(".graph-sections input[data-section]");
    var enabled = {};
    checks.forEach(function (c) { enabled[c.dataset.section] = c.checked; });
    visible = new Set(
      nodes.filter(function (n) { return enabled[n.section]; }).map(function (n) { return n.id; })
    );
    var visNodes = nodes.filter(function (n) { return visible.has(n.id); });
    if (statsEl) {
      statsEl.textContent = visNodes.length + " nodes · " +
        edges.filter(function (e) { return visible.has(e.source) && visible.has(e.target); }).length + " edges";
    }
  }

  function tick() {
    var w = wrap.clientWidth;
    var h = wrap.clientHeight;
    var cx = w / 2;
    var cy = h / 2;
    var repulse = 2600;
    var spring = 0.02;
    var springLen = 130;

    for (var iter = 0; iter < 3; iter++) {
      // repulsion (O(n^2) is fine for editorial-scale graphs)
      for (var i = 0; i < nodes.length; i++) {
        var a = nodes[i];
        for (var j = i + 1; j < nodes.length; j++) {
          var b = nodes[j];
          var dx = b.x - a.x, dy = b.y - a.y;
          var d2 = dx * dx + dy * dy || 0.01;
          var d = Math.sqrt(d2);
          var f = (repulse / d2) * alpha;
          var fx = (dx / d) * f, fy = (dy / d) * f;
          a.fx -= fx; a.fy -= fy;
          b.fx += fx; b.fy += fy;
        }
      }
      // springs
      edges.forEach(function (e) {
        var s = byId[e.source], t = byId[e.target];
        if (!s || !t) return;
        var dx = t.x - s.x, dy = t.y - s.y;
        var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        var f = (d - springLen) * spring * alpha;
        var fx = (dx / d) * f, fy = (dy / d) * f;
        s.fx += fx; s.fy += fy;
        t.fx -= fx; t.fy -= fy;
      });
      // integrate with weak center gravity
      nodes.forEach(function (n) {
        if (n === dragged) { n.fx = n.fy = 0; return; }
        n.fx += (cx - n.x) * 0.012 * alpha;
        n.fy += (cy - n.y) * 0.012 * alpha;
        n.vx = (n.vx + n.fx) * 0.82;
        n.vy = (n.vy + n.fy) * 0.82;
        n.fx = n.fy = 0;
        n.x += n.vx;
        n.y += n.vy;
        var pad = radius(n) + 6;
        if (n.x < pad) { n.x = pad; n.vx *= -0.4; }
        if (n.y < pad) { n.y = pad; n.vy *= -0.4; }
        if (n.x > w - pad) { n.x = w - pad; n.vx *= -0.4; }
        if (n.y > h - pad) { n.y = h - pad; n.vy *= -0.4; }
      });
    }
    alpha = Math.max(0.02, alpha * 0.995);
  }

  var byId = {};

  function draw() {
    var ctx = canvas.getContext("2d");
    var w = wrap.clientWidth;
    var h = wrap.clientHeight;
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 1;
    edges.forEach(function (e) {
      var s = byId[e.source], t = byId[e.target];
      if (!s || !t || !visible.has(s.id) || !visible.has(t.id)) return;
      var active = hovered && (hovered.id === s.id || hovered.id === t.id);
      ctx.strokeStyle = active ? "rgba(245, 207, 88, 0.9)" : "rgba(61, 51, 25, 0.7)";
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });
    nodes.forEach(function (n) {
      if (!visible.has(n.id)) return;
      var r = radius(n);
      var color = (SECTIONS[n.section] || { color: "#888" }).color;
      var isHover = hovered && hovered.id === n.id;
      ctx.beginPath();
      ctx.arc(n.x, n.y, isHover ? r + 3 : r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = hovered && !isHover &&
        !edges.some(function (e) {
          return (e.source === hovered.id && e.target === n.id) ||
                 (e.target === hovered.id && e.source === n.id);
        }) ? 0.35 : 1;
      ctx.fill();
      ctx.globalAlpha = 1;
      if (isHover || n.degree >= 4) {
        ctx.fillStyle = "#ececec";
        ctx.font = (isHover ? "600 " : "") + "11px ui-sans-serif, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(n.title, n.x, n.y - r - 6);
      }
    });
  }

  function loop() {
    tick();
    draw();
    requestAnimationFrame(loop);
  }

  function nodeAt(x, y) {
    for (var i = nodes.length - 1; i >= 0; i--) {
      var n = nodes[i];
      if (!visible.has(n.id)) continue;
      var dx = x - n.x, dy = y - n.y;
      if (dx * dx + dy * dy <= (radius(n) + 5) * (radius(n) + 5)) return n;
    }
    return null;
  }

  function pos(evt) {
    var rect = canvas.getBoundingClientRect();
    return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
  }

  canvas.addEventListener("mousemove", function (evt) {
    var p = pos(evt);
    if (dragged) {
      dragged.x = p.x;
      dragged.y = p.y;
      alpha = Math.max(alpha, 0.3);
      return;
    }
    var n = nodeAt(p.x, p.y);
    hovered = n;
    canvas.style.cursor = n ? "pointer" : "default";
    if (n && tooltip) {
      tooltip.textContent = n.title + " (" + n.section + ")";
      tooltip.style.opacity = 1;
      tooltip.style.left = Math.min(p.x + 14, wrap.clientWidth - 200) + "px";
      tooltip.style.top = (p.y - 30) + "px";
    } else if (tooltip) {
      tooltip.style.opacity = 0;
    }
  });

  canvas.addEventListener("mousedown", function (evt) {
    var p = pos(evt);
    dragged = nodeAt(p.x, p.y);
  });

  window.addEventListener("mouseup", function () { dragged = null; });

  canvas.addEventListener("click", function (evt) {
    var p = pos(evt);
    var n = nodeAt(p.x, p.y);
    if (n && n.href) window.location.href = n.href;
  });

  function reheat() { alpha = 1; }
  var reheatBtn = document.getElementById("graph-reheat");
  if (reheatBtn) reheatBtn.addEventListener("click", reheat);
  document.querySelectorAll(".graph-sections input[data-section]").forEach(function (c) {
    c.addEventListener("change", applyFilters);
  });

  window.addEventListener("resize", function () {
    resize();
    nodes.forEach(function (n) {
      n.x = Math.min(n.x, wrap.clientWidth - 10);
      n.y = Math.min(n.y, wrap.clientHeight - 10);
    });
  });

  fetch(canvas.dataset.src)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      nodes = data.nodes.map(function (n, i) {
        var angle = (i / data.nodes.length) * Math.PI * 2;
        return Object.assign({}, n, {
          x: wrap.clientWidth / 2 + Math.cos(angle) * wrap.clientWidth * 0.25,
          y: wrap.clientHeight / 2 + Math.sin(angle) * wrap.clientHeight * 0.25,
          vx: 0, vy: 0, fx: 0, fy: 0,
        });
      });
      edges = data.edges;
      nodes.forEach(function (n) { byId[n.id] = n; });
      computeDegrees();
      applyFilters();
      resize();
      loop();
    });
})();
