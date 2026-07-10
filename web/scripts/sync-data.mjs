// Copies the pipeline's web-data/ JSON layer into public/data/ so the app
// (and Vercel builds, which clone the whole repo) always serve the current
// pipeline outputs. Run automatically via predev/prebuild.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "web-data");
const dest = join(here, "..", "public", "data");

if (!existsSync(src)) {
  console.error(`web-data/ not found at ${src} — run: python code/export_web_data.py`);
  process.exit(1);
}
mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });
console.log(`synced web-data -> public/data`);
