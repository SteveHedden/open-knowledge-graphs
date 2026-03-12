#!/usr/bin/env node

/**
 * Seeds the Vectorize index with embeddings from ontologies.json and software.json.
 *
 * Prerequisites:
 *   npx wrangler vectorize create okg-catalog --dimensions 768 --metric cosine
 *
 * Usage:
 *   CLOUDFLARE_ACCOUNT_ID=xxx CLOUDFLARE_API_TOKEN=xxx node scripts/seed.js
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const ACCOUNT_ID = process.env.CLOUDFLARE_ACCOUNT_ID;
const API_TOKEN = process.env.CLOUDFLARE_API_TOKEN;
const INDEX_NAME = "okg-catalog";
const EMBED_MODEL = "@cf/baai/bge-base-en-v1.5";
const BATCH_SIZE = 100;

const API_BASE = `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}`;
const headers = {
  Authorization: `Bearer ${API_TOKEN}`,
  "Content-Type": "application/json",
};

async function main() {
  if (!ACCOUNT_ID || !API_TOKEN) {
    console.error(
      "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN environment variables.\n" +
        "Create a token at https://dash.cloudflare.com/profile/api-tokens"
    );
    process.exit(1);
  }

  // Load data
  const dataDir = join(__dirname, "..", "..", "data");
  const ontologies = JSON.parse(readFileSync(join(dataDir, "ontologies.json"), "utf8"));
  const software = JSON.parse(readFileSync(join(dataDir, "software.json"), "utf8"));

  const items = [
    ...ontologies.items.map((i) => ({ ...i, dataset: "ontologies" })),
    ...software.items.map((i) => ({ ...i, dataset: "software" })),
  ];

  console.log(`Seeding ${items.length} items into Vectorize index "${INDEX_NAME}"...\n`);

  let processed = 0;

  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);

    // Build text for each item
    const texts = batch.map((item) =>
      [item.title, item.description, (item.types || []).join(", "), item.category]
        .filter(Boolean)
        .join(". ")
    );

    // Get embeddings from Workers AI
    const embedRes = await fetch(`${API_BASE}/ai/run/${EMBED_MODEL}`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text: texts }),
    });

    const embedData = await embedRes.json();
    if (!embedData.success) {
      console.error("Embedding error:", JSON.stringify(embedData.errors, null, 2));
      process.exit(1);
    }

    // Build NDJSON for Vectorize upsert
    const ndjson = batch
      .map((item, j) =>
        JSON.stringify({
          id: item.wikidataId,
          values: embedData.result.data[j],
          metadata: {
            title: item.title || "",
            description: item.description || "",
            types: (item.types || []).join(", "),
            category: item.category || "",
            dataset: item.dataset,
            homepage: item.homepage || "",
            licenses: (item.licenses || []).join(", "),
            wikidataId: item.wikidataId || "",
            ...(item.latestVersion ? { latestVersion: item.latestVersion } : {}),
            ...(item.releaseDate ? { releaseDate: item.releaseDate } : {}),
            ...(item.partOf ? { partOf: item.partOf } : {}),
          },
        })
      )
      .join("\n");

    // Upsert to Vectorize
    const upsertRes = await fetch(
      `${API_BASE}/vectorize/v2/indexes/${INDEX_NAME}/upsert`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/x-ndjson" },
        body: ndjson,
      }
    );

    const upsertData = await upsertRes.json();
    if (!upsertData.success) {
      console.error("Upsert error:", JSON.stringify(upsertData.errors, null, 2));
      process.exit(1);
    }

    processed += batch.length;
    console.log(`  ${processed}/${items.length} items`);
  }

  console.log(`\nDone! Seeded ${processed} items.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
