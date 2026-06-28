// Static module metadata. This lives entirely in the frontend; there is no
// metadata endpoint.
import type { ModuleName, Vector } from './types';

export interface VectorMeta {
  id: Vector;
  label: string;
  /** Analyzer family used for this assessment. */
  analyzer: string;
  /** One-line product description. */
  description: string;
}

export interface ModuleMeta {
  id: ModuleName;
  title: string;
  /** "We scan your …" marketing analog. */
  analog: string;
  /** Longer real-world framing. */
  blurb: string;
  accent: string; // tailwind text color class for the module accent
  icon: string;
  vectors: VectorMeta[];
}

export const MODULES: ModuleMeta[] = [
  {
    id: 'iac',
    title: 'IaC Scanning',
    analog: 'Terraform and Kubernetes policy assessment',
    blurb:
      'Evaluate infrastructure definitions with policy engines that mirror enterprise scanner behavior, including custom rule discovery and policy-pack governance.',
    accent: 'text-cyan',
    icon: 'IaC',
    vectors: [
      {
        id: 'checkov_external_checks',
        label: 'Policy pack review',
        analyzer: 'checkov',
        description:
          'Reviews custom policy-pack discovery, rule ownership, and IaC assessment configuration.',
      },
    ],
  },
  {
    id: 'sca',
    title: 'SCA / Dependency Analysis',
    analog: 'Package metadata and lifecycle analysis',
    blurb:
      'Assess dependency manifests across Python, Ruby, and Node ecosystems with native package tooling paths that reflect production scanner integrations.',
    accent: 'text-neon',
    icon: 'SCA',
    vectors: [
      {
        id: 'setup_py_exec',
        label: 'Python package metadata review',
        analyzer: 'python',
        description:
          'Reviews Python package metadata collection and dependency inventory normalization.',
      },
      {
        id: 'gemspec_eval',
        label: 'Ruby package metadata review',
        analyzer: 'ruby/gem',
        description: 'Reviews Ruby package metadata collection and gem inventory normalization.',
      },
      {
        id: 'npm_lifecycle',
        label: 'Node dependency workflow review',
        analyzer: 'node/npm',
        description:
          'Reviews Node dependency workflow settings used during package inventory collection.',
      },
    ],
  },
  {
    id: 'sast',
    title: 'Security Tools',
    analog: 'Analyzer configuration and rule-loading workflows',
    blurb:
      'Exercise security tools that consume repository configuration, managed plugins, and language-specific rule packs before analysis begins.',
    accent: 'text-magenta',
    icon: 'TOOL',
    vectors: [
      {
        id: 'eslintrc_js_exec',
        label: 'JavaScript analyzer policy review',
        analyzer: 'eslint',
        description:
          'Reviews JavaScript analyzer configuration, project policy, and rule governance.',
      },
      {
        id: 'rubocop_require',
        label: 'Ruby analyzer policy review',
        analyzer: 'rubocop',
        description: 'Reviews Ruby analyzer configuration, project policy, and rule governance.',
      },
    ],
  },
  {
    id: 'secrets',
    title: 'Secret Scanning',
    analog: 'Credential governance and repository boundary checks',
    blurb:
      'Inspect repository content for credential governance, ownership routing, and workspace boundary handling during secret scanning.',
    accent: 'text-amber',
    icon: 'SEC',
    vectors: [
      {
        id: 'symlink_traversal',
        label: 'Repository boundary review',
        analyzer: 'secret-scanner',
        description:
          'Reviews scanner workspace boundaries and how repository file references are normalized.',
      },
    ],
  },
];

export const MODULE_MAP: Record<ModuleName, ModuleMeta> = Object.fromEntries(
  MODULES.map((m) => [m.id, m]),
) as Record<ModuleName, ModuleMeta>;

export function moduleFor(id: string): ModuleMeta | undefined {
  return MODULE_MAP[id as ModuleName];
}

// Per-assessment color for the live feed / tags.
export const VECTOR_COLOR: Record<Vector, string> = {
  checkov_external_checks: 'text-cyan border-cyan/60',
  setup_py_exec: 'text-neon border-neon/60',
  gemspec_eval: 'text-emerald-400 border-emerald-400/60',
  npm_lifecycle: 'text-lime-400 border-lime-400/60',
  eslintrc_js_exec: 'text-magenta border-magenta/60',
  rubocop_require: 'text-pink-400 border-pink-400/60',
  symlink_traversal: 'text-amber border-amber/60',
};

export function vectorColor(vector: string): string {
  return VECTOR_COLOR[vector as Vector] ?? 'text-dim border-edge';
}

export function vectorLabel(vector: string): string {
  for (const module of MODULES) {
    const match = module.vectors.find((candidate) => candidate.id === vector);
    if (match) return match.label;
  }
  return vector.replaceAll('_', ' ');
}
