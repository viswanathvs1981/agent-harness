const state = {
  devices: [],
  selected: null,
  demo: false,
  hint: "",
};

const groupsEl = document.getElementById("groups");
const nowEl = document.getElementById("now");
const remoteEl = document.getElementById("remote");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const bannerEl = document.getElementById("banner");
const lanEl = document.getElementById("lan");

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
    wrap.innerHTML = `<h2>${kind}</h2>`;
    for (const device of items) {
      const button = document.createElement("button");
      button.className = "device" + (state.selected === device.id ? " active" : "");
      button.type = "button";
      button.innerHTML = `<span class="name">${device.name}</span><span class="meta">${device.address} · ${device.protocol}</span>`;
      button.addEventListener("click", () => select(device.id));
      wrap.appendChild(button);
    }
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
  const bits = [
    device.manufacturer,
    device.model,
    power === false ? "off" : power ? "on" : "",
    volume != null ? `vol ${volume}` : "",
  ].filter(Boolean);
  nowEl.innerHTML = `<p class="kicker">${device.kind} · ${device.protocol}</p><h2>${device.name}</h2><p class="meta">${bits.join(" · ")}</p>`;
  remoteEl.hidden = false;
  for (const button of remoteEl.querySelectorAll("[data-action]")) {
    const action = button.getAttribute("data-action");
    const allowed = !device.capabilities.length || device.capabilities.includes(action);
    button.disabled = !allowed;
  }
}

function select(id) {
  state.selected = id;
  renderDevices();
  renderStage();
}

function updateBanner() {
  const show = Boolean(state.hint) && (state.demo || !state.devices.length);
  bannerEl.classList.toggle("hidden", !show);
  bannerEl.textContent = state.hint || "";
}

async function refreshHealth() {
  const health = await api("/api/health");
  state.demo = health.demo;
  state.hint = health.hint || "";
  lanEl.textContent = health.lan_ip
    ? `This machine: ${health.lan_ip}`
    : "No private LAN address on this host";
  updateBanner();
}

async function loadDevices() {
  const data = await api("/api/devices");
  state.devices = data.devices || [];
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

async function scan(deep) {
  statusEl.textContent = deep ? "Deep scanning…" : "Scanning Wi-Fi…";
  const data = await api("/api/scan", {
    method: "POST",
    body: JSON.stringify({ deep: Boolean(deep) }),
  });
  state.devices = data.devices || [];
  state.hint = data.hint || state.hint;
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
}

async function chat(text) {
  say("user", text);
  const result = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message: text }),
  });
  say("agent", result.reply);
  await loadDevices();
  if (result.device_ids && result.device_ids.length === 1) {
    select(result.device_ids[0]);
  }
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
    return null;
  })
  .catch(showError);
