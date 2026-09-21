"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const APP_SOURCE = fs.readFileSync(path.join(ROOT, "site", "app.js"), "utf8");
const STYLE_SOURCE = fs.readFileSync(path.join(ROOT, "site", "style.css"), "utf8");
const SITE_SOURCE = fs.readFileSync(path.join(ROOT, "site", "index.html"), "utf8");
const STANDALONE_SOURCE = fs.readFileSync(path.join(ROOT, "jobs", "site", "index.html"), "utf8");

function namedFunctionSource(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `missing ${name}`);
  const body = source.indexOf("{", start);
  let depth = 0;
  for (let index = body; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  throw new Error(`unterminated ${name}`);
}

function dataName(attribute) {
  return attribute
    .slice(5)
    .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

function matches(element, selector) {
  if (!element || element.tagName === "#text") return false;
  if (selector.startsWith("#")) return element.id === selector.slice(1);
  if (selector.startsWith(".")) {
    return element.className.split(/\s+/).filter(Boolean).includes(selector.slice(1));
  }
  const suffix = selector.match(/^([a-z]+)\[href\$="([^"]+)"\]$/i);
  if (suffix) {
    return (
      element.tagName === suffix[1].toUpperCase() &&
      String(element.getAttribute("href") || "").endsWith(suffix[2])
    );
  }
  const attribute = selector.match(/^(?:([a-z]+))?\[([^=\]]+)(?:="([^"]*)")?\]$/i);
  if (attribute) {
    if (attribute[1] && element.tagName !== attribute[1].toUpperCase()) return false;
    const actual = element.getAttribute(attribute[2]);
    return attribute[3] === undefined ? actual !== null : actual === attribute[3];
  }
  return element.tagName === selector.toUpperCase();
}

function descendants(element) {
  return element.children.flatMap((child) => [child, ...descendants(child)]);
}

class FakeClassList {
  constructor(element) {
    this.element = element;
  }

  toggle(name, force) {
    const names = new Set(this.element.className.split(/\s+/).filter(Boolean));
    const enabled = force === undefined ? !names.has(name) : Boolean(force);
    if (enabled) names.add(name);
    else names.delete(name);
    this.element.className = [...names].join(" ");
    return enabled;
  }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = tagName.toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.parentElement = null;
    this.attributes = new Map();
    this.dataset = {};
    this.listeners = new Map();
    this.className = "";
    this.id = "";
    this.hidden = false;
    this.disabled = false;
    this.value = "";
    this.title = "";
    this._textContent = "";
    this.classList = new FakeClassList(this);
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get textContent() {
    if (this.children.length) {
      return this.children.map((child) => child.textContent).join("");
    }
    return this._textContent;
  }

  set textContent(value) {
    this.children = [];
    this._textContent = String(value ?? "");
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    this._textContent = "";
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index >= 0) this.children.splice(index, 1);
    child.parentElement = null;
    return child;
  }

  replaceChildren(...children) {
    this.children.forEach((child) => {
      child.parentElement = null;
    });
    this.children = [];
    this._textContent = "";
    children.forEach((child) => this.appendChild(child));
  }

  setAttribute(name, value) {
    const text = String(value);
    this.attributes.set(name, text);
    if (name === "id") this.id = text;
    if (name === "class") this.className = text;
    if (name.startsWith("data-")) this.dataset[dataName(name)] = text;
  }

  getAttribute(name) {
    if (name === "id") return this.id || null;
    if (name === "class") return this.className || null;
    if (name.startsWith("data-")) {
      const value = this.dataset[dataName(name)];
      return value === undefined ? null : String(value);
    }
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  removeAttribute(name) {
    this.attributes.delete(name);
    if (name.startsWith("data-")) delete this.dataset[dataName(name)];
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  dispatch(type, extra = {}) {
    const event = {
      type,
      target: this,
      key: extra.key,
      preventDefault() {},
      ...extra,
    };
    for (const listener of this.listeners.get(type) || []) listener(event);
  }

  click() {
    if (!this.disabled) this.dispatch("click");
  }

  focus() {
    this.ownerDocument.activeElement = this;
  }

  querySelectorAll(selector) {
    return queryAll(this, selector);
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  closest(selector) {
    let current = this;
    while (current) {
      if (matches(current, selector)) return current;
      current = current.parentElement;
    }
    return null;
  }
}

class FakeTextNode extends FakeElement {
  constructor(text, ownerDocument) {
    super("#text", ownerDocument);
    this._textContent = String(text);
  }
}

function queryAll(root, selector) {
  const split = selector.indexOf(" ");
  if (split > 0) {
    const left = selector.slice(0, split);
    const right = selector.slice(split + 1);
    return queryAll(root, left).flatMap((element) => queryAll(element, right));
  }
  return descendants(root).filter((element) => matches(element, selector));
}

class FakeDocument {
  constructor() {
    this.root = new FakeElement("html", this);
    this.activeElement = null;
    this.listeners = new Map();
  }

  createElement(tagName) {
    return new FakeElement(tagName, this);
  }

  createTextNode(text) {
    return new FakeTextNode(text, this);
  }

  getElementById(id) {
    return [this.root, ...descendants(this.root)].find((element) => element.id === id) || null;
  }

  querySelectorAll(selector) {
    return queryAll(this.root, selector);
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }
}

function append(document, parent, tagName, options = {}) {
  const element = document.createElement(tagName);
  if (options.id) element.setAttribute("id", options.id);
  if (options.className) element.className = options.className;
  for (const [name, value] of Object.entries(options.attributes || {})) {
    element.setAttribute(name, value);
  }
  if (options.hidden) element.hidden = true;
  parent.appendChild(element);
  return element;
}

function buildDocument() {
  const document = new FakeDocument();
  const body = append(document, document.root, "body");
  const search = append(document, body, "input", { id: "catalog-search" });
  append(document, body, "p", { id: "results-meta" }).textContent = "Loading catalog data...";

  const categoryFilters = append(document, body, "div", {
    id: "ontology-category-filters",
  });
  const categoryList = append(document, categoryFilters, "div", {
    className: "category-pill-list",
  });
  append(document, categoryList, "button", { className: "category-pill" }).dataset.category = "all";

  const softwareFilters = append(document, body, "div", {
    id: "software-type-filters",
    hidden: true,
  });
  const softwareList = append(document, softwareFilters, "div", {
    className: "category-pill-list",
  });
  append(document, softwareList, "button", { className: "category-pill" }).dataset.softwareType = "all";

  for (const tabName of ["ontologies", "software", "jobs"]) {
    const tab = append(document, body, "button", {
      id: `tab-${tabName}`,
      className: `tab${tabName === "ontologies" ? " is-active" : ""}`,
      attributes: { role: "tab" },
    });
    tab.dataset.tab = tabName;
  }

  const sortFields = {
    ontologies: ["title", "types", "licenses", "partOf", "releaseDate"],
    software: ["title", "licenses", "latestVersion", "releaseDate"],
    jobs: ["title", "employer", "location", "remote", "firstSeenAt", "datePosted", "salary"],
  };
  for (const tabName of ["ontologies", "software", "jobs"]) {
    const panel = append(document, body, "section", {
      id: `panel-${tabName}`,
      attributes: { role: "tabpanel", "data-panel": tabName },
      hidden: tabName !== "ontologies",
    });
    const table = append(document, panel, "table");
    const head = append(document, table, "thead");
    const headRow = append(document, head, "tr");
    for (const sort of sortFields[tabName]) {
      const th = append(document, headRow, "th");
      const button = append(document, th, "button", { className: "sort-button" });
      button.dataset.sort = sort;
    }
    const bodyElement = append(document, table, "tbody", {
      id: `${tabName}-table-body`,
    });
    bodyElement.textContent = "";
    append(document, panel, "div", {
      id: `${tabName}-cards`,
      className: "cards",
    });
  }

  const pagination = append(document, body, "nav", {
    id: "catalog-pagination",
    hidden: true,
  });
  append(document, pagination, "button", {
    id: "previous-page",
    attributes: { "aria-label": "Go to previous catalog page" },
  });
  append(document, pagination, "span", { id: "page-status" });
  append(document, pagination, "button", {
    id: "next-page",
    attributes: { "aria-label": "Go to next catalog page" },
  });

  const freshness = append(document, body, "p", { id: "catalog-freshness", hidden: true });
  append(document, freshness, "code", { id: "generation-id" });
  append(document, freshness, "time", { id: "last-updated" });
  append(document, body, "a", {
    attributes: { href: "./data/ontologies.ttl" },
  });
  append(document, body, "a", {
    attributes: { href: "./data/software.ttl" },
  });

  for (const tab of ["ontologies", "software", "jobs"]) {
    append(document, body, "ul", { id: `new-${tab}` });
  }
  return { document, search };
}

function makeMedia(width) {
  const listeners = [];
  return {
    matches: width <= 760,
    addEventListener(type, listener) {
      if (type === "change") listeners.push(listener);
    },
    setWidth(nextWidth) {
      const matches = nextWidth <= 760;
      if (matches === this.matches) return;
      this.matches = matches;
      listeners.forEach((listener) => listener({ matches }));
    },
  };
}

function makeHistory(window, initialSearch) {
  const entries = [initialSearch || ""];
  let cursor = 0;
  const setUrl = (url) => {
    const parsed = new URL(url, "https://example.test/");
    window.location.pathname = parsed.pathname;
    window.location.search = parsed.search;
  };
  return {
    pushState(_state, _title, url) {
      entries.splice(cursor + 1);
      entries.push(new URL(url, "https://example.test/").search);
      cursor = entries.length - 1;
      setUrl(url);
    },
    replaceState(_state, _title, url) {
      entries[cursor] = new URL(url, "https://example.test/").search;
      setUrl(url);
    },
    back() {
      if (cursor === 0) return;
      cursor -= 1;
      setUrl(entries[cursor] || "/");
      window.dispatchEvent({ type: "popstate" });
    },
    forward() {
      if (cursor >= entries.length - 1) return;
      cursor += 1;
      setUrl(entries[cursor] || "/");
      window.dispatchEvent({ type: "popstate" });
    },
  };
}

function syntheticItems(count, kind) {
  return Array.from({ length: count }, (_, index) => ({
    title: `${kind} ${String(index).padStart(5, "0")}`,
    wikidataId: `https://www.wikidata.org/wiki/Q${kind === "Resource" ? 100000 : 200000}${index}`,
    types: [kind === "Resource" ? "Ontology" : "Software"],
    canonicalUrl: `https://openknowledgegraphs.com/${kind === "Resource" ? "resource" : "software"}/${index}/`,
    description: `Deterministic ${kind.toLowerCase()} fixture ${index}`,
    category: kind === "Resource" ? "Science" : undefined,
    softwareType: kind === "Software" ? "Library" : undefined,
    licenses: ["Fixture License"],
  }));
}

function defaultPayloads(ontologies, software) {
  const qids = { resource: {}, software: {} };
  for (const [dataset, items] of [
    ["resource", ontologies],
    ["software", software],
  ]) {
    for (const item of items.slice(0, 100)) {
      qids[dataset][item.wikidataId.split("/").pop()] = `${dataset}-${item.title.toLowerCase().replace(/\s+/g, "-")}`;
    }
  }
  return {
    ontologies: { generatedAt: "2099-01-01T00:00:00Z", items: ontologies },
    software: { generatedAt: "1999-01-01T00:00:00Z", items: software },
    controlled_vocabularies: {
      categories: [{ id: "science", label: "Science" }],
      softwareTypes: [{ id: "library", label: "Library" }],
    },
    page_qids: qids,
    jobs: [],
    manifest: {
      generationId: "20260817T120000Z-0123456789ab",
      sourceRetrievedAt: "2026-08-17T11:59:00Z",
    },
  };
}

async function createApp({ payloads, failures = [], width = 1200, search = "" }) {
  const { document } = buildDocument();
  const media = makeMedia(width);
  const listeners = new Map();
  const fetchRequests = [];
  const location = { pathname: "/", search };
  Object.defineProperty(location, "href", {
    get() {
      return `https://example.test${this.pathname}${this.search}`;
    },
  });
  const window = {
    document,
    location,
    console: { warn() {}, error() {} },
    setTimeout(callback) {
      callback();
      return 1;
    },
    clearTimeout() {},
    matchMedia() {
      return media;
    },
    addEventListener(type, listener) {
      const current = listeners.get(type) || [];
      current.push(listener);
      listeners.set(type, current);
    },
    dispatchEvent(event) {
      for (const listener of listeners.get(event.type) || []) listener(event);
    },
    async fetch(requestPath, options = {}) {
      fetchRequests.push({ path: requestPath, options });
      const name = path.basename(requestPath, ".json");
      if (failures.includes(name) || !(name in payloads)) {
        return { ok: false, status: 404, async json() { return {}; } };
      }
      return { ok: true, status: 200, async json() { return payloads[name]; } };
    },
  };
  window.history = makeHistory(window, search);
  window.window = window;
  const context = vm.createContext({
    window,
    document,
    Element: FakeElement,
    URL,
    URLSearchParams,
    console: window.console,
    setTimeout: window.setTimeout,
    clearTimeout: window.clearTimeout,
  });
  vm.runInContext(APP_SOURCE, context, { filename: "site/app.js" });
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await new Promise((resolve) => setImmediate(resolve));
    if (document.getElementById("results-meta").textContent !== "Loading catalog data...") {
      break;
    }
  }
  return { document, window, media, fetchRequests };
}

test("jobs payload revalidates independently of the catalog cache", async () => {
  const payloads = defaultPayloads([], []);
  const app = await createApp({ payloads });
  const jobsRequest = app.fetchRequests.find((request) =>
    request.path.endsWith("/data/jobs/jobs.json")
  );
  assert.ok(jobsRequest);
  assert.equal(jobsRequest.options.cache, "no-cache");
});

function recordCount(element) {
  return descendants(element).filter((node) => node.dataset.record === "true").length;
}

function searchFor(app, query) {
  const input = app.document.getElementById("catalog-search");
  input.value = query;
  input.dispatch("input");
}

test("10,000-record catalogs render one accessible 50-record presentation and paginate", async () => {
  const ontologies = syntheticItems(10000, "Resource");
  const software = syntheticItems(10000, "Software");
  const app = await createApp({ payloads: defaultPayloads(ontologies, software) });
  const ontologyRows = app.document.getElementById("ontologies-table-body");
  const ontologyCards = app.document.getElementById("ontologies-cards");
  const softwareRows = app.document.getElementById("software-table-body");
  const softwareCards = app.document.getElementById("software-cards");

  assert.equal(recordCount(ontologyRows), 50);
  assert.equal(recordCount(ontologyCards), 0);
  assert.equal(recordCount(softwareRows) + recordCount(softwareCards), 0);
  assert.equal(app.document.getElementById("page-status").textContent, "Page 1 of 200");
  assert.equal(app.document.getElementById("previous-page").disabled, true);
  assert.equal(app.document.getElementById("next-page").disabled, false);
  assert.match(app.document.getElementById("previous-page").getAttribute("aria-label"), /previous/i);
  assert.match(app.document.getElementById("next-page").getAttribute("aria-label"), /next/i);

  app.document.getElementById("next-page").click();
  assert.equal(recordCount(ontologyRows), 50);
  assert.equal(new URLSearchParams(app.window.location.search).get("page"), "2");

  const scienceFilter = app.document
    .querySelectorAll("#ontology-category-filters .category-pill")
    .find((button) => button.dataset.category === "science");
  scienceFilter.click();
  assert.equal(new URLSearchParams(app.window.location.search).get("page"), "1");
  app.document.getElementById("next-page").click();

  const titleSort = app.document
    .getElementById("panel-ontologies")
    .querySelectorAll(".sort-button")[0];
  titleSort.click();
  assert.equal(new URLSearchParams(app.window.location.search).get("page"), "1");

  app.document.getElementById("tab-software").click();
  assert.equal(recordCount(ontologyRows) + recordCount(ontologyCards), 0);
  assert.equal(recordCount(softwareRows), 50);
  assert.equal(recordCount(softwareCards), 0);

  app.document.getElementById("next-page").click();
  const libraryFilter = app.document
    .querySelectorAll("#software-type-filters .category-pill")
    .find((button) => button.dataset.softwareType === "library");
  libraryFilter.click();
  assert.equal(new URLSearchParams(app.window.location.search).get("page"), "1");

  app.media.setWidth(760);
  assert.equal(recordCount(softwareRows), 0);
  assert.equal(recordCount(softwareCards), 50);
  assert.equal(recordCount(ontologyRows) + recordCount(ontologyCards), 0);
});

test("current catalog data renders 50 records and a short final page", async () => {
  const ontologies = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "ontologies.json"), "utf8"));
  const software = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "software.json"), "utf8"));
  const payloads = defaultPayloads(ontologies.items, software.items);
  payloads.ontologies = ontologies;
  payloads.software = software;
  for (const name of ["controlled_vocabularies", "page_qids", "manifest"]) {
    payloads[name] = JSON.parse(
      fs.readFileSync(path.join(ROOT, "data", `${name}.json`), "utf8")
    );
  }
  const finalPage = Math.ceil(ontologies.items.length / 50);
  const app = await createApp({
    payloads,
    search: `?tab=ontologies&q=&category=all&softwareType=all&sort=title&order=asc&page=${finalPage}`,
  });
  const expected = ontologies.items.length % 50 || 50;
  assert.equal(recordCount(app.document.getElementById("ontologies-table-body")), expected);
  assert.equal(recordCount(app.document.getElementById("ontologies-cards")), 0);
});

test("search covers every semantic, identifier, URL, version, and date field", async () => {
  const resource = {
    title: "TitleNeedle",
    description: "DescriptionNeedle",
    wikidataId: "https://www.wikidata.org/wiki/Q42424242",
    types: ["TypeNeedle"],
    canonicalUrl: "https://example.test/CanonicalNeedle/",
    category: "CategoryNeedle",
    homepage: "https://HomepageNeedle.example/",
    sourceRepo: "https://example.test/RepositoryNeedle",
    namespaceURI: "https://example.test/NamespaceNeedle#",
    licenses: ["LicenseNeedle"],
    creators: [{ name: "CreatorNeedle" }],
    partOf: "ParentNeedle",
    relatedTools: [{ title: "RelatedNeedle" }],
  };
  const software = {
    title: "Software Fixture",
    wikidataId: "https://www.wikidata.org/wiki/Q43434343",
    types: ["Software"],
    canonicalUrl: "https://example.test/software/fixture/",
    description: "Software search fixture",
    softwareType: "SoftwareTypeNeedle",
    programmingLanguages: ["LanguageNeedle"],
    latestVersion: "VersionNeedle-7.2",
    releaseDate: "2042-03-04",
  };
  const app = await createApp({ payloads: defaultPayloads([resource], [software]) });
  for (const query of [
    "TitleNeedle",
    "DescriptionNeedle",
    "Q424242",
    "TypeNeedle",
    "CanonicalNeedle",
    "CategoryNeedle",
    "HomepageNeedle",
    "RepositoryNeedle",
    "NamespaceNeedle",
    "LicenseNeedle",
    "CreatorNeedle",
    "ParentNeedle",
    "RelatedNeedle",
  ]) {
    searchFor(app, query);
    assert.equal(recordCount(app.document.getElementById("ontologies-table-body")), 1, query);
  }
  app.document.getElementById("tab-software").click();
  for (const query of ["SoftwareTypeNeedle", "LanguageNeedle", "VersionNeedle", "2042-03"]) {
    searchFor(app, query);
    assert.equal(recordCount(app.document.getElementById("software-table-body")), 1, query);
  }
});

test("selected sort order remains authoritative while search is active", async () => {
  const items = [
    {
      title: "Needle",
      description: "Exact-title search result",
      wikidataId: "https://www.wikidata.org/wiki/Q500001",
      types: ["Ontology"],
      canonicalUrl: "https://openknowledgegraphs.com/resource/needle/",
    },
    {
      title: "A Needle Extension",
      description: "Partial-title search result",
      wikidataId: "https://www.wikidata.org/wiki/Q500002",
      types: ["Ontology"],
      canonicalUrl: "https://openknowledgegraphs.com/resource/a-needle-extension/",
    },
  ];
  const app = await createApp({
    payloads: defaultPayloads(items, syntheticItems(1, "Software")),
  });
  searchFor(app, "needle");

  const tableBody = app.document.getElementById("ontologies-table-body");
  const titleSort = app.document
    .getElementById("panel-ontologies")
    .querySelectorAll(".sort-button")[0];
  titleSort.click();
  assert.deepEqual(
    tableBody.children.map((row) => row.children[0].textContent),
    ["A Needle Extension", "Needle"]
  );
  let params = new URLSearchParams(app.window.location.search);
  assert.equal(params.get("sort"), "title");
  assert.equal(params.get("order"), "asc");

  titleSort.click();
  assert.deepEqual(
    tableBody.children.map((row) => row.children[0].textContent),
    ["Needle", "A Needle Extension"]
  );
  params = new URLSearchParams(app.window.location.search);
  assert.equal(params.get("order"), "desc");
});

test("URL state restores on load and browser back/forward while view changes reset page", async () => {
  const payloads = defaultPayloads(
    syntheticItems(200, "Resource"),
    syntheticItems(200, "Software")
  );
  const app = await createApp({
    payloads,
    search: "?tab=software&q=fixture&category=all&softwareType=library&sort=title&order=desc&page=2",
  });
  let params = new URLSearchParams(app.window.location.search);
  assert.deepEqual(
    Object.fromEntries(params),
    {
      tab: "software",
      q: "fixture",
      category: "all",
      softwareType: "library",
      sort: "title",
      order: "desc",
      page: "2",
    }
  );
  assert.equal(app.document.getElementById("catalog-search").value, "fixture");
  assert.equal(app.document.getElementById("page-status").textContent, "Page 2 of 4");

  app.document.getElementById("next-page").click();
  searchFor(app, "software 001");
  params = new URLSearchParams(app.window.location.search);
  assert.equal(params.get("page"), "1");
  assert.equal(params.get("q"), "software 001");

  app.window.history.back();
  params = new URLSearchParams(app.window.location.search);
  assert.equal(params.get("page"), "3");
  assert.equal(params.get("q"), "fixture");
  assert.equal(app.document.getElementById("page-status").textContent, "Page 3 of 4");
  assert.equal(app.document.getElementById("catalog-search").value, "fixture");
  app.window.history.forward();
  assert.equal(new URLSearchParams(app.window.location.search).get("q"), "software 001");
});

test("artifact failures degrade independently and freshness is shared from the manifest", async () => {
  const ontologies = syntheticItems(75, "Resource");
  const software = syntheticItems(75, "Software");
  const payloads = defaultPayloads(ontologies, software);

  const oneCatalog = await createApp({ payloads, failures: ["ontologies"] });
  assert.equal(recordCount(oneCatalog.document.getElementById("ontologies-table-body")), 0);
  oneCatalog.document.getElementById("tab-software").click();
  assert.equal(recordCount(oneCatalog.document.getElementById("software-table-body")), 50);

  const otherCatalog = await createApp({ payloads, failures: ["software"] });
  assert.equal(recordCount(otherCatalog.document.getElementById("ontologies-table-body")), 50);
  otherCatalog.document.getElementById("tab-software").click();
  assert.equal(recordCount(otherCatalog.document.getElementById("software-table-body")), 0);

  const filters = await createApp({ payloads, failures: ["controlled_vocabularies"] });
  assert.equal(recordCount(filters.document.getElementById("ontologies-table-body")), 50);
  assert.equal(
    filters.document.getElementById("ontology-category-filters").getAttribute("aria-disabled"),
    "true"
  );
  assert.equal(filters.document.querySelector("#ontology-category-filters .category-pill").disabled, true);
  assert.equal(filters.document.querySelector("#software-type-filters .category-pill").disabled, true);

  const qids = await createApp({ payloads, failures: ["page_qids"] });
  const firstTitleCell = qids.document.getElementById("ontologies-table-body").children[0].children[0];
  assert.equal(firstTitleCell.children.length, 0);
  assert.equal(recordCount(qids.document.getElementById("ontologies-table-body")), 50);

  const noManifest = await createApp({ payloads, failures: ["manifest"] });
  assert.equal(noManifest.document.getElementById("catalog-freshness").hidden, true);
  assert.equal(recordCount(noManifest.document.getElementById("ontologies-table-body")), 50);

  const complete = await createApp({ payloads });
  assert.equal(complete.document.getElementById("catalog-freshness").hidden, false);
  assert.equal(
    complete.document.getElementById("generation-id").textContent,
    payloads.manifest.generationId
  );
  assert.equal(
    complete.document.getElementById("last-updated").getAttribute("datetime"),
    payloads.manifest.sourceRetrievedAt
  );
});

test("job catalog mentions render as accessible linked chips in rows and mobile cards", async () => {
  const payloads = defaultPayloads(
    syntheticItems(1, "Resource"),
    syntheticItems(1, "Software")
  );
  payloads.jobs = [
    {
      id: "fixture-job",
      title: "Knowledge Graph Engineer",
      description: "Description text must remain internal only.",
      hiringOrganization: "Fixture Labs",
      location: "Remote",
      remote: true,
      datePosted: "2026-08-24",
      salary: "USD 100,000",
      canonicalUrl: "https://jobs.example.test/fixture-job",
      sourceName: "Fixture Jobs",
      sourceAttributionUrl: "https://jobs.example.test/",
      classification: "qualified",
      catalogMentions: [
        {
          title: "TQ Data Foundation",
          dataset: "software",
          qid: "Q140443441",
          canonicalUrl: "https://openknowledgegraphs.com/software/tq-data-foundation/",
          matchedPhrase: "TopQuadrant",
        },
        {
          title: "data.world Data Catalog Platform",
          dataset: "software",
          qid: "Q141112432",
          canonicalUrl: "https://openknowledgegraphs.com/software/data-world-data-catalog-platform/",
          matchedPhrase: "data.world",
        },
      ],
      jobTags: [{ label: "SPARQL", matchedPhrase: "SPARQL" }],
    },
  ];
  const app = await createApp({ payloads });
  app.document.getElementById("tab-jobs").click();

  const row = app.document.getElementById("jobs-table-body").children[0];
  const rowList = row.querySelector(".catalog-mentions");
  const rowLinks = rowList.querySelectorAll("a");
  assert.equal(
    rowList.getAttribute("aria-label"),
    "Catalog resources mentioned in this posting"
  );
  assert.deepEqual(rowLinks.map((link) => link.textContent), ["TopQuadrant", "data.world"]);
  assert.deepEqual(rowLinks.map((link) => link.href), [
    "https://openknowledgegraphs.com/software/tq-data-foundation/",
    "https://openknowledgegraphs.com/software/data-world-data-catalog-platform/",
  ]);
  assert.match(rowLinks[0].getAttribute("aria-label"), /software catalog page/);
  assert.match(rowLinks[0].getAttribute("aria-label"), /TQ Data Foundation/);
  assert.match(rowLinks[0].title, /TQ Data Foundation/);
  assert.match(rowLinks[1].getAttribute("aria-label"), /data\.world Data Catalog Platform/);
  assert.match(rowLinks[1].title, /data\.world Data Catalog Platform/);
  assert.equal(row.querySelectorAll(".catalog-mentions").length, 1);
  assert.doesNotMatch(row.textContent, /Description text must remain internal/);

  app.media.setWidth(760);
  assert.equal(recordCount(app.document.getElementById("jobs-table-body")), 0);
  const card = app.document.getElementById("jobs-cards").children[0];
  assert.deepEqual(
    card.querySelectorAll(".catalog-mention-chip a").map((link) => link.textContent),
    ["TopQuadrant", "data.world"]
  );
  assert.equal(card.querySelectorAll(".catalog-mentions").length, 1);
  assert.doesNotMatch(card.textContent, /Description text must remain internal/);
  assert.match(card.textContent, /View posting/);
});

test("Task 44 workplace, combined compensation, and language tags render in both main layouts", async () => {
  assert.match(SITE_SOURCE, />\s*Workplace\s*<\/button>/);
  const payloads = defaultPayloads(syntheticItems(1, "Resource"), syntheticItems(1, "Software"));
  const expectedModes = [
    ["A Remote", "remote", "Remote available"],
    ["B Hybrid", "hybrid", "Hybrid"],
    ["C On-site", "onsite", "On-site"],
    ["D Unknown", "unknown", "Not reported"],
  ];
  const modes = [expectedModes[3], expectedModes[1], expectedModes[2], expectedModes[0]];
  payloads.jobs = modes.map(([title, workplaceMode]) => ({
    id: title, title, description: "Use Cypher and GQL.", hiringOrganization: "Fixture Labs",
    location: "Palo Alto", workplaceMode,
    firstSeenAt: { remote: "2026-08-28T00:00:00Z", hybrid: "2026-08-29T00:00:00Z", onsite: "2026-08-30T00:00:00Z", unknown: "2026-08-31T00:00:00Z" }[workplaceMode],
    datePosted: { remote: "2026-08-28", hybrid: "2026-08-29", onsite: "2026-08-30", unknown: "2026-08-31" }[workplaceMode],
    canonicalUrl: `https://jobs.example.test/${title[0].toLowerCase()}`,
    classification: "qualified", catalogMentions: [],
    jobTags: [
      { label: "Cypher", matchedPhrase: "Cypher", relatedCatalogPage: "https://openknowledgegraphs.com/software/neo4j/" },
      { label: "GQL", matchedPhrase: "GQL" },
    ],
    ...(title === "B Hybrid" ? { combinedCompensation: {
      currency: "USD", minValue: 106900, maxValue: 229400, unitText: "annual",
      basis: "base-plus-variable-target",
    }} : {}),
  }));
  const app = await createApp({ payloads });
  app.document.getElementById("tab-jobs").click();

  const rows = app.document.getElementById("jobs-table-body").children;
  const byTitle = new Map(rows.map((row) => [row.children[0].textContent, row]));
  expectedModes.forEach(([title, , label]) => assert.equal(byTitle.get(`${title}Cypher`).children[3].textContent, label));
  const hybrid = byTitle.get("B HybridCypher");
  assert.equal(hybrid.children[6].textContent, "USD 106,900–229,400 annual combined compensation (base salary + target variable incentive)");
  const tags = hybrid.querySelector(".catalog-mentions");
  assert.equal(tags.getAttribute("aria-label"), "Job language tags");
  assert.deepEqual(tags.children.map((entry) => entry.textContent), ["Cypher"]);
  assert.equal(tags.querySelector("a").href, "https://openknowledgegraphs.com/software/neo4j/");
  assert.equal(tags.children.length, 1);

  const preClickOrder = app.document.getElementById("jobs-table-body").children.map(
    (row) => row.children[3].textContent
  );
  assert.deepEqual(preClickOrder, ["Not reported", "On-site", "Hybrid", "Remote available"]);
  assert.notDeepEqual(preClickOrder, ["Remote available", "Hybrid", "On-site", "Not reported"]);
  app.document.querySelector('[data-sort="remote"]').click();
  assert.deepEqual(
    app.document.getElementById("jobs-table-body").children.map((row) => row.children[3].textContent),
    ["Remote available", "Hybrid", "On-site", "Not reported"]
  );

  app.media.setWidth(760);
  const cards = app.document.getElementById("jobs-cards").children;
  assert.deepEqual(cards.map((card) => card.querySelectorAll(".card-row")[2].textContent), [
    "Workplace: Remote available", "Workplace: Hybrid", "Workplace: On-site", "Workplace: Not reported",
  ]);
  const hybridCard = cards[1];
  assert.match(hybridCard.textContent, /Salary: USD 106,900–229,400 annual combined compensation \(base salary \+ target variable incentive\)/);
  const mobileTags = hybridCard.querySelector(".catalog-mentions");
  assert.deepEqual(mobileTags.children.map((entry) => entry.textContent), ["Cypher"]);
  assert.equal(mobileTags.children[0].querySelector("a").href, "https://openknowledgegraphs.com/software/neo4j/");
  assert.equal(mobileTags.children.length, 1);
});

test("Task 44 standalone fixture executes desktop and mobile presentation contracts", () => {
  assert.match(STANDALONE_SOURCE, />Workplace<\/button>/);
  const context = vm.createContext({
    Intl,
    summaryText: () => "summary",
    conceptChips: () => "",
    evidenceDetails: () => "",
    sourceActions: () => "",
    formatDate: () => "Aug 31, 2026",
  });
  ["escapeHtml", "workplaceMode", "remoteLabel", "salaryLabel", "jobTagChips", "tableRow", "card",
    "strongSignalCount", "rankDate", "remoteRank", "compareRecords"]
    .forEach((name) => vm.runInContext(namedFunctionSource(STANDALONE_SOURCE, name), context));
  context.records = [
    { id: "unknown", workplaceMode: "unknown" }, { id: "onsite", workplaceMode: "onsite" },
    { id: "hybrid", workplaceMode: "hybrid" }, { id: "remote", workplaceMode: "remote" },
  ];
  const expectedLabels = ["Not reported", "On-site", "Hybrid", "Remote available"];
  assert.deepEqual(Array.from(vm.runInContext("records.map(remoteLabel)", context)), expectedLabels);
  for (let index = 0; index < context.records.length; index += 1) {
    context.record = {
      ...context.records[index], title: context.records[index].id, description: "Cypher and GQL",
      hiringOrganization: "Fixture Labs", location: "Palo Alto", datePosted: "2026-08-31",
      jobTags: [
        { label: "Cypher", relatedCatalogPage: "https://openknowledgegraphs.com/software/neo4j/" },
        { label: "GQL" },
      ],
      ...(context.records[index].id === "hybrid" ? { combinedCompensation: {
        currency: "USD", minValue: 106900, maxValue: 229400,
      }} : {}),
    };
    for (const markup of [
      vm.runInContext("tableRow(record)", context), vm.runInContext("card(record)", context),
    ]) {
      assert.match(markup, new RegExp(expectedLabels[index]));
      assert.match(markup, /href="https:\/\/openknowledgegraphs.com\/software\/neo4j\/">Cypher<\/a>/);
      assert.match(markup, />GQL<\/span>/);
      if (context.record.id === "hybrid") {
        assert.match(markup, /USD 106,900–229,400 annual combined compensation \(base salary \+ target variable incentive\)/);
      }
    }
  }
  context.currentSort = { key: "remote", direction: "asc" };
  assert.deepEqual(Array.from(vm.runInContext("records.sort(compareRecords).map(record => record.id)", context)), [
    "remote", "hybrid", "onsite", "unknown",
  ]);
  assert.deepEqual(Array.from(vm.runInContext("records.map(remoteRank)", context)), [0, 1, 2, 3]);
});

test("first-party jobs retain official source attribution in rows and mobile cards", async () => {
  const payloads = defaultPayloads(
    syntheticItems(1, "Resource"),
    syntheticItems(1, "Software")
  );
  payloads.jobs = [
    {
      id: "firstparty:first-party-graphwise:249103",
      title: "Semantic AI Engineer",
      description: "RDF and ontology engineering.",
      hiringOrganization: "Graphwise",
      location: "Sofia",
      canonicalUrl: "https://graphwise.bamboohr.com/careers/111",
      sourceName: "Careers at Graphwise",
      sourceAttributionUrl: "https://graphwise.ai/careers/",
      classification: "qualified",
      catalogMentions: [],
    },
  ];
  const app = await createApp({ payloads });
  app.document.getElementById("tab-jobs").click();

  const row = app.document.getElementById("jobs-table-body").children[0];
  const rowSource = row.querySelectorAll("a").find(
    (link) => link.textContent === "Source: Careers at Graphwise"
  );
  assert.equal(rowSource.href, "https://graphwise.ai/careers/");

  app.media.setWidth(760);
  const card = app.document.getElementById("jobs-cards").children[0];
  const cardSource = card.querySelectorAll("a").find(
    (link) => link.textContent === "Source: Careers at Graphwise"
  );
  assert.equal(cardSource.href, "https://graphwise.ai/careers/");
  assert.doesNotMatch(card.textContent, /RDF and ontology engineering/);
});

test("job catalog chip hover text meets WCAG AA contrast", () => {
  const color = STYLE_SOURCE.match(/--brand-strong:\s*(#[0-9a-f]{6})/i)[1];
  const background = STYLE_SOURCE.match(
    /\.catalog-mention-chip a:hover\s*\{[^}]*background:\s*(#[0-9a-f]{6})/is
  )[1];
  const hoverColor = STYLE_SOURCE.match(
    /\.catalog-mention-chip a:hover\s*\{[^}]*color:\s*var\(--brand-strong\)/is
  );
  assert.ok(hoverColor);

  function luminance(hex) {
    const channels = [1, 3, 5]
      .map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255)
      .map((value) =>
        value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
      );
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  }
  const values = [luminance(color), luminance(background)].sort((a, b) => b - a);
  assert.ok((values[0] + 0.05) / (values[1] + 0.05) >= 4.5);
});


test("resource release sorting and mobile dates preserve missing and coarse precision", async () => {
  const resources = [
    { title: "Undated", wikidataId: "https://www.wikidata.org/wiki/Q700001", types: ["Ontology"], latestVersion: "1" },
    { title: "Year release", wikidataId: "https://www.wikidata.org/wiki/Q700002", types: ["Ontology"], latestVersion: "2", releaseDate: "2024" },
    { title: "Month release", wikidataId: "https://www.wikidata.org/wiki/Q700003", types: ["Ontology"], latestVersion: "3", releaseDate: "2025-07" },
  ];
  const app = await createApp({ payloads: defaultPayloads(resources, []), search: "?tab=ontologies&sort=releaseDate&order=desc" });
  const rows = app.document.getElementById("ontologies-table-body").children;
  assert.deepEqual(rows.map(row => row.children[0].textContent), ["Month release", "Year release", "Undated"]);
  assert.match(rows[0].children[5].textContent, /3.*Jul.*2025/);
  assert.equal(rows[1].children[5].textContent, "2 · 2024");
  assert.equal(rows[2].children[5].textContent, "1");
  const mobile = await createApp({ payloads: defaultPayloads(resources, []), width: 400 });
  const text = mobile.document.getElementById("ontologies-cards").textContent;
  assert.match(text, /2024/); assert.doesNotMatch(text, /Jan 1, 2024|Jul 1, 2025/);
});

test("jobs default to discovery date and keep source posting dates separate", async () => {
  const payloads = defaultPayloads([], []);
  payloads.jobs = [
    { id: "old", title: "Old job reposted", firstSeenAt: "2026-08-01T00:00:00Z", datePosted: "2026-09-21" },
    { id: "new", title: "New discovery", firstSeenAt: "2026-09-20T00:00:00Z", datePosted: "2026-08-01" },
    { id: "unknown", title: "Unknown discovery", datePosted: "2026-09-22" },
  ].map(row => ({ ...row, classification: "qualified", active: true }));
  const app = await createApp({ payloads, search: "?tab=jobs" });
  const rows = app.document.getElementById("jobs-table-body").children;
  assert.deepEqual(rows.map(row => row.children[0].textContent), ["New discovery", "Old job reposted", "Unknown discovery"]);
  assert.match(rows[0].children[4].textContent, /Sep.*20.*2026/);
  assert.match(rows[0].children[5].textContent, /Aug.*1.*2026/);
  const byPosted = await createApp({ payloads, search: "?tab=jobs&sort=datePosted&order=desc" });
  assert.equal(byPosted.document.getElementById("jobs-table-body").children[0].children[0].textContent, "Unknown discovery");
  const mobile = await createApp({ payloads, width: 400, search: "?tab=jobs" });
  assert.match(mobile.document.getElementById("jobs-cards").textContent, /Added to OKG/);
  assert.match(mobile.document.getElementById("jobs-cards").textContent, /Posted/);
});

test("recent activity uses actual dates, distinct identities, eligibility, and a five-item limit", () => {
  const select = vm.runInNewContext(`${namedFunctionSource(APP_SOURCE, "activityDateEnd")}\n${namedFunctionSource(APP_SOURCE, "selectRecentActivity")}\nselectRecentActivity`);
  const entry = (identity, date, extra = {}) => ({ identity, date, title: identity, type: "release", eligible: true, url: "https://example.org/", ...extra });
  const entries = [entry("old", "2020-01-01", {discoveredAt: "2026-09-21"}),
    entry("future", "2026-09-22"), entry("unfinished-month", "2026-09"),
    entry("invalid", "2026-02-30"), entry("withdrawn", "2026-09-21", {eligible: false}),
    entry("bad-url", "2026-09-21", {url: "javascript:alert(1)"}),
    entry("a", "2026-09-20"), entry("a", "2026-09-19", {type: "new-to-okg"}),
    ...["b", "c", "d", "e", "f"].map(id => entry(id, "2026-09-18"))];
  assert.deepEqual(Array.from(select(entries, new Date("2026-09-21")), e => e.identity), ["a", "b", "c", "d", "e"]);
  assert.equal(select([entry("month", "2026-08")], new Date("2026-09-21")).length, 1);
});

test("activity resolves QID variants and registered pages, labels dates, and excludes unqualified or expired jobs", async () => {
  const resources = syntheticItems(3, "Resource");
  const software = syntheticItems(3, "Software");
  const payloads = defaultPayloads(resources, software);
  const today = new Date().toISOString().slice(0, 10);
  delete payloads.page_qids.resource[resources[1].wikidataId.split("/").pop()];
  payloads["catalog-events"] = {events: [...resources, ...software].map((item, i) => ({
    identity: `item-${i}`, title: "Old title", kind: i < 3 ? "resource" : "software", eligible: true,
    wikidataId: `http://www.wikidata.org/entity/${item.wikidataId.split("/").pop()}`,
    type: i % 3 === 2 ? "new-to-okg" : "release", date: today, release: {version: "1.2"},
  }))};
  payloads.jobs = [
    { id: "ok", title: "Qualified job", classification: "qualified", active: true, datePosted: today, canonicalUrl: "https://example.org/job" },
    { id: "review", title: "Needs review", classification: "review", datePosted: today, canonicalUrl: "https://example.org/review" },
    { id: "expired", title: "Expired", classification: "qualified", datePosted: today, validThrough: "2000-01-01", canonicalUrl: "https://example.org/expired" },
  ];
  const app = await createApp({payloads});
  const list = app.document.getElementById("new-ontologies");
  assert.equal(list.children.length, 2);
  assert.doesNotMatch(list.textContent, /Added to OKG|Resource 00002/);
  const softwareList = app.document.getElementById("new-software");
  assert.equal(softwareList.children.length, 2);
  assert.match(softwareList.textContent, /Released/);
  assert.doesNotMatch(softwareList.textContent, /Added to OKG|Software 00002/);
  assert.match(list.textContent, /Released/);
  assert.equal(list.querySelectorAll("a")[0].href, "./resource/resource-resource-00000/");
  assert.match(list.querySelectorAll("a")[1].href, /^https:\/\/www.wikidata.org\/wiki\/Q/);
  assert.equal(app.document.getElementById("new-jobs").children.length, 1);
  assert.match(app.document.getElementById("new-jobs").textContent, /Qualified job/);
  const failed = await createApp({payloads, failures: ["catalog-events"]});
  assert.match(failed.document.getElementById("new-ontologies").textContent, /temporarily unavailable/);
  assert.match(failed.document.getElementById("new-jobs").textContent, /Qualified job/);
  assert.equal(failed.document.getElementById("ontologies-table-body").children.length, 3);
});

test("current activity feed renders up to five linked entries in each homepage box", async () => {
  const read = name => JSON.parse(fs.readFileSync(path.join(ROOT, "data", name), "utf8"));
  const payloads = defaultPayloads([], []);
  Object.assign(payloads, {
    ontologies: read("ontologies.json"), software: read("software.json"),
    page_qids: read("page_qids.json"), jobs: read("jobs/jobs.json"),
    "catalog-events": read("catalog-events.json"),
  });
  const app = await createApp({payloads});
  // Live snapshots age: verify the selected rows against the same 90-day window.
  for (const tab of ["ontologies", "software", "jobs"]) {
    const list = app.document.getElementById(`new-${tab}`);
    const links = list.querySelectorAll("a");
    assert.ok(links.length <= 5);
    if (tab === "software") {
      const cutoff = new Date().getTime() - 89 * 86400000;
      const recent = payloads.software.items.filter(item => item.latestVersion &&
        Date.parse(item.releaseDate) >= cutoff && Date.parse(item.releaseDate) <= Date.now());
      if (recent.length >= 5) assert.equal(links.length, 5, "recent catalog releases must populate the box");
    }
    assert.equal(links.length, list.querySelectorAll("time").length);
    for (const link of links) assert.ok(link.href.startsWith("./") || /^https?:\/\//.test(link.href));
    assert.doesNotMatch(list.textContent, /temporarily unavailable|Loading/);
  }
});


test("software activity displays catalog release dates when legacy software has no ledger releases", async () => {
  const software = syntheticItems(8, "Software");
  const date = new Date();
  for (const [index, item] of software.entries()) {
    item.latestVersion = `1.${index}`;
    item.releaseDate = new Date(date.getTime() - index * 86400000).toISOString().slice(0, 10);
  }
  const payloads = defaultPayloads([], software);
  payloads["catalog-events"] = {events: [{ kind: "software", type: "release", eligible: false,
    wikidataId: software[0].wikidataId, identity: "withdrawn", date: software[0].releaseDate }]};
  software[1].latestRelease = { ambiguous: true };
  const app = await createApp({payloads});
  const list = app.document.getElementById("new-software");
  assert.deepEqual(list.querySelectorAll("a").map(link => link.textContent),
    software.slice(2, 7).map(item => item.title));
  assert.deepEqual(list.querySelectorAll("time").map(time => time.getAttribute("datetime")),
    software.slice(2, 7).map(item => item.releaseDate));
  assert.doesNotMatch(list.textContent, /No recent activity/);
});

test("homepage scripts and styles use matching content versions to avoid stale CDN assets", () => {
  const {createHash} = require("node:crypto");
  for (const asset of ["style.css", "contribute.css", "app.js", "contribute.js", "shared-tags.css", "shared-tags.js"]) {
    const digest = createHash("sha256").update(fs.readFileSync(path.join(ROOT, "site", asset))).digest("hex").slice(0, 12);
    assert.ok(SITE_SOURCE.includes(`./${asset}?v=${digest}"`), `refresh the homepage content version for ${asset}`);
  }
});
