// ==UserScript==
// @name         TradingView — App Panel
// @namespace    http://tampermonkey.net/
// @version      2.1
// @match        https://www.tradingview.com/*
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// @connect      localhost
// ==/UserScript==

(function () {
    "use strict";

    const PORT = 5050;
    let panelEl = null, bodyEl = null, titleEl = null, symbolsEl = null, btnCartera = null;
    let minimized = false;
    let symbolsVisible = false;
    let _symbols = [];
    let isDragging = false, startX = 0, startY = 0, origLeft = 0, origTop = 0;
    let lastPosicion = null;

    // ── TV native drawings ─────────────────────────────────────────────────
    let _tvShapes = { zona: null, avgline: null, objline: null };
    let _lastDrawKey = "";   // evitar redibujar si los valores no cambiaron
    let _dec = 2;            // decimales precio: 2=Stock/FCI, 4=Crypto
    function tvChart() {
        try {
            const api = unsafeWindow.TradingViewApi;
            return api ? api.activeChart() : null;
        } catch (_) { return null; }
    }

    function clearTvShapes() {
        const ac = tvChart();
        if (!ac) return;

        // Eliminar todos los shapes nuestros — por color/texto para cubrir sesiones anteriores
        try {
            (ac.getAllShapes() || []).forEach(s => {
                try {
                    const p = ac.getShapeById(s.id).getProperties();
                    const esNuestro =
                        (s.name === "rectangle"       && p.backgroundColor === "rgba(200,170,0,0.12)") ||
                        (s.name === "horizontal_line" && p.linecolor === "#FFD700") ||
                        (s.name === "horizontal_line" && p.linecolor === "#2196F3");
                    if (esNuestro) ac.removeEntity(s.id);
                } catch (_) {}
            });
        } catch (_) {}

        ["zona", "avgline", "objline"].forEach(k => { _tvShapes[k] = null; });
    }

    function drawTvShapes(posicion, lotes) {
        const ac = tvChart();
        if (!ac) return;

        // Precios y fechas: todos los lotes (gain + lost) — zona cubre el historial completo
        const avgcost = posicion.avgcost || 0;
        const prices = lotes.map(l => l.precio || 0).filter(p => p > 0);
        if (!prices.length && !avgcost) return;

        const minP = prices.length ? Math.min(...prices) : avgcost;
        const maxP = prices.length ? Math.max(...prices) : avgcost;

        // Fecha más antigua de TODOS los lotes (gain + lost) → cubre el historial completo
        const fechas = lotes
            .map(l => l.fechahora || l.fecha || "")
            .filter(f => f)
            .map(f => Math.floor(new Date(f.replace(" ", "T")).getTime() / 1000))
            .filter(t => t > 0);
        const t1 = fechas.length ? Math.min(...fechas) : null;
        const t2 = Math.floor(Date.now() / 1000);

        // Evitar redibujar si los valores no cambiaron
        const objetivo = posicion.objetivo || 0;
        const drawKey = `${avgcost}|${minP}|${maxP}|${t1}|${objetivo}`;
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
                            text: `base $${avgcost.toFixed(_dec)}`,
                            textcolor: "#FFD700",
                        },
                    }
                );
            } catch (_) {}
        }

        // Línea objetivo azul
        if (objetivo) {
            try {
                _tvShapes.objline = ac.createShape(
                    { price: objetivo },
                    {
                        shape: "horizontal_line",
                        lock: false,
                        overrides: {
                            linecolor: "#2196F3",
                            linewidth: 2,
                            linestyle: 1,
                            showLabel: true,
                            text: `obj $${objetivo.toFixed(_dec)}`,
                            textcolor: "#2196F3",
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

    // ── Guardar layout TV antes de navegar (evita mensaje "perderás cambios")
    function tvSave() {
        try {
            unsafeWindow.document.dispatchEvent(new KeyboardEvent("keydown", {
                key: "s", ctrlKey: true, bubbles: true, cancelable: true
            }));
        } catch (_) {}
    }

    // ── Navegar a nuevo símbolo preservando timeframe ─────────────────────
    function navegarSi(symbol) {
        if (!symbol || symbol === tvSymbol()) return;
        const prefix = (symbol.includes("USDT") || symbol.includes("BTC")) ? "BINANCE:" : "";
        // Leer intervalo desde API TV (más confiable que la URL)
        let interval = "";
        try {
            const res = tvChart().getResolution();
            if (res) interval = `&interval=${res}`;
        } catch (_) {
            const m = window.location.href.match(/[?&]interval=([^&]+)/);
            if (m) interval = `&interval=${m[1]}`;
        }
        tvSave();
        setTimeout(() => {
            window.location.href = `https://www.tradingview.com/chart/?symbol=${prefix}${symbol}${interval}`;
        }, 300);
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
        const vehiculo = data.vehiculo || "Stock";
        const isCrypto = vehiculo === "Crypto";
        _dec = isCrypto ? 4 : 2;

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
              <td style="text-align:right;padding:3px 5px;color:cyan">${fmt(last, _dec)}</td>
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
              <td style="text-align:right;padding:2px 5px">${fmt(l.precio, _dec)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmts(l.cantidad)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumCant)}</td>
              <td style="text-align:right;padding:2px 5px;color:${ac}">${fmts(acumGyp)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumCosto)}</td>
              <td style="text-align:right;padding:2px 5px;color:#aaa">${fmt(acumTotal)}</td>
              <td style="text-align:right;padding:2px 5px;color:${ac}">${fmtsp(acumRoi)}</td>
              <td style="text-align:right;padding:2px 5px;color:${lc}">${fmts(l.gyp)}</td>
            </tr>`;
        }).join("");

        const td1 = `style="color:#787b86;padding:2px 0;width:55%"`;
        const td2 = `style="text-align:right;padding:2px 0"`;

        return `
        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Posición</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr><td ${td1}>Precio medio</td><td ${td2}>${fmt(avgcost, _dec)}</td></tr>
          <tr><td ${td1}>Cantidad</td><td ${td2}>${fmt(position, 4)}</td></tr>
          <tr><td ${td1}>Costo base</td><td ${td2}>${fmt(costo)}</td></tr>
          <tr><td ${td1}>Precio actual</td><td id="tv-last" ${td2} style="padding:2px 0;color:cyan">${fmt(last, _dec)}</td></tr>
          <tr><td ${td1}>G/P</td>
              <td id="tv-gyp" ${td2} style="padding:2px 0;color:${gColor}">${fmts(gyp_total)} (${fmtsp(roi_total)})</td></tr>
        </table>

        ${!isCrypto && pos.consenso_label ? `
        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Consenso</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr>
            <td ${td1}>Consenso</td>
            <td style="text-align:right;padding:2px 0;font-weight:bold">
              ${pos.consenso_label}
              ${pos.consenso_suma ? `<span style="color:#787b86;font-size:11px;margin-left:6px">${pos.consenso_suma}</span>` : ""}
            </td>
          </tr>
        </table>` : ""}

        <div style="font-size:10px;color:#787b86;text-transform:uppercase;letter-spacing:1px;
                    border-bottom:1px solid #2a2e39;padding-bottom:4px;margin-bottom:6px">Estrategia</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
          <tr><td ${td1}>Precio entrada</td><td ${td2}>${fmt(avgcost, _dec)}</td></tr>
          <tr><td ${td1}>Objetivo</td>
              <td ${td2} style="padding:2px 0;color:#00FF88">${fmt(objetivo, _dec)} (${fmtsp(obj_pct)})</td></tr>
          <tr><td ${td1}>Ref. SL</td>
              <td ${td2} style="padding:2px 0;color:#FF6060">${fmt(sl, _dec)} (${fmtsp(sl_pct)})</td></tr>
          <tr><td ${td1}>R/R</td><td ${td2}>1:${rr.toFixed(1)}</td></tr>
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

        <div style="margin-top:14px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <button id="tv-modo-toggle"
              style="padding:10px 16px;background:#2a2e39;color:#d1d4dc;border:1px solid #434651;
                     border-radius:4px;font-size:15px;font-weight:bold;cursor:pointer;white-space:nowrap;min-width:70px">QTY</button>
            <input id="tv-order-qty" type="number" min="0" step="any"
              style="flex:1;padding:10px 14px;background:#1a1e2e;color:#fff;border:2px solid #434651;
                     border-radius:4px;font-size:22px;font-weight:bold;outline:none" placeholder="0" />
          </div>
          <div id="tv-qty-calc"
            style="text-align:right;font-size:13px;color:#9598a1;min-height:20px;margin-bottom:8px;padding-right:2px"></div>
          <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
            <span id="tv-order-status" style="font-size:10px;color:#787b86;flex:1;text-align:right"></span>
          </div>
          <div style="display:flex;gap:8px">
            <button id="tv-btn-buy"
              style="flex:1;padding:10px;background:#26a69a;color:#fff;border:none;border-radius:4px;
                     font-size:14px;font-weight:bold;cursor:pointer">BUY</button>
            <button id="tv-btn-sell"
              style="flex:1;padding:10px;background:#ef5350;color:#fff;border:none;border-radius:4px;
                     font-size:14px;font-weight:bold;cursor:pointer">SELL</button>
          </div>
        </div>`;
    }

    // ── Crear panel (solo la primera vez) ──────────────────────────────────
    function crearPanel() {
        panelEl = document.createElement("div");
        panelEl.id = "app-tv-panel";
        Object.assign(panelEl.style, {
            position: "fixed", top: "120px", left: "50px", width: "560px",
            background: "#1e2130", color: "#d1d4dc",
            borderRadius: "6px", border: "1px solid #2a2e39",
            fontFamily: "Arial,sans-serif", fontSize: "12px",
            zIndex: "9999", boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            userSelect: "none",  // header drag — input fields override esto automáticamente
        });

        // barra de título
        const header = document.createElement("div");
        Object.assign(header.style, {
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "6px 10px", cursor: "move",
            borderBottom: "1px solid #2a2e39", background: "#FFD700",
            borderRadius: "6px 6px 0 0",
        });

        titleEl = document.createElement("span");
        titleEl.textContent = "Análisis";
        titleEl.style.cssText = "color:#1a1a1a;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:bold";

        const btnBar = document.createElement("div");
        btnBar.style.cssText = "display:flex;gap:8px;align-items:center";

        const btnMin = document.createElement("span");
        btnMin.textContent = "−";
        btnMin.style.cssText = "cursor:pointer;color:#1a1a1a;font-size:16px;line-height:1;padding:0 3px";
        btnMin.onclick = (e) => {
            e.stopPropagation();
            minimized = !minimized;
            bodyEl.style.display = minimized ? "none" : "block";
            btnMin.textContent = minimized ? "+" : "−";
        };

        const btnClose = document.createElement("span");
        btnClose.id = "app-tv-close";
        btnClose.textContent = "✕";
        btnClose.style.cssText = "cursor:pointer;color:#1a1a1a;font-size:13px;padding:0 3px";
        btnClose.onclick = (e) => {
            e.stopPropagation();
            panelEl.style.display = "none";
            clearTvShapes();
        };

        btnCartera = document.createElement("span");
        btnCartera.textContent = "≡";
        btnCartera.title = "Cartera";
        btnCartera.style.cssText = "cursor:pointer;color:#1a1a1a;font-size:16px;line-height:1;padding:0 3px";
        btnCartera.onclick = (e) => {
            e.stopPropagation();
            symbolsVisible = !symbolsVisible;
            symbolsEl.style.display = symbolsVisible ? "flex" : "none";
            btnCartera.style.color = symbolsVisible ? "#4a72c8" : "#787b86";
            if (symbolsVisible && !_symbols.length) fetchSymbols();
        };

        btnBar.appendChild(btnCartera);
        btnBar.appendChild(btnMin);
        btnBar.appendChild(btnClose);
        header.appendChild(titleEl);
        header.appendChild(btnBar);

        symbolsEl = document.createElement("div");
        Object.assign(symbolsEl.style, {
            display: "none",
            flexWrap: "wrap",
            gap: "4px",
            padding: "6px 10px",
            borderBottom: "1px solid #2a2e39",
            background: "#161a25",
            maxHeight: "68px",
            overflowY: "auto",
        });

        bodyEl = document.createElement("div");
        Object.assign(bodyEl.style, {
            padding: "12px", overflowY: "auto", maxHeight: "80vh",
        });

        panelEl.appendChild(header);
        panelEl.appendChild(symbolsEl);
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

        // Botón flotante siempre visible — reabre el panel si fue cerrado
        const fab = document.createElement("div");
        fab.id = "app-tv-fab";
        fab.textContent = "📊";
        Object.assign(fab.style, {
            position: "fixed", bottom: "80px", right: "14px",
            width: "36px", height: "36px",
            background: "#1e2130", border: "1px solid #2a2e39",
            borderRadius: "50%", display: "flex",
            alignItems: "center", justifyContent: "center",
            fontSize: "18px", cursor: "pointer",
            zIndex: "10000", boxShadow: "0 2px 8px rgba(0,0,0,0.5)",
            userSelect: "none",
        });
        fab.title = "App Panel";
        fab.onclick = () => {
            panelEl.style.display = "block";
        };
        document.body.appendChild(fab);
    }

    // ── Lista de símbolos en cartera ──────────────────────────────────────
    function renderSymbols(symbols, currentSym) {
        if (!symbolsEl) return;
        symbolsEl.innerHTML = "";
        if (!symbols.length) return;
        symbols.forEach(sym => {
            const isCurrent = sym === currentSym;
            const chip = document.createElement("span");
            chip.textContent = sym;
            Object.assign(chip.style, {
                padding: "2px 7px",
                borderRadius: "3px",
                fontSize: "11px",
                cursor: "pointer",
                fontWeight: isCurrent ? "bold" : "normal",
                background: isCurrent ? "#2a5298" : "#2a2e39",
                color: isCurrent ? "#fff" : "#9598a1",
                border: isCurrent ? "1px solid #4a72c8" : "1px solid #363a45",
                userSelect: "none",
                flexShrink: "0",
            });
            chip.onclick = () => switchSymbol(sym);
            symbolsEl.appendChild(chip);
        });
    }

    function fetchSymbols() {
        GM_xmlhttpRequest({
            method: "GET",
            url: `http://localhost:${PORT}/symbols`,
            onload: (r) => {
                try {
                    const d = JSON.parse(r.responseText);
                    _symbols = d.symbols || [];
                    renderSymbols(_symbols, tvSymbol());
                    if (btnCartera) btnCartera.title = `Cartera (${_symbols.length})`;
                } catch (_) {}
            },
            onerror: () => {},
        });
    }

    function switchSymbol(sym) {
        GM_xmlhttpRequest({
            method: "POST",
            url: `http://localhost:${PORT}/current`,
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify({ symbol: sym }),
            onload: (r) => {
                try {
                    const d = JSON.parse(r.responseText);
                    if (d.ok) {
                        navegarSi(sym);
                        setTimeout(poll, 500);
                    }
                } catch (_) {}
            },
            onerror: () => {},
        });
    }

    // ── Modo QTY / USD ────────────────────────────────────────────────────
    let _tvModo = "QTY"; // "QTY" | "USD"

    function _calcEquiv() {
        const inp = document.getElementById("tv-order-qty");
        const calc = document.getElementById("tv-qty-calc");
        if (!inp || !calc) return;
        const v = parseFloat(inp.value);
        const price = (lastPosicion || {}).last || 0;
        const sym = tvSymbol();
        const isCrypto = _dec === 4;
        if (v > 0 && price > 0) {
            if (_tvModo === "USD") {
                const qty = isCrypto ? (v / price).toFixed(4) : Math.floor(v / price);
                calc.textContent = `≈ ${qty} ${sym}`;
            } else {
                calc.textContent = `≈ $${(v * price).toFixed(2)} USD`;
            }
        } else {
            calc.textContent = "";
        }
    }

    function _bindModoToggle() {
        const btn = document.getElementById("tv-modo-toggle");
        const inp = document.getElementById("tv-order-qty");
        if (!btn) return;
        // Restaurar estado visual desde _tvModo (necesario en cada redraw)
        btn.textContent = _tvModo;
        btn.style.color = _tvModo === "USD" ? "#26a69a" : "#d1d4dc";
        btn.style.borderColor = _tvModo === "USD" ? "#26a69a" : "#434651";
        btn.onclick = () => {
            _tvModo = _tvModo === "QTY" ? "USD" : "QTY";
            btn.textContent = _tvModo;
            btn.style.color = _tvModo === "USD" ? "#26a69a" : "#d1d4dc";
            btn.style.borderColor = _tvModo === "USD" ? "#26a69a" : "#434651";
            if (inp) inp.value = "";
            const calc = document.getElementById("tv-qty-calc");
            if (calc) calc.textContent = "";
        };
        if (inp) inp.oninput = () => _calcEquiv();
    }

    // ── Enviar orden al servidor local ────────────────────────────────────
    function _doPostOrder(body, qtyEl, statusEl) {
        GM_xmlhttpRequest({
            method: "POST",
            url: `http://localhost:${PORT}/order`,
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify(body),
            onload: (r) => {
                try {
                    const d = JSON.parse(r.responseText);
                    const ok = d.ok || d.status in { Submitted: 1, PreSubmitted: 1, FILLED: 1 };
                    if (statusEl) {
                        statusEl.textContent = d.status || (ok ? "✔ enviado" : d.error || "error");
                        statusEl.style.color = ok ? "#26a69a" : "#ef5350";
                    }
                    if (ok && qtyEl) qtyEl.value = "";
                    if (ok) setTimeout(poll, 800);
                } catch (_) { if (statusEl) { statusEl.textContent = "error"; statusEl.style.color = "#ef5350"; } }
            },
            onerror: () => { if (statusEl) { statusEl.textContent = "sin conexión"; statusEl.style.color = "#ef5350"; } },
        });
    }

    function postOrder(side) {
        const qtyEl = document.getElementById("tv-order-qty");
        const statusEl = document.getElementById("tv-order-status");
        const val = parseFloat(qtyEl ? qtyEl.value : 0);
        if (!val || val <= 0) { if (statusEl) { statusEl.textContent = "valor requerido"; statusEl.style.color = "#ef5350"; } return; }
        const pos = lastPosicion || {};
        const price = pos.last || 0;
        if (!price) { if (statusEl) { statusEl.textContent = "sin precio"; statusEl.style.color = "#ef5350"; } return; }
        if (statusEl) { statusEl.textContent = "enviando…"; statusEl.style.color = "#787b86"; }
        const body = {
            symbol: tvSymbol(),
            vehiculo: pos.vehiculo || "Stock",
            account: pos.account || "",
            side: side,
            price: price,
            conid: pos.conid || null,
        };
        if (_tvModo === "USD") body.importe = val;
        else body.qty = val;

        // Para BUY Crypto: verificar saldo USDT antes de enviar
        if (side === "BUY" && (pos.vehiculo || "") === "Crypto") {
            const cost = _tvModo === "USD" ? val : val * price;
            GM_xmlhttpRequest({
                method: "GET",
                url: `http://localhost:${PORT}/balance`,
                onload: (rb) => {
                    try {
                        const bd = JSON.parse(rb.responseText);
                        const usdt = bd.usdt_free || 0;
                        if (usdt < cost) {
                            if (statusEl) {
                                statusEl.textContent = `USDT insuficiente: necesitás $${cost.toFixed(2)}, disponible $${usdt.toFixed(2)}`;
                                statusEl.style.color = "#ef5350";
                            }
                            return;
                        }
                    } catch (_) { /* si falla el chequeo, deja pasar */ }
                    _doPostOrder(body, qtyEl, statusEl);
                },
                onerror: () => _doPostOrder(body, qtyEl, statusEl),
            });
            return;
        }

        _doPostOrder(body, qtyEl, statusEl);
    }

    // ── Actualizar contenido ───────────────────────────────────────────────
    function upsertPanel(html, posicion, lotes, symbol) {
        if (!panelEl) crearPanel();

        // Preservar qty y foco antes de redibujar
        const prevQty = document.getElementById("tv-order-qty")?.value || "";
        const hadFocus = document.activeElement?.id === "tv-order-qty";

        if (!minimized) bodyEl.style.display = "block";
        bodyEl.innerHTML = html;
        panelEl.style.display = "block";
        if (titleEl && symbol) titleEl.textContent = `${symbol} — Análisis`;
        lastPosicion = posicion;
        renderSymbols(_symbols, symbol);

        // Restaurar qty y foco
        const qtyEl = document.getElementById("tv-order-qty");
        if (qtyEl) {
            if (prevQty) qtyEl.value = prevQty;
            if (hadFocus) qtyEl.focus();
        }

        _bindModoToggle();
        if (prevQty) _calcEquiv();
        const btnBuy = document.getElementById("tv-btn-buy");
        const btnSell = document.getElementById("tv-btn-sell");
        if (btnBuy) btnBuy.onclick = () => postOrder("BUY");
        if (btnSell) btnSell.onclick = () => postOrder("SELL");
        // Retry hasta que TV API esté lista (necesario tras navegación/recarga)
        let _attempts = 0;
        const _tryDraw = () => {
            if (tvChart()) { drawTvShapes(posicion, lotes); }
            else if (_attempts++ < 10) { setTimeout(_tryDraw, 1000); }
        };
        setTimeout(_tryDraw, 800);
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
                                    // Obtener precio live antes de renderizar para que nunca sea stale
                                    GM_xmlhttpRequest({
                                        method: "GET",
                                        url: `http://localhost:${PORT}/price?symbol=${sym}`,
                                        onload: (rp) => {
                                            try {
                                                const pd = JSON.parse(rp.responseText);
                                                if (pd.last) data.posicion.last = pd.last;
                                            } catch (_) {}
                                            data.posicion.vehiculo = data.vehiculo;
                                            upsertPanel(buildPanel(data), data.posicion, data.lotes || [], sym);
                                        },
                                        onerror: () => {
                                            data.posicion.vehiculo = data.vehiculo;
                                            upsertPanel(buildPanel(data), data.posicion, data.lotes || [], sym);
                                        },
                                    });
                                } else {
                                    clearTvShapes();
                                    lastPosicion = null;
                                    if (bodyEl) bodyEl.style.display = "none";
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
                    if (elLast) elLast.textContent = fmt(last, _dec);
                    if (elGyp)  { elGyp.textContent = `${fmts(gyp)} (${fmtsp(roi)})`; elGyp.style.color = color; }
                    lastPosicion.last = last;
                } catch (_) {}
            },
            onerror: () => {},
        });
    }

    crearPanel();
    setInterval(poll, 3000);
    setInterval(pollPrice, 2000);
    setInterval(fetchSymbols, 30000);
    setTimeout(poll, 1500);
})();
