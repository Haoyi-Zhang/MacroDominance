"""Direct Cartesian-product oracle. No DP or checker imports."""
import itertools
import math


def optimum(instance,limit=100000):
    regions=instance['regions'];counts=[len(r['candidates']) for r in regions]
    if math.prod(counts)>limit:raise ValueError('oracle enumeration limit')
    alternatives=[]
    for region in regions:
        definitions={m['id']:m for m in region['macros']};alist=[]
        for candidate in region['candidates']:
            pins=[]
            for position in candidate:
                m=definitions[position['macro']];w,h=m['size'];x,y=position['xy'];rot=position['rotation']
                for p in m['pins']:
                    a,b=p['offset']
                    if rot==0:u,v=a,b
                    elif rot==90:u,v=h-b,a
                    elif rot==180:u,v=w-a,h-b
                    elif rot==270:u,v=b,w-a
                    else:raise ValueError('rotation')
                    pins.append((p['net'],x+u,y+v))
            alist.append(pins)
        alternatives.append(alist)
    best=None;bestchoices=None;visited=0
    for choices in itertools.product(*(range(c) for c in counts)):
        allpins=list(itertools.chain.from_iterable(alternatives[r][c] for r,c in enumerate(choices)))
        total=0
        for net,w in instance['weights'].items():
            pts=[(x,y) for e,x,y in allpins if e==net]
            # Pairwise diameter per axis, rather than a summary-merge recurrence.
            total+=w*sum(max(abs(a[d]-b[d]) for a in pts for b in pts) for d in (0,1))
        visited+=1
        if best is None or total<best:best=total;bestchoices=choices
    return {'optimum':best,'choices':bestchoices,'assignments':visited}
