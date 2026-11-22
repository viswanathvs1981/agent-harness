const state = {
  devices: [],
  selected: null,
  demo: false,
  hint: "",
  now: [],
  history: [],
  recommendations: [],
  accessed: [],
  pins: [],
  notes: [],
  shownNotes: {},
};

const groupsEl = document.getElementById("groups");
const nowEl = document.getElementById("now");
const remoteEl = document.getElementById("remote");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const bannerEl = document.getElementById("banner");
const lanEl = document.getElementById("lan");
const nowCardsEl = document.getElementById("now-cards");
const recsEl = document.getElementById("recs");
const accessedEl = document.getElementById("accessed");
const pinsEl = document.getElementById("pins");
const localNoteEl = document.getElementById("local-note");

function say(role, text) {
  const p = document.createElement("p");
  p.className = `msg ${role}`;
  p.textContent = text;
  logEl.appendChild(p);
  logEl.scrollTop = logEl.scrollHeight;
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || response.statusText);
  }
  return data;
}

function groupDevices(devices) {
  const order = ["tv", "speaker", "light", "plug", "hub", "media", "printer", "computer", "other"];
  const grouped = {};
  for (const device of devices) {
    const key = device.kind || "other";
    grouped[key] = grouped[key] || [];
    grouped[key].push(device);
  }
  return order.filter((key) => grouped[key]).map((key) => [key, grouped[key]]);
}

function renderDevices() {
  groupsEl.innerHTML = "";
  if (!state.devices.length) {
    groupsEl.innerHTML = `<p class="meta empty">${state.hint || "Nothing yet. Scan this Wi-Fi."}</p>`;
    return;
  }
  for (const [kind, items] of groupDevices(state.devices)) {
    const wrap = document.createElement("div");
    wrap.className = "group";
    const heading = document.createElement("h2");
    heading.textContent = kind;
    wrap.appendChild(heading);
    items.forEach((device) => {
      const row = document.createElement("div");
      row.className = "device-row";
      const button = document.createElement("button");
      button.className = "device" + (state.selected === device.id ? " active" : "");
      button.type = "button";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = device.name;
      const meta = document.createElement("span");
      meta.className = "meta";
      const app = device.extras && device.extras.app ? ` · ${device.extras.app}` : "";
      meta.textContent = `${device.protocol}${app}`;
      button.appendChild(name);
      button.appendChild(meta);
      button.addEventListener("click", () => select(device.id));
      const movers = document.createElement("div");
      movers.className = "movers";
      const up = document.createElement("button");
      up.type = "button";
      up.className = "ghost tiny";
      up.textContent = "↑";
      up.addEventListener("click", (event) => {
        event.stopPropagation();
        moveDevice(device.id, -1);
      });
      const down = document.createElement("button");
      down.type = "button";
      down.className = "ghost tiny";
      down.textContent = "↓";
      down.addEventListener("click", (event) => {
        event.stopPropagation();
        moveDevice(device.id, 1);
      });
      movers.appendChild(up);
      movers.appendChild(down);
      row.appendChild(button);
      row.appendChild(movers);
      wrap.appendChild(row);
    });
    groupsEl.appendChild(wrap);
  }
}

function selectedDevice() {
  return state.devices.find((item) => item.id === state.selected) || null;
}

function renderStage() {
  const device = selectedDevice();
  if (!device) {
    nowEl.innerHTML = "<p class='kicker'>No device selected</p><h2>Scan, then pick a TV</h2>";
    remoteEl.hidden = true;
    return;
  }
  const power = device.extras && device.extras.power;
  const volume = device.extras && device.extras.volume;
  const title = device.extras && device.extras.title;
  const app = device.extras && device.extras.app;
  const bits = [
    device.manufacturer,
    device.model,
    power === false ? "off" : power ? "on" : "",
    volume != null ? `vol ${volume}` : "",
    app || "",
    title || "",
  ].filter(Boolean);
  nowEl.innerHTML = "";
  const kicker = document.createElement("p");
  kicker.className = "kicker";
  kicker.textContent = `${device.kind} · ${device.protocol}`;
  const heading = document.createElement("h2");
  heading.textContent = device.name;
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = bits.join(" · ");
  nowEl.appendChild(kicker);
  nowEl.appendChild(heading);
  nowEl.appendChild(meta);
  remoteEl.hidden = false;
  for (const button of remoteEl.querySelectorAll("[data-action]")) {
    const action = button.getAttribute("data-action");
    const allowed = !device.capabilities.length || device.capabilities.includes(action);
    button.disabled = !allowed;
  }
  renderPins();
}

function renderPins() {
  pinsEl.innerHTML = "";
  for (const app of state.pins) {
    const wrap = document.createElement("div");
    wrap.className = "pin";
    const launch = document.createElement("button");
    launch.type = "button";
    launch.textContent = app;
    launch.addEventListener("click", () => command("launch", app).catch(showError));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost tiny";
    remove.textContent = "×";
    remove.addEventListener("click", () => unpin(app));
    wrap.appendChild(launch);
    wrap.appendChild(remove);
    pinsEl.appendChild(wrap);
  }
}

function renderWatching() {
  nowCardsEl.innerHTML = "";
  if (!state.now.length) {
    const empty = document.createElement("p");
    empty.className = "meta";
    empty.textContent = "Waiting for a TV to report what’s on.";
    nowCardsEl.appendChild(empty);
    return;
  }
  for (const item of state.now) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "now-card" + (state.selected === item.device_id ? " active" : "");
    const kicker = document.createElement("p");
    kicker.className = "kicker";
    kicker.textContent = `${item.device_name} · ${item.state}`;
    const title = document.createElement("strong");
    title.textContent = item.title || item.app;
    const app = document.createElement("p");
    app.className = "meta";
    app.textContent = item.app;
    card.appendChild(kicker);
    card.appendChild(title);
    card.appendChild(app);
    card.addEventListener("click", () => select(item.device_id));
    nowCardsEl.appendChild(card);
  }
}

function renderRecs() {
  recsEl.innerHTML = "";
  if (!state.recommendations.length) {
    recsEl.innerHTML = "<p class='meta'>Watch something and I will suggest a follow-up.</p>";
    return;
  }
  for (const rec of state.recommendations) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rec";
    const name = document.createElement("strong");
    name.textContent = rec.app;
    const reason = document.createElement("span");
    reason.className = "meta";
    reason.textContent = rec.reason;
    button.appendChild(name);
    button.appendChild(reason);
    button.addEventListener("click", () => {
      if (rec.device_id) select(rec.device_id);
      command("launch", rec.app).catch(showError);
    });
    recsEl.appendChild(button);
  }
}

function renderAccessed() {
  accessedEl.innerHTML = "";
  if (!state.accessed.length) {
    accessedEl.innerHTML = "<p class='meta'>Nothing accessed yet this session.</p>";
    return;
  }
  for (const row of state.accessed) {
    const p = document.createElement("p");
    p.className = "access";
    p.textContent = `${row.app} · ${row.count} time${row.count === 1 ? "" : "s"}`;
    accessedEl.appendChild(p);
  }
}

function select(id) {
  state.selected = id;
  renderDevices();
  renderStage();
  renderWatching();
}

function updateBanner() {
  const show = Boolean(state.hint) && (state.demo || !state.devices.length);
  bannerEl.classList.toggle("hidden", !show);
  bannerEl.textContent = state.hint || "";
}

function applyDashboard(data) {
  state.now = data.now || [];
  state.history = data.history || [];
  state.recommendations = data.recommendations || [];
  state.accessed = data.accessed || [];
  state.pins = data.pins || [];
  state.notes = data.notes || [];
  for (const item of state.now) {
    const device = state.devices.find((row) => row.id === item.device_id);
    if (!device) continue;
    device.extras = device.extras || {};
    device.extras.app = item.app;
    if (item.title) device.extras.title = item.title;
    device.extras.watch_state = item.state;
  }
  for (const note of state.notes) {
    if (state.shownNotes[note]) continue;
    state.shownNotes[note] = true;
    say("agent", note);
  }
  renderWatching();
  renderRecs();
  renderAccessed();
  renderDevices();
  renderStage();
}

async function refreshHealth() {
  const health = await api("/api/health");
  state.demo = health.demo;
  state.hint = health.hint || "";
  lanEl.textContent = health.lan_ip
    ? `This machine: ${health.lan_ip}`
    : "No private LAN address on this host";
  const brainEl = document.getElementById("brain");
  if (brainEl) {
    brainEl.textContent =
      health.brain === "claude"
        ? `Agent: Claude (${health.model || "sonnet"})`
        : "Agent: local rules — restart from Terminal; it will ask for the Claude key";
  }
  updateBanner();
}

async function loadDevices() {
  const data = await api("/api/devices");
  state.devices = data.devices || [];
  localNoteEl.hidden = state.devices.length > 0;
  if (state.selected && !state.devices.some((item) => item.id === state.selected)) {
    state.selected = null;
  }
  if (!state.selected) {
    const tv = state.devices.find((item) => item.kind === "tv");
    state.selected = (tv || state.devices[0] || {}).id || null;
  }
  renderDevices();
  renderStage();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  applyDashboard(data);
}

async function scan(deep) {
  statusEl.textContent = deep ? "Deep scanning…" : "Scanning Wi-Fi…";
  const data = await api("/api/scan", {
    method: "POST",
    body: JSON.stringify({ deep: Boolean(deep) }),
  });
  state.devices = data.devices || [];
  state.hint = data.hint || state.hint;
  localNoteEl.hidden = state.devices.length > 0;
  if (!state.selected && state.devices[0]) {
    state.selected = state.devices[0].id;
  }
  renderDevices();
  renderStage();
  updateBanner();
  statusEl.textContent = `${state.devices.length} device${state.devices.length === 1 ? "" : "s"}`;
  if (!state.devices.length && state.hint) {
    say("agent", state.hint);
  }
  await loadDashboard();
}

async function command(action, value) {
  const device = selectedDevice();
  if (!device) {
    statusEl.textContent = "Pick a device first.";
    return;
  }
  const result = await api(`/api/devices/${encodeURIComponent(device.id)}/command`, {
    method: "POST",
    body: JSON.stringify({ action, value }),
  });
  statusEl.textContent = result.message;
  await loadDevices();
  await loadDashboard();
}

async function chat(text) {
  say("user", text);
  const result = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message: text, device_id: state.selected }),
  });
  say("agent", result.reply);
  await loadDevices();
  await loadDashboard();
  if (result.device_ids && result.device_ids.length === 1) {
    select(result.device_ids[0]);
  }
}

async function unpin(app) {
  const pins = state.pins.filter((item) => item !== app);
  const data = await api("/api/layout", {
    method: "PUT",
    body: JSON.stringify({ pins }),
  });
  state.pins = data.pins || pins;
  renderPins();
}

async function moveDevice(id, delta) {
  const ids = state.devices.map((item) => item.id);
  const index = ids.indexOf(id);
  const next = index + delta;
  if (index < 0 || next < 0 || next >= ids.length) return;
  ids.splice(next, 0, ids.splice(index, 1)[0]);
  const data = await api("/api/layout", {
    method: "PUT",
    body: JSON.stringify({ device_order: ids }),
  });
  const order = data.device_order || ids;
  state.devices.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  renderDevices();
}

document.getElementById("scan").addEventListener("click", () => scan(false).catch(showError));
document.getElementById("deep").addEventListener("click", () => scan(true).catch(showError));
document.getElementById("ask").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("prompt");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  chat(text).catch(showError);
});
document.getElementById("pin-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("pin-app");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  chat(text.startsWith("pin ") ? text : `pin ${text}`).catch(showError);
});
remoteEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  command(button.getAttribute("data-action"), button.getAttribute("data-value")).catch(showError);
});

window.addEventListener("keydown", (event) => {
  if (event.target && event.target.tagName === "INPUT") return;
  const map = {
    ArrowUp: "up",
    ArrowDown: "down",
    ArrowLeft: "left",
    ArrowRight: "right",
    Enter: "select",
    Escape: "back",
    m: "mute",
    " ": "pause",
  };
  const action = map[event.key];
  if (!action) return;
  event.preventDefault();
  command(action).catch(showError);
});

function showError(error) {
  statusEl.textContent = error.message;
  say("agent", error.message);
}

refreshHealth()
  .then(loadDevices)
  .then(() => {
    if (!state.devices.length) {
      return scan(false);
    }
    return loadDashboard();
  })
  .then(() => {
    setInterval(() => loadDashboard().catch(() => {}), 5000);
  })
  .catch(showError);
