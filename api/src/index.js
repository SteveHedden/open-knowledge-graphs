const CACHE_TTL = 60 * 60; // 1 hour
const EMBED_MODEL = "@cf/baai/bge-base-en-v1.5";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return json(null, 204);
    }
    if (request.method !== "GET") {
      return json({ error: "Method not allowed" }, 405);
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (path === "/" || path === "") return handleRoot(env);
      if (path === "/search" || path === "/ontologies" || path === "/software") {
        return handleSearch(url, env, path);
      }
      return json({ error: "Not found" }, 404);
    } catch (err) {
      return json({ error: err.message }, 500);
    }
  },
};

async function handleRoot(env) {
  const [ontologies, software] = await Promise.all([
    getData(env, "ontologies"),
    getData(env, "software"),
  ]);

  return json({
    name: "Open Knowledge Graphs API",
    description:
      "Semantic search over 1,800+ ontologies, vocabularies, taxonomies, and semantic software tools cataloged from Wikidata.",
    endpoints: {
      "/search":
        "Semantic search across all resources. Params: q, category, type (ontology|software), limit",
      "/ontologies":
        "Semantic search ontologies/vocabularies/taxonomies. Params: q, category, limit",
      "/software": "Semantic search semantic software tools. Params: q, limit",
    },
    categories: [
      "Life Sciences & Healthcare",
      "Geospatial",
      "Government & Public Sector",
      "International Development",
      "Finance & Business",
      "Library & Cultural Heritage",
      "Technology & Web",
      "Environment & Agriculture",
      "General / Cross-domain",
    ],
    source: "https://openknowledgegraphs.com",
    total_ontologies: ontologies.length,
    total_software: software.length,
  });
}

async function handleSearch(url, env, path) {
  const q = (url.searchParams.get("q") || "").trim();
  const category = url.searchParams.get("category") || "";
  const type = url.searchParams.get("type") || "";
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "20", 10), 100);

  if (!q) {
    return json({ error: "Query parameter 'q' is required" }, 400);
  }

  // Use semantic search if Vectorize is available, else fall back to text search
  if (env.VECTORIZE) {
    return semanticSearch(env, { q, category, type, limit, path });
  }
  return textSearch(env, { q, category, type, limit, path });
}

// --- Semantic search via Workers AI + Vectorize ---

async function semanticSearch(env, { q, category, type, limit, path }) {
  // Build metadata filter
  const filter = {};
  if (path === "/ontologies" || type === "ontology") filter.dataset = "ontologies";
  if (path === "/software" || type === "software") filter.dataset = "software";
  if (category) filter.category = category;

  // Embed query
  const embedding = await embed(env, q);

  // Query Vectorize
  const results = await env.VECTORIZE.query(embedding, {
    topK: limit,
    filter: Object.keys(filter).length > 0 ? filter : undefined,
    returnMetadata: "all",
  });

  const items = results.matches.map(formatVectorResult);

  await logQuery(env, { q, category, type, path, total: items.length });

  return json({ query: q, category: category || null, total: items.length, results: items });
}

function formatVectorResult(match) {
  const m = match.metadata || {};
  const result = {
    score: match.score,
    title: m.title,
    wikidataId: m.wikidataId,
  };
  if (m.description) result.description = m.description;
  if (m.types) result.types = m.types.split(", ").filter(Boolean);
  if (m.category) result.category = m.category;
  if (m.homepage) result.homepage = m.homepage;
  if (m.sourceRepo) result.sourceRepo = m.sourceRepo;
  if (m.licenses) result.licenses = m.licenses.split(", ").filter(Boolean);
  if (m.latestVersion) result.latestVersion = m.latestVersion;
  if (m.releaseDate) result.releaseDate = m.releaseDate;
  if (m.partOf) result.partOf = m.partOf;
  return result;
}

async function embed(env, text) {
  const result = await env.AI.run(EMBED_MODEL, { text: [text] });
  return result.data[0];
}

// --- Text search fallback (for local dev without Vectorize) ---

async function textSearch(env, { q, category, type, limit, path }) {
  let datasets = [];
  if (path !== "/software" && type !== "software") {
    datasets.push(await getData(env, "ontologies"));
  }
  if (path !== "/ontologies" && type !== "ontology") {
    datasets.push(await getData(env, "software"));
  }

  const terms = q.toLowerCase().split(/\s+/);
  let results = [];

  for (const items of datasets) {
    for (const item of items) {
      if (category && (item.category || "").toLowerCase() !== category.toLowerCase()) continue;
      const text = [
        item.title,
        item.description,
        (item.types || []).join(" "),
        item.category,
        (item.licenses || []).join(" "),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (terms.every((t) => text.includes(t))) {
        results.push(item);
      }
    }
  }

  const total = results.length;
  const paged = results.slice(0, limit);

  await logQuery(env, { q, category, type, path, total });

  return json({ query: q, category: category || null, total, results: paged });
}

// --- Data loading with in-memory cache ---

let cache = {};

async function getData(env, dataset) {
  const now = Date.now();
  if (cache[dataset] && now - cache[dataset].fetchedAt < CACHE_TTL * 1000) {
    return cache[dataset].items;
  }

  const url = `${env.ORIGIN}/data/${dataset}.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);

  const data = await res.json();
  const items = data.items || [];
  cache[dataset] = { items, fetchedAt: now };
  return items;
}

// --- Helpers ---

async function logQuery(env, { q, category, type, path, total }) {
  const timestamp = new Date().toISOString();
  console.log(JSON.stringify({ event: "search", q, category: category || null, type: type || null, path, results: total, timestamp }));

  if (env.DB) {
    try {
      await env.DB.prepare(
        "INSERT INTO queries (query, category, type, path, results, timestamp) VALUES (?, ?, ?, ?, ?, ?)"
      ).bind(q, category || null, type || null, path, total, timestamp).run();
    } catch (e) {
      console.error("D1 log error:", e.message);
    }
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}
