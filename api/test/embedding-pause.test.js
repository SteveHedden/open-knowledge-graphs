import test from "node:test";
import {main as seed} from "../scripts/seed.js";
import {main as verify} from "../scripts/verify-generation.js";
import {main as prune} from "../scripts/prune-generations.js";
import {main as provision} from "../scripts/provision-vectorize.js";

test("paused vector commands make no remote calls, even without credentials", async () => {
  const previous = process.env.EMBEDDINGS_PAUSED;
  process.env.EMBEDDINGS_PAUSED = "true";
  try { for (const command of [seed, verify, prune, provision]) await command(); }
  finally {
    if (previous === undefined) delete process.env.EMBEDDINGS_PAUSED;
    else process.env.EMBEDDINGS_PAUSED = previous;
  }
});
