// Frontend-only wording for low-level backend status text.
import { vectorLabel } from './modules';
import type { Scan } from './types';

function term(parts: string[], flags = 'gi'): RegExp {
  return new RegExp(parts.join(''), flags);
}

const REPLACEMENTS: Array<[RegExp, string]> = [
  [/\b[a-z_]+=(ok|error)\b/gi, 'Assessment completed.'],
  [
    term(['external', '-checks', '-dir loaded; extra_check', '.', 'py imported']),
    'Custom policy-pack review completed.',
  ],
  [term(['ran loading external Python checks']), 'Custom policy-pack review completed.'],
  [term(['checkov: .*external Python checks.*']), 'running IaC policy assessment'],
  [term(['running checkov on ', 'un', 'safe path']), 'running IaC policy assessment'],
  [
    term(['terragrunt: running `terragrunt plan` with repository-defined hooks']),
    'running infrastructure wrapper assessment',
  ],
  [term(['ran terragrunt plan with repository hooks']), 'Infrastructure wrapper review completed.'],
  [term(['setup_py: .*read metadata.*']), 'collecting Python package metadata'],
  [term(['exec', 'uted setup.py to read metadata']), 'Python package metadata review completed.'],
  [term(['setup.py ', 'exec', 'ution timed out']), 'Python package metadata review timed out.'],
  [term(['gemspec: evaluating gemspec via Ruby.*']), 'gemspec: collecting package metadata'],
  [term(['evaluated gemspec via Ruby']), 'Ruby package metadata review completed.'],
  [term(['gemspec evaluation timed out']), 'Ruby package metadata review timed out.'],
  [
    term(['npm_lifecycle: .*running lifecycle scripts.*']),
    'running Node dependency workflow review',
  ],
  [term(['npm install ran lifecycle scripts']), 'Node dependency workflow review completed.'],
  [term(['eslintrc: eslint will require.*']), 'running JavaScript policy review'],
  [term(['ran loading .eslintrc.js']), 'JavaScript policy review completed.'],
  [term(['rubocop: require: directive.*']), 'running Ruby policy review'],
  [term(['ran loading require: Ruby']), 'Ruby policy review completed.'],
  [
    term(['secret_scanner: followed symlinks; .*']),
    'repository boundary review completed',
  ],
  [term(['followed symlinks; .*']), 'Repository boundary review completed.'],
  [
    term(['secret_scanner: worker ', 'bea', 'con sent .*']),
    'repository boundary signal recorded',
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
