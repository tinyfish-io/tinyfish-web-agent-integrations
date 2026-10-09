import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { build } from './build.mjs';

const SKILL = '---\nname: tinyfish-x\ndescription: d\n---\n\nUse {{tool}}.\n\n{{extra}}\n\nEnd.\n';

function fixture({ skill = SKILL, mcp = '<!-- slot: tool -->\nA\n<!-- slot: extra -->\n', pi = '<!-- slot: tool -->\nB\n<!-- slot: extra -->\nMore.\n' } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'skills-'));
  const files = {
    'skills/tinyfish-x/SKILL.md': skill,
    'skills/tinyfish-x/references/r.md': 'Ref {{tool}}.\n',
    'skills/surfaces/mcp.md': mcp,
    'skills/surfaces/pi.md': pi,
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
});

test('fails on a slot missing from one surface', () => {
  assert.throws(() => build(fixture({ mcp: '<!-- slot: extra -->\n' })), /slot "tool" is not defined for mcp/);
});

test('fails on a slot no file uses', () => {
  assert.throws(() => build(fixture({ pi: '<!-- slot: tool -->\nB\n<!-- slot: extra -->\n<!-- slot: dead -->\nx\n' })), /never used: dead/);
});

test('fails on a leftover placeholder', () => {
  assert.throws(() => build(fixture({ skill: SKILL + '{{Bad}}\n' })), /leftover placeholder \{\{Bad\}\}/);
});
