"""Deterministic synthetic controls and an explicit OpenROAD regression adapter.

The adapter reads two exact upstream text files. Its region ownership and
candidate portfolios are newly specified, not upstream placement results.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import itertools
import json
import math
from pathlib import Path
import random
import re


def balanced(names):
    if len(names)==1:return names[0]
    m=len(names)//2
    return [balanced(names[:m]),balanced(names[m:])]


def single_region(name,box,size,pins,poses):
    mid='m_'+name
    return {'id':name,'box':box,'macros':[{'id':mid,'size':size,'pins':pins}],
            'candidates':[[{'macro':mid,'xy':xy,'rotation':rot}] for xy,rot in poses]}


def pin(name,net,x,y):
    return {'id':name,'net':net,'offset':[x,y]}


def random_small(seed,n=4,q=3):
    rng=random.Random(seed);regions=[];nets=set()
    for r in range(n):
        w=rng.randrange(2,8);h=rng.randrange(2,8)
        pp=[]
        for j in range(rng.randrange(1,4)):
            e='e'+str(rng.randrange(max(1,n)));nets.add(e)
            pp.append(pin('p'+str(j),e,rng.randrange(w+1),rng.randrange(h+1)))
        poses=[([r*40+rng.randrange(1,20),rng.randrange(1,20)],rng.choice((0,90,180,270))) for _ in range(q)]
        regions.append(single_region('r'+str(r),[r*40,0,r*40+36,36],[w,h],pp,poses))
    ids=[r['id'] for r in regions];rng.shuffle(ids)
    return {'name':f'random_{seed}_{n}_{q}','regions':regions,'weights':{e:rng.randrange(1,6) for e in sorted(nets)},'tree':balanced(ids)}


def masked(k,q):
    """Two fixed anchors bracket every variable pin. All assignments are optimal."""
    regs=[];W=q+20;H=12*k+10
    for i in range(k):
        regs.append(single_region('v'+str(i),[10,12*i,10+q+2,12*i+10],[1,1],
                                  [pin('p','e'+str(i),0,0)], [([11+c,12*i+5],0) for c in range(q)]))
    for r,x in [('left',0),('right',W)]:
        regs.append(single_region(r,[x,0,x+5,H],[5,H],
                                  [pin('p'+str(i),'e'+str(i),2,12*i+5) for i in range(k)],[([x,0],0)]))
    return {'name':f'masked_{k}_{q}','regions':regs,'weights':{f'e{i}':1 for i in range(k)},
            'tree':[balanced([f'v{i}' for i in range(k)]),['left','right']]}


def exposed(k,q,paired=False):
    """Independent exterior choices expose q**k distinct response profiles."""
    regs=[]
    for i in range(k):
        x=i*40
        regs.append(single_region('v'+str(i),[x,0,x+36,10],[1,1],[pin('p','e'+str(i),0,0)],
                                  [([x+4+c,5],0) for c in range(q)]))
    for i in range(k):
        x=i*40
        regs.append(single_region('a'+str(i),[x,20,x+36,30],[1,1],[pin('p','e'+str(i),0,0)],
                                  [([x+1,25],0),([x+34,25],0)]))
    tree=balanced([[f'v{i}',f'a{i}'] for i in range(k)]) if paired else [balanced([f'v{i}' for i in range(k)]),balanced([f'a{i}' for i in range(k)])]
    return {'name':f'exposed_{k}_{q}'+('_paired' if paired else ''),'regions':regs,
            'weights':{f'e{i}':1 for i in range(k)},'tree':tree}


def public_case(upstream:Path,layout='balanced'):
    lef=(upstream/'macro_only.lef').read_text();verilog=(upstream/'macro_only.v').read_text()
    cells={};scale=2000
    def exact(s):
        value=Fraction(s)*scale
        if value.denominator!=1:raise ValueError('nonintegral DBU conversion')
        return int(value)
    for match in re.finditer(r'^MACRO\s+(\w+)\s*\n(.*?)^END\s+\1\s*$',lef,re.M|re.S):
        name,body=match.group(1),match.group(2)
        if not re.search(r'CLASS\s+BLOCK\s*;',body):continue
        size=re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)\s*;',body)
        if not size:raise ValueError('BLOCK size missing')
        offsets={}
        for pm in re.finditer(r'^\s+PIN\s+(\w+)\s*\n(.*?)^\s+END\s+\1\s*$',body,re.M|re.S):
            rects=re.findall(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*;',pm.group(2))
            if len(rects)!=1:raise ValueError('adapter requires one rectangle per used pin')
            a,b,c,d=map(Fraction,rects[0]);offsets[pm.group(1)]=[exact((a+c)/2),exact((b+d)/2)]
        cells[name]=([exact(x) for x in size.groups()],offsets)
    if set(cells)!={'HM_100x400_4x4','HM_100x100_1x1'}:raise ValueError('unexpected BLOCK inventory')
    regs=[];netnames=set()
    for cm in re.finditer(r'\b(HM_\w+)\s+(U\d+)\s*\((.*?)\)\s*;',verilog,re.S):
        kind,instance,connections=cm.groups();size,offsets=cells[kind]
        pp=[]
        for pname,net in re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)',connections):
            if pname not in offsets:raise ValueError('missing pin definition')
            pp.append(pin(pname,net,*offsets[pname]));netnames.add(net)
        if instance=='U1':box=[0,0,100,450];xy=[0,10]
        elif instance=='U6':box=[350,0,450,450];xy=[350,10]
        else:
            idx=int(instance[1:]);row=(idx-2) if idx<=5 else (idx-7);x=125 if idx<=5 else 225;y=25+100*row
            box=[x,y,x+100,y+100];xy=[x,y]
        box=[v*scale for v in box];xy=[v*scale for v in xy]
        regs.append(single_region(instance,box,size,pp,[(xy,0),(xy,180)]))
    if len(regs)!=10 or len(netnames)!=12:raise ValueError('unexpected netlist inventory')
    ids=[r['id'] for r in regs]
    if layout=='balanced':tree=balanced(ids)
    elif layout=='columns':tree=[['U1',balanced(['U2','U3','U4','U5'])],[balanced(['U7','U8','U9','U10']),'U6']]
    elif layout=='chain':
        tree=ids[0]
        for name in ids[1:]:tree=[tree,name]
    else:raise ValueError(layout)
    return {'name':'openroad_macro_only_'+layout,'regions':regs,'weights':{e:1 for e in sorted(netnames)},'tree':tree,
            'provenance':'OpenROAD regression LEF/Verilog, point pins at RECT centers; new fixed owner regions in a 450um square and R0/R180 portfolios. No OpenROAD execution, routing or upstream placement results.'}



def _parse_core_bookshelf(upstream:Path,circuit:str):
    """Parse the normalized CORE copies of one MCNC/GSRC block/net pair.

    The returned topology retains only placeable blocks. Terminals are parsed
    only to validate the original file; terminal-only connections are not
    represented in the independently placed-region model.
    """
    block_path=upstream/(circuit+'.block');net_path=upstream/(circuit+'.nets')
    block_lines=[line.strip() for line in block_path.read_text().splitlines() if line.strip()]
    require=lambda test,msg: test or (_ for _ in ()).throw(ValueError(msg))
    require(block_lines and block_lines[0].startswith('Outline:'),'missing outline')
    nblocks=int(block_lines[1].split(':',1)[1]);nterm=int(block_lines[2].split(':',1)[1])
    blocks={}
    terminals={}
    for line in block_lines[3:]:
        fields=line.split()
        if len(fields)==3 and fields[1]!='terminal' and len(blocks)<nblocks:
            name,w,h=fields;blocks[name]=(int(w),int(h))
        elif len(fields)==4 and fields[1]=='terminal':
            name,_,x,y=fields;terminals[name]=(int(x),int(y))
        else:raise ValueError('malformed block line: '+line)
    require(len(blocks)==nblocks,'block count mismatch')
    require(len(terminals)==nterm,'terminal count mismatch')
    lines=[line.strip() for line in net_path.read_text().splitlines() if line.strip()]
    require(lines and lines[0].startswith('NumNets:'),'missing net count')
    declared=int(lines[0].split(':',1)[1]);i=1;nets=[]
    while i<len(lines):
        require(lines[i].startswith('NetDegree:'),'missing NetDegree')
        degree=int(lines[i].split(':',1)[1]);members=lines[i+1:i+1+degree]
        require(len(members)==degree,'short net')
        require(all(x in blocks or x in terminals for x in members),'unknown cell in net')
        nets.append(tuple(members));i+=1+degree
    require(i==len(lines) and len(nets)==declared,'net count mismatch')
    induced=Counter()
    for members in nets:
        edge=tuple(sorted(set(x for x in members if x in blocks)))
        if len(edge)>=2:induced[edge]+=1
    require(induced,'no block-induced nets')
    return blocks,nets,induced


def _netaware_tree(names,weighted_edges):
    """Exact deterministic recursive minimum-cut hierarchy for <=11 owners.

    Each split has floor(n/2) leaves on the anchored side. Only the public
    macro hypergraph and multiplicities are used; candidate coordinates and
    method outcomes are not consulted.
    """
    names=tuple(sorted(names))
    if len(names)==1:return names[0]
    left_size=len(names)//2;anchor=names[0];best=None
    for tail in itertools.combinations(names[1:],left_size-1):
        left=frozenset((anchor,*tail));right=frozenset(names)-left
        cut=sum(weight for edge,weight in weighted_edges.items()
                if left.intersection(edge) and right.intersection(edge))
        key=(cut,tuple(sorted(left)))
        if best is None or key<best[0]:best=(key,left,right)
    _,left,right=best
    return [_netaware_tree(tuple(sorted(left)),weighted_edges),
            _netaware_tree(tuple(sorted(right)),weighted_edges)]


def core_public_case(upstream:Path,circuit='hp',layout='balanced',portfolio='orientation'):
    """Adapt a public MCNC/GSRC macro hypergraph into a finite portfolio case.

    The source block dimensions and macro-only connectivity are retained.
    Terminals are removed; duplicate induced hyperedges become integer weights.
    Every block gets a disjoint owner box, deterministic quarter-offset pins,
    and fixed R0/R180 alternatives. These portfolios and hierarchies are new experiment inputs,
    not placements distributed by the source project.
    """
    if circuit not in ('hp','n10','apte','xerox'):raise ValueError(circuit)
    if portfolio not in ('orientation','orientation4','translation'):raise ValueError(portfolio)
    blocks,raw_nets,edges=_parse_core_bookshelf(upstream,circuit)
    names=sorted(blocks);edge_names={edge:f'e{i:02d}' for i,edge in enumerate(sorted(edges))}
    if portfolio=='orientation':
        cell_w=max(w for w,_ in blocks.values())+100
        cell_h=max(h for _,h in blocks.values())+100
    elif portfolio=='orientation4':
        side=max(max(w,h) for w,h in blocks.values())
        cell_w=cell_h=side+100
    else:
        cell_w=max(w+max(1,w//4) for w,_ in blocks.values())+100
        cell_h=max(h+max(1,h//4) for _,h in blocks.values())+100
    cols=math.ceil(math.sqrt(len(names)));regions=[]
    for index,name in enumerate(names):
        w,h=blocks[name];x=(index%cols)*cell_w;y=(index//cols)*cell_h
        incident=sorted(e for e in edges if name in e)
        if portfolio in ('orientation','orientation4'):
            x1=max(1,w//4);x2=w-x1;y1=max(1,h//4);y2=h-y1
            sites=((x1,y1),(x2,y1),(x1,y2),(x2,y2))
            pins=[pin('p'+str(j),edge_names[edge],*sites[j%len(sites)])
                  for j,edge in enumerate(incident)]
            if portfolio=='orientation':
                box=[x,y,x+w,y+h];poses=[([x,y],0),([x,y],180)]
            else:
                side=max(w,h);box=[x,y,x+side,y+side]
                poses=[([x,y],angle) for angle in (0,90,180,270)]
        else:
            dx=max(1,w//4);dy=max(1,h//4)
            pins=[pin('p'+str(j),edge_names[edge],w//2,h//2)
                  for j,edge in enumerate(incident)]
            box=[x,y,x+w+dx,y+h+dy];poses=[([x,y],0),([x+dx,y+dy],0)]
        regions.append(single_region(name,box,[w,h],pins,poses))
    if layout=='balanced':tree=balanced(names)
    elif layout=='netaware':tree=_netaware_tree(names,edges)
    else:raise ValueError(layout)
    suite='GSRC' if circuit.startswith('n') else 'MCNC'
    suffix={'orientation':'','orientation4':'_orientation4','translation':'_translation'}[portfolio]
    return {'name':f'core_{circuit}_{layout}{suffix}','regions':regions,
            'weights':{edge_names[e]:edges[e] for e in sorted(edges)},'tree':tree,
            'provenance':f'{suite} {circuit} block dimensions and macro-only hypergraph from normalized text copies in the CORE repository. Fixed terminals are removed and repeated block-induced hyperedges become integer weights. '+('Disjoint owner boxes, deterministic quarter-offset point pins, and R0/R180 alternatives are newly constructed by the frozen orientation adapter.' if portfolio=='orientation' else ('Disjoint square owner boxes, the same deterministic quarter-offset point pins, and R0/R90/R180/R270 alternatives are newly constructed by the frozen four-orientation extension adapter.' if portfolio=='orientation4' else 'Disjoint owner boxes, center pins, and two diagonal translations are newly constructed by the retained development null adapter.'))+' This is not an original benchmark placement or a CORE execution result.'}

def generate(out:Path,upstream:Path,include_core:bool=False):
    out.mkdir(parents=True,exist_ok=True)
    cases=[]
    for k in (2,4,6,8,10,12):
        for q in (2,4):
            cases.extend([masked(k,q),exposed(k,q)])
    cases.extend([exposed(12,q,True) for q in (2,4)])
    cases.extend(public_case(upstream,l) for l in ('balanced','columns','chain'))
    if include_core:
        core=upstream/'core'
        cases.extend(core_public_case(core,circuit,layout)
                     for circuit in ('hp','n10','apte','xerox') for layout in ('balanced','netaware'))
    for c in cases:(out/(c['name']+'.json')).write_text(json.dumps(c,indent=2)+'\n')
    return cases


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='data/cases');p.add_argument('--upstream',default='data/upstream');a=p.parse_args()
    print(json.dumps({'generated':len(generate(Path(a.out),Path(a.upstream)))}))
