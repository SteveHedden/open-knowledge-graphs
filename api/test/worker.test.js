import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import worker, { resetCatalogCache } from "../src/index.js";

function makeDb({ rows = {}, latest = null } = {}) {
  return {
    prepare(sql) {
      const statement = {
        args: [],
        bind(...args) {
          this.args = args;
          return this;
        },
        async first() {
          if (sql.includes("WHERE generation_id = ?")) return rows[this.args[0]] || null;
          if (sql.includes("WHERE status = 'ready'")) return latest;
          return null;
        },
        async run() {
          return { success: true };
        },
      };
      return statement;
    },
  };
}

function originFixture(initial = {}) {
  const state = {
    generationId: initial.generationId || "G1",
    ontologies: initial.ontologies || [],
    software: initial.software || [],
    failDatasets: false,
    datasetFetches: 0,
    datasetUrls: [],
    digestOverrides: {},
    countOverrides: {},
    beforeDatasetResponse: null,
  };

  const datasetText = (dataset) => JSON.stringify({ items: state[dataset] });
  const digest = (text) => createHash("sha256").update(text).digest("hex");
  const manifest = () => ({
    generationId: state.generationId,
    counts: {
      records: {
        resources: state.countOverrides.ontologies ?? state.ontologies.length,
        software: state.countOverrides.software ?? state.software.length,
      },
    },
    artifacts: ["ontologies", "software"].map((dataset) => ({
      path: `data/${dataset}.json`,
      sha256: state.digestOverrides[dataset] || digest(datasetText(dataset)),
    })),
  });
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith("/data/manifest.json")) {
      return Response.json(manifest());
    }
    const match = url.pathname.match(/\/data\/(ontologies|software)\.json$/);
    if (match) {
      state.datasetFetches += 1;
      state.datasetUrls.push(url);
      if (state.failDatasets) return new Response("unavailable", { status: 503 });
      if (state.beforeDatasetResponse) state.beforeDatasetResponse(match[1]);
      return new Response(datasetText(match[1]), {
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };
  return { state, fetchImpl };
}

async function requestJson(env, path) {
  const response = await worker.fetch(new Request(`https://api.test${path}`), env);
  return { response, body: await response.json() };
}

function withFetch(t, fetchImpl) {
  const original = globalThis.fetch;
  globalThis.fetch = fetchImpl;
  resetCatalogCache();
  t.after(() => {
    globalThis.fetch = original;
    resetCatalogCache();
  });
}

test("queries only the ready live namespace and reports semantic generation metadata", async (t) => {
  const origin = originFixture();
  withFetch(t, origin.fetchImpl);
  let options;
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ rows: { G1: { generation_id: "G1", status: "ready", vector_count: 1 } } }),
    AI: { run: async () => ({ data: [[0.1, 0.2]] }) },
    VECTORIZE: {
      query: async (_embedding, queryOptions) => {
        options = queryOptions;
        return {
          matches: [
            {
              id: "G1:software:Q1",
              namespace: "G1",
              score: 0.9,
              metadata: {
                generationId: "G1",
                dataset: "software",
                title: "Graph tool",
                wikidataId: "https://www.wikidata.org/wiki/Q1",
              },
            },
          ],
        };
      },
    },
  };

  const { response, body } = await requestJson(env, "/software?q=graph");
  assert.equal(response.status, 200);
  assert.equal(options.namespace, "G1");
  assert.equal(options.filter.dataset, "software");
  assert.equal(body.searchMode, "semantic");
  assert.equal(body.catalogGenerationId, "G1");
  assert.equal(body.vectorGenerationId, "G1");
  assert.equal(body.fallbackReason, null);
  assert.equal(origin.state.datasetFetches, 0);
});

test("generation mismatch never queries stale vectors and falls back to current JSON", async (t) => {
  const origin = originFixture({
    software: [
      {
        title: "Current graph tool",
        wikidataId: "https://www.wikidata.org/wiki/Q2",
        programmingLanguages: ["Rust"],
      },
    ],
  });
  withFetch(t, origin.fetchImpl);
  let vectorQueries = 0;
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ latest: { generation_id: "G0", vector_count: 1 } }),
    AI: { run: async () => ({ data: [[0.1]] }) },
    VECTORIZE: { query: async () => (vectorQueries += 1) },
  };

  const { body } = await requestJson(env, "/software?q=Rust");
  assert.equal(vectorQueries, 0);
  assert.equal(body.searchMode, "text-fallback");
  assert.equal(body.catalogGenerationId, "G1");
  assert.equal(body.vectorGenerationId, "G0");
  assert.equal(body.fallbackReason, "generation-mismatch");
  assert.equal(body.results[0].title, "Current graph tool");
});

test("an incomplete current namespace reports index-not-ready", async (t) => {
  const origin = originFixture({ software: [{ title: "Tool", wikidataId: "https://www.wikidata.org/wiki/Q3" }] });
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({
      rows: { G1: { generation_id: "G1", status: "seeding" } },
      latest: { generation_id: "G0" },
    }),
    AI: { run: async () => ({ data: [[0.1]] }) },
    VECTORIZE: { query: async () => assert.fail("incomplete namespace was queried") },
  };
  const { body } = await requestJson(env, "/software?q=Tool");
  assert.equal(body.fallbackReason, "index-not-ready");
  assert.equal(body.vectorGenerationId, "G0");
});

test("Workers AI failure returns current-generation text fallback", async (t) => {
  const origin = originFixture({ software: [{ title: "Fallback Tool", wikidataId: "https://www.wikidata.org/wiki/Q4" }] });
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ rows: { G1: { generation_id: "G1", status: "ready" } } }),
    AI: { run: async () => { throw new Error("AI unavailable"); } },
    VECTORIZE: { query: async () => assert.fail("query should not run without embedding") },
  };
  const { response, body } = await requestJson(env, "/software?q=Fallback");
  assert.equal(response.status, 200);
  assert.equal(body.searchMode, "text-fallback");
  assert.equal(body.fallbackReason, "embedding-error");
  assert.equal(body.catalogGenerationId, "G1");
  assert.equal(body.vectorGenerationId, "G1");
});

test("Vectorize failure returns current-generation text fallback", async (t) => {
  const origin = originFixture({ ontologies: [{ title: "Fallback Ontology", wikidataId: "https://www.wikidata.org/wiki/Q5" }] });
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ rows: { G1: { generation_id: "G1", status: "ready" } } }),
    AI: { run: async () => ({ data: [[0.1]] }) },
    VECTORIZE: { query: async () => { throw new Error("Vectorize unavailable"); } },
  };
  const { body } = await requestJson(env, "/ontologies?q=Fallback");
  assert.equal(body.searchMode, "text-fallback");
  assert.equal(body.fallbackReason, "vector-error");
  assert.equal(body.results[0].title, "Fallback Ontology");
});

test("a stale vector result is rejected rather than merged with current fallback", async (t) => {
  const origin = originFixture({
    software: [{ title: "Current Only", wikidataId: "https://www.wikidata.org/wiki/Q8" }],
  });
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ rows: { G1: { generation_id: "G1", status: "ready" } } }),
    AI: { run: async () => ({ data: [[0.1]] }) },
    VECTORIZE: {
      query: async () => ({
        matches: [
          {
            namespace: "G0",
            score: 1,
            metadata: {
              generationId: "G0",
              dataset: "software",
              title: "Stale Result",
              wikidataId: "https://www.wikidata.org/wiki/Q9",
            },
          },
        ],
      }),
    },
  };
  const { body } = await requestJson(env, "/software?q=Current");
  assert.equal(body.searchMode, "text-fallback");
  assert.equal(body.fallbackReason, "vector-error");
  assert.deepEqual(body.results.map(({ title }) => title), ["Current Only"]);
});

test("returns 503 only when current static fallback data is also unavailable", async (t) => {
  const origin = originFixture();
  origin.state.failDatasets = true;
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ latest: { generation_id: "G0" } }),
    AI: { run: async () => ({ data: [[0.1]] }) },
    VECTORIZE: { query: async () => assert.fail("stale vectors must not be queried") },
  };
  const { response, body } = await requestJson(env, "/search?q=graph");
  assert.equal(response.status, 503);
  assert.equal(body.searchMode, "unavailable");
  assert.equal(body.catalogGenerationId, "G1");
});

test("static fallback rejects bytes that do not match the live manifest digest", async (t) => {
  const origin = originFixture({
    software: [{ title: "Untrusted", wikidataId: "https://www.wikidata.org/wiki/Q10" }],
  });
  origin.state.digestOverrides.software = "0".repeat(64);
  withFetch(t, origin.fetchImpl);
  const { response, body } = await requestJson(
    { ORIGIN: "https://origin.test", DB: makeDb() },
    "/software?q=Untrusted"
  );
  assert.equal(response.status, 503);
  assert.match(body.error, /digest mismatch/);
});

test("static fallback rejects a record count that differs from the live manifest", async (t) => {
  const origin = originFixture({
    ontologies: [{ title: "Counted", wikidataId: "https://www.wikidata.org/wiki/Q11" }],
  });
  origin.state.countOverrides.ontologies = 2;
  withFetch(t, origin.fetchImpl);
  const { response, body } = await requestJson(
    { ORIGIN: "https://origin.test", DB: makeDb() },
    "/ontologies?q=Counted"
  );
  assert.equal(response.status, 503);
  assert.match(body.error, /count mismatch/);
});

test("manifest generation change invalidates cached datasets before TTL", async (t) => {
  const origin = originFixture({
    generationId: "G1",
    software: [{ title: "Alpha", wikidataId: "https://www.wikidata.org/wiki/Q6" }],
  });
  withFetch(t, origin.fetchImpl);
  const env = { ORIGIN: "https://origin.test", DB: makeDb() };

  const first = await requestJson(env, "/software?q=Alpha");
  assert.equal(first.body.results[0].title, "Alpha");
  origin.state.generationId = "G2";
  origin.state.software = [{ title: "Beta", wikidataId: "https://www.wikidata.org/wiki/Q7" }];
  const second = await requestJson(env, "/software?q=Beta");
  assert.equal(second.body.catalogGenerationId, "G2");
  assert.equal(second.body.results[0].title, "Beta");
  assert.equal(origin.state.datasetFetches, 2);
  assert.deepEqual(
    origin.state.datasetUrls.map((url) => url.searchParams.get("catalog-generation")),
    ["G1", "G2"]
  );
  assert.equal(
    origin.state.datasetUrls.every((url) => /^[a-f0-9]{64}$/.test(url.searchParams.get("artifact-sha256"))),
    true
  );
});

test("fallback retries against a new manifest instead of serving mixed-generation bytes", async (t) => {
  const origin = originFixture({
    generationId: "G1",
    software: [{ title: "Alpha", wikidataId: "https://www.wikidata.org/wiki/Q12" }],
  });
  origin.state.beforeDatasetResponse = () => {
    origin.state.beforeDatasetResponse = null;
    origin.state.generationId = "G2";
    origin.state.software = [
      { title: "Beta", wikidataId: "https://www.wikidata.org/wiki/Q13" },
    ];
  };
  withFetch(t, origin.fetchImpl);

  const { response, body } = await requestJson(
    { ORIGIN: "https://origin.test", DB: makeDb() },
    "/software?q=Beta"
  );
  assert.equal(response.status, 200);
  assert.equal(body.catalogGenerationId, "G2");
  assert.deepEqual(body.results.map(({ title }) => title), ["Beta"]);
  assert.equal(origin.state.datasetFetches, 2);
});

test("root and health expose live generation and semantic mode", async (t) => {
  const origin = originFixture({ ontologies: [{ title: "O" }], software: [{ title: "S" }] });
  withFetch(t, origin.fetchImpl);
  const env = {
    ORIGIN: "https://origin.test",
    DB: makeDb({ rows: { G1: { generation_id: "G1", status: "ready", vector_count: 2 } } }),
    AI: {},
    VECTORIZE: {},
  };
  for (const path of ["/", "/health"]) {
    const { response, body } = await requestJson(env, path);
    assert.equal(response.status, 200);
    assert.equal(body.status, "ok");
    assert.equal(body.searchMode, "semantic");
    assert.equal(body.catalogGenerationId, "G1");
    assert.equal(body.vectorGenerationId, "G1");
    assert.equal(body.total_ontologies, 1);
    assert.equal(body.total_software, 1);
  }
});

test("shared tag comparison verifies snapshots and counts unique supply against eligible jobs",async(t)=>{
 const domain={id:'https://test/health',label:'Health',dimension:'domains',broader:[]},child={id:'https://test/clinical',label:'Clinical',dimension:'domains',broader:[domain.id]};
 const resource={title:'Clinical vocabulary',wikidataId:'Q1',canonicalUrl:'https://test/resource',sharedTags:{domains:[{id:child.id,label:child.label}]}};
 const job={id:'job1',active:true,classification:'qualified',canonicalFingerprint:'job-1',hiringOrganization:'Employer',sharedTags:{domains:[{id:child.id,label:child.label}]}};
 const documents={
  'data/ontologies.json':{items:[resource]},'data/software.json':{items:[{...resource,canonicalUrl:'https://test/software'}]},
  'data/tag-vocabularies.json':{version:'1.0.0',terms:[domain,child]},'data/jobs/jobs.json':[job,{...job,id:'copy'}, {...job,id:'ineligible',classification:'not_match',canonicalFingerprint:'job-2'}],
 };
 const artifacts=Object.entries(documents).map(([path,value])=>({path,sha256:createHash('sha256').update(JSON.stringify(value)).digest('hex')}));
 documents['data/manifest.json']={generationId:'G1',counts:{records:{resources:1,software:1}},artifacts:artifacts.filter(a=>!a.path.startsWith('data/jobs/'))};
 documents['data/jobs/manifest.json']={generationId:'J1',artifacts:artifacts.filter(a=>a.path.startsWith('data/jobs/'))};
 withFetch(t,async(input)=>{const path=new URL(String(input)).pathname.replace(/^\//,'');return new Response(JSON.stringify(documents[path]),{headers:{'Content-Type':'application/json'}});});
 const response=await requestJson({ORIGIN:'https://test'},'/tag-comparison?dimension=domains&domains='+encodeURIComponent(domain.id));
 assert.equal(response.response.status,200);assert.deepEqual(response.body.totals,{resources:1,software:1,catalogEntities:1,jobs:1});
 assert.equal(response.body.counts.find(r=>r.id===domain.id).employers,1);
 const filtered=await requestJson({ORIGIN:'https://test'},'/search?domains='+encodeURIComponent(domain.id));
 assert.equal(filtered.response.status,200);assert.equal(filtered.body.total,2);assert.equal(filtered.body.fallbackReason,'shared-tag-filter');
 documents['data/jobs/jobs.json'].push({...job,id:'tampered'});
 const invalid=await requestJson({ORIGIN:'https://test'},'/tag-comparison');
 assert.equal(invalid.response.status,503);assert.match(invalid.body.error,/digest mismatch/);
});
