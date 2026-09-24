"""Derive paper aggregates from recorded runs; never synthesize missing outcomes."""
import argparse,collections,csv,json,statistics
from pathlib import Path
MODES=('equality','containment','leaf','response')
def analyze(root,out):
    records=json.loads((root/'records.json').read_text());by={(r['case'],r['mode']):r for r in records}
    assert len(by)==len(records)==308
    assert len({r['case'] for r in records})==77
    generated=[];pairs={}
    for mode in MODES:
        group=[by[(f'random_{s}_6_4',mode)] for s in range(100,140)]
        assert all(r['status']=='success' for r in group)
        generated.append(dict(mode=mode,transitions=sum(r['producer']['transitions'] for r in group),
                              retained_rows=sum(r['producer']['total_states'] for r in group),
                              producer_cpu_seconds=sum(r['producer']['cpu_seconds'] for r in group),
                              checker_cpu_seconds=sum(r['checker']['cpu_seconds'] for r in group)))
    for mode in MODES[:-1]:
        ratios=[];fewer=ties=greater=0
        for s in range(100,140):
            a=by[(f'random_{s}_6_4',mode)]['producer']['transitions'];b=by[(f'random_{s}_6_4','response')]['producer']['transitions']
            ratios.append(a/b);fewer+=b<a;ties+=b==a;greater+=b>a
        pairs[mode]=dict(median_ratio=statistics.median(ratios),min_ratio=min(ratios),max_ratio=max(ratios),response_fewer=fewer,tied=ties,response_greater=greater)
    result=dict(generated=generated,paired_transitions=pairs,
                status_counts=dict(collections.Counter(r['status'] for r in records)),
                caps_by_mode=dict(collections.Counter(r['mode'] for r in records if r['status']=='limit')),
                cap_reasons=[{k:r[k] for k in ('case','mode','reason')} for r in records if r['status']=='limit'],
                public=[{k:r[k] for k in ('case','mode','producer')} for r in records
                        if r['case'].startswith(('openroad','core_'))],
                public_pairs=[dict(case=name,
                                   leaf_transitions=by[(name,'leaf')]['producer']['transitions'],
                                   response_transitions=by[(name,'response')]['producer']['transitions'],
                                   delta=by[(name,'leaf')]['producer']['transitions']-by[(name,'response')]['producer']['transitions'],
                                   optimum=by[(name,'response')]['producer']['optimum'])
                              for name in sorted({r['case'] for r in records
                                                if r['case'].startswith(('openroad','core_'))})])
    out.mkdir(parents=True,exist_ok=True)
    (out/'dominance-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'dominance-work.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(generated[0]));w.writeheader();w.writerows(generated)
    with (out/'public-work.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result['public_pairs'][0]));w.writeheader();w.writerows(result['public_pairs'])
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',nargs='?',default='results/dominance-campaign');p.add_argument('--out',default='results/derived')
    a=p.parse_args();r=analyze(Path(a.directory),Path(a.out));print(json.dumps({k:v for k,v in r.items() if k not in ('public','cap_reasons')},sort_keys=True))
