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
