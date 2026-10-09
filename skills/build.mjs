#!/usr/bin/env node
// Renders skills/tinyfish-*/ into each surface's output dir; `make skills-check` uses git to catch drift.
import { readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

export const TARGETS = { mcp: 'grok/skills', pi: 'pi/skills' };

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)],
  );
}

export function parseSlots(text, file) {
  const slots = {};
  const parts = text.split(/^<!-- slot: ([a-z0-9-]+) -->$/m);
  for (let i = 1; i < parts.length; i += 2) {
    if (parts[i] in slots) throw new Error(`${file}: slot "${parts[i]}" defined twice`);
    slots[parts[i]] = parts[i + 1].trim();
  }
  return slots;
}

export function render(text, slots, file, target, used) {
  const out = text
    // An empty slot on its own line takes its trailing blank line with it.
    .replace(/^\{\{([a-z0-9-]+)\}\}\n\n?/gm, (m, k) => (slots[k] === '' ? (used.add(k), '') : m))
    .replace(/\{\{([a-z0-9-]+)\}\}/g, (_, k) => {
      if (!(k in slots)) throw new Error(`${file}: slot "${k}" is not defined for ${target}`);
      used.add(k);
      return slots[k];
    });
  const leftover = out.match(/\{\{[^}]*\}\}/);
  if (leftover) throw new Error(`${file} → ${target}: leftover placeholder ${leftover[0]}`);
  return out;
}

// Returns { [outputPathRelativeToRoot]: contents } for every target.
export function build(root) {
  const src = join(root, 'skills');
  const files = readdirSync(src)
    .filter((d) => d.startsWith('tinyfish-'))
    .flatMap((d) => walk(join(src, d)));
  const outputs = {};
  for (const [target, outDir] of Object.entries(TARGETS)) {
    const surface = `skills/surfaces/${target}.md`;
    const slots = parseSlots(readFileSync(join(root, surface), 'utf8'), surface);
    const used = new Set();
    for (const path of files) {
      const rel = relative(src, path);
      outputs[join(outDir, rel)] = render(readFileSync(path, 'utf8'), slots, `skills/${rel}`, target, used);
    }
    const unused = Object.keys(slots).filter((k) => !used.has(k));
    if (unused.length) throw new Error(`${surface}: slots never used: ${unused.join(', ')}`);
  }
  return outputs;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const outputs = build(root);
  for (const outDir of Object.values(TARGETS)) {
    for (const d of readdirSync(join(root, outDir))) {
      if (d.startsWith('tinyfish-')) rmSync(join(root, outDir, d), { recursive: true });
    }
  }
  for (const [p, text] of Object.entries(outputs)) {
    mkdirSync(dirname(join(root, p)), { recursive: true });
    writeFileSync(join(root, p), text);
  }
  console.log(`wrote ${Object.keys(outputs).length} files`);
}
