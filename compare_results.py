"""Compare exact scientific outputs of two completed campaigns, not their timings."""
import argparse
import json
from pathlib import Path


def compare(left: Path, right: Path, expected_jobs: int = 87) -> dict:
    names = sorted(p.name for p in (left / 'jobs').glob('*.json'))
    other = sorted(p.name for p in (right / 'jobs').glob('*.json'))
    if names != other or len(names) != expected_jobs:
        raise ValueError(f'Both directories must contain the same {expected_jobs} jobs')
    certificates = 0
    for name in names:
        a = json.loads((left / 'jobs' / name).read_text())
        b = json.loads((right / 'jobs' / name).read_text())
        for key in ('case', 'method', 'status', 'optimum', 'limits', 'reason'):
            if a.get(key) != b.get(key):
                raise ValueError(f'{name}: {key} differs')
        if a['status'] == 'complete':
            for key in ('transitions', 'table_states', 'peak_states', 'width', 'per_node'):
                if a['repetitions'][0]['producer'][key] != b['repetitions'][0]['producer'][key]:
                    raise ValueError(f'{name}: producer {key} differs')
            pa = (left / 'certificates' / name).read_bytes()
            pb = (right / 'certificates' / name).read_bytes()
            if pa != pb:
                raise ValueError(f'{name}: serialized certificate differs')
            certificates += 1
    return {'matched_jobs': len(names), 'identical_certificates': certificates,
            'comparison': 'exact statuses, optima, limits, cap reasons, state/transition counts and certificate bytes; timing/RSS excluded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--expected-jobs', type=int, default=87)
    args = parser.parse_args()
    try:
        report = compare(args.left, args.right, args.expected_jobs)
        text = json.dumps(report, indent=2) + '\n'
        if args.report:
            args.report.write_text(text)
        print(text, end='')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
