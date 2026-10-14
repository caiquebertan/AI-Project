// {{header}}
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseProbe, probeLabel } from './probe';

describe('core probe', () => {
  it('PLAT-WEB-016 smoke id is carried in the JUnit report', () => {
    expect(parseProbe('{"name":"a","probe_count":2,"extra":true}')).toEqual({ name: 'a', probe_count: 2 });
    expect(probeLabel('http://localhost:8080')).toBe('probe@localhost:8080');
  });

  it('PLAT-WEB-004 smoke core tests run without a DOM', () => {
    expect(typeof (globalThis as { document?: unknown }).document).toBe('undefined');
  });

  it('PLAT-WEB-014 smoke repo root is visible to tests', () => {
    const root = process.env.AWARE_REPO_ROOT;
    expect(root).toBeTruthy();
    expect(existsSync(join(root ?? '', 'spec', 'README.md'))).toBe(true);
  });
});
