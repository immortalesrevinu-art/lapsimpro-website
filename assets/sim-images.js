/**
 * Hydrates in-sim frames from assets/img/sim/manifest.json.
 * Replacing a WebP at the same path needs no code change.
 * Appending a gallery entry to the manifest adds a frame without editing HTML.
 */
const manifestUrl = new URL("./img/sim/manifest.json", import.meta.url);

function assetUrl(relativePath) {
  return new URL(`./img/sim/${relativePath}`, import.meta.url).href;
}

function sameUrl(a, b) {
  try {
    return new URL(a, location.href).href === new URL(b, location.href).href;
  } catch {
    return a === b;
  }
}

function ensureBadge(frame, placeholder) {
  frame.classList.toggle("is-placeholder", Boolean(placeholder));
  let badge = frame.querySelector(":scope > .sim-badge");
  if (placeholder) {
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "sim-badge";
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = "Placeholder art";
      frame.append(badge);
    }
    return;
  }
  badge?.remove();
}

function applyItem(frame, item, { eager = false } = {}) {
  let picture = frame.querySelector("picture");
  let img = frame.querySelector("img");
  if (!picture) {
    picture = document.createElement("picture");
    frame.prepend(picture);
  }
  if (!img) {
    img = document.createElement("img");
    picture.append(img);
  } else if (img.parentElement !== picture) {
    picture.append(img);
  }

  let source = picture.querySelector('source[type="image/webp"]');
  if (item.webp) {
    if (!source) {
      source = document.createElement("source");
      source.type = "image/webp";
      picture.insertBefore(source, img);
    }
    const webp = assetUrl(item.webp);
    if (!sameUrl(source.srcset, webp)) source.srcset = webp;
    if (item.width) source.sizes = source.sizes || frame.dataset.sizes || "100vw";
  }

  if (item.jpeg) {
    let jpeg = picture.querySelector('source[type="image/jpeg"]');
    if (!jpeg) {
      jpeg = document.createElement("source");
      jpeg.type = "image/jpeg";
      picture.insertBefore(jpeg, img);
    }
    jpeg.srcset = assetUrl(item.jpeg);
  }

  const fallback = item.fallback ? assetUrl(item.fallback) : img.getAttribute("src");
  if (fallback && !sameUrl(img.getAttribute("src") || "", fallback)) img.src = fallback;
  if (item.alt) img.alt = item.alt;
  if (item.width) img.width = item.width;
  if (item.height) img.height = item.height;
  img.decoding = "async";
  if (eager) {
    img.loading = "eager";
    img.setAttribute("fetchpriority", "high");
  } else if (!img.getAttribute("loading")) {
    img.loading = "lazy";
  }
  ensureBadge(frame, item.placeholder);
}

function frameFor(item) {
  const frame = document.createElement("figure");
  frame.className = "sim-frame";
  frame.dataset.simId = item.id;
  applyItem(frame, item);
  return frame;
}

function indexItems(data) {
  const map = new Map();
  if (data.hero) map.set(data.hero.id, data.hero);
  for (const item of data.overlays || []) map.set(item.id, item);
  for (const item of data.gallery || []) map.set(item.id, item);
  return map;
}

export async function hydrateSimImages(root = document) {
  let data;
  try {
    const response = await fetch(manifestUrl);
    if (!response.ok) return;
    data = await response.json();
  } catch {
    return;
  }

  const byId = indexItems(data);
  root.querySelectorAll("[data-sim-id]").forEach((frame) => {
    const item = byId.get(frame.getAttribute("data-sim-id"));
    if (!item) return;
    applyItem(frame, item, { eager: frame.dataset.simEager === "true" });
  });

  const gallery = root.querySelector("[data-sim-gallery]");
  if (!gallery || !Array.isArray(data.gallery)) return;
  const present = new Set(
    [...gallery.querySelectorAll("[data-sim-id]")].map((node) => node.getAttribute("data-sim-id")),
  );
  for (const item of data.gallery) {
    if (present.has(item.id)) continue;
    gallery.append(frameFor(item));
  }
}

if (document.querySelector("[data-sim-id], [data-sim-gallery]")) {
  const run = () => {
    hydrateSimImages();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
}
