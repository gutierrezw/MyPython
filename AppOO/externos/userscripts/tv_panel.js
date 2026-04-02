// ==UserScript==
// @name         TradingView — App Panel
// @namespace    http://tampermonkey.net/
// @version      1.5
// @match        https://www.tradingview.com/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

(function () {
    "use strict";

    const PORT = 5050;
    let panelEl = null, bodyEl = null, titleEl = null;
    let minimized = false;
    let isDragging = false, startX = 0, startY = 0, origLeft = 0, origTop = 0;
    let lastPosicion = null;

    // ── TV native drawings ─────────────────────────────────────────────────
    let _tvShapes = { zona: null, avgline: null };
    let _lastDrawKey = "";   // evitar redibujar si los valores no cambiaron

    function tvChart() {
        try { return window.TradingViewApi && TradingViewApi.activeChart(); }
        catch (_) { return null; }
    }

    function clearTvShapes() {
        const ac = tvChart();
        if (!ac) return;
        ["zona", "avgline"].forEach(k => {
            if (_tvShapes[k]) {
                try { ac.removeEntity(_tvShapes[k]); } catch (_) {}
                _tvShapes[k] = null;
            }
        });
    }

    function drawTvShapes(posicion, lotes) {
        const ac = tvChart();
        if (!ac) return;

        const avgcost = posicion.avgcost || 0;
        const prices = lotes.map(l => l.precio || 0).filter(p => p > 0);
        if (!prices.length && !avgcost) return;

        const minP = prices.length ? Math.min(...prices) : avgcost;
        const maxP = prices.length ? Math.max(...prices) : avgcost;

        // Fecha del lote más antiguo → epoch segundos
        const fechas = lotes
            .map(l => l.fechahora || l.fecha || "")
            .filter(f => f)
            .map(f => Math.floor(new Date(f.replace(" ", "T")).getTime() / 1000))
            .filter(t => t > 0);
        const t1 = fechas.length ? Math.min(...fechas) : null;
        const t2 = Math.floor(Date.now() / 1000);

        // Evitar redibujar si los valores no cambiaron
        const drawKey = `${avgcost}|${minP}|${maxP}|${t1}`;
        if (drawKey === _lastDrawKey) return;
        _lastDrawKey = drawKey;

        clearTvShapes();

        // Zona de compra: rectángulo desde primera compra hasta hoy
        if (t1 && maxP > minP) {
            try {
                _tvShapes.zona = ac.createMultipointShape(
                    [{ time: t1, price: maxP }, { time: t2, price: minP }],
                    {
                        shape: "rectangle",
                        lock: false,
                        overrides: {
                            backgroundColor: "rgba(200,170,0,0.12)",
                            borderColor: "rgba(255,210,0,0.35)",
                            linewidth: 1,
                        },
                    }
                );
            } catch (_) {}
        }

        // Línea avgcost punteada amarilla
        if (avgcost) {
            try {
                _tvShapes.avgline = ac.createShape(
                    { price: avgcost },
                    {
                        shape: "horizontal_line",
                        lock: false,
                        overrides: {
                            linecolor: "#FFD700",
                            linewidth: 2,
                            linestyle: 1,
                            showLabel: true,
                            text: `base $${avgcost.toFixed(2)}`,
                        },
                    }
                );
            } catch (_) {}
        }
    }

    // ── Heartbeat ──────────────────────────────────────────────────────────
    function ping() {
        GM_xmlhttpRequest({ method: "GET", url: `http://localhost:${PORT}/ping`, onerror: () => { } });
    }

    // ── Leer símbolo actual de TV desde la URL ─────────────────────────────
    function tvSymbol() {
        const m = window.location.href.match(/[?&]symbol=([^&]+)/);
        return m ? decodeURIComponent(m[1]).split(":").pop() : "";
    }

    // ── Auto-scale todos los paneles (botón A de cada pane) ───────────────
    function autoScalePanes() {
        setTimeout(() => {
            document.querySelectorAll("button[data-name='scale-mode-button']").forEach(btn => btn.click());
        }, 2000);
    }

    // ── Navegar a nuevo símbolo sin abrir pestaña nueva ────────────────────
    function navegarSi(symbol) {
        if (!symbol || symbol === tvSymbol()) return;
        const prefix = (symbol.includes("USDT") || symbol.includes("BTC")) ? "BINANCE:" : "";
        window.location.href = `https://www.tradingview.com/chart/?symbol=${prefix}${symbol}`;
    }

    // Auto-scale al cargar la página
    window.addEventListener("load", () => autoScalePanes());

    // ── Helpers de formato ─────────────────────────────────────────────────
    const fmt = (v, d = 2) => (v != null && v !== 0) ? v.toLocaleString("es", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—";
    const fmtp = (v) => (v != null && v !== 0) ? (v * 100).toFixed(1) + "%" : "—";
    const fmts = (v) => v == null ? "—" : (v >= 0 ? `+${fmt(v)}` : fmt(v));
    const fmtsp = (v) => v == null ? "—" : (v >= 0 ? `+${fmtp(v)}` : fmtp(v));

    // ── Construir HTML del panel ───────────────────────────────────────────
    function buildPanel(data) {
        const pos = data.posicion || {};
        const lotes = data.lotes || [];

        const avgcost = pos.avgcost || 0;
        const last = pos.last || 0;
        const costo = pos.costo_base || 0;
        const position = pos.position || 0;
        const objetivo = pos.objetivo || 0;
        const sl = pos.stop_loss || 0;

        const gyp_total = (last && position && costo) ? last * position - costo : 0;
        const roi_total = costo ? gyp_total / costo : 0;
        const gColor = gyp_total >= 0 ? "#00FF88" : "#FF6060";

        const obj_pct = (avgcost && objetivo) ? (objetivo - avgcost) / avgcost : 0;
        const sl_pct = (avgcost && sl) ? (sl - avgcost) / avgcost : 0;
        const rr = sl_pct ? Math.abs(obj_pct / sl_pct) : 0;

        // separar gain / lost
        const gains = lotes.filter(l => (l.gyp || 0) >= 0);
        const losts = lotes.filter(l => (l.gyp || 0) < 0);

        const sumLost = losts.reduce((a, l) => a + (l.gyp || 0), 0);
        const cantLost = losts.reduce((a, l) => a + (l.cantidad || 0), 0);
        const costoLost = losts.reduce((a, l) => a + (l.costo || 0), 0);
        const roiLost = costoLost ? sumLost / costoLost : 0;

        const th = (txt, align = "right") =>
            `<th style="text-align:${align};padding:2px 5px;color:#787b86;border-bottom:1px solid #2a2e39;font-weight:normal;font-size:10px;white-space:nowrap">${txt}</th>`;

        // fila last — resumen total (azul)
        const cumTotal = costo + gyp_total;
        const filaLast = `
            <tr style="background:#1a3a6b">
              <td colspan="2" style="padding:3px 5px;color:#d1d4dc;font-weight:bold">last</td>
              <td style="text-align:right;padding:3px 5px;color:cyan">${fmt(last)}</td>
              <td style="text-align:right;padding:3px 5px;color:#aaa">${fmts(position)}</td>
              <td style="text-align:right;padding:3px 5px;color:#aaa">${fmt(position)}</td>
              <td style="text-align:right;padding:3px 5px;color:${gColor}">${fmts(gyp_total)}</td>
              <td style="text-align:right;padding:3px 5px;color:#aaa">${fmt(costo)}</td>
              <td style="text-align:right;padding:3px 5px;color:#aaa">${fmt(cumTotal)}</td>
              <td style="text-align:right;padding:3px 5px;color:${gColor}">${fmtsp(roi_total)}</td>
              <td style="text-align:right;padding:3px 5px;color:${gColor}">${fmts(gyp_total)}</td>
            </tr>`;

        // fila lost agrupada (gris oscuro)
        const filaLost = losts.length ? `
            <tr style="background:#1a1a2e;color:#787b86">
              <td colspan="2" style="padding:2px 5px">▷ lost (${losts.length})</td>
              <td></td>
              <td style="text-align:right;padding:2px 5px">${fmt(cantLost)}</td>
              <td></td>
              <td style="text-align:right;padding:2px 5px;color:#FF6060">${fmts(sumLost)}</td>
              <td style="text-align:right;padding:2px 5px">${fmt(costoLost)}</td>
              <td style="text-align:right;padding:2px 5px">${fmt(costoLost + sumLost)}</td>
              <td style="text-align:right;padding:2px 5px;color:#FF6060">${fmtsp(roiLost)}</td>
              <td></td>
            </tr>` : "";

        // filas gain con acumulados (verde)
        let acumGyp = 0, acumCosto = 0, acumCant = 0;
        const filasGain = gains.map((l, i) => {
            acumGyp += l.gyp || 0;
            acumCosto += l.costo || 0;
            acumCant += l.cantidad || 0;
            const acumRoi = acumCosto ? acumGyp / acumCosto : 0;
            const acumTotal = acumCosto + acumGyp;
            const ac = acumGyp >= 0 ? "#00FF88" : "#FF6060";
            const lc = (l.gyp || 0) >= 0 ? "#00FF88" : "#FF6060";
            return `<tr style="background:#152a1e">
              <td style="color:#aaa;padding:2px 5px">${i + 1}</td>
              <td style="color:#aaa;padding:2px 5px;font-size:10px;white-space:nowrap">${l.fechahora || l.fecha || ""}</td>
              <td style="text-align:right;padding:2px 5px">${fmt(l.precio)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmts(l.cantidad)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumCant)}</td>
              <td style="text-align:right;padding:2px 5px;color:${ac}">${fmts(acumGyp)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumCosto)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumTotal)}</td>
              <td style="text-align:right;padding:2px 5px;color:${ac}">${fmtsp(acumRoi)}</td>
              <td style="text-align:right;padding:2px 5px;color:${lc}">${fmts(l.gyp)}</td>
            </tr>`;
        }).join("");

        return `
        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Posición</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr><td style="color:#787b86;padding:2px 0">Precio medio</td><td style="text-align:right">${fmt(avgcost)}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Cantidad</td><td style="text-align:right">${fmt(position, 4)}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Costo base</td><td style="text-align:right">${fmt(costo)}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Precio actual</td><td id="tv-last" style="text-align:right;color:cyan">${fmt(last)}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">G/P</td>
              <td id="tv-gyp" style="text-align:right;color:${gColor}">${fmts(gyp_total)} (${fmtsp(roi_total)})</td></tr>
        </table>

        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Consenso</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr><td style="color:#787b86;padding:2px 0">Rotación</td><td style="text-align:right">${pos.rotacion || "—"}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Inst Señal</td><td style="text-align:right">${pos.senal_inst || "—"}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Analistas</td><td style="text-align:right">${pos.senal_ana || "—"}</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">IA Signal</td><td style="text-align:right">${pos.ia_signal || "—"}</td></tr>
          ${pos.consenso_label ? `<tr style="border-top:1px solid #2a2e39">
            <td style="color:#787b86;padding:4px 0 2px">Consenso</td>
            <td style="text-align:right;padding:4px 0 2px;font-weight:bold">
              ${pos.consenso_label}
              ${pos.consenso_suma ? `<span style="color:#787b86;font-size:11px;margin-left:6px">${pos.consenso_suma}</span>` : ""}
            </td>
          </tr>` : ""}
        </table>

        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Estrategia</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr><td style="color:#787b86;padding:2px 0">Objetivo</td>
              <td style="text-align:right;color:#00FF88">${fmt(objetivo)} (${fmtsp(obj_pct)})</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">Ref. SL</td>
              <td style="text-align:right;color:#FF6060">${fmt(sl)} (${fmtsp(sl_pct)})</td></tr>
          <tr><td style="color:#787b86;padding:2px 0">R/R</td><td style="text-align:right">1:${rr.toFixed(1)}</td></tr>
        </table>

        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Lotes</div>
        <div style="overflow-x:auto">
        <table style="border-collapse:collapse;font-size:11px;min-width:100%">
          <thead><tr>
            ${th("Lote", "left")}${th("Fecha", "left")}${th("Precio")}${th("Cant")}
            ${th("Cum Cant")}${th("Cum G/P")}${th("Cum Costo")}${th("Cum Total")}${th("%ROI")}${th("G/P")}
          </tr></thead>
          <tbody>
            ${filaLast}
            ${filaLost}
            ${filasGain}
          </tbody>
        </table>
        </div>

        <div style="display:flex;gap:8px;margin-top:14px">
          <button onclick="void(0)" style="flex:1;padding:8px;background:#26a69a;color:#fff;
                  border:none;border-radius:4px;font-size:13px;font-weight:bold;cursor:not-allowed;
                  opacity:0.7">BUY</button>
          <button onclick="void(0)" style="flex:1;padding:8px;background:#ef5350;color:#fff;
                  border:none;border-radius:4px;font-size:13px;font-weight:bold;cursor:not-allowed;
                  opacity:0.7">SELL</button>
        </div>`;
    }

    // ── Crear panel (solo la primera vez) ──────────────────────────────────
    function crearPanel() {
        panelEl = document.createElement("div");
        panelEl.id = "app-tv-panel";
        Object.assign(panelEl.style, {
            position: "fixed", top: "50px", left: "50px", width: "560px",
            background: "#1e2130", color: "#d1d4dc",
            borderRadius: "6px", border: "1px solid #2a2e39",
            fontFamily: "Arial,sans-serif", fontSize: "12px",
            zIndex: "9999", boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            userSelect: "none",
        });

        // barra de título
        const header = document.createElement("div");
        Object.assign(header.style, {
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "6px 10px", cursor: "move",
            borderBottom: "1px solid #2a2e39", background: "#161a25",
            borderRadius: "6px 6px 0 0",
        });

        titleEl = document.createElement("span");
        titleEl.textContent = "Análisis";
        titleEl.style.cssText = "color:#787b86;font-size:11px;text-transform:uppercase;letter-spacing:1px";

        const btnBar = document.createElement("div");
        btnBar.style.cssText = "display:flex;gap:8px;align-items:center";

        const btnMin = document.createElement("span");
        btnMin.textContent = "−";
        btnMin.style.cssText = "cursor:pointer;color:#787b86;font-size:16px;line-height:1;padding:0 3px";
        btnMin.onclick = (e) => {
            e.stopPropagation();
            minimized = !minimized;
            bodyEl.style.display = minimized ? "none" : "block";
            btnMin.textContent = minimized ? "+" : "−";
        };

        const btnClose = document.createElement("span");
        btnClose.id = "app-tv-close";
        btnClose.textContent = "✕";
        btnClose.style.cssText = "cursor:pointer;color:#787b86;font-size:13px;padding:0 3px";
        btnClose.onclick = (e) => {
            e.stopPropagation();
            panelEl.style.display = "none";
            clearTvShapes();
        };

        btnBar.appendChild(btnMin);
        btnBar.appendChild(btnClose);
        header.appendChild(titleEl);
        header.appendChild(btnBar);

        bodyEl = document.createElement("div");
        Object.assign(bodyEl.style, {
            padding: "12px", overflowY: "auto", maxHeight: "80vh",
        });

        panelEl.appendChild(header);
        panelEl.appendChild(bodyEl);

        // drag desde header
        header.addEventListener("mousedown", (e) => {
            if (e.target === btnMin || e.target === btnClose) return;
            isDragging = true;
            startX = e.clientX; startY = e.clientY;
            const rect = panelEl.getBoundingClientRect();
            origLeft = rect.left; origTop = rect.top;
            panelEl.style.right = "auto";
            panelEl.style.left = origLeft + "px";
            panelEl.style.top = origTop + "px";
        });
        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            panelEl.style.left = (origLeft + e.clientX - startX) + "px";
            panelEl.style.top = (origTop + e.clientY - startY) + "px";
        });
        document.addEventListener("mouseup", () => { isDragging = false; });

        document.body.appendChild(panelEl);
    }

    // ── Actualizar contenido ───────────────────────────────────────────────
    function upsertPanel(html, posicion, lotes, symbol) {
        if (!panelEl) crearPanel();
        bodyEl.innerHTML = html;
        panelEl.style.display = "block";
        if (titleEl && symbol) titleEl.textContent = `${symbol} — Análisis`;
        lastPosicion = posicion;
        setTimeout(() => drawTvShapes(posicion, lotes), 800);
    }

    // ── Loop principal ─────────────────────────────────────────────────────
    function poll() {
        ping();
        GM_xmlhttpRequest({
            method: "GET",
            url: `http://localhost:${PORT}/current`,
            onload: (r) => {
                try {
                    const cur = JSON.parse(r.responseText).symbol || "";
                    const cambia = cur && cur !== tvSymbol();
                    navegarSi(cur);
                    if (cambia) autoScalePanes();
                    const sym = tvSymbol() || cur;
                    if (!sym) return;

                    GM_xmlhttpRequest({
                        method: "GET",
                        url: `http://localhost:${PORT}/position?symbol=${sym}`,
                        onload: (r2) => {
                            try {
                                const data = JSON.parse(r2.responseText);
                                if (data && data.posicion && Object.keys(data.posicion).length) {
                                    upsertPanel(buildPanel(data), data.posicion, data.lotes || [], sym);
                                } else {
                                    if (panelEl) panelEl.style.display = "none";
                                    clearTvShapes();
                                    lastPosicion = null;
                                }
                            } catch (_) { }
                        },
                        onerror: () => { },
                    });
                } catch (_) { }
            },
            onerror: () => { },
        });
    }

    // ── Poll precio live (cada 2s) ─────────────────────────────────────────
    function pollPrice() {
        const sym = tvSymbol();
        if (!sym || !panelEl || panelEl.style.display === "none") return;
        GM_xmlhttpRequest({
            method: "GET",
            url: `http://localhost:${PORT}/price?symbol=${sym}`,
            onload: (r) => {
                try {
                    const d = JSON.parse(r.responseText);
                    const last = d.last;
                    if (!last || !lastPosicion) return;
                    const costo = lastPosicion.costo_base || 0;
                    const position = lastPosicion.position || 0;
                    const gyp = (last && position && costo) ? last * position - costo : 0;
                    const roi = costo ? gyp / costo : 0;
                    const color = gyp >= 0 ? "#00FF88" : "#FF6060";
                    // actualizar celdas sin redibujar el panel completo
                    const elLast = document.getElementById("tv-last");
                    const elGyp  = document.getElementById("tv-gyp");
                    if (elLast) elLast.textContent = fmt(last);
                    if (elGyp)  { elGyp.textContent = `${fmts(gyp)} (${fmtsp(roi)})`; elGyp.style.color = color; }
                    lastPosicion.last = last;
                } catch (_) {}
            },
            onerror: () => {},
        });
    }

    setInterval(poll, 3000);
    setInterval(pollPrice, 2000);
    setTimeout(poll, 1500);
})();
