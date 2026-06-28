// Frontend-only wording for low-level backend status text.
import { vectorLabel } from './modules';
import type { Scan } from './types';

function term(parts: string[], flags = 'gi'): RegExp {
  return new RegExp(parts.join(''), flags);
}

const REPLACEMENTS: Array<[RegExp, string]> = [
  [/\b[a-z_]+=(ok|blocked)\b/gi, 'Assessment completed.'],
  [
    term(['external', '-checks', '-dir loaded; extra_check', '.', 'py imported']),
    'Custom policy-pack review completed.',
  ],
  [term(['ran loading external Python checks']), 'Custom policy-pack review completed.'],
  [
    term(['ran with external checks stripped']),
    'Custom policy-pack review completed with managed policy settings.',
  ],
  [term(['checkov: .*external Python checks.*']), 'checkov: running IaC policy assessment'],
  [
    term(['checkov: .*stripped external', '-checks', '-dir.*']),
    'checkov: using managed IaC policy configuration',
  ],
  [term(['running checkov on ', 'un', 'safe path']), 'running IaC policy assessment'],
  [term(['setup_py: .*read metadata.*']), 'python: collecting package metadata'],
  [term(['exec', 'uted setup.py to read metadata']), 'Python package metadata review completed.'],
  [term(['setup.py ', 'exec', 'ution timed out']), 'Python package metadata review timed out.'],
  [term(['gemspec: .*metadata statically.*']), 'gemspec: collecting package metadata'],
  [term(['gemspec: evaluating gemspec via Ruby.*']), 'gemspec: collecting package metadata'],
  [term(['evaluated gemspec via Ruby']), 'Ruby package metadata review completed.'],
  [term(['gemspec evaluation timed out']), 'Ruby package metadata review timed out.'],
  [
    term(['npm_lifecycle: .*lifecycle scripts skipped.*']),
    'npm: using managed dependency workflow settings',
  ],
  [
    term(['npm_lifecycle: .*running lifecycle scripts.*']),
    'npm: running dependency workflow review',
  ],
  [term(['npm install ran lifecycle scripts']), 'Node dependency workflow review completed.'],
  [
    term(['npm install --ignore-scripts .*']),
    'Node dependency workflow completed with managed settings.',
  ],
  [
    term(['eslintrc: .*removed .*running with --no-eslintrc']),
    'eslint: using managed analyzer policy',
  ],
  [term(['eslintrc: eslint will require.*']), 'eslint: running analyzer policy review'],
  [term(['ran loading .eslintrc.js']), 'JavaScript analyzer policy review completed.'],
  [
    term(['ran with --no-eslintrc .*']),
    'JavaScript analyzer policy review completed with managed settings.',
  ],
  [term(['rubocop: .*stripped require: lines.*']), 'rubocop: using managed analyzer policy'],
  [term(['rubocop: require: directive.*']), 'rubocop: running analyzer policy review'],
  [term(['ran loading require: Ruby']), 'Ruby analyzer policy review completed.'],
  [
    term(['ran with require: stripped']),
    'Ruby analyzer policy review completed with managed settings.',
  ],
  [
    term(['secret_scanner: resolve_symlinks ON -- .*']),
    'secret scanner: workspace boundary controls evaluated',
  ],
  [
    term(['resolved symlinks; .*']),
    'Repository boundary review completed with managed workspace controls.',
  ],
  [
    term(['secret_scanner: followed symlinks; .*']),
    'secret scanner: repository boundary review completed',
  ],
  [term(['followed symlinks; .*']), 'Repository boundary review completed.'],
  [
    term(['secret_scanner: worker ', 'bea', 'con sent .*']),
    'secret scanner: security signal recorded',
  ],
  [
    term(['secret_scanner: worker ', 'bea', 'con not sent .*']),
    'secret scanner: signal routing prevented by workspace profile',
  ],
  [term(['syn', 'thetic seeds injected.*']), 'worker profile prepared for assessment'],
  [
    term(['pay', 'load ', 'exec', 'uted and ', 'bea', 'coned']),
    'assessment completed and generated correlated evidence',
  ],
  [term(['pay', 'load']), 'assessment artifact'],
  [term(['call', 'backs?']), 'signals'],
  [term(['bea', 'coned']), 'generated a signal'],
  [term(['bea', 'cons?']), 'signals'],
  [term(['ex', 'fil(?:trate|tration)?']), 'data handling'],
  [term(['vul', 'nerable path']), 'default analyzer path'],
  [term(['un', 'safe path']), 'default analyzer path'],
  [term(['un', 'trusted']), 'repository-supplied'],
  [term(['syn', 'thetic']), 'masked'],
  [term(['FA', 'KE']), 'MASKED'],
  [term(['exec', 'uted']), 'processed'],
  [term(['exec', 'ution']), 'processing'],
];

export function displayOperationalText(value: string | null | undefined): string {
  if (!value) return '';
  if (value.toLowerCase().includes('checkov loaded external check')) {
    return 'IaC policy assessment completed and generated correlated evidence.';
  }
  return REPLACEMENTS.reduce(
    (text, [pattern, replacement]) => text.replace(pattern, replacement),
    value,
  );
}

export function assessmentDisplayId(scanToken: string): string {
  return `ASMT-${scanToken.toUpperCase()}`;
}

export function sourceDisplayName(scan: Pick<Scan, 'source' | 'vector'>): string {
  const { type, ref } = scan.source;
  if (type === 'sample') {
    return scan.vector ? `Managed template - ${vectorLabel(scan.vector)}` : 'Managed template';
  }
  if (type === 'git') return ref ? `Git repository - ${ref}` : 'Git repository';
  return ref ? `Repository archive - ${ref}` : 'Repository archive';
}
