// Landing page : boutons « copier » et playground (client MCP + LLM du visiteur).
// Aucune dépendance : le navigateur parle directement au fournisseur choisi et au serveur MCP.
(function () {
  "use strict";

  var LANG = document.documentElement.lang === "fr" ? "fr" : "en";
  var T = {
    en: {
      copy: "Copy", copied: "Copied", getKey: "Get a key", thinking: "Thinking…",
      needKey: "Enter an API key for this provider first.",
      needQ: "Type a question first.",
      connecting: "Connecting to the nutshell server…",
      mcpFail: "Cannot reach the nutshell server: ",
      network: "The request was blocked (CORS) or the network is down. This provider may not accept calls from a browser: try OpenRouter.",
      badKey: "The provider rejected the key (HTTP 401/403).",
      http: "Provider error ",
      maxTurns: "Stopped after 12 tool rounds. Ask a narrower question.",
      refusal: "The model declined to answer.",
      stopped: "Stopped.", empty: "(no text answer)",
      oauthFail: "OpenRouter sign-in failed: ", oauthOk: "Signed in with OpenRouter. Key kept in this tab.",
      args: "arguments", error: "error",
      system: "You answer questions about European territories with the nutshell tools " +
        "(Eurostat, Copernicus and OpenStreetMap at NUTS level). Never give figures from memory: " +
        "fetch them with the tools. Present results as a compact Markdown table, then say how " +
        "reliable each source is (quality flags, provenance line). Answer in the user's language."
    },
    fr: {
      copy: "Copier", copied: "Copié", getKey: "Obtenir une clé", thinking: "Réflexion…",
      needKey: "Saisissez d'abord une clé d'API pour ce fournisseur.",
      needQ: "Saisissez d'abord une question.",
      connecting: "Connexion au serveur nutshell…",
      mcpFail: "Serveur nutshell injoignable : ",
      network: "La requête a été bloquée (CORS) ou le réseau est indisponible. Ce fournisseur n'accepte peut-être pas les appels depuis un navigateur : essayez OpenRouter.",
      badKey: "Le fournisseur a refusé la clé (HTTP 401/403).",
      http: "Erreur du fournisseur ",
      maxTurns: "Arrêt après 12 tours d'appels de tools. Posez une question plus ciblée.",
      refusal: "Le modèle a refusé de répondre.",
      stopped: "Interrompu.", empty: "(pas de réponse textuelle)",
      oauthFail: "Échec de la connexion OpenRouter : ", oauthOk: "Connecté à OpenRouter. Clé conservée dans cet onglet.",
      args: "arguments", error: "erreur",
      system: "Tu réponds aux questions sur les territoires européens avec les tools nutshell " +
        "(Eurostat, Copernicus et OpenStreetMap au niveau NUTS). Ne donne jamais de chiffres de " +
        "mémoire : récupère-les avec les tools. Présente les résultats dans un tableau Markdown " +
        "compact, puis indique la fiabilité de chaque source (drapeaux de qualité, ligne de " +
        "provenance). Réponds dans la langue de l'utilisateur."
    }
  }[LANG];

  // ------------------------------------------------------------ copier

  document.querySelectorAll("button[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var t = document.getElementById(b.dataset.copy).textContent;
      try {
        navigator.clipboard.writeText(t).then(function () {
          b.textContent = T.copied; setTimeout(function () { b.textContent = T.copy; }, 1500);
        });
      } catch (e) { /* clipboard indisponible */ }
    });
  });

  var root = document.getElementById("playground");
  if (!root) return;

  // ------------------------------------------------------------ stockage (onglet uniquement)

  function load(k) { try { return sessionStorage.getItem("nutshell.pg." + k) || ""; } catch (e) { return ""; } }
  function save(k, v) {
    try { v ? sessionStorage.setItem("nutshell.pg." + k, v) : sessionStorage.removeItem("nutshell.pg." + k); }
    catch (e) { /* stockage bloqué : la clé reste en mémoire */ }
  }

  // ------------------------------------------------------------ fournisseurs

  var PROVIDERS = {
    openrouter: { label: "OpenRouter", kind: "openai", base: "https://openrouter.ai/api/v1",
      model: "mistralai/mistral-small-3.2-24b-instruct", keyUrl: "https://openrouter.ai/settings/keys" },
    anthropic: { label: "Anthropic", kind: "anthropic", base: "https://api.anthropic.com/v1",
      model: "claude-opus-5", keyUrl: "https://console.anthropic.com/settings/keys" },
    openai: { label: "OpenAI", kind: "openai", base: "https://api.openai.com/v1",
      model: "gpt-5-mini", keyUrl: "https://platform.openai.com/api-keys" },
    gemini: { label: "Google Gemini", kind: "openai",
      base: "https://generativelanguage.googleapis.com/v1beta/openai",
      model: "gemini-2.5-flash", keyUrl: "https://aistudio.google.com/apikey" },
    mistral: { label: "Mistral AI", kind: "openai", base: "https://api.mistral.ai/v1",
      model: "mistral-small-latest", keyUrl: "https://console.mistral.ai/api-keys" },
    local: { label: "Local (Ollama, LM Studio…)", kind: "openai", base: "http://localhost:11434/v1",
      model: "gemma3:27b", keyOptional: true }
  };

  function authHeaders(p, key) {
    if (p.kind === "anthropic") {
      return { "x-api-key": key, "anthropic-version": "2023-06-01",
               "anthropic-dangerous-direct-browser-access": "true" };
    }
    var h = key ? { "authorization": "Bearer " + key } : {};
    if (p === PROVIDERS.openrouter) h["x-title"] = "nutshell-mcp playground";
    return h;
  }

  // ------------------------------------------------------------ client MCP (streamable HTTP)

  function Mcp(url) { this.url = url; this.sid = ""; this.proto = ""; this.id = 0; this.tools = null; }

  Mcp.prototype.rpc = async function (method, params, notify, retried) {
    var h = { "content-type": "application/json", "accept": "application/json, text/event-stream" };
    if (this.sid) h["mcp-session-id"] = this.sid;
    if (this.proto) h["mcp-protocol-version"] = this.proto;
    var id = notify ? undefined : ++this.id;
    var body = { jsonrpc: "2.0", method: method };
    if (params) body.params = params;
    if (!notify) body.id = id;
    var r = await fetch(this.url, { method: "POST", headers: h, body: JSON.stringify(body) });
    if (r.status === 404 && this.sid && !retried) {   // session expirée (redémarrage serveur)
      this.sid = ""; this.proto = ""; this.tools = null;
      await this.connect();
      return this.rpc(method, params, notify, true);
    }
    if (!r.ok) throw new Error("HTTP " + r.status);
    var sid = r.headers.get("mcp-session-id");
    if (sid) this.sid = sid;
    if (notify) return null;
    var msg = null;
    if ((r.headers.get("content-type") || "").indexOf("text/event-stream") >= 0) {
      (await r.text()).split(/\r?\n\r?\n/).forEach(function (ev) {
        var data = ev.split(/\r?\n/).filter(function (l) { return l.indexOf("data:") === 0; })
          .map(function (l) { return l.slice(5).trim(); }).join("\n");
        if (!data) return;
        try { var m = JSON.parse(data); if (m.id === id) msg = m; } catch (e) { /* événement ignoré */ }
      });
    } else {
      msg = await r.json();
    }
    if (!msg) throw new Error("empty MCP response");
    if (msg.error) throw new Error(msg.error.message);
    return msg.result;
  };

  Mcp.prototype.connect = async function () {
    if (this.tools) return;
    var res = await this.rpc("initialize", { protocolVersion: "2025-06-18", capabilities: {},
      clientInfo: { name: "nutshell-playground", version: "1" } }, false, true);
    this.proto = res.protocolVersion || "";
    await this.rpc("notifications/initialized", null, true, true);
    this.tools = (await this.rpc("tools/list", {}, false, true)).tools || [];
  };

  Mcp.prototype.call = async function (name, args) {
    try {
      var res = await this.rpc("tools/call", { name: name, arguments: args || {} });
      var text = (res.content || []).filter(function (c) { return c.type === "text"; })
        .map(function (c) { return c.text; }).join("\n");
      return { text: text, isError: !!res.isError };
    } catch (e) {
      return { text: "Erreur d'appel du tool : " + e.message, isError: true };
    }
  };

  // ------------------------------------------------------------ appels LLM

  function ProviderError(msg) { this.message = msg; }

  async function post(url, headers, body, signal) {
    var r;
    try {
      r = await fetch(url, { method: "POST", signal: signal,
        headers: Object.assign({ "content-type": "application/json" }, headers),
        body: JSON.stringify(body) });
    } catch (e) {
      if (e.name === "AbortError") throw e;
      throw new ProviderError(T.network);
    }
    if (r.status === 401 || r.status === 403) throw new ProviderError(T.badKey);
    var data = null;
    try { data = await r.json(); } catch (e) { /* corps non JSON */ }
    if (!r.ok) {
      var err = data && (data.error && (data.error.message || data.error) || data.message);
      throw new ProviderError(T.http + r.status + (err ? " : " + (typeof err === "string" ? err : JSON.stringify(err)) : ""));
    }
    return data;
  }

  // Une étape : renvoie { texts: [...], calls: [{id, name, args, bad}], done, refusal }.
  async function stepAnthropic(ctx, signal) {
    var d = await post(ctx.base + "/messages", authHeaders(ctx.p, ctx.key), {
      model: ctx.model, max_tokens: 16000, system: T.system, messages: ctx.history,
      tools: ctx.mcp.tools.map(function (t) {
        return { name: t.name, description: t.description || "", input_schema: t.inputSchema };
      })
    }, signal);
    ctx.history.push({ role: "assistant", content: d.content });
    var out = { texts: [], calls: [], refusal: d.stop_reason === "refusal" };
    (d.content || []).forEach(function (b) {
      if (b.type === "text" && b.text) out.texts.push(b.text);
      if (b.type === "tool_use") out.calls.push({ id: b.id, name: b.name, args: b.input || {} });
    });
    return out;
  }

  function pushResultsAnthropic(ctx, results) {
    ctx.history.push({ role: "user", content: results.map(function (r) {
      return { type: "tool_result", tool_use_id: r.id, content: r.text, is_error: r.isError };
    }) });
  }

  async function stepOpenAI(ctx, signal) {
    var d = await post(ctx.base + "/chat/completions", authHeaders(ctx.p, ctx.key), {
      model: ctx.model,
      messages: [{ role: "system", content: T.system }].concat(ctx.history),
      tools: ctx.mcp.tools.map(function (t) {
        return { type: "function", function: { name: t.name, description: t.description || "",
                                                parameters: t.inputSchema } };
      })
    }, signal);
    var m = (d.choices && d.choices[0] && d.choices[0].message) || {};
    var kept = { role: "assistant", content: m.content || "" };
    if (m.tool_calls && m.tool_calls.length) kept.tool_calls = m.tool_calls;
    ctx.history.push(kept);
    var out = { texts: m.content ? [m.content] : [], calls: [], refusal: !!m.refusal };
    (m.tool_calls || []).forEach(function (tc) {
      var args = {}, bad = false;
      try { args = JSON.parse(tc.function.arguments || "{}"); } catch (e) { bad = true; }
      out.calls.push({ id: tc.id, name: tc.function.name, args: args, bad: bad });
    });
    return out;
  }

  function pushResultsOpenAI(ctx, results) {
    results.forEach(function (r) {
      ctx.history.push({ role: "tool", tool_call_id: r.id, content: r.text });
    });
  }

  // ------------------------------------------------------------ rendu (texte échappé)

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
               '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  }

  function cells(line) {
    return line.trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); });
  }

  // Markdown minimal : titres, listes, tableaux, blocs de code, paragraphes.
  function markdown(src) {
    var lines = String(src).split(/\r?\n/), html = [], i = 0;
    while (i < lines.length) {
      var l = lines[i];
      if (/^```/.test(l)) {
        var code = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
        i++; html.push("<pre>" + esc(code.join("\n")) + "</pre>"); continue;
      }
      if (/^\s*\|.*\|\s*$/.test(l)) {
        var rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(lines[i++]);
        var head = cells(rows[0]), body = rows.slice(1).filter(function (r) { return !/^\s*\|[\s:|-]+\|\s*$/.test(r); });
        html.push('<div class="tablewrap"><table><thead><tr>' +
          head.map(function (c) { return "<th>" + inline(c) + "</th>"; }).join("") + "</tr></thead><tbody>" +
          body.map(function (r) {
            return "<tr>" + cells(r).map(function (c) {
              return (/^[-+]?[\d\s.,]+\s*(%|°C|€)?$/.test(c) ? '<td class="num">' : "<td>") + inline(c) + "</td>";
            }).join("") + "</tr>";
          }).join("") + "</tbody></table></div>");
        continue;
      }
      var h = /^(#{1,4})\s+(.*)$/.exec(l);
      if (h) { html.push("<h4>" + inline(h[2]) + "</h4>"); i++; continue; }
      if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
        var ordered = /^\s*\d+\./.test(l), items = [];
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          items.push("<li>" + inline(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, "")) + "</li>");
        }
        html.push((ordered ? "<ol>" : "<ul>") + items.join("") + (ordered ? "</ol>" : "</ul>"));
        continue;
      }
      if (!l.trim()) { i++; continue; }
      var para = [];
      while (i < lines.length && lines[i].trim() && !/^(```|#{1,4}\s|\s*\||\s*([-*]|\d+\.)\s)/.test(lines[i])) {
        para.push(inline(lines[i++]));
      }
      if (!para.length) para.push(inline(lines[i++]));
      html.push("<p>" + para.join("<br>") + "</p>");
    }
    return html.join("");
  }

  // ------------------------------------------------------------ interface

  var $ = function (id) { return document.getElementById(id); };
  var sel = $("pg-provider"), modelIn = $("pg-model"), keyIn = $("pg-key"), baseIn = $("pg-base"),
      mcpIn = $("pg-mcp"), log = $("pg-log"), q = $("pg-q"), send = $("pg-send"),
      stopBtn = $("pg-stop"), models = $("pg-models"), keyLink = $("pg-keylink"), oauth = $("pg-oauth");

  var DEFAULT_MCP = location.hostname === "nutshell.arcamens.ai"
    ? location.origin + "/mcp" : "https://nutshell.arcamens.ai/mcp";
  var mcp = null, convo = [], convoKind = "", abort = null;

  Object.keys(PROVIDERS).forEach(function (id) {
    var o = document.createElement("option"); o.value = id; o.textContent = PROVIDERS[id].label; sel.appendChild(o);
  });
  sel.value = PROVIDERS[load("provider")] ? load("provider") : "openrouter";
  mcpIn.value = load("mcp") || DEFAULT_MCP;

  function provider() { return PROVIDERS[sel.value]; }

  function refreshProvider() {
    var p = provider();
    modelIn.value = load("model." + sel.value) || p.model;
    keyIn.value = load("key." + sel.value);
    baseIn.value = load("base." + sel.value) || p.base;
    keyIn.placeholder = p.keyOptional ? "(optional)" : "sk-…";
    keyLink.hidden = !p.keyUrl;
    if (p.keyUrl) keyLink.href = p.keyUrl;
    oauth.hidden = sel.value !== "openrouter";
    models.innerHTML = "";
    listModels();
  }

  // Suggestions de modèles depuis /models (silencieux en cas d'échec).
  async function listModels() {
    var p = provider(), key = keyIn.value.trim(), id = sel.value;
    if (!key && !p.keyOptional) return;
    try {
      var r = await fetch(baseIn.value.replace(/\/$/, "") + "/models", { headers: authHeaders(p, key) });
      if (!r.ok || id !== sel.value) return;
      var data = (await r.json()).data || [];
      if (id === "openrouter") {
        data = data.filter(function (m) { return (m.supported_parameters || []).indexOf("tools") >= 0; });
      }
      if (id === "openai") data = data.filter(function (m) { return /^(gpt|o\d)/.test(m.id); });
      models.innerHTML = "";
      data.map(function (m) { return String(m.id).replace(/^models\//, ""); }).sort()
        .forEach(function (m) { var o = document.createElement("option"); o.value = m; models.appendChild(o); });
    } catch (e) { /* suggestions indisponibles */ }
  }

  sel.addEventListener("change", function () { save("provider", sel.value); refreshProvider(); });
  modelIn.addEventListener("change", function () { save("model." + sel.value, modelIn.value.trim()); });
  keyIn.addEventListener("change", function () { save("key." + sel.value, keyIn.value.trim()); listModels(); });
  baseIn.addEventListener("change", function () { save("base." + sel.value, baseIn.value.trim()); listModels(); });
  mcpIn.addEventListener("change", function () { save("mcp", mcpIn.value.trim()); mcp = null; });

  function add(cls, html) {
    var d = document.createElement("div"); d.className = "pg-msg " + cls; d.innerHTML = html;
    log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
  }

  function addTool(call) {
    var d = document.createElement("details"); d.className = "pg-msg pg-tool";
    var args = JSON.stringify(call.args);
    d.innerHTML = "<summary><code>" + esc(call.name) + "</code> <span class=\"pg-args\">" +
      esc(args.length > 90 ? args.slice(0, 90) + "…" : args) + "</span></summary>" +
      "<pre class=\"pg-in\">" + esc(JSON.stringify(call.args, null, 2)) + "</pre><pre class=\"pg-out\">…</pre>";
    log.appendChild(d); log.scrollTop = log.scrollHeight;
    return d;
  }

  function busy(on) {
    send.disabled = on; stopBtn.hidden = !on; q.disabled = on;
  }

  async function ask(text) {
    var p = provider(), key = keyIn.value.trim();
    if (!key && !p.keyOptional) { add("pg-err", esc(T.needKey)); keyIn.focus(); return; }
    if (!text) { add("pg-err", esc(T.needQ)); return; }
    if (convoKind !== p.kind) { convo = []; convoKind = p.kind; }
    add("pg-user", esc(text));
    busy(true);
    abort = new AbortController();
    var wait = add("pg-wait", esc(T.connecting));
    try {
      if (!mcp || mcp.url !== mcpIn.value.trim()) mcp = new Mcp(mcpIn.value.trim());
      try { await mcp.connect(); } catch (e) { throw new ProviderError(T.mcpFail + e.message); }
      wait.textContent = T.thinking;
      var ctx = { p: p, key: key, model: modelIn.value.trim() || p.model,
                  base: baseIn.value.trim().replace(/\/$/, "") || p.base, mcp: mcp, history: convo };
      var step = p.kind === "anthropic" ? stepAnthropic : stepOpenAI;
      var pushResults = p.kind === "anthropic" ? pushResultsAnthropic : pushResultsOpenAI;
      convo.push({ role: "user", content: text });
      for (var turn = 0; ; turn++) {
        if (turn >= 12) { add("pg-err", esc(T.maxTurns)); break; }
        var out = await step(ctx, abort.signal);
        wait.remove();
        out.texts.forEach(function (t) { add("pg-bot", markdown(t)); });
        if (out.refusal) { add("pg-err", esc(T.refusal)); break; }
        if (!out.calls.length) { if (!out.texts.length) add("pg-bot", esc(T.empty)); break; }
        var results = await Promise.all(out.calls.map(async function (c) {
          var box = addTool(c);
          var r = c.bad ? { text: "Arguments JSON invalides.", isError: true } : await mcp.call(c.name, c.args);
          box.querySelector(".pg-out").textContent = r.text;
          if (r.isError) box.classList.add("pg-bad");
          return { id: c.id, text: r.text, isError: r.isError };
        }));
        pushResults(ctx, results);
        wait = add("pg-wait", esc(T.thinking));
        log.appendChild(wait);
      }
    } catch (e) {
      add("pg-err", esc(e.name === "AbortError" ? T.stopped : e.message));
      // Un tour inachevé rendrait l'historique invalide : on repart de zéro.
      convo = [];
    } finally {
      if (wait) wait.remove();
      busy(false); abort = null; q.focus();
    }
  }

  $("pg-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var text = q.value.trim(); q.value = ""; ask(text);
  });
  q.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("pg-form").requestSubmit(); }
  });
  stopBtn.addEventListener("click", function () { if (abort) abort.abort(); });
  $("pg-reset").addEventListener("click", function () { convo = []; log.innerHTML = ""; q.focus(); });
  root.querySelectorAll("button[data-q]").forEach(function (b) {
    b.addEventListener("click", function () { q.value = b.dataset.q; q.focus(); });
  });

  // ------------------------------------------------------------ OpenRouter OAuth (PKCE)

  function b64url(bytes) {
    return btoa(String.fromCharCode.apply(null, new Uint8Array(bytes)))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  oauth.addEventListener("click", async function () {
    var verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
    var challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
    save("pkce", verifier);
    var cb = location.origin + location.pathname;
    location.href = "https://openrouter.ai/auth?callback_url=" + encodeURIComponent(cb) +
      "&code_challenge=" + challenge + "&code_challenge_method=S256";
  });

  async function finishOAuth() {
    var params = new URLSearchParams(location.search), code = params.get("code"), verifier = load("pkce");
    if (!code || !verifier) return;
    save("pkce", "");
    window.history.replaceState(null, "", location.pathname + "#playground");
    try {
      var d = await post("https://openrouter.ai/api/v1/auth/keys", {},
        { code: code, code_verifier: verifier, code_challenge_method: "S256" });
      sel.value = "openrouter"; save("provider", "openrouter");
      save("key.openrouter", d.key); refreshProvider();
      add("pg-bot", esc(T.oauthOk));
    } catch (e) {
      add("pg-err", esc(T.oauthFail + e.message));
    }
    root.scrollIntoView();
  }

  refreshProvider();
  finishOAuth();
})();
