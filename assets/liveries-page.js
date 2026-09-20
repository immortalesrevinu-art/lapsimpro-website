const MANIFEST_URL = "./data/liveries.json";

function $(sel, root = document) {
  return root.querySelector(sel);
}

function showInstallHandoff(fallback) {
  const note = document.querySelector("[data-install-handoff]");
  if (!note) return;
  note.hidden = false;
  const link = note.querySelector("[data-install-fallback]");
  if (link) link.setAttribute("href", fallback);
  note.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function protocolFallback(href, fallback) {
  showInstallHandoff(fallback);
  const start = Date.now();
  const timer = window.setTimeout(() => {
    if (document.visibilityState === "visible" && Date.now() - start < 2800) {
      window.location.href = fallback;
    }
  }, 1600);
  const cancel = () => window.clearTimeout(timer);
  window.addEventListener("blur", cancel, { once: true });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") cancel();
  }, { once: true });
  window.location.href = href;
}

function previewSrc(livery) {
  const preview = livery.preview;
  if (typeof preview === "string") return preview;
  return preview?.src || "";
}

function card(livery) {
  const featured = livery.priority ? " featured" : "";
  const pills = [
    `<span class="pill">${livery.class || "GT3"}</span>`,
    livery.priority ? `<span class="pill">Priority</span>` : "",
    livery.placeholder || !livery.assets_ready ? `<span class="pill warn">Preview</span>` : "",
  ]
    .filter(Boolean)
    .join("");
  const src = previewSrc(livery);
  const alt = (typeof livery.preview === "object" && livery.preview?.alt) || `${livery.name} house livery`;
  const href = livery.download?.href || "";
  const fallback = livery.download?.fallback || "./download.html?paint=1";
  return `<article class="card livery-card${featured}" data-livery="${livery.id}" data-car-path="${livery.car_path}">
    <div class="livery-preview">
      <img src="${src}" alt="${alt}" width="640" height="360" />
    </div>
    <div class="livery-body">
      <div class="livery-pills">${pills}</div>
      <h3>${livery.name}</h3>
      <p class="livery-path"><code>${livery.car_path}</code></p>
      <p>${livery.blurb || ""}</p>
      <div class="btn-row livery-actions">
        <a class="btn btn-primary" data-paint-install href="${href}" data-fallback="${fallback}">Download</a>
      </div>
      <p class="livery-hint">Opens the LapSimPro paint installer. Copies into Documents/iRacing/paint/${livery.car_path}/</p>
    </div>
  </article>`;
}

function render(manifest) {
  const grid = $("[data-livery-grid]");
  const empty = $("[data-livery-empty]");
  const count = $("[data-livery-count]");
  const pack = $("[data-pack-install]");
  if (!grid) return;
  const items = [...(manifest.liveries || [])].sort((a, b) => Number(b.priority) - Number(a.priority));
  grid.innerHTML = items.map(card).join("");
  if (empty) empty.hidden = items.length > 0;
  if (count) {
    const ready = items.filter((item) => item.assets_ready).length;
    count.textContent = ready
      ? `${items.length} GT3 house wraps · ${ready} paint files ready`
      : `${items.length} GT3 house wraps · previews up, TGA pack drops next`;
  }
  if (pack) {
    const href = manifest.install?.pack_href || "lapsimpro://paint/install?pack=lapsimpro-house-gt3";
    const fallback = manifest.install?.fallback || "./download.html?paint=1";
    pack.setAttribute("href", href);
    pack.dataset.fallback = fallback;
  }
  document.querySelectorAll("[data-paint-install]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const protocol = link.getAttribute("href") || "";
      const fallback = link.getAttribute("data-fallback") || "./download.html?paint=1";
      if (!protocol.startsWith("lapsimpro://")) return;
      event.preventDefault();
      protocolFallback(protocol, fallback);
    });
  });
}

async function boot() {
  const grid = $("[data-livery-grid]");
  const empty = $("[data-livery-empty]");
  try {
    const res = await fetch(MANIFEST_URL, { cache: "no-cache" });
    if (!res.ok) throw new Error("Could not load liveries.");
    const manifest = await res.json();
    window.__lspLiveries = manifest;
    render(manifest);
  } catch (err) {
    if (grid) grid.innerHTML = "";
    if (empty) {
      empty.hidden = false;
      empty.textContent = err.message || "Could not load the house livery catalog.";
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  boot().catch(() => {});
});
