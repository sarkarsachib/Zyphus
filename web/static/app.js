/* Zyphus, in the room with you.
 *
 * The dashboard is a viewing surface: it reads /api/agent (read-only), plays the
 * utterances he produces on his own, and drives him through the one gated
 * endpoint the engine exposes (/api/agent/task, X-Zyphus-Token).
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const face = new window.EvilFace($("face"));
  const mist = new window.Mist($("mist"));
  const audio = $("voice-audio");
  const input = $("say-input");

  const state = {
    token: localStorage.getItem("zyphus.token") || "",
    agent: null,
    substrate: null,
    capabilities: null,
    memory: null,
    substrateAt: 0,
    panel: null,
    lastUtterance: null,
    seeded: false,
    speaking: false,
    speakingUntil: 0,
    lastResult: "",
    busy: false,
  };

  const EPITHET = {
    diffuse: "diffuse · reading the field",
    structural: "structural · composing a plan",
    convergent: "convergent · committing to act",
  };

  /* ── pointer ───────────────────────────────────────────────────────── */
  window.addEventListener("pointermove", (e) => {
    const nx = (e.clientX / window.innerWidth) * 2 - 1;
    const ny = (e.clientY / window.innerHeight) * 2 - 1;
    face.setPointer(nx, ny);
    mist.setPointer(nx, ny);
  });

  /* ── audio: real amplitude when the browser lets us have it ────────── */
  let audioCtx = null;
  let analyser = null;
  let wave = null;

  function unlockAudio() {
    if (audioCtx) {
      if (audioCtx.state === "suspended") audioCtx.resume();
      return;
    }
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaElementSource(audio);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      wave = new Uint8Array(analyser.fftSize);
      source.connect(analyser);
      analyser.connect(audioCtx.destination);
    } catch (err) {
      audioCtx = null;
      analyser = null;
    }
  }
  window.addEventListener("pointerdown", unlockAudio, { passive: true });
  window.addEventListener("keydown", unlockAudio);

  /** Mouth motion per frame: measured when possible, acted when not. */
  function driveMouth(ts) {
    let level = 0;
    if (state.speaking) {
      if (analyser) {
        analyser.getByteTimeDomainData(wave);
        let sum = 0;
        for (let i = 0; i < wave.length; i++) {
          const d = (wave[i] - 128) / 128;
          sum += d * d;
        }
        const rms = Math.sqrt(sum / wave.length);
        level = Math.min(1, rms * 5.2);
      } else {
        const t = ts / 1000;
        level = 0.34 + 0.3 * Math.abs(Math.sin(t * 7.4) * Math.sin(t * 2.3 + 0.7));
      }
      if (Math.random() < 0.06) level *= 0.35;
    }
    const target = state.speaking ? level : 0;
    face.setVoice(face.voice + (target - face.voice) * 0.4);
    requestAnimationFrame(driveMouth);
  }
  requestAnimationFrame(driveMouth);

  /* ── caption ───────────────────────────────────────────────────────── */
  let typing = null;
  function setCaption(text, speaking) {
    const node = $("caption");
    node.classList.toggle("speaking", Boolean(speaking));
    clearInterval(typing);
    const full = String(text || "");
    if (!full) { node.textContent = ""; return; }
    let i = 0;
    node.textContent = "";
    typing = setInterval(() => {
      i += 2;
      node.textContent = full.slice(0, i);
      if (i >= full.length) clearInterval(typing);
    }, 26);
  }

  function endSpeech() {
    state.speaking = false;
    face.setSpeaking(false);
    $("caption").classList.remove("speaking");
    try { audio.pause(); } catch (e) { /* nothing to stop */ }
  }

  function speak(file, text, seconds) {
    state.speaking = true;
    face.setSpeaking(true);
    setCaption(text || "…", true);  // no logged words: show him breathing, not old text
    const url = "/api/agent/voice/" + file;
    if (audio.getAttribute("src") !== url) audio.src = url;
    audio.currentTime = 0;
    const played = audio.play();
    if (played && played.catch) {
      played.catch(() => {
        // autoplay refused: keep the mouth moving for the utterance's length
        state.speakingUntil = Date.now() + Math.max(1200, (seconds || 3) * 1000);
      });
    }
  }

  audio.addEventListener("ended", endSpeech);
  audio.addEventListener("error", () => { if (state.speaking) endSpeech(); });
  setInterval(() => {
    if (state.speaking && state.speakingUntil && Date.now() > state.speakingUntil) endSpeech();
  }, 400);

  /** The words behind an utterance: the speak call logged closest to the wav. */
  function spokenTextFor(file, agent) {
    const match = /^voice-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})\.wav$/.exec(file || "");
    const at = match
      ? new Date(+match[1], +match[2] - 1, +match[3], +match[4], +match[5], +match[6]).getTime()
      : NaN;
    let best = "";
    let bestDelta = Infinity;
    (agent.recent_actions || []).filter((a) => a.tool === "speak").forEach((a) => {
      const text = String((a.arguments || {}).text || "");
      if (!text) return;
      const logged = Date.parse(String(a.created_at || "").replace(" ", "T"));
      const delta = Number.isNaN(at) || Number.isNaN(logged) ? 0 : Math.abs(logged - at);
      if (delta < bestDelta) { bestDelta = delta; best = text; }
    });
    return bestDelta <= 15000 ? best : "";
  }

  function onVoice(agent) {
    const latest = (agent.voice || {}).latest;
    if (!state.seeded) {
      state.seeded = true;
      state.lastUtterance = latest ? latest.file : null;
      return;
    }
    if (!latest || latest.file === state.lastUtterance) return;
    state.lastUtterance = latest.file;
    speak(latest.file, spokenTextFor(latest.file, agent), latest.seconds);
  }

  /* ── data ──────────────────────────────────────────────────────────── */
  async function getJSON(url) {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    const data = await res.json().catch(() => ({ error: "unreadable response" }));
    if (!res.ok && !data.error) data.error = "HTTP " + res.status;
    return data;
  }

  function setHint(text, bad) {
    const node = $("hint");
    node.textContent = text || "";
    node.classList.toggle("bad", Boolean(bad));
  }

  function renderTelemetry(agent) {
    const running = Boolean(agent.running);
    $("dot-loop").classList.toggle("live", running);
    $("t-state").textContent = running ? "awake" : "dormant";
    $("t-ticks").textContent = String(agent.ticks ?? "—");
    const regime = (agent.field || {}).regime || "—";
    $("t-regime").textContent = regime;
    face.setRegime(regime);
    $("epithet").textContent = EPITHET[regime] || "adaptive cognitive substrate";
    const q = agent.queue || {};
    $("t-queue").textContent = String((q.pending || 0) + (q.running || 0));
    const pulse = (agent.vitals || {}).pulse || {};
    $("t-rhythm").textContent = pulse.available === false
      ? "—"
      : `${pulse.rhythm || "—"} ${pulse.rate_hz ?? ""}hz`;
  }

  async function pollAgent() {
    try {
      const agent = await getJSON("/api/agent");
      if (agent.available === false) {
        setHint(agent.error || "agent layer not loaded", true);
        return;
      }
      state.agent = agent;
      renderTelemetry(agent);
      onVoice(agent);
      if (state.panel) renderPanel();
      if (!state.busy) {
        const armed = (agent.control || {}).configured;
        setHint(armed
          ? (state.token ? "remote control armed" : "remote control armed · paste your key to transmit")
          : "remote control off on the server", !armed);
      }
    } catch (err) {
      setHint("no signal from the engine — retrying", true);
    }
  }

  async function openPanel(name) {
    if (state.panel === name) { closePanel(); return; }
    state.panel = name;
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.panel === name));
    $("drawer").hidden = false;
    if (name === "memory") state.memory = await getJSON("/api/agent/memory");
    if (name === "mind") await loadMind();
    if (name === "body" && !state.agent) await pollAgent();
    renderPanel();
  }

  function closePanel() {
    state.panel = null;
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    $("drawer").hidden = true;
    $("drawer").innerHTML = "";
  }

  async function loadMind() {
    if (Date.now() - state.substrateAt < 15000 && state.substrate) return;
    state.substrate = await getJSON("/api/substrate");
    state.capabilities = await getJSON("/api/capabilities");
    state.substrateAt = Date.now();
  }

  /* ── drawer rendering ──────────────────────────────────────────────── */
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function card(name, meta, body) {
    const box = el("div", "card");
    box.appendChild(el("div", "name", name));
    if (meta) box.appendChild(el("div", "meta", meta));
    if (body) box.appendChild(el("div", "body", body));
    return box;
  }

  function bars(entries) {
    const wrap = el("div", "bars");
    entries.forEach(([label, value, display]) => {
      const row = el("div", "bar");
      row.appendChild(el("span", "", label));
      const track = el("div", "track");
      const fill = el("div", "fill");
      fill.style.width = Math.round(Math.max(0, Math.min(1, value)) * 100) + "%";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("b", "", display));
      wrap.appendChild(row);
    });
    return wrap;
  }

  function rows(entries) {
    const wrap = el("div", "rows");
    entries.forEach(([key, value]) => {
      const row = el("div", "row");
      row.appendChild(el("span", "key", key));
      row.appendChild(el("span", "", String(value)));
      wrap.appendChild(row);
    });
    return wrap;
  }

  function renderPanel() {
    const drawer = $("drawer");
    if (!state.panel) return;
    drawer.innerHTML = "";
    const agent = state.agent || {};
    const field = agent.field || {};
    const vitals = agent.vitals || {};

    if (state.panel === "tools") {
      drawer.appendChild(el("h3", "", "tools he can reach"));
      const grid = el("div", "grid");
      (agent.tools || []).forEach((tool) => {
        const box = card(tool.name, Object.keys(tool.parameters || {}).length
          ? Object.keys(tool.parameters).join(" · ")
          : "no parameters", tool.description);
        box.setAttribute("role", "button");
        box.setAttribute("tabindex", "0");
        box.addEventListener("click", () => {
          input.value = "tool " + tool.name + " ";
          input.focus();
          setHint("argument json ready for " + tool.name);
        });
        grid.appendChild(box);
      });
      drawer.appendChild(grid);
      return;
    }

    if (state.panel === "agents") {
      drawer.appendChild(el("h3", "", "the queue"));
      const q = agent.queue || {};
      drawer.appendChild(rows([
        ["awake", agent.running ? "yes · " + agent.ticks + " ticks" : "no"],
        ["brain", agent.brain || "—"],
        ["pending", q.pending || 0],
        ["running", q.running || 0],
        ["done", q.done || 0],
        ["failed", q.failed || 0],
        ["tick", Math.round(agent.interval_seconds || 0) + "s"],
      ]));
      drawer.appendChild(el("h3", "", "working now"));
      const pending = agent.pending_tasks || [];
      const now = el("div", "grid");
      if (!pending.length) now.appendChild(card("idle", "", "nothing claimed; he will invent work on the next self-tick"));
      pending.forEach((t) => now.appendChild(card(t.title || t.id, t.status, t.id)));
      drawer.appendChild(now);
      drawer.appendChild(el("h3", "", "last actions"));
      const actions = el("div", "rows");
      (agent.recent_actions || []).slice(0, 12).forEach((a) => {
        const row = el("div", "row");
        row.appendChild(el("span", "key", a.tool));
        row.appendChild(el("span", "body", (a.created_at ? a.created_at + " · " : "")
          + String(a.error || a.output || "").slice(0, 160)));
        actions.appendChild(row);
      });
      drawer.appendChild(actions);
      if (state.lastResult) {
        drawer.appendChild(el("h3", "", "last transmission"));
        const log = el("div", "log");
        log.textContent = state.lastResult;
        drawer.appendChild(log);
      }
      return;
    }

    if (state.panel === "mind") {
      drawer.appendChild(el("h3", "", "cognitive field"));
      const activations = field.activations || {};
      drawer.appendChild(bars(Object.entries(activations).map(([k, v]) => [k, v, Number(v).toFixed(2)])));
      const winning = field.winning_coalition || [];
      drawer.appendChild(rows([
        ["regime", field.regime || "—"],
        ["coalition", winning.length ? winning.slice(0, 6).join(", ") : "—"],
        ["cells", field.cell_count ?? "—"],
        ["dominance", field.dominance ?? "—"],
        ["steps", field.steps ?? "—"],
      ]));
      const substrate = state.substrate || {};
      if (substrate.error) drawer.appendChild(el("div", "note", "substrate: " + substrate.error));
      const last = substrate.last || {};
      if (last && (last.goal || last.nodes)) {
        drawer.appendChild(el("h3", "", "last structure"));
        drawer.appendChild(rows([
          ["goal", last.goal || "—"],
          ["class", last.klass || "—"],
          ["nodes", (last.nodes || []).length],
        ]));
        const grid = el("div", "grid");
        (last.nodes || []).slice(0, 8).forEach((n) => {
          grid.appendChild(card(n.primitive || n.name || "unit", n.status || "", n.produces ? "produces " + n.produces : ""));
        });
        drawer.appendChild(grid);
      }
      const world = substrate.world || {};
      if (Object.keys(world).length) {
        drawer.appendChild(el("h3", "", "world model"));
        drawer.appendChild(rows(Object.entries(world).slice(0, 6).map(([k, v]) => [k.replace(/_/g, " "), v])));
      }
      const caps = state.capabilities || {};
      if (!caps.error) {
        drawer.appendChild(el("h3", "", "reach"));
        drawer.appendChild(rows([
          ["models", (caps.models || []).length + " · active " + (caps.active_model || "env default")],
          ["apis", (caps.apis || []).length],
          ["connectors", (caps.connectors || []).length],
          ["index", ((caps.rag || {}).chunks ?? 0) + " chunks"],
        ]));
      }
      return;
    }

    if (state.panel === "body") {
      const pulse = vitals.pulse || {};
      drawer.appendChild(el("h3", "", "body"));
      drawer.appendChild(rows([
        ["rhythm", pulse.available === false ? "unavailable" : `${pulse.rhythm || "—"} · ${pulse.rate_hz ?? "—"} hz`],
        ["meaning", pulse.rhythm_meaning || "—"],
        ["mood", (vitals.mood || {}).label || "—"],
        ["load", vitals.load ?? "—"],
      ]));
      if (pulse.available !== false) {
        drawer.appendChild(bars([
          ["energy", pulse.energy ?? 0, Number(pulse.energy ?? 0).toFixed(2)],
          ["stress", pulse.stress ?? 0, Number(pulse.stress ?? 0).toFixed(2)],
          ["coherence", pulse.coherence ?? 0, Number(pulse.coherence ?? 0).toFixed(2)],
        ]));
      }
      const links = vitals.links || [];
      if (links.length) {
        drawer.appendChild(el("h3", "", "engine links"));
        const grid = el("div", "grid");
        links.forEach((l) => grid.appendChild(card(l.module, l.status === "linked" ? "linked" : "off", "")));
        drawer.appendChild(grid);
      }
      return;
    }

    if (state.panel === "memory") {
      drawer.appendChild(el("h3", "", "persistent memory"));
      const entries = (state.memory || {}).entries || [];
      if (!entries.length) drawer.appendChild(el("div", "note", "memory is empty"));
      const grid = el("div", "grid");
      entries.forEach((e) => grid.appendChild(card(e.key, (e.tag ? "[" + e.tag + "] " : "") + (e.created_at || ""), e.value)));
      drawer.appendChild(grid);
      return;
    }

    if (state.panel === "key") {
      drawer.appendChild(el("h3", "", "control key"));
      const box = el("div", "card");
      const field = el("input", "text");
      field.type = "password";
      field.placeholder = "ZYPHUS_CONTROL_TOKEN";
      field.value = state.token;
      box.appendChild(field);
      const save = el("button", "btn primary", "save key");
      save.type = "button";
      save.style.marginTop = "10px";
      save.addEventListener("click", () => {
        state.token = field.value.trim();
        if (state.token) localStorage.setItem("zyphus.token", state.token);
        else localStorage.removeItem("zyphus.token");
        setHint(state.token ? "key held in this browser" : "key cleared");
        closePanel();
      });
      box.appendChild(save);
      drawer.appendChild(box);
      drawer.appendChild(el("div", "note",
        "Only POST /api/agent/task runs tools, and only for a caller holding the control token. "
        + "The key stays in this browser (localStorage) and is sent as X-Zyphus-Token. "
        + "Speaking and the queue are read-only without it."));
      return;
    }
  }

  /* ── driving him ───────────────────────────────────────────────────── */
  async function runTask(instruction) {
    if (state.busy) return;
    if (!state.token) {
      setHint("no key — open key and paste the control token", true);
      openPanel("key");
      return;
    }
    state.busy = true;
    $("transmit").disabled = true;
    $("voice-btn").disabled = true;
    setHint("transmitting…");
    try {
      const res = await fetch("/api/agent/task", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Zyphus-Token": state.token },
        body: JSON.stringify({ instructions: instruction }),
      });
      const data = await res.json().catch(() => ({ error: "unreadable response" }));
      if (!res.ok || data.error) {
        state.lastResult = data.error || "HTTP " + res.status;
        setHint(state.lastResult, true);
      } else {
        state.lastResult = String(data.output || data.thought || JSON.stringify(data, null, 2)).slice(0, 4000);
        setHint("done · " + (data.action || "executed"));
        setCaption(state.lastResult.split("\n")[0].slice(0, 220), false);
      }
      if (state.panel) renderPanel();
      setTimeout(pollAgent, 700);
      setTimeout(pollAgent, 2600);
    } catch (err) {
      setHint("transmission failed: " + err.message, true);
    } finally {
      state.busy = false;
      $("transmit").disabled = false;
      $("voice-btn").disabled = false;
    }
  }

  $("say").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    runTask(text);
  });

  $("voice-btn").addEventListener("click", () => {
    const text = input.value.trim();
    input.value = "";
    runTask(text ? "say: " + text : "self:voice");
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => openPanel(tab.dataset.panel));
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.panel) closePanel();
  });

  /* ── boot ──────────────────────────────────────────────────────────── */
  setHint("establishing link…");
  pollAgent();
  setInterval(pollAgent, 5000);
})();
