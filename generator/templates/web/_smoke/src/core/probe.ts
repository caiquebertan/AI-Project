// {{header}}
export type ProbeWire = { name: string; probe_count: number };

export function probeLabel(baseUrl: string): string {
  return `probe@${new URL(baseUrl).host}`;
}

export function parseProbe(text: string): ProbeWire {
  const value: unknown = JSON.parse(text);
  if (typeof value !== 'object' || value === null) throw new Error('not an object');
  const record = value as Record<string, unknown>;
  if (typeof record.name !== 'string' || typeof record.probe_count !== 'number') throw new Error('bad shape');
  return { name: record.name, probe_count: record.probe_count };
}
