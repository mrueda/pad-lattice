import type {
  DemoManifest,
  FullSurfaceFrame,
  PerformanceManifest,
} from './types';

export interface ExperienceAssets {
  demo: DemoManifest;
  performance: PerformanceManifest;
}

export async function loadExperienceAssets(): Promise<ExperienceAssets> {
  const [demoResponse, performanceResponse] = await Promise.all([
    fetch('./experiences/demo-v1.json', {cache: 'no-store'}),
    fetch('./experiences/constellation-v1.json', {cache: 'no-store'}),
  ]);
  if (!demoResponse.ok || !performanceResponse.ok) {
    throw new Error('Experience assets are unavailable.');
  }
  const demo = await demoResponse.json() as unknown;
  const performance = await performanceResponse.json() as unknown;
  return {
    demo: parseDemoManifest(demo),
    performance: parsePerformanceManifest(performance),
  };
}

export function performanceFrame(
  manifest: PerformanceManifest,
  cueIndex: number,
): FullSurfaceFrame {
  const cue = manifest.cues[cueIndex];
  if (!cue) throw new Error(`Unknown performance cue ${cueIndex}.`);
  const color = (index: number) => {
    const entry = manifest.palette[index];
    if (!entry) throw new Error(`Unknown performance palette index ${index}.`);
    return `#${entry.rgb.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
  };
  return {
    grid: cue.frame.grid.map((row) => row.map(color)),
    top: cue.frame.top.map(color),
    right: cue.frame.right.map(color),
  };
}

export function cueIndexAt(manifest: PerformanceManifest, elapsedMs: number): number {
  let boundary = 0;
  for (let index = 0; index < manifest.cues.length; index += 1) {
    boundary += manifest.cues[index].duration_ms;
    if (elapsedMs < boundary) return index;
  }
  return manifest.cues.length - 1;
}

export function parseDemoManifest(value: unknown): DemoManifest {
  if (!isObject(value) || value.schema_version !== 1 || value.kind !== 'demo') {
    throw new Error('Unsupported Demo manifest.');
  }
  if (typeof value.id !== 'string' || typeof value.title !== 'string'
    || typeof value.initial_stage !== 'string' || !Array.isArray(value.stages)) {
    throw new Error('Malformed Demo manifest.');
  }
  const manifest = value as unknown as DemoManifest;
  if (!manifest.stages.some((stage) => stage.id === manifest.initial_stage)) {
    throw new Error('Demo initial stage is unknown.');
  }
  return manifest;
}

export function parsePerformanceManifest(value: unknown): PerformanceManifest {
  if (!isObject(value) || value.schema_version !== 1 || value.kind !== 'performance') {
    throw new Error('Unsupported performance manifest.');
  }
  if (!Array.isArray(value.palette) || !Array.isArray(value.cues)
    || value.cues.length === 0 || typeof value.duration_ms !== 'number') {
    throw new Error('Malformed performance manifest.');
  }
  return value as unknown as PerformanceManifest;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
