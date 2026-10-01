"""Nonconstant controls for response dominance; no external data are synthesized."""
from instances import single_region,pin,balanced

def biased(k,q):
    """Each variable has a weight-two local anchor and a weight-one live net.
    Every net is nonconstant. Leftmost candidates dominate, so a leaf-only
    response preprocessor is an intentionally strong null baseline.
    """
    regs=[]
    for i in range(k):
        x=i*40;r=f'v{i}';fixed=f'f{i}';moving=f'm{i}'
        macros=[{'id':fixed,'size':[1,1],'pins':[pin('b',f'b{i}',0,0)]},
                {'id':moving,'size':[1,1],'pins':[pin('b',f'b{i}',0,0),pin('e',f'e{i}',0,0)]}]
        choices=[[{'macro':fixed,'xy':[x+1,5],'rotation':0},
                  {'macro':moving,'xy':[x+4+c,5],'rotation':0}] for c in range(q)]
        regs.append({'id':r,'box':[x,0,x+36,10],'macros':macros,'candidates':choices})
        regs.append(single_region(f'a{i}',[x,20,x+36,30],[1,1],
                                  [pin('p',f'e{i}',0,0)],[([x+1,25],0),([x+34,25],0)]))
    return {'name':f'biased_{k}_{q}','regions':regs,
            'weights':dict([(f'e{i}',1) for i in range(k)]+[(f'b{i}',2) for i in range(k)]),
            'tree':[balanced([f'v{i}' for i in range(k)]),balanced([f'a{i}' for i in range(k)])]}


def online_frontier_stress(k, reverse=False):
    """Legal two-owner, width-one case with small final and large online frontier.

    In forward order, the first ``k`` inside alternatives are mutually
    incomparable; the last one dominates all of them.  Reversing the candidate
    list presents that dominator first.  This case is used only to audit the
    producer-complexity distinction between final rows and transient online rows.
    """
    if type(k) is not int or k < 1:
        raise ValueError("positive integer k required")
    inside_candidates = [
        [
            {"macro": "A", "xy": [i, 0], "rotation": 0},
            {"macro": "B", "xy": [i + k, 1], "rotation": 0},
        ]
        for i in range(1, k + 1)
    ]
    inside_candidates.append([
        {"macro": "A", "xy": [0, 0], "rotation": 0},
        {"macro": "B", "xy": [0, 1], "rotation": 0},
    ])
    if reverse:
        inside_candidates = list(reversed(inside_candidates))
    inside = {
        "id": "inside",
        "box": [0, 0, 3 * k + 5, 3],
        "macros": [
            {"id": "A", "size": [1, 1], "pins": [
                pin("local", "local", 0, 0),
                pin("live", "live", 0, 0),
            ]},
            {"id": "B", "size": [1, 1], "pins": [pin("local", "local", 0, 0)]},
        ],
        "candidates": inside_candidates,
    }
    outside = {
        "id": "outside",
        "box": [0, 10, 3 * k + 5, 12],
        "macros": [
            {"id": "C", "size": [1, 1], "pins": [pin("live", "live", 0, 0)]},
        ],
        "candidates": [
            [{"macro": "C", "xy": [0, 10], "rotation": 0}],
            [{"macro": "C", "xy": [k + 1, 10], "rotation": 0}],
        ],
    }
    order = "reverse" if reverse else "forward"
    return {
        "name": f"online_frontier_{k}_{order}",
        "regions": [inside, outside],
        "weights": {"local": 1, "live": 1},
        "tree": ["inside", "outside"],
    }
