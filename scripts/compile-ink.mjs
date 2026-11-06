import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";

const require = createRequire(import.meta.url);
const { Compiler } = require("../player/vendor/ink-full.js");

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: node scripts/compile-ink.mjs <input.ink> <output.json>");
  process.exit(2);
}

const source = readFileSync(resolve(input), "utf8");
const compiler = new Compiler(source);
const story = compiler.Compile();

if (compiler.errors && compiler.errors.length) {
  for (const error of compiler.errors) {
    console.error(String(error));
  }
  process.exit(1);
}
if (!story) {
  console.error("Compilation produced no story.");
  process.exit(1);
}

writeFileSync(resolve(output), story.ToJson(), "utf8");
console.log(`Compiled ${input} -> ${output}`);
