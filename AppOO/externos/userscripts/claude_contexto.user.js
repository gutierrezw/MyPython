// ==UserScript==
// @name         AppOO — Contexto de Cartera en Claude
// @namespace    AppOO
// @version      1.1
// @description  Inyecta contexto de cartera desde la app local en claude.ai
// @match        https://claude.ai/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-end
// ==/UserScript==

(function () {
    "use strict";

    const SERVER = "http://localhost:8050/tv/contexto";
    const BTN_ID = "appoo-ctx-btn";
    let contextoData = null;

    // ── Estilos ────────────────────────────────────────────────────────────────
    GM_addStyle(`
        #${BTN_ID} {
            position: fixed;
            bottom: 88px;
            right: 20px;
            z-index: 9999;
            background: #1e3a5f;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 13px;
            font-family: "Segoe UI", sans-serif;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
            transition: background 0.2s;
        }
        #${BTN_ID}:hover { background: #2a4f80; }
        #${BTN_ID}.ok    { border-color: #a6e3a1; color: #a6e3a1; }
        #${BTN_ID}.error { border-color: #f38ba8; color: #f38ba8; }
    `);

    // ── Fetch contexto desde la app ────────────────────────────────────────────
    function fetchContexto(callback) {
        GM_xmlhttpRequest({
            method: "GET",
            url: SERVER,
            timeout: 3000,
            onload: function (r) {
                try {
                    contextoData = JSON.parse(r.responseText);
                    if (callback) callback(true);
                } catch (e) {
                    contextoData = null;
                    if (callback) callback(false);
                }
            },
            onerror: function () {
                contextoData = null;
                if (callback) callback(false);
            },
            ontimeout: function () {
                contextoData = null;
                if (callback) callback(false);
            },
        });
    }

    // ── Formatear contexto como texto para insertar ───────────────────────────
    function formatContexto(data) {
        if (!data || !data.posiciones || !data.posiciones.length) {
            return "[AppOO] Sin posiciones disponibles.";
        }
        const lineas = data.posiciones.map(
            (p) => `  • ${p.symbol} (${p.nombre}): $${Number(p.precio).toFixed(2)}`
        );
        return `[Contexto AppOO — Posiciones en cartera]\n${lineas.join("\n")}\n\n`;
    }

    // ── Inyectar texto en el editor de claude.ai (ProseMirror) ───────────────
    function inyectarEnEditor(texto) {
        // claude.ai usa un div contenteditable (ProseMirror)
        const editor = document.querySelector("div[contenteditable='true']");
        if (!editor) {
            alert("AppOO: no se encontró el editor de claude.ai.");
            return false;
        }
        editor.focus();
        // Mover cursor al inicio
        const sel = window.getSelection();
        const range = document.createRange();
        range.setStart(editor, 0);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        // Insertar texto via execCommand (funciona en ProseMirror)
        document.execCommand("insertText", false, texto);
        return true;
    }

    // ── Botón principal ────────────────────────────────────────────────────────
    function crearBoton() {
        if (document.getElementById(BTN_ID)) return;
        const btn = document.createElement("button");
        btn.id = BTN_ID;
        btn.textContent = "📊 Cartera";
        btn.title = "Inyectar posiciones de cartera desde AppOO";

        btn.addEventListener("click", function () {
            btn.textContent = "⏳ Cargando...";
            btn.className = "";
            fetchContexto(function (ok) {
                if (!ok || !contextoData) {
                    btn.textContent = "📊 Cartera";
                    btn.className = "error";
                    btn.title = "Error: AppOO no responde en localhost:8050";
                    setTimeout(() => { btn.className = ""; btn.title = "Inyectar posiciones de cartera desde AppOO"; }, 3000);
                    return;
                }
                const texto = formatContexto(contextoData);
                const insertado = inyectarEnEditor(texto);
                btn.textContent = "📊 Cartera";
                btn.className = insertado ? "ok" : "error";
                setTimeout(() => { btn.className = ""; }, 2000);
            });
        });

        document.body.appendChild(btn);
    }

    // ── Observar DOM — claude.ai es SPA, el editor aparece después de navegar ─
    const observer = new MutationObserver(function () {
        if (!document.getElementById(BTN_ID)) crearBoton();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    crearBoton();

    // Prefetch al cargar para tener el contexto listo
    fetchContexto(null);
})();
