const READ_KEY = "dossier:read-ids";
const state = {
  categories: [],
  activeCategory: "all",
  items: [],
  query: "",
  readIds: new Set(JSON.parse(localStorage.getItem(READ_KEY) || "[]")),
};

const el = (sel) => document.querySelector(sel);
const catRail = el("#category-rail");
const list = el("#article-list");
const searchInput = el("#search-input");
const statusLine = el("#status-line");

function saveReadIds() {
  localStorage.setItem(READ_KEY, JSON.stringify([...state.readIds]));
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

function categoryColor(id) {
  const cat = state.categories.find((c) => c.id === id);
  return cat ? cat.color : "#555";
}

function categoryLabel(id) {
  const cat = state.categories.find((c) => c.id === id);
  return cat ? cat.label : id;
}

function renderRail() {
  const chips = [
    `<button class="chip" data-cat="all" data-active="${state.activeCategory === "all"}">All</button>`,
    ...state.categories.map(
      (c) => `<button class="chip" data-cat="${c.id}" data-active="${state.activeCategory === c.id}">
        <span class="dot" style="background:${c.color}"></span>${c.label}
      </button>`
    ),
  ];
  catRail.innerHTML = chips.join("");
  catRail.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.activeCategory = btn.dataset.cat;
      renderRail();
      renderList();
    });
  });
}

function matchesQuery(item, q) {
  if (!q) return true;
  const hay = `${item.title} ${item.summary} ${item.source}`.toLowerCase();
  return hay.includes(q.toLowerCase());
}

function renderList() {
  let items = state.items;
  if (state.activeCategory !== "all") {
    items = items.filter((i) => i.category === state.activeCategory);
  }
  items = items.filter((i) => matchesQuery(i, state.query));

  if (items.length === 0) {
    list.innerHTML = `<div class="empty-state">Nothing here yet.<br>Either the crawler hasn't run, or nothing matches your filter.</div>`;
    return;
  }

  list.innerHTML = items
    .map((item) => {
      const isRead = state.readIds.has(item.id);
      return `
        <article class="article" data-id="${item.id}">
          <div class="article-meta">
            <span class="cat-tag" style="background:${categoryColor(item.category)}">${categoryLabel(item.category)}</span>
            <span>${item.source}</span>
            <span>&middot;</span>
            <span>${timeAgo(item.published)}</span>
          </div>
          <h2><a href="${item.link}" target="_blank" rel="noopener">${item.title}</a></h2>
          <p class="summary">${item.summary}</p>
          <div class="article-footer">
            <a class="source-link" href="${item.link}" target="_blank" rel="noopener">${new URL(item.link).hostname.replace("www.", "")}</a>
            <button class="read-btn" data-read="${isRead}" data-id="${item.id}">${isRead ? "Read" : "Mark read"}</button>
          </div>
        </article>
      `;
    })
    .join("");

  list.querySelectorAll(".read-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      if (state.readIds.has(id)) {
        state.readIds.delete(id);
      } else {
        state.readIds.add(id);
      }
      saveReadIds();
      renderList();
    });
  });
}

async function loadData() {
  const catData = await loadJSON("data/categories.json");
  state.categories = catData.categories;

  const index = await loadJSON("data/index.json").catch(() => null);

  const results = await Promise.allSettled(
    state.categories.map((c) => loadJSON(`data/${c.id}.json`))
  );

  state.items = results
    .filter((r) => r.status === "fulfilled")
    .flatMap((r) => r.value.items);

  state.items.sort((a, b) => new Date(b.published) - new Date(a.published));

  const failed = results.filter((r) => r.status === "rejected").length;
  const updated = index ? new Date(index.updated).toLocaleString() : "unknown";
  statusLine.innerHTML = `
    <span>${state.items.length} items &middot; last crawl ${updated}</span>
    <span>${failed > 0 ? `${failed} categor${failed === 1 ? "y" : "ies"} unavailable` : ""}</span>
  `;
}

function wireSearch() {
  searchInput.addEventListener("input", (e) => {
    state.query = e.target.value;
    renderList();
  });
}

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isInStandaloneMode() {
  // already installed / launched from home screen
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}

function wireInstallPrompt() {
  const banner = el("#install-banner");
  const textEl = el("#install-text");
  const acceptBtn = el("#install-accept");
  const dismissBtn = el("#install-dismiss");
  let deferredPrompt = null;

  if (isInStandaloneMode() || localStorage.getItem("dossier:install-dismissed")) {
    return;
  }

  if (isIos()) {
    // iOS Safari never fires beforeinstallprompt — there is no programmatic
    // install API at all, so we just show the manual steps.
    textEl.textContent = "Install: tap the Share icon below, then \u201cAdd to Home Screen.\u201d";
    acceptBtn.style.display = "none";
    banner.dataset.visible = "true";
  } else {
    // Android / desktop Chrome, Edge, etc. — use the native prompt.
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredPrompt = e;
      textEl.textContent = "Add Dossier to your home screen for quick access.";
      acceptBtn.style.display = "";
      banner.dataset.visible = "true";
    });

    acceptBtn.addEventListener("click", async () => {
      banner.dataset.visible = "false";
      if (deferredPrompt) {
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
      }
    });
  }

  dismissBtn.addEventListener("click", () => {
    banner.dataset.visible = "false";
    localStorage.setItem("dossier:install-dismissed", "1");
  });
}

async function init() {
  renderRail();
  wireSearch();
  wireInstallPrompt();
  try {
    await loadData();
    renderRail();
    renderList();
  } catch (err) {
    statusLine.textContent = "Couldn't load data — check that docs/data/*.json exists.";
    console.error(err);
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("service-worker.js").catch(() => {});
  }
}

init();