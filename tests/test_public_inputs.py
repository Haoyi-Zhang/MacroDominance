"""Parse every retained public input and check its declared inventory."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from instances import _parse_core_bookshelf, core_public_case, public_case
from oracle import optimum

EXPECTED={'hp':(11,70,16,44,2048),'n10':(10,118,26,54,1024),
          'apte':(9,96,18,44,512),'xerox':(10,182,47,182,1024)}

def main():
    rows=[]
    for circuit,expected in EXPECTED.items():
        blocks,nets,edges=_parse_core_bookshelf(ROOT/'data/upstream/core',circuit)
        observed=(len(blocks),len(nets),len(edges),sum(edges.values()))
        assert observed==expected[:4]
        for layout in ('balanced','netaware'):
            case=core_public_case(ROOT/'data/upstream/core',circuit,layout)
            truth=optimum(case)
            assert truth['assignments']==expected[4]
            rows.append({'case':case['name'],'blocks':len(blocks),'source_nets':len(nets),
                         'induced_edges':len(edges),'edge_multiplicity':sum(edges.values()),
                         'assignments':truth['assignments'],'optimum':truth['optimum']})
    for layout in ('balanced','columns','chain'):
        case=public_case(ROOT/'data/upstream',layout); truth=optimum(case)
        assert len(case['regions'])==10 and len(case['weights'])==12 and truth['assignments']==1024
        rows.append({'case':case['name'],'blocks':10,'source_nets':12,
                     'induced_edges':12,'edge_multiplicity':12,
                     'assignments':truth['assignments'],'optimum':truth['optimum']})
    out={'cases':len(rows),'oracle_assignments':sum(r['assignments'] for r in rows),'rows':rows}
    (ROOT/'results/public-input-tests.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'cases':out['cases'],'oracle_assignments':out['oracle_assignments']},sort_keys=True))
if __name__=='__main__': main()
