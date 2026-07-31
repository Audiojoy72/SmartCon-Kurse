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
      const hint = c.hint ? `<span class="hint">→ ${c.hint}</span>` : "";
      li.innerHTML =
        `<span class="punkt ${c.status}"></span>` +
        `<span><span class="name">${c.name}</span><br>` +
        `<span class="detail">${c.detail || ""}</span>${hint}</span>`;
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
  form.whisper_command.value = cfg.whisper_command;
}

document.getElementById("settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const cfg = {
    backend: form.backend.value,
    default_design_md: form.default_design_md.value.trim(),
    whisper_command: form.whisper_command.value.trim() || "whisper",
  };
  await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  const s = document.getElementById("settings-status");
  s.textContent = "Gespeichert.";
  setTimeout(() => (s.textContent = ""), 2500);
  ladeAmpel();
});

ladeAmpel();
ladeSettings();
