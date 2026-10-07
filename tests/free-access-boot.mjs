// Boots the free-access module against a tiny DOM. The code under test is supplied
// by the pytest runner and is not a published access code.
import { createHash } from "node:crypto";

const code = process.env.LAPSIMPRO_TEST_ACCESS_CODE || "";
if (!code) {
  console.error("missing test code");
  process.exit(1);
}

const expected = createHash("sha256").update(code).digest("hex");
const published = "f9c67c5045d2151dcb760b4871fbd9c1b292294d72380a1d0ed35e3716ce1f2a";
const network = [];
const assigned = [];
const store = new Map();

function matches(node, sel) {
  const parts = sel.split(",").map((part) => part.trim());
  return parts.some((part) => {
    if (part.startsWith("[") && part.endsWith("]")) {
      return Object.prototype.hasOwnProperty.call(node.attrs, part.slice(1, -1));
    }
    const typed = part.match(/^(\w+)\[type=(.+)]$/);
    if (typed) return node.tag === typed[1] && node.attrs.type === typed[2];
    return node.tag === part;
  });
}

function queryAll(node, sel) {
  const out = [];
  for (const child of node.children || []) {
    if (matches(child, sel)) out.push(child);
    out.push(...queryAll(child, sel));
  }
  return out;
}

function el(tag, attrs = {}, children = []) {
  const node = {
    tag,
    attrs,
    children,
    hidden: false,
    value: "",
    textContent: "",
    dataset: {},
    disabled: false,
    listeners: {},
  };
  node.hasAttribute = (name) => Object.prototype.hasOwnProperty.call(node.attrs, name);
  node.addEventListener = (type, fn) => {
    (node.listeners[type] ||= []).push(fn);
  };
  node.querySelector = (sel) => queryAll(node, sel)[0] || null;
  node.querySelectorAll = (sel) => queryAll(node, sel);
  return node;
}

function mount(resume) {
  const input = el("input", { type: "text", "data-free-access-input": "" });
  const button = el("button", { type: "submit" });
  const form = el("form", { "data-free-access-form": "" }, [input, button]);
  const status = el("p", { "data-free-access-status": "" });
  const link = el("a");
  const download = el("div", { "data-free-access-download": "" }, [link]);
  download.hidden = true;
  const rootAttrs = { "data-free-access": "" };
  if (resume) rootAttrs["data-free-access-resume"] = "";
  const root = el("article", rootAttrs, [form, status, download]);
  const document = {
    readyState: "complete",
    children: [root],
    querySelector(sel) {
      return queryAll(document, sel)[0] || null;
    },
    addEventListener() {},
  };
  globalThis.document = document;
  return { input, button, form, status, link, download, root };
}

globalThis.window = globalThis;
globalThis.location = {
  search: "",
  pathname: "/download.html",
  hash: "",
  assign(url) {
    assigned.push(String(url));
  },
};
globalThis.history = { replaceState(_s, _t, next) { globalThis.__nextUrl = next; } };
globalThis.localStorage = {
  getItem: (key) => (store.has(key) ? store.get(key) : null),
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: (key) => store.delete(key),
};
globalThis.fetch = () => {
  network.push("fetch");
  return Promise.reject(new Error("network disabled"));
};
globalThis.__LSP_SKIP_FREE_ACCESS_BOOT = true;

const { ALLOWED_ACCESS_CODE_HASHES } = await import(
  new URL("../assets/access-codes.js", import.meta.url)
);
const { INSTALLER_URL } = await import(new URL("../assets/installer.js", import.meta.url));
const { bootFreeAccess } = await import(new URL("../assets/free-access.js", import.meta.url));
ALLOWED_ACCESS_CODE_HASHES.push(expected);

function assert(ok, message) {
  if (!ok) {
    console.error(message);
    process.exitCode = 1;
  }
}

const page = mount(false);
page.input.value = `  ${code.toUpperCase()} \n`;
await bootFreeAccess();
const pending = page.form.listeners.submit[0]({ preventDefault() {} });
await pending;
assert(assigned.length === 1 && assigned[0] === INSTALLER_URL, "valid code should start the installer");
assert(page.status.textContent === "Code accepted - your download is starting", "success status");
assert(page.download.hidden === false, "download button shown");
assert(localStorage.getItem("lsp_token") == null, "no login token");
assert(localStorage.getItem("lapsimpro.freeAccess") === "1", "unlock remembered");
assert(network.length === 0, "no backend call");
assert(!String(assigned[0]).includes("login.html"), "no login redirect");
assert(expected !== published, "test code is not the published code");

const beforeClick = assigned.length;
page.link.listeners.click[0]({ preventDefault() {} });
assert(assigned.length === beforeClick + 1 && assigned.at(-1) === INSTALLER_URL, "button repeats the download");
assert(network.length === 0, "button does not call the backend");

assigned.length = 0;
page.input.value = "not-a-valid-code";
await page.form.listeners.submit[0]({ preventDefault() {} });
assert(assigned.length === 0, "invalid code must not start the download");
assert(page.status.textContent === "That code isn't valid", "invalid status");
assert(localStorage.getItem("lsp_token") == null, "invalid code still has no login");

assigned.length = 0;
network.length = 0;
store.delete("lapsimpro.freeAccess");
const remembered = mount(true);
localStorage.setItem("lapsimpro.freeAccess", "1");
await bootFreeAccess();
assert(assigned.length === 1 && assigned[0] === INSTALLER_URL, "remembered unlock starts the download");
assert(localStorage.getItem("lsp_token") == null, "remembered unlock has no login");
assert(network.length === 0, "remembered unlock makes no backend call");
assert(remembered.status.textContent === "Code accepted - your download is starting", "resume status");

assigned.length = 0;
const callsBefore = network.length;
store.delete("lapsimpro.freeAccess");
mount(true);
location.search = `?code=${encodeURIComponent(`  ${code.toUpperCase()}  `)}&paint=1`;
location.pathname = "/releases/";
await bootFreeAccess();
assert(assigned.length === 1 && assigned[0] === INSTALLER_URL, "query code starts the installer");
assert(!String(globalThis.__nextUrl).includes("code="), "query code is removed from the address");
assert(String(globalThis.__nextUrl).includes("paint=1"), "other query params stay");
assert(localStorage.getItem("lsp_token") == null, "query code has no login");
assert(network.length === callsBefore, "query code makes no backend call");

if (process.exitCode) process.exit(process.exitCode);
console.log("ok");
