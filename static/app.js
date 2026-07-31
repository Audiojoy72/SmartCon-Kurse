"use strict";

// Tabs
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("aktiv"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("aktiv"));
    btn.classList.add("aktiv");
    document.getElementById("view-" + btn.dataset.tab).classList.add("aktiv");
  });
});

// Preflight-Ampel
async function ladeAmpel() {
  const liste = document.getElementById("ampel-liste");
  liste.innerHTML = "<li class='muted'>Prüfe … (dauert wenige Sekunden)</li>";
  try {
    const res = await fetch("/api/preflight");
    const data = await res.json();
    liste.innerHTML = "";
    for (const c of data.checks) {
      const li = document.createElement("li");
      if (c.anleitung) li.classList.add("aufklappbar");
      const hint = c.hint ? `<span class="hint">→ ${c.hint}</span>` : "";
      li.innerHTML =
        `<span class="punkt ${c.status}"></span>` +
        `<span class="inhalt"><span class="name">${c.name}</span><br>` +
        `<span class="detail">${c.detail || ""}</span>${hint}` +
        (c.anleitung ? `<pre class="anleitung">${c.anleitung}</pre>` : "") +
        `</span>`;
      if (c.anleitung) {
        li.title = "Anklicken für die Anleitung";
        li.addEventListener("click", () => li.classList.toggle("offen"));
      }
      liste.appendChild(li);
    }
  } catch (e) {
    liste.innerHTML = `<li><span class="punkt fail"></span>
      <span class="name">Backend nicht erreichbar: ${e}</span></li>`;
  }
}
document.getElementById("btn-recheck").addEventListener("click", ladeAmpel);

// Einstellungen
async function ladeSettings() {
  const cfg = await (await fetch("/api/config")).json();
  const form = document.getElementById("settings-form");
  form.backend.value = cfg.backend;
  form.default_design_md.value = cfg.default_design_md;
  form.whisper_modus.value = cfg.whisper_modus || "lokal";
  form.whisper_command.value = cfg.whisper_command;
  form.whisper_api_url.value = cfg.whisper_api_url || "";
  form.whisper_api_key.value = cfg.whisper_api_key || "";
  form.whisper_api_model.value = cfg.whisper_api_model || "whisper-1";
  form.cf_access_client_id.value = cfg.cf_access_client_id || "";
  form.cf_access_client_secret.value = cfg.cf_access_client_secret || "";
  form.lan_erreichbar.checked = !!cfg.lan_erreichbar;
  whisperSichtbarkeit();
}

function whisperSichtbarkeit() {
  const modus = document.querySelector('[name="whisper_modus"]').value;
  document.querySelectorAll(".whisper-lokal").forEach(
    (el) => (el.style.display = modus === "lokal" ? "" : "none"));
  document.querySelectorAll(".whisper-api").forEach(
    (el) => (el.style.display = modus === "api" ? "" : "none"));
}
document.querySelector('[name="whisper_modus"]').addEventListener("change", whisperSichtbarkeit);
document.getElementById("btn-openrouter").addEventListener("click", () => {
  document.querySelector('[name="whisper_api_url"]').value = "https://openrouter.ai/api/v1";
});

document.getElementById("settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const cfg = {
    backend: form.backend.value,
    default_design_md: form.default_design_md.value.trim(),
    whisper_modus: form.whisper_modus.value,
    whisper_command: form.whisper_command.value.trim() || "whisper",
    whisper_api_url: form.whisper_api_url.value.trim(),
    whisper_api_key: form.whisper_api_key.value.trim(),
    whisper_api_model: form.whisper_api_model.value.trim() || "whisper-1",
    cf_access_client_id: form.cf_access_client_id.value.trim(),
    cf_access_client_secret: form.cf_access_client_secret.value.trim(),
    lan_erreichbar: form.lan_erreichbar.checked,
  };
  await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  const s = document.getElementById("settings-status");
  s.textContent = "Gespeichert. (LAN-Erreichbarkeit greift nach Neustart der App.)";
  setTimeout(() => (s.textContent = ""), 4000);
  ladeAmpel();
});

ladeAmpel();
ladeSettings();
