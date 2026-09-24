"""Finite integer probe of the self-context maximum identity (not a general proof)."""
import itertools, json, resource, time
start=time.process_time(); checks=0; contexts=0
ints=[(a,b) for a in range(5) for b in range(a,5)]
def clip(x,a,b):return min(b,max(a,x))
def span(l,u,a,b):return max(u,b)-min(l,a)
for A in ints:
 for B in ints:
  if A[0]>B[0] or A[1]>B[1]:continue
  D=[(a,b) for a in range(A[0],A[1]+1) for b in range(B[0],B[1]+1) if a<=b]
  for p in ints:
   for q in ints:
    pk=(clip(p[0],*A),clip(p[1],*B));qk=(clip(q[0],*A),clip(q[1],*B))
    dp=max(A[0]-p[0],0)+max(p[1]-B[1],0)
    dq=max(A[0]-q[0],0)+max(q[1]-B[1],0)
    direct=max(span(*p,*c)-span(*q,*c) for c in D)
    closed=dp-dq+max(qk[0]-pk[0],0)+max(pk[1]-qk[1],0)
    assert direct==closed,(A,B,p,q,direct,closed)
    assert qk in D
    assert direct==span(*p,*qk)-span(*q,*qk)
    checks+=1;contexts+=len(D)
print(json.dumps({'identity_pairs':checks,'explicit_context_evaluations':contexts,'cpu_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'passed':True},indent=2))
