// Static integrity checks for the @tiny-fish/pi package. Run: node test/validate.mjs
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const failures = [];
const checks = [];

const fail = (name, msg) => failures.push(`${name}: ${msg}`);
const ok = (name) => checks.push(name);
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const readJson = (p) => JSON.parse(read(p));

const pkg = readJson('package.json');
const mcp = readJson('mcp.json');

// Pi's skill name rules, from its docs/skills.md: 1-64 chars, lowercase alnum and
// single hyphens, no leading/trailing hyphen. A violating name still loads but warns.
const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const MAX_DESC = 1024;

// Deliberately not a YAML parser. It recognises plain scalars and rejects everything else,
// so a form it cannot measure correctly fails loudly instead of being mis-measured: a block
// scalar (`description: |`) would otherwise read as the literal "|" and sail past the length
// cap that pi's real YAML parser would enforce against the full text.
function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return { error: 'no YAML frontmatter' };
  const out = {};
  const lines = m[1].split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || line.startsWith('#')) continue;
    const kv = line.match(/^([A-Za-z][A-Za-z0-9_-]*):(.*)$/);
    if (!kv) {
      if (/^\s/.test(line)) return { error: `frontmatter uses multi-line YAML at "${line.trim().slice(0, 40)}" — this package keeps name and description as single-line plain scalars` };
      return { error: `unparsable frontmatter line: ${line.slice(0, 60)}` };
    }
    const raw = kv[2].trim();
    if (/^[|>]/.test(raw)) {
      return { error: `"${kv[1]}" uses a block scalar (${raw[0]}); keep it a single-line plain scalar so its length can be checked` };
    }
    if (raw.startsWith('&') || raw.startsWith('*')) {
      return { error: `"${kv[1]}" uses a YAML anchor/alias; keep it a plain scalar` };
    }
    out[kv[1]] = raw.replace(/^["']|["']$/g, '');
  }
  return out;
}

function skillDirs() {
  const base = join(ROOT, 'skills');
  if (!existsSync(base)) return null;
  return readdirSync(base).filter((d) => statSync(join(base, d)).isDirectory());
}

// --- manifest ------------------------------------------------------------
{
  const name = 'manifest';
  if (pkg.name !== '@tiny-fish/pi') fail(name, `package name is ${pkg.name}`);
  if (!pkg.keywords?.includes('pi-package')) {
    fail(name, 'keywords must include "pi-package" — it is the entire gallery discovery mechanism');
  }
  if (!pkg.pi?.mcp) fail(name, 'pi.mcp is not declared');
  if (!pkg.pi?.skills?.length) fail(name, 'pi.skills is not declared');
  for (const p of [pkg.pi?.mcp, ...(pkg.pi?.skills ?? [])].filter(Boolean)) {
    if (!existsSync(join(ROOT, p))) fail(name, `pi manifest points at missing path ${p}`);
  }
  ok(name);
}

// --- mcp.json ------------------------------------------------------------
{
  const name = 'mcp';
  const server = mcp.mcpServers?.tinyfish;
  if (!server) {
    fail(name, 'mcpServers.tinyfish is missing');
  } else {
    if ('type' in server) {
      fail(name, 'ServerEntry has no "type" field — the adapter ignores it; a bare url means HTTP');
    }
    // The adapter interpolates /\$\{(\w+)\}/ only; ${VAR:-} ships as a literal header value.
    for (const [h, v] of Object.entries(server.headers ?? {})) {
      if (/\$\{[^}]*[^\w}][^}]*\}/.test(v)) {
        fail(name, `header ${h} uses an interpolation form the adapter cannot parse: ${v}`);
      }
    }
    // Without directTools the adapter registers nothing top-level; everything hides
    // behind the mcp proxy and the skills' tool names stop resolving.
    if (!Array.isArray(server.directTools) || server.directTools.length === 0) {
      fail(name, 'directTools must be a non-empty array or no tools register top-level');
    } else if (new Set(server.directTools).size !== server.directTools.length) {
      fail(name, 'directTools contains duplicates');
    }
    ok(name);
  }
}

// --- skills --------------------------------------------------------------
const dirs = skillDirs();
if (!dirs) {
  fail('skills', 'skills/ directory is missing');
} else {
  const seen = new Map();
  for (const dir of dirs) {
    const rel = `skills/${dir}/SKILL.md`;
    if (!existsSync(join(ROOT, rel))) {
      fail('skills', `${dir}/ has no SKILL.md`);
      continue;
    }
    const text = read(rel);
    const fm = parseFrontmatter(text);
    if (fm.error) {
      fail(rel, fm.error);
      continue;
    }
    if (!fm.name) fail(rel, 'frontmatter has no name');
    else {
      if (!NAME_RE.test(fm.name) || fm.name.length > 64) {
        fail(rel, `name "${fm.name}" violates pi's rules (lowercase alnum, single hyphens, <= 64)`);
      }
      if (fm.name !== dir) fail(rel, `name "${fm.name}" does not match its directory "${dir}"`);
      if (seen.has(fm.name)) fail(rel, `duplicate skill name "${fm.name}", also in ${seen.get(fm.name)}`);
      seen.set(fm.name, rel);
    }
    // Pi does not load a skill whose description is missing — it vanishes silently.
    if (!fm.description) fail(rel, 'frontmatter has no description; pi will not load the skill');
    else if (fm.description.length > MAX_DESC) {
      fail(rel, `description is ${fm.description.length} chars, over pi's ${MAX_DESC} cap`);
    }

    // Skill-relative paths, the bug class that shipped a dangling rules/security.md pointer.
    // Both spellings pi documents: a backticked path, and a Markdown link destination.
    const refs = [
      ...[...text.matchAll(/`([^`\s]+\.md)`/g)].map((m) => m[1]),
      ...[...text.matchAll(/\]\(([^)\s]+\.md)(?:\s[^)]*)?\)/g)].map((m) => m[1]),
    ];
    for (const ref of refs) {
      if (/^(https?:|#|\/)/.test(ref)) continue;
      const target = resolve(ROOT, 'skills', dir, ref);
      if (!existsSync(target)) fail(rel, `references missing file ${ref}`);
    }

    // The adapter derives the prefix from the install, so a hardcoded proxy name is correct
    // for package installs and wrong for CLI ones. Skills must use the name search returns.
    // A `<placeholder>` is the correct thing to write here; a literal derived name is not.
    for (const m of text.matchAll(/mcp\(\{\s*tool:\s*["']([^"']+)["']/g)) {
      if (!m[1].includes('<') && /^(tiny-?fish|.*__)/.test(m[1])) {
        fail(rel, `hardcodes a proxy tool name (${m[1]}); call the name mcp({ search }) returned`);
      }
    }
  }
  if (seen.size) ok(`skills (${seen.size} valid)`);
}

// --- skills vs directTools ----------------------------------------------
// A tool the skills teach but that is not registered forces a proxy call the
// capability skills never explain.
if (dirs) {
  const name = 'skills-vs-directTools';
  const registered = new Set(mcp.mcpServers?.tinyfish?.directTools ?? []);
  // Every TinyFish tool name the skills could plausibly name. An incomplete list silently
  // narrows the check, which is how `list_browser_sessions` slipped through review once —
  // the guard below keeps it from falling behind mcp.json again.
  const KNOWN = [
    'search', 'fetch_content', 'run_web_automation', 'run_web_automation_async',
    'get_run', 'cancel_run', 'list_runs', 'poll_status', 'discover_run', 'get_steps',
    'guide_next_step', 'batch_status', 'batch_cancel',
    'create_browser_session', 'list_browser_sessions', 'close_browser_session',
    'get_wallet', 'get_search_usage', 'list_fetch_usage',
  ];
  const unknownRegistered = [...registered].filter((t) => !KNOWN.includes(t));
  if (unknownRegistered.length) {
    fail(name, `directTools names not in this file's KNOWN list — add them: ${unknownRegistered.join(', ')}`);
  }
  const taught = new Set();
  for (const dir of dirs) {
    const files = [`skills/${dir}/SKILL.md`];
    const refs = join(ROOT, 'skills', dir, 'references');
    if (existsSync(refs)) for (const f of readdirSync(refs)) files.push(`skills/${dir}/references/${f}`);
    for (const f of files) {
      if (!existsSync(join(ROOT, f))) continue;
      const text = read(f);
      for (const t of KNOWN) if (text.includes(`\`${t}\``)) taught.add(t);
    }
  }
  const missing = [...taught].filter((t) => !registered.has(t)).sort();
  if (missing.length) fail(name, `taught by the skills but not in directTools: ${missing.join(', ')}`);
  else ok(`${name} (${taught.size} taught, all registered)`);
}

// --- README claims -------------------------------------------------------
// The stated tool count has drifted twice already: once when directTools grew, once in review.
{
  const name = 'readme';
  const readme = existsSync(join(ROOT, 'README.md')) ? read('README.md') : null;
  const count = mcp.mcpServers?.tinyfish?.directTools?.length;
  if (!readme) {
    fail(name, 'README.md is missing');
  } else if (count) {
    const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
      'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
      'seventeen', 'eighteen', 'nineteen', 'twenty'];
    const m = readme.match(/registers\s+([a-z]+|\d+)\s+tools directly/i);
    if (!m) {
      fail(name, 'could not find the "registers N tools directly" claim to check');
    } else {
      const stated = /^\d+$/.test(m[1]) ? Number(m[1]) : WORDS.indexOf(m[1].toLowerCase());
      if (stated !== count) {
        fail(name, `README says it registers ${m[1]} tools but directTools has ${count}`);
      }
    }
  }
  ok(name);
}

// --- files ---------------------------------------------------------------
{
  const name = 'files';
  for (const entry of ['skills', 'rules', 'mcp.json', 'README.md', 'LICENSE']) {
    if (!pkg.files?.includes(entry)) fail(name, `"${entry}" is missing from package.json files`);
  }
  for (const entry of pkg.files ?? []) {
    if (entry === 'test' || entry.startsWith('test/')) {
      fail(name, `"${entry}" would ship the test directory in the tarball`);
    }
  }
  ok(name);
}

// --- report --------------------------------------------------------------
for (const c of checks) console.log(`  ok  ${c}`);
if (failures.length) {
  console.error(`\n${failures.length} failure(s):`);
  for (const f of failures) console.error(`  FAIL  ${f}`);
  process.exit(1);
}
console.log(`\nAll checks passed (${checks.length}).`);
