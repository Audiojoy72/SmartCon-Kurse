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

// ==========================================================================
// Projekte
// ==========================================================================

const PHASEN_LABEL = {
  briefing: "Briefing",
  curriculum_laeuft: "Curriculum läuft …",
  curriculum_fertig: "Curriculum fertig",
  fehler: "Fehler",
};

let aktuellerSlug = null;
let eventQuelle = null;

function zeigePanel(id) {
  ["pv-liste", "pv-formular", "pv-detail"].forEach((p) => {
    document.getElementById(p).hidden = p !== id;
  });
}

function badge(phase) {
  return `<span class="badge phase-${phase}">${PHASEN_LABEL[phase] || phase}</span>`;
}

async function ladeProjekte() {
  const box = document.getElementById("projekt-liste");
  try {
    const data = await (await fetch("/api/projekte")).json();
    if (!data.projekte.length) {
      box.innerHTML = "<p class='muted'>Noch keine Projekte — „Neue Schulung“ legt das erste an.</p>";
      return;
    }
    box.innerHTML = "";
    for (const p of data.projekte) {
      const karte = document.createElement("div");
      karte.className = "projekt-karte";
      const datum = p.geaendert_am ? p.geaendert_am.slice(0, 16).replace("T", " ") : "";
      karte.innerHTML =
        `<div class="pk-titel">${p.thema || p.slug}</div>` +
        `<div class="pk-meta">${badge(p.phase)} <span class="muted">${datum} UTC</span></div>`;
      karte.addEventListener("click", () => oeffneProjekt(p.slug));
      box.appendChild(karte);
    }
  } catch (e) {
    box.innerHTML = `<p class="muted">Projektliste nicht ladbar: ${e}</p>`;
  }
}

// --- Formular -------------------------------------------------------------

async function ladePresets() {
  const box = document.getElementById("preset-karten");
  try {
    const data = await (await fetch("/api/presets")).json();
    box.innerHTML = "";
    for (const [i, p] of data.presets.entries()) {
      const karte = document.createElement("label");
      karte.className = "preset-karte";
      karte.innerHTML =
        `<input type="radio" name="stil" value="${p.name}" ${i === 0 ? "checked" : ""}>` +
        `<span class="pk-name">${p.titel}</span>` +
        `<span class="pk-beschr">${p.beschreibung}</span>` +
        (p.kosten ? `<span class="pk-kosten">${p.kosten}</span>` : "");
      box.appendChild(karte);
    }
    const eigene = document.createElement("label");
    eigene.className = "preset-karte";
    eigene.innerHTML =
      `<input type="radio" name="stil" value="design">` +
      `<span class="pk-name">Eigene design.md</span>` +
      `<span class="pk-beschr">Vollständig eigene Design-Vorgabe — die Datei wird hochgeladen und ersetzt das Preset.</span>`;
    box.appendChild(eigene);
    box.querySelectorAll('input[name="stil"]').forEach((r) =>
      r.addEventListener("change", () => {
        document.getElementById("design-upload-wrap").hidden =
          box.querySelector('input[name="stil"]:checked').value !== "design";
      }));
  } catch (e) {
    box.innerHTML = `<p class="muted">Presets nicht ladbar: ${e}</p>`;
  }
}

document.getElementById("btn-neu").addEventListener("click", () => {
  zeigePanel("pv-formular");
  ladePresets();
});
document.getElementById("btn-form-zurueck").addEventListener("click", () => {
  zeigePanel("pv-liste");
  ladeProjekte();
});

document.querySelector('[name="sprache_select"]').addEventListener("change", (e) => {
  document.getElementById("sprache-frei-wrap").hidden = e.target.value !== "";
});

document.getElementById("projekt-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const status = document.getElementById("projekt-form-status");
  const sprache = form.sprache_select.value || form.sprache_frei.value.trim();
  if (!sprache) {
    status.textContent = "Bitte eine Sprache wählen oder eintragen.";
    return;
  }
  const fd = new FormData();
  fd.append("thema", form.thema.value);
  fd.append("lernziele", form.lernziele.value);
  fd.append("zielgruppe", form.zielgruppe.value);
  fd.append("vorwissen", form.vorwissen.value);
  fd.append("sprache", sprache);
  fd.append("dauer", form.dauer.value);
  fd.append("stil", form.querySelector('input[name="stil"]:checked')?.value || "cinematic");
  fd.append("material_hinweise", form.material_hinweise.value);
  if (form.design_md.files[0]) fd.append("design_md", form.design_md.files[0]);
  for (const f of form.material.files) fd.append("material", f);
  status.textContent = "Lege an …";
  const res = await fetch("/api/projekte", { method: "POST", body: fd });
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    status.textContent = "Fehler: " + (fehler.detail || res.status);
    return;
  }
  const { slug } = await res.json();
  form.reset();
  status.textContent = "";
  oeffneProjekt(slug);
});

// --- Detailansicht --------------------------------------------------------

async function oeffneProjekt(slug) {
  aktuellerSlug = slug;
  zeigePanel("pv-detail");
  const res = await fetch(`/api/projekte/${slug}`);
  if (!res.ok) {
    alert("Projekt nicht gefunden");
    zeigePanel("pv-liste");
    return;
  }
  const p = await res.json();
  document.getElementById("detail-titel").textContent =
    p.briefing.thema || slug;
  aktualisiereStatuszeile(p);
  sseVerbinden(slug);
  ladeCurriculum();
}

function aktualisiereStatuszeile(p) {
  document.getElementById("detail-badge").outerHTML =
    `<span id="detail-badge" class="badge phase-${p.status.phase}">` +
    `${PHASEN_LABEL[p.status.phase] || p.status.phase}</span>`;
  document.getElementById("detail-meta").textContent =
    ` angelegt ${(p.status.erstellt_am || "").slice(0, 16).replace("T", " ")} UTC · ` +
    `Stil: ${p.briefing.stil || "?"}` +
    (p.material.length ? ` · Material: ${p.material.join(", ")}` : "");
  document.getElementById("detail-hinweis").textContent =
    p.status.letzter_fehler ? `Letzter Fehler: ${p.status.letzter_fehler}` : "";
}

async function aktualisiereDetail() {
  if (!aktuellerSlug) return;
  const res = await fetch(`/api/projekte/${aktuellerSlug}`);
  if (res.ok) aktualisiereStatuszeile(await res.json());
}

async function ladeCurriculum() {
  if (!aktuellerSlug) return;
  const res = await fetch(`/api/projekte/${aktuellerSlug}/curriculum`);
  if (res.ok) {
    document.getElementById("curriculum-editor").value = await res.text();
  }
}

// Fortschritts-Log (SSE): hängt Events als Zeilen an, scrollt automatisch
function logZeile(html, klasse) {
  const log = document.getElementById("lauf-log");
  if (log.querySelector(".muted")) log.innerHTML = "";
  const div = document.createElement("div");
  div.className = "log-" + klasse;
  div.innerHTML = html;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function sseVerbinden(slug) {
  if (eventQuelle) eventQuelle.close();
  const log = document.getElementById("lauf-log");
  log.innerHTML = "";
  eventQuelle = new EventSource(`/api/projekte/${slug}/events`);
  eventQuelle.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    if (ev.typ === "status") {
      logZeile(`▶ ${esc(ev.text)}`, "status");
    } else if (ev.typ === "tool") {
      logZeile(`🔧 <b>${esc(ev.tool)}</b> <span class="muted">${esc(ev.eingabe || "")}</span>`, "tool");
    } else if (ev.typ === "text") {
      logZeile(esc(ev.text).replace(/\n/g, "<br>"), "text");
    } else if (ev.typ === "fertig") {
      logZeile(`✅ <b>Fertig</b> (${ev.dauer}s)<br>${esc(ev.text || "").replace(/\n/g, "<br>")}`, "fertig");
      aktualisiereDetail();
      ladeCurriculum();
      eventQuelle.close();
    } else if (ev.typ === "fehler") {
      logZeile(`❌ <b>Fehler:</b> ${esc(ev.text)}`, "fehler");
      aktualisiereDetail();
      eventQuelle.close();
    }
  };
}

document.getElementById("btn-detail-zurueck").addEventListener("click", () => {
  if (eventQuelle) eventQuelle.close();
  aktuellerSlug = null;
  zeigePanel("pv-liste");
  ladeProjekte();
});

document.getElementById("btn-curriculum-start").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const res = await fetch(`/api/projekte/${aktuellerSlug}/curriculum/starten`,
    { method: "POST" });
  if (res.status === 409) {
    document.getElementById("detail-hinweis").textContent =
      "Es läuft bereits ein Agent für dieses Projekt.";
    return;
  }
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    document.getElementById("detail-hinweis").textContent =
      "Fehler: " + (fehler.detail || res.status);
    return;
  }
  document.getElementById("lauf-log").innerHTML = "";
  sseVerbinden(aktuellerSlug);
  aktualisiereDetail();
});

document.getElementById("btn-curriculum-save").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const status = document.getElementById("curriculum-save-status");
  const res = await fetch(`/api/projekte/${aktuellerSlug}/curriculum`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: document.getElementById("curriculum-editor").value }),
  });
  status.textContent = res.ok ? "Gespeichert." : "Fehler beim Speichern.";
  setTimeout(() => (status.textContent = ""), 3000);
});

document.getElementById("btn-kommentar-send").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const box = document.getElementById("kommentar-box");
  const status = document.getElementById("kommentar-status");
  const kommentar = box.value.trim();
  if (!kommentar) return;
  const res = await fetch(`/api/projekte/${aktuellerSlug}/curriculum/kommentar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kommentar }),
  });
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    status.textContent = "Fehler: " + (fehler.detail || res.status);
    return;
  }
  box.value = "";
  status.textContent = "Agent arbeitet am Änderungswunsch …";
  setTimeout(() => (status.textContent = ""), 5000);
  document.getElementById("lauf-log").innerHTML = "";
  sseVerbinden(aktuellerSlug);
  aktualisiereDetail();
});

ladeProjekte();
