"""Derive every manuscript data table and plot from the two recorded campaigns."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import statistics

ROOT = Path(__file__).resolve().parent
MODES = ('raw', 'envelope', 'support', 'constant_raw')
LABELS = {'raw': 'Raw', 'envelope': 'Envelope', 'support': 'Two-sided', 'constant_raw': 'Constant + raw'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary', type=Path, default=ROOT / 'results/campaign')
    parser.add_argument('--null', type=Path, default=ROOT / 'results/null-baseline')
    parser.add_argument('--out', type=Path, default=ROOT / 'results/derived')
    parser.add_argument('--paper-dir', type=Path)
    args = parser.parse_args()
    rows = [json.loads(p.read_text()) for d in (args.primary, args.null) for p in sorted((d / 'jobs').glob('*.json'))]
    index = {(r['case'], r['method']): r for r in rows}
    if len(rows) != 116 or len(index) != 116:
        raise ValueError('Expected exactly 29 cases in each of four modes')
    monotone_cases = 0
    for case in sorted({row['case'] for row in rows}):
        triplet = [index[(case, method)] for method in MODES[:3]]
        if all(row['status'] == 'complete' for row in triplet):
            nodes = [{v['node']: v['states'] for v in row['repetitions'][0]['producer']['per_node']} for row in triplet]
            if set(nodes[0]) != set(nodes[1]) or set(nodes[1]) != set(nodes[2]):
                raise ValueError('Node coverage differs between methods')
            if any(not (nodes[2][v] <= nodes[1][v] <= nodes[0][v]) for v in nodes[0]):
                raise ValueError('Key coarsening state monotonicity failed')
            transitions = [row['repetitions'][0]['producer']['transitions'] for row in triplet]
            if not transitions[2] <= transitions[1] <= transitions[0]:
                raise ValueError('Transition monotonicity failed')
            monotone_cases += 1
    counts = {m: dict(Counter(r['status'] for r in rows if r['method'] == m)) for m in MODES}
    if any(set(c) - {'complete', 'producer_capped'} for c in counts.values()):
        raise ValueError('An unresolved execution failure cannot be summarized as a cap')
    args.out.mkdir(parents=True, exist_ok=True)
    overall = {'mode_counts': counts, 'recorded_jobs': len(rows),
               'reported_child_cpu_seconds': sum(r['cpu_seconds'] for r in rows),
               'maximum_child_peak_rss_kib': max(r['peak_rss_kib'] for r in rows),
               'distinct_public_topologies': 1, 'complete_triplets_checked_for_monotonicity': monotone_cases,
               'public_hierarchies': 3,
               'timing_scope': 'Three within-process repetitions per successful job; no general speedup inference',
               'null_baseline_scope': 'Exploratory adversarial addition after the three-mode campaign'}
    (args.out / 'analysis.json').write_text(json.dumps(overall, indent=2) + '\n')
    with (args.out / 'masked-states.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['k'] + list(MODES))
        for k in (2, 4, 6, 8, 10, 12):
            writer.writerow([k] + [index[(f'masked_{k}_2', m)]['repetitions'][0]['producer']['peak_states'] for m in MODES])
    with (args.out / 'completion-table.tex').open('w') as f:
        for m in MODES:
            c = counts[m]
            f.write(f"{LABELS[m]} & {c.get('complete', 0)} & {c.get('producer_capped', 0)} \\\\\n")
    with (args.out / 'public-table.tex').open('w') as f:
        for h in ('balanced', 'columns', 'chain'):
            for m in MODES:
                r = index[('openroad_macro_only_' + h, m)]
                assert r['status'] == 'complete' and r['optimum'] == 1998880
                reps = r['repetitions']; s = reps[0]['producer']
                prod = statistics.median(x['producer']['wall_seconds'] for x in reps) * 1000
                replay = statistics.median(x['checker']['wall_seconds'] for x in reps) * 1000
                f.write(f"{h.capitalize()} & {LABELS[m]} & {s['width']} & {s['table_states']} & {s['transitions']} & {reps[0]['certificate_bytes']:,} & {prod:.2f} & {replay:.2f} \\\\\n")
            if h != 'chain':
                f.write('\\midrule\n')
    with (args.out / 'selected-table.tex').open('w') as f:
        for case, name in [('masked_12_2', 'Masked, $12,2$'), ('masked_12_4', 'Masked, $12,4$'), ('exposed_12_4_paired', 'Paired, $12,4$')]:
            for m in MODES:
                r = index[(case, m)]
                if r['status'] == 'complete':
                    s = r['repetitions'][0]['producer']
                    f.write(f"{name} & {LABELS[m]} & {s['peak_states']:,} & {s['transitions']:,} & {r['repetitions'][0]['certificate_bytes']:,} \\\\\n")
                else:
                    f.write(f"{name} & {LABELS[m]} & \\multicolumn{{3}}{{c}}{{Transition cap before completion}} \\\\\n")
            if case != 'exposed_12_4_paired':
                f.write('\\midrule\n')
    specifications = {
        'completion-table.tex': ('lrr', 'Method & Complete & Structural cap'),
        'selected-table.tex': ('llrrr', 'Case & Method & Peak rows & Generated transitions & Certificate bytes'),
        'public-table.tex': ('llrrrrrr', 'Hierarchy & Method & Width & Total rows & Transitions & Bytes & Produce & Replay'),
    }
    for filename, (columns, header) in specifications.items():
        target = args.out / filename
        body = target.read_text()
        target.write_text('\\begin{tabular}{' + columns + '}\\toprule\n' + header + r'\\' + '\n\\midrule\n' + body + '\\bottomrule\n\\end{tabular}\n')
    if args.paper_dir:
        args.paper_dir.mkdir(parents=True, exist_ok=True)
        for p in args.out.iterdir():
            if p.suffix in ('.tex', '.csv'):
                shutil.copyfile(p, args.paper_dir / p.name)
    print(json.dumps(overall, indent=2))


if __name__ == '__main__':
    main()
