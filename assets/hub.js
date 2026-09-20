function youtubeId(video) {
  const raw = String(video?.id || "").trim();
  return /^[A-Za-z0-9_-]{11}$/.test(raw) ? raw : "";
}

function embedSrc(video) {
  const id = youtubeId(video);
  if (!id) return "";
  const fromJson = String(video.embedUrl || "");
  if (fromJson.startsWith("https://www.youtube-nocookie.com/embed/")) return fromJson;
  if (fromJson.startsWith("https://www.youtube.com/embed/")) {
    return fromJson.replace("https://www.youtube.com/embed/", "https://www.youtube-nocookie.com/embed/");
  }
  return `https://www.youtube-nocookie.com/embed/${id}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDate(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

function embedFrame(video) {
  const src = embedSrc(video);
  const title = escapeHtml(video.title || "YouTube video");
  if (!src) return "";
  return `<div class="embed-frame">
      <iframe
        src="${escapeHtml(src)}"
        title="${title}"
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerpolicy="strict-origin-when-cross-origin"
        allowfullscreen
      ></iframe>
    </div>`;
}

function watchLink(video) {
  const href = video.watchUrl || (youtubeId(video) ? `https://www.youtube.com/watch?v=${youtubeId(video)}` : "");
  if (!href) return "";
  return `<a class="more" href="${escapeHtml(href)}" rel="noopener noreferrer" target="_blank">Watch on YouTube →</a>`;
}

function renderNews(items) {
  const root = document.querySelector("[data-news-grid]");
  if (!root) return;
  if (!items.length) {
    root.innerHTML = `<p class="lede">No headlines in this filter.</p>`;
    return;
  }
  root.innerHTML = items
    .map(
      (item) => `<article class="card news-card">
        <div class="meta-row">
          <span class="pill">${escapeHtml(item.source || "News")}</span>
          <time datetime="${escapeHtml(item.date || "")}">${escapeHtml(formatDate(item.date || ""))}</time>
        </div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.summary || "")}</p>
        <a class="more" href="${escapeHtml(item.url)}" rel="noopener noreferrer" target="_blank">Read at ${escapeHtml(item.source || "source")} →</a>
      </article>`
    )
    .join("");
}

function renderFeatured(videos) {
  const root = document.querySelector("[data-featured-grid]");
  if (!root) return;
  root.innerHTML = videos
    .map(
      (video) => `<article class="card featured-card">
        ${embedFrame(video)}
        <p class="creator">${escapeHtml(video.creator)}${video.duration ? ` · ${escapeHtml(video.duration)}` : ""}</p>
        <h3>${escapeHtml(video.title)}</h3>
        <p>${escapeHtml(video.summary || "")}</p>
        <div class="attr-row">
          ${watchLink(video)}
          <a class="more" href="${escapeHtml(video.creatorUrl || "#")}" rel="noopener noreferrer" target="_blank">Channel →</a>
        </div>
      </article>`
    )
    .join("");
}

function renderVideos(videos) {
  const root = document.querySelector("[data-video-grid]");
  if (!root) return;
  if (!videos.length) {
    root.innerHTML = `<p class="lede">No videos in this topic.</p>`;
    return;
  }
  root.innerHTML = videos
    .map(
      (video) => `<article class="card video-card">
        ${embedFrame(video)}
        <div class="chip-row">${(video.topics || []).map((t) => `<span class="pill">${escapeHtml(t)}</span>`).join("")}</div>
        <p class="creator">${escapeHtml(video.creator)}${video.duration ? ` · ${escapeHtml(video.duration)}` : ""}</p>
        <h3>${escapeHtml(video.title)}</h3>
        <p>${escapeHtml(video.summary || "")}</p>
        <div class="attr-row">
          ${watchLink(video)}
          <a class="more" href="${escapeHtml(video.creatorUrl || "#")}" rel="noopener noreferrer" target="_blank">Channel →</a>
        </div>
      </article>`
    )
    .join("");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function wireFilters(buttons, onPick) {
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((other) => other.setAttribute("aria-pressed", String(other === btn)));
      onPick(btn.getAttribute("data-filter") || "all");
    });
  });
}

async function bootNews() {
  const status = document.querySelector("[data-hub-status]");
  try {
    const res = await fetch("./data/news.json", { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("Could not load news.json");
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items.slice() : [];
    items.sort((a, b) => String(b.date).localeCompare(String(a.date)));
    const sources = unique(items.map((item) => item.source));
    const bar = document.querySelector("[data-news-filters]");
    if (bar) {
      bar.innerHTML = `<button type="button" data-filter="all" aria-pressed="true">All</button>${sources
        .map((source) => `<button type="button" data-filter="${escapeHtml(source)}">${escapeHtml(source)}</button>`)
        .join("")}`;
      wireFilters([...bar.querySelectorAll("button")], (filter) => {
        renderNews(filter === "all" ? items : items.filter((item) => item.source === filter));
      });
    }
    renderNews(items);
    if (status) {
      status.textContent = `${items.length} headlines · updated ${data.updated || "n/a"} · edit data/news.json to refresh the desk`;
    }
  } catch (err) {
    if (status) status.textContent = err.message || "News feed failed to load.";
  }
}

async function bootCoaching() {
  const status = document.querySelector("[data-hub-status]");
  try {
    const res = await fetch("./data/coaching-videos.json", { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("Could not load coaching-videos.json");
    const data = await res.json();
    const videos = (Array.isArray(data.videos) ? data.videos : []).filter((video) => youtubeId(video));
    const featured = videos.filter((video) => video.featured);
    const grid = videos.filter((video) => !video.featured);
    const topics = unique(videos.flatMap((video) => video.topics || []));
    const bar = document.querySelector("[data-coach-filters]");
    if (bar) {
      bar.innerHTML = `<button type="button" data-filter="all" aria-pressed="true">All</button>${topics
        .map((topic) => `<button type="button" data-filter="${escapeHtml(topic)}">${escapeHtml(topic)}</button>`)
        .join("")}`;
      wireFilters([...bar.querySelectorAll("button")], (filter) => {
        const list = filter === "all" ? grid : grid.filter((video) => (video.topics || []).includes(filter));
        renderVideos(list);
      });
    }
    renderFeatured(featured.length ? featured : videos.slice(0, 2));
    renderVideos(grid);
    if (status) {
      status.textContent = `${videos.length} public YouTube embeds · metadata verified ${data.updated || "n/a"} · edit data/coaching-videos.json to curate`;
    }
  } catch (err) {
    if (status) status.textContent = err.message || "Coaching library failed to load.";
  }
}

function boot() {
  if (document.querySelector("[data-news-grid]")) bootNews();
  if (document.querySelector("[data-video-grid]") || document.querySelector("[data-featured-grid]")) bootCoaching();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
