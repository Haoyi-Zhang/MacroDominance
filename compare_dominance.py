"""Compare deterministic results and exact input/certificate bytes, not timings."""
import argparse,json
from pathlib import Path
VOLATILE={'cpu_seconds','wall_seconds','total_cpu_seconds','peak_rss_kib'}
def deterministic(v):
    if isinstance(v,dict):return {k:deterministic(x) for k,x in v.items() if k not in VOLATILE}
    if isinstance(v,list):return [deterministic(x) for x in v]
    return v

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('expected');p.add_argument('fresh');a=p.parse_args();e,f=Path(a.expected),Path(a.fresh)
    for name in ('records.json','oracles.json','summary.json'):
        assert deterministic(json.loads((e/name).read_text()))==deterministic(json.loads((f/name).read_text())),name
    counts={}
    for folder in ('inputs','certificates'):
        names={x.name for x in (e/folder).iterdir()};assert names=={x.name for x in (f/folder).iterdir()}
        for name in names:assert (e/folder/name).read_bytes()==(f/folder/name).read_bytes(),name
        counts[folder]=len(names)
    expected_summary=json.loads((e/'summary.json').read_text())
    assert counts=={'inputs':expected_summary['cases'],'certificates':expected_summary['success']}
    print(json.dumps(dict(exact_jobs=expected_summary['jobs'],exact_inputs=counts['inputs'],byte_equal_certificates=counts['certificates'],timing_and_rss_compared=False),sort_keys=True))
if __name__=='__main__':main()
