/** Accessible overlay tabs. Arrow keys move the selected tab. */
export function wireOverlayTabs(root = document) {
  const list = root.querySelector("[data-overlay-tabs]");
  if (!list) return;
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const panels = [...root.querySelectorAll("[data-overlay-panel]")];
  if (!tabs.length) return;

  function select(id, { focus = false } = {}) {
    for (const tab of tabs) {
      const on = tab.getAttribute("aria-controls") === id;
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
      if (on && focus) tab.focus();
    }
    for (const panel of panels) {
      panel.hidden = panel.id !== id;
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      select(tab.getAttribute("aria-controls"));
    });
    tab.addEventListener("keydown", (event) => {
      const keys = ["ArrowRight", "ArrowLeft", "Home", "End"];
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      select(tabs[next].getAttribute("aria-controls"), { focus: true });
    });
  });
}

if (document.querySelector("[data-overlay-tabs]")) {
  const run = () => wireOverlayTabs();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
}
