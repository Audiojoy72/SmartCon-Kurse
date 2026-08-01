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
  kostenplan_laeuft: "Kostenplan läuft …",
  freigabe_laeuft: "Freigabe läuft …",
  freigegeben: "Freigegeben",
  produktion_laeuft: "Produktion läuft …",
  fertig: "Fertig",
  fehler: "Fehler",
};

let aktuellerSlug = null;
let eventQuelle = null;
let listeTimer = null;

function zeigePanel(id) {
  ["pv-liste", "pv-formular", "pv-detail"].forEach((p) => {
    document.getElementById(p).hidden = p !== id;
  });
  if (id !== "pv-liste") listePollingStoppen();
}

function listePollingStoppen() {
  if (listeTimer) {
    clearTimeout(listeTimer);
    listeTimer = null;
  }
}

function badge(phase) {
  return `<span class="badge phase-${phase}">${PHASEN_LABEL[phase] || phase}</span>`;
}

async function ladeProjekte() {
  const box = document.getElementById("projekt-liste");
  listePollingStoppen();
  try {
    const data = await (await fetch("/api/projekte")).json();
    // Läuft irgendwo ein Agent, holt sich die Liste den neuen Stand selbst —
    // sonst bliebe „Produktion läuft …" bis zum manuellen Reload stehen.
    if (data.projekte.some((p) => (p.phase || "").endsWith("_laeuft"))) {
      listeTimer = setTimeout(ladeProjekte, 15000);
    }
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
        const gewaehlt = box.querySelector('input[name="stil"]:checked').value;
        document.getElementById("design-upload-wrap").hidden = gewaehlt !== "design";
        // Preset „kostenlos" erzwingt KI-Medien: Nein
        const schalter = document.querySelector('input[name="ki_medien"]');
        const aus = gewaehlt === "kostenlos";
        schalter.disabled = aus;
        if (aus) schalter.checked = false;
        document.getElementById("ki-medien-hinweis").hidden = !aus;
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
  fd.append("ki_medien", form.ki_medien.checked ? "ja" : "nein");
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
  ladeGate(p);
  ladeProduktion(p);
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
      ladeGate();
      ladeProduktion();
      eventQuelle.close();
    } else if (ev.typ === "fehler") {
      logZeile(`❌ <b>Fehler:</b> ${esc(ev.text)}`, "fehler");
      aktualisiereDetail();
      ladeProduktion();
      eventQuelle.close();
    }
  };
}

document.getElementById("btn-detail-zurueck").addEventListener("click", () => {
  if (eventQuelle) eventQuelle.close();
  verbrauchPollingStoppen();
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

// ==========================================================================
// Freigabe-Gate
// ==========================================================================

// Zustand des Gates: vom Parser vorbelegte Medien, gesammelte Änderungen
// (medium_overrides), Kostenplan und Guthaben
const gateZustand = { level: [], overrides: {}, kosten: null, guthaben: null };

// Phasen, in denen das Gate sichtbar ist (curriculum_fertig oder später)
const GATE_PHASEN = ["curriculum_fertig", "kostenplan_laeuft",
                     "freigabe_laeuft", "freigegeben",
                     "produktion_laeuft", "fertig"];
const MEDIUM_OPTIONEN = ["FILM", "ANIMATION", "BILD"];

function mediumNorm(m) {
  const u = (m || "").toUpperCase();
  for (const k of MEDIUM_OPTIONEN) if (u.includes(k)) return k;
  return u;
}

function fmtCredits(n) {
  return Number(n).toLocaleString("de-DE", { maximumFractionDigits: 1 });
}

async function ladeGate(projekt) {
  const gate = document.getElementById("gate");
  if (!aktuellerSlug) return;
  if (!projekt) {
    const res = await fetch(`/api/projekte/${aktuellerSlug}`);
    if (!res.ok) return;
    projekt = await res.json();
  }
  const sichtbar = projekt.hat_curriculum &&
                   GATE_PHASEN.includes(projekt.status.phase);
  gate.hidden = !sichtbar;
  if (!sichtbar) return;
  const res = await fetch(`/api/projekte/${aktuellerSlug}/gate`);
  if (!res.ok) return;
  const data = await res.json();
  gateZustand.level = data.level || [];
  gateZustand.kosten = data.kosten;
  gateZustand.guthaben = data.guthaben;
  gateZustand.overrides = {};  // nach Reload neu sammeln
  rendereLevelTabelle();
  rendereKosten();
  document.getElementById("gate-hinweis").textContent =
    ["freigegeben", "produktion_laeuft", "fertig"].includes(projekt.status.phase)
      ? "Freigegeben — unten „Produktion starten“ klicken."
      : "";
}

function rendereLevelTabelle() {
  const box = document.getElementById("gate-level");
  if (!gateZustand.level.length) {
    box.innerHTML = "<p class='muted'>Keine Level-Übersicht im curriculum.md gefunden.</p>";
    return;
  }
  const tabelle = document.createElement("table");
  tabelle.className = "gate-tabelle";
  tabelle.innerHTML =
    "<thead><tr><th>Level</th><th>Lernziel</th><th>Medium</th><th>Interaktion</th></tr></thead>";
  const tbody = document.createElement("tbody");
  for (const e of gateZustand.level) {
    const original = mediumNorm(e.medium);
    const optionen = MEDIUM_OPTIONEN.includes(original) || !original
      ? MEDIUM_OPTIONEN : [original, ...MEDIUM_OPTIONEN];
    const lernziel = e.lernziel.length > 80
      ? e.lernziel.slice(0, 80) + " …" : e.lernziel;
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${esc(e.level)}</td>` +
      `<td title="${esc(e.lernziel)}">${esc(lernziel)}</td>` +
      `<td><select data-level="${esc(e.level)}" data-original="${esc(original)}">` +
      optionen.map((o) =>
        `<option value="${o}"${o === original ? " selected" : ""}>${o}</option>`
      ).join("") +
      `</select></td>` +
      `<td>${esc(e.interaktion)}</td>`;
    tbody.appendChild(tr);
  }
  tabelle.appendChild(tbody);
  box.innerHTML = "";
  const scrollbox = document.createElement("div");
  scrollbox.className = "tabelle-scroll";
  scrollbox.appendChild(tabelle);
  box.appendChild(scrollbox);
  // Geänderte Dropdowns als medium_overrides sammeln
  tabelle.querySelectorAll("select").forEach((sel) => {
    sel.addEventListener("change", () => {
      if (sel.value === sel.dataset.original) {
        delete gateZustand.overrides[sel.dataset.level];
      } else {
        gateZustand.overrides[sel.dataset.level] = sel.value;
      }
    });
  });
}

function rendereKosten() {
  const box = document.getElementById("gate-kosten");
  const { kosten, guthaben } = gateZustand;
  if (!kosten) {
    box.innerHTML = "<p class='muted'>Noch kein Kostenplan vorhanden — " +
      "„Kostenplan (neu) berechnen“ startet den Agenten.</p>";
    return;
  }
  const zeilen = (kosten.posten || []).map((p) =>
    `<tr><td>${esc(p.typ || "")}</td><td>${esc(p.beschreibung || "")}</td>` +
    `<td class="zahl">${fmtCredits(p.anzahl ?? 0)}</td>` +
    `<td class="zahl">${fmtCredits(p.credits_je ?? 0)}</td>` +
    `<td class="zahl">${fmtCredits(p.credits_summe ?? 0)}</td></tr>`).join("");
  const summe = kosten.summe ?? 0;
  let urteil;
  if (typeof guthaben !== "number") {
    urteil = `<div class="gate-urteil unbekannt">Guthaben nicht abrufbar — ` +
      `Higgsfield-CLI prüfen (System-Check).</div>`;
  } else if (guthaben >= summe) {
    urteil = `<div class="gate-urteil reicht">Guthaben reicht ` +
      `(${fmtCredits(guthaben)} Credits verfügbar)</div>`;
  } else {
    urteil = `<div class="gate-urteil reicht-nicht">Guthaben reicht NICHT — ` +
      `Differenz ${fmtCredits(summe - guthaben)} Credits</div>`;
  }
  box.innerHTML =
    `<div class="tabelle-scroll"><table class="gate-tabelle"><thead><tr>` +
    `<th>Typ</th><th>Beschreibung</th><th>Anzahl</th><th>Credits je</th><th>Summe</th>` +
    `</tr></thead><tbody>${zeilen}</tbody></table></div>` +
    `<div class="gate-summe">Geschätzte Summe: ${fmtCredits(summe)} Credits</div>` +
    `<div class="muted">Aktuelles Higgsfield-Guthaben: ` +
    (typeof guthaben === "number" ? fmtCredits(guthaben) + " Credits" : "unbekannt") +
    `</div>` + urteil;
}

document.getElementById("btn-kostenplan").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const hinweis = document.getElementById("gate-hinweis");
  const res = await fetch(`/api/projekte/${aktuellerSlug}/gate/kostenplan`,
    { method: "POST" });
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    hinweis.textContent = "Fehler: " + (fehler.detail || res.status);
    return;
  }
  hinweis.textContent = "Kostenplan wird berechnet — Fortschritt siehe Log oben …";
  document.getElementById("lauf-log").innerHTML = "";
  sseVerbinden(aktuellerSlug);
  aktualisiereDetail();
});

document.getElementById("btn-go").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const hinweis = document.getElementById("gate-hinweis");
  const { kosten, guthaben } = gateZustand;
  if (kosten && typeof guthaben === "number" && guthaben < (kosten.summe ?? 0)) {
    if (!confirm("Guthaben reicht nicht. Trotzdem freigeben?")) return;
  }
  const res = await fetch(`/api/projekte/${aktuellerSlug}/go`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ medium_overrides: gateZustand.overrides }),
  });
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    hinweis.textContent = "Fehler: " + (fehler.detail || res.status);
    return;
  }
  const data = await res.json();
  if (data.phase === "freigabe_laeuft") {
    // Agent arbeitet die Medien-Änderungen ein — Fortschritt im Log verfolgen
    hinweis.textContent = "Agent arbeitet die Medien-Änderungen ein …";
    document.getElementById("lauf-log").innerHTML = "";
    sseVerbinden(aktuellerSlug);
  } else {
    hinweis.textContent = "Freigegeben — unten „Produktion starten“ klicken.";
  }
  aktualisiereDetail();
  ladeProduktion();
});

// ==========================================================================
// Produktion + Ergebnis (Fertig-Ansicht)
// ==========================================================================

// Phasen, in denen der Produktions-Block sichtbar ist
const PRODUKTION_PHASEN = ["freigegeben", "produktion_laeuft", "fertig"];
let verbrauchTimer = null;

function verbrauchPollingStoppen() {
  if (verbrauchTimer) {
    clearInterval(verbrauchTimer);
    verbrauchTimer = null;
  }
  document.getElementById("produktion-verbrauch").hidden = true;
}

async function ladeProduktion(projekt) {
  if (!aktuellerSlug) return;
  if (!projekt) {
    const res = await fetch(`/api/projekte/${aktuellerSlug}`);
    if (!res.ok) return;
    projekt = await res.json();
  }
  const phase = projekt.status.phase;
  const sichtbar = PRODUKTION_PHASEN.includes(phase);
  document.getElementById("produktion").hidden = !sichtbar;
  document.getElementById("btn-produktion-start").hidden =
    phase !== "freigegeben";
  document.getElementById("produktion-hinweis").textContent =
    phase === "produktion_laeuft"
      ? "Läuft — Fortschritt im Log oben. Das kann 30–60 Minuten dauern."
      : "";
  // Verbrauchs-Zähler nur während des Laufs pollen (alle 30 s)
  verbrauchPollingStoppen();
  if (phase === "produktion_laeuft") {
    aktualisiereVerbrauch();
    verbrauchTimer = setInterval(aktualisiereVerbrauch, 30000);
  }
  ladeErgebnis(phase);
}

async function aktualisiereVerbrauch() {
  if (!aktuellerSlug) return;
  const zeile = document.getElementById("produktion-verbrauch");
  try {
    const res = await fetch(`/api/projekte/${aktuellerSlug}/produktion/status`);
    if (!res.ok) return;
    const d = await res.json();
    zeile.hidden = false;
    if (typeof d.verbraucht === "number") {
      zeile.textContent =
        `Verbraucht seit Produktionsstart: ${fmtCredits(d.verbraucht)} Credits ` +
        `(Guthaben: ${fmtCredits(d.guthaben_jetzt)})`;
    } else {
      zeile.textContent =
        "Verbrauch unbekannt — Higgsfield-Guthaben nicht abrufbar.";
    }
  } catch (e) {
    // einzelner Poll-Fehler ist egal — der nächste Intervall versucht es neu
  }
}

document.getElementById("btn-produktion-start").addEventListener("click", async () => {
  if (!aktuellerSlug) return;
  const hinweis = document.getElementById("produktion-hinweis");
  const res = await fetch(`/api/projekte/${aktuellerSlug}/produktion/starten`,
    { method: "POST" });
  if (!res.ok) {
    const fehler = await res.json().catch(() => ({}));
    hinweis.textContent = "Fehler: " + (fehler.detail || res.status);
    return;
  }
  hinweis.textContent = "Produktion gestartet — Fortschritt im Log oben …";
  document.getElementById("lauf-log").innerHTML = "";
  sseVerbinden(aktuellerSlug);
  aktualisiereDetail();
  ladeProduktion();
});

function fmtGroesse(bytes) {
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  return Math.max(1, Math.round(bytes / 1024)) + " KB";
}

async function ladeErgebnis(phase) {
  const box = document.getElementById("ergebnis");
  box.hidden = phase !== "fertig";
  if (box.hidden || !aktuellerSlug) return;
  const liste = document.getElementById("ergebnis-liste");
  const res = await fetch(`/api/projekte/${aktuellerSlug}/ergebnis`);
  if (!res.ok) return;
  const { dateien } = await res.json();
  if (!dateien.length) {
    liste.innerHTML = "<p class='muted'>Keine HTML-Datei im Projektordner gefunden.</p>";
    return;
  }
  liste.innerHTML = "";
  for (const d of dateien) {
    const zeile = document.createElement("div");
    zeile.className = "ergebnis-datei";
    const datum = new Date(d.mtime * 1000).toLocaleString("de-DE");
    const url = `/api/projekte/${aktuellerSlug}`;
    zeile.innerHTML =
      `<span class="name">${esc(d.name)}</span>` +
      `<span class="meta">${fmtGroesse(d.groesse)} · ${datum}</span>`;
    const btnAnsehen = document.createElement("button");
    btnAnsehen.textContent = "Ansehen";
    btnAnsehen.addEventListener("click", () =>
      window.open(`${url}/vorschau/${encodeURIComponent(d.name)}`, "_blank"));
    const btnDownload = document.createElement("button");
    btnDownload.textContent = "Herunterladen";
    btnDownload.addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = `${url}/ergebnis/${encodeURIComponent(d.name)}`;
      a.download = d.name;
      a.click();
    });
    zeile.appendChild(btnAnsehen);
    zeile.appendChild(btnDownload);
    liste.appendChild(zeile);
  }
}
