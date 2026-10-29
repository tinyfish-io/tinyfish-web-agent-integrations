import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { build } from './build.mjs';

const SKILL = '---\nname: tinyfish-x\ndescription: d\n---\n\nUse {{tool}}.\n\n{{extra}}\n\nEnd.\n';

function fixture({ skill = SKILL, grok = '<!-- slot: tool -->\nA\n<!-- slot: extra -->\n', mcp = '<!-- slot: tool -->\nM\n<!-- slot: extra -->\n', pi = '<!-- slot: tool -->\nB\n<!-- slot: extra -->\nMore.\n', cli = '<!-- slot: tool -->\nC\n<!-- slot: extra -->\n', claude = '<!-- slot: tool -->\nK\n<!-- slot: extra -->\n', kiro = '<!-- slot: tool -->\nR\n<!-- slot: extra -->\n' } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'skills-'));
  const files = {
    'skills/tinyfish-x/SKILL.md': skill,
    'skills/tinyfish-x/references/r.md': 'Ref {{tool}}.\n',
    'skills/surfaces/grok.md': grok,
    'skills/surfaces/mcp.md': mcp,
    'skills/surfaces/pi.md': pi,
    'skills/surfaces/cli.md': cli,
    'skills/surfaces/claude.md': claude,
    'skills/surfaces/kiro.md': kiro,
  };
  for (const [p, c] of Object.entries(files)) {
    mkdirSync(dirname(join(root, p)), { recursive: true });
    writeFileSync(join(root, p), c);
  }
  return root;
}

test('renders slots and drops empty slot lines', () => {
  const out = build(fixture());
  const grok = out['grok/skills/tinyfish-x/SKILL.md'];
  assert.match(grok, /^---\nname: tinyfish-x\ndescription: d\n---\n\nUse A/);
  assert.match(grok, /Use A\.\n\nEnd\.\n$/);
  assert.match(out['pi/skills/tinyfish-x/SKILL.md'], /Use B\.\n\nMore\.\n\nEnd\.\n$/);
  assert.equal(out['pi/skills/tinyfish-x/references/r.md'], 'Ref B.\n');
  assert.equal(out['cli/skills/tinyfish-x/references/r.md'], 'Ref C.\n');
  assert.equal(out['mcp/skills/tinyfish-x/references/r.md'], 'Ref M.\n');
  assert.equal(out['claude/skills/tinyfish-x/references/r.md'], 'Ref K.\n');
  assert.equal(out['kiro/tinyfish/skills/tinyfish-x/references/r.md'], 'Ref R.\n');
});

test('fails on a slot missing from one surface', () => {
  assert.throws(() => build(fixture({ grok: '<!-- slot: extra -->\n' })), /slot "tool" is not defined for grok/);
});

test('fails on a slot no file uses', () => {
  assert.throws(() => build(fixture({ pi: '<!-- slot: tool -->\nB\n<!-- slot: extra -->\n<!-- slot: dead -->\nx\n' })), /never used: dead/);
});

test('fails on a leftover placeholder', () => {
  assert.throws(() => build(fixture({ skill: SKILL + '{{Bad}}\n' })), /leftover placeholder \{\{Bad\}\}/);
});

test('a description-<skill> slot overrides that surface only', () => {
  const out = build(fixture({ claude: '<!-- slot: tool -->\nK\n<!-- slot: extra -->\n<!-- slot: description-tinyfish-x -->\nTuned.\n' }));
  assert.match(out['claude/skills/tinyfish-x/SKILL.md'], /^---\nname: tinyfish-x\ndescription: "Tuned."\n---/);
  assert.match(out['grok/skills/tinyfish-x/SKILL.md'], /^---\nname: tinyfish-x\ndescription: d\n---/);
});
