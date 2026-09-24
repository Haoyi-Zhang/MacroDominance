"""Recheck all complete certificates and reproduce all structural cap failures."""
import argparse
import csv
import json
from pathlib import Path
import resource
import sys
import time
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from checker import verify
from producer import solve, BudgetExceeded
from instances import generate
from constant_net_baseline import solve_reduced, verify_reduced


def validate(directory: Path, methods=('raw', 'envelope', 'support')) -> dict:
    cpu = time.process_time()
    wall = time.perf_counter()
    cases = generate(ROOT / 'data' / 'cases', ROOT / 'data' / 'upstream')
    expected = {(case['name'], mode) for case in cases for mode in methods}
    files = sorted((directory / 'jobs').glob('*.json'))
    reports = [json.loads(path.read_text()) for path in files]
    if len(reports) != len(expected) or {(r['case'], r['method']) for r in reports} != expected:
        raise ValueError('Campaign identity or expected-job coverage mismatch')
    checked = failed = 0
    summary = {(row['case'], row['method']): row for row in csv.DictReader((directory / 'summary.csv').open())}
    if set(summary) != expected:
        raise ValueError('Summary coverage mismatch')
    for row in reports:
        name, mode = row['case'], row['method']
        data = json.loads((ROOT / 'data' / 'cases' / (name + '.json')).read_text())
        s = summary[(name, mode)]
        if s['status'] != row['status'] or row.get('process', {}).get('exit_code') != 0:
            raise ValueError('Status/exit discrepancy in ' + name)
        if row['status'] == 'complete':
            payload = (directory / 'certificates' / (name + '__' + mode + '.json')).read_bytes()
            cert = json.loads(payload)
            check = verify_reduced(data, cert) if mode == 'constant_raw' else verify(data, cert)
            if check['optimum'] != row['optimum'] or int(s['optimum']) != row['optimum']:
                raise ValueError('Optimum discrepancy in ' + name)
            if cert['method'] != mode or len(row['repetitions']) != 3:
                raise ValueError('Method / repetition discrepancy in ' + name)
            for rep in row['repetitions']:
                if rep['certificate_bytes'] != len(payload) or not rep['checker']['accepted']:
                    raise ValueError('Certificate-size / acceptance discrepancy in ' + name)
                if check['replayed_transitions'] != rep['producer']['transitions']:
                    raise ValueError('Transition discrepancy in ' + name)
            for key in ('width', 'transitions', 'table_states', 'peak_states'):
                if int(s[key]) != row['repetitions'][0]['producer'][key]:
                    raise ValueError('Summary discrepancy in ' + name + ': ' + key)
            if int(s['certificate_bytes']) != len(payload):
                raise ValueError('Summary byte count discrepancy in ' + name)
            if name.startswith('masked_'):
                _, k, q = name.split('_')
                if cert['optimum'] != int(k) * (int(q) + 20):
                    raise ValueError('Masked analytic optimum mismatch')
            elif name.startswith('exposed_'):
                k = int(name.split('_')[1])
                if cert['optimum'] != 23 * k:
                    raise ValueError('Exposed analytic optimum mismatch')
            elif cert['optimum'] != 1998880:
                raise ValueError('Public-case oracle mismatch')
            checked += 1
        elif row['status'] == 'producer_capped':
            try:
                solve_reduced(data) if mode == 'constant_raw' else solve(data, mode)
            except BudgetExceeded as exc:
                if str(exc) != row['reason']:
                    raise ValueError('Cap reason changed in ' + name)
            else:
                raise ValueError('Claimed cap not reproduced in ' + name)
            failed += 1
        else:
            raise ValueError('Unresolved process/replay failure in ' + name)
    return {'expected_jobs': len(expected), 'methods': list(methods), 'rechecked_certificates': checked, 'reproduced_structural_caps': failed,
            'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'scope': 'Replays and deterministic cap checks; not a general proof or a speed replication.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--methods', nargs='+', choices=['raw', 'envelope', 'support', 'constant_raw'], default=['raw', 'envelope', 'support'])
    a = p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    try:
        report = validate(a.directory, a.methods)
        text = json.dumps(report, indent=2) + '\n'
        if a.report:
            a.report.write_text(text)
        print(text, end='')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
