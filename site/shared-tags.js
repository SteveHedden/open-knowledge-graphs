/* Shared OR-within / AND-across matching used by the catalog, comparison and API. */
(function (root) {
  const dimensions = ["tools", "activities", "domains"];
  function termIndex(vocabulary) {
    const index = new Map((vocabulary?.terms || []).map(t => [t.id, t]));
    index.pages = new Map(); index.children = new Map(); index.expanded = new Map();
    for (const t of index.values()) {
      for (const page of t.catalogIdentities || t.catalogPages || []) index.pages.set(page, t.id);
      for (const parent of t.broader || []) { if (!index.children.has(parent)) index.children.set(parent, []); index.children.get(parent).push(t.id); }
    }
    return index;
  }
  function descendants(index, id) {
    if (index.expanded?.has(id)) return index.expanded.get(id);
    const found = new Set(), pending = [id];
    while (pending.length) { const next = pending.pop(); if (found.has(next)) continue; found.add(next); pending.push(...(index.children?.get(next) || [])); }
    index.expanded?.set(id, found); return found;
  }

  function selections(params) {
    return Object.fromEntries(dimensions.map(d => [d, params.getAll(d).flatMap(v => v.split(",")).filter(Boolean)]));
  }
  function matches(item, selected, index, includeOwnIdentity = true) {
    return dimensions.every(d => {
      if (!(selected[d] || []).length) return true;
      const accepted = new Set((item.sharedTags?.[d] || []).map(t => t.id));
      if (d === "tools" && includeOwnIdentity && item.wikidataId) {
        const own = index.pages?.get(item.canonicalUrl); if (own) accepted.add(own);
      }
      return selected[d].some(id => [...descendants(index, id)].some(candidate => accepted.has(candidate)));
    });
  }
  function uniqueCatalog(items) {
    const byId = new Map();
    for (const item of items) {
      const id = item.wikidataId || item.canonicalUrl;
      if (!byId.has(id)) byId.set(id, { ...item, sharedTags: { ...(item.sharedTags || {}) } });
      else {
        const prior = byId.get(id);
        for (const dim of dimensions) prior.sharedTags[dim] = [...new Map([...(prior.sharedTags[dim] || []), ...(item.sharedTags?.[dim] || [])].map(t => [t.id, t])).values()];
      }
    }
    return [...byId.values()];
  }
  function eligibleJobs(items) {
    return [...new Map(items.filter(r => r.active !== false && ["qualified", "review"].includes(r.classification)).map(r => [r.canonicalFingerprint || r.canonicalUrl || r.id, r])).values()];
  }
  function coverageRows(resources, software, jobs, index, dimension) {
    const rows = new Map();
    function add(item, kind) {
      const ids = new Set((item.sharedTags?.[dimension] || []).map(t => t.id));
      if (dimension === "tools" && kind !== "jobs") { const own = index.pages?.get(item.canonicalUrl); if (own) ids.add(own); }
      const pending = [...ids];
      while (pending.length) for (const parent of index.get(pending.pop())?.broader || []) if (!ids.has(parent)) { ids.add(parent); pending.push(parent); }
      for (const id of ids) {
        const term = index.get(id); if (!term || term.dimension !== dimension) continue;
        if (!rows.has(id)) rows.set(id, {id,label:term.label,resources:new Set(),software:new Set(),catalogEntities:new Set(),jobs:new Set(),employers:new Set()});
        const row = rows.get(id);
        if (kind === "jobs") { row.jobs.add(item.canonicalFingerprint || item.canonicalUrl || item.id); const employer = item.organizationIri || String(item.hiringOrganization || "").trim().toLowerCase(); if (employer) row.employers.add(employer); }
        else { row[kind].add(item.canonicalUrl); row.catalogEntities.add(item.wikidataId || item.canonicalUrl); }
      }
    }
    for (const item of resources) add(item,"resources"); for (const item of software) add(item,"software"); for (const item of jobs) add(item,"jobs");
    return [...rows.values()].map(row => Object.fromEntries(Object.entries(row).map(([k,v])=>[k,v instanceof Set ? v.size : v]))).sort((a,b)=>b.jobs-a.jobs||b.catalogEntities-a.catalogEntities||a.label.localeCompare(b.label));
  }
  function tagChips(container, item, document, pageUrls = new Set()) {
    const row = document.createElement("ul"); row.className = "catalog-mentions";
    row.setAttribute("aria-label", "Catalog resources mentioned in this posting");
    const seen = new Set();
    for (const tag of item.sharedTags?.tools || []) {
      for (const url of tag.catalogPages || []) {
        if (!pageUrls.has(url) || seen.has(url) || !/^https:\/\/openknowledgegraphs\.com\/(resource|software)\//.test(url)) continue;
        seen.add(url);
        const entry = document.createElement("li"); entry.className = "catalog-mention-chip";
        const link = document.createElement("a"); link.href = url; link.textContent = tag.label;
        entry.appendChild(link); row.appendChild(entry);
      }
    }
    if (seen.size) container.appendChild(row);
  }
  root.OKGTags = { dimensions, termIndex, descendants, selections, matches, uniqueCatalog, eligibleJobs, coverageRows, tagChips };
})(globalThis);
