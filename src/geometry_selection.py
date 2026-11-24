"""Physical geometry selection, separate from the unchanged v1.3 engine.

For OD/ID entry retain the historical ODmin/IDmax convention. For independent
diameter/thickness limits select the physical geometry with highest utilisation
across working/test and applicable criteria. All reported stresses refer to that
one geometry. In ratio x=R/t, stresses on each edge of the tolerance rectangle
have form a*x+b+c/x. At fixed x, utilisation is convex in 1/t**2 (axial stress
is affine in it), so maxima lie on the rectangle boundary. Split edges at x=10.
Von Mises stationary points satisfy a quartic; shear pair differences have at
most one stationary point each. Check edge ends and those stationary points.
"""
import math
from cases import calculate_case
from input_validation import validate_inputs

def _roots(coeff,lo,hi):
    # Real roots on a positive finite interval, isolated by derivative roots.
    # Scale x to [0,1] for evaluating the stopping tolerance, not coefficients.
    coeff=list(coeff)
    while len(coeff)>1 and coeff[0]==0:coeff.pop(0)
    if len(coeff)==1:return []
    scale=max(abs(c) for c in coeff)
    if not scale:return []
    coeff=[c/scale for c in coeff]
    if len(coeff)==2:
        r=-coeff[1]/coeff[0]
        return [r] if lo<=r<=hi else []
    degree=len(coeff)-1
    critical=_roots([c*(degree-i) for i,c in enumerate(coeff[:-1])],lo,hi)
    knots=sorted(set([lo,*critical,hi]))
    def val(x):
        y=0.
        for c in coeff:y=y*x+c
        return y
    roots=[]
    for x in knots:
        v=val(x)
        magnitude=sum(abs(c)*x**(degree-i) for i,c in enumerate(coeff))
        if abs(v)<=1e-12*max(magnitude,1e-300):roots.append(x)
    for a,b in zip(knots,knots[1:]):
        fa,fb=val(a),val(b)
        if (fa<0)==(fb<0) or fa==0 or fb==0:continue
        for _ in range(100):
            mid=a+(b-a)/2
            if mid==a or mid==b:break
            fm=val(mid)
            if fm==0:a=b=mid;break
            if (fm<0)==(fa<0):a=mid;fa=fm
            else:b=mid
        roots.append(a+(b-a)/2)
    return sorted(set(roots))

def _stress_coeff(x_const,kind,diam,thick,external,capped,p,F):
    # triples are coefficient of x, constant, coefficient of 1/x.
    sign=-1 if external else 1
    if kind=="t":ax=(0.,0.,F/(2*math.pi*x_const*x_const))
    else:
        k=2*F/(math.pi*diam*diam)
        ax=(k,k if kind=="od" else -k,k/4)
    if thick:
        hoop=(-p,-p,-p/4) if external else (p,0.,p/4)
        radial=(0.,0.,0. if external else 0.) if external else (0.,-p,0.)
        z=(sign*p/2,-p/2,sign*p/8) if capped else (0.,0.,0.)
    else:
        hoop=(sign*p,0.,0.);radial=(0.,0.,0.)
        z=(sign*p/2,0.,0.) if capped else (0.,0.,0.)
    long=tuple(a+b for a,b in zip(z,ax))
    return [tuple(a-b for a,b in zip(u,v)) for u,v in ((long,hoop),(hoop,radial),(radial,long))]

def _stationary(lo,hi,diffs,thick):
    A=sum(a*a for a,b,c in diffs);B=2*sum(a*b for a,b,c in diffs)
    D=2*sum(b*c for a,b,c in diffs);E=sum(c*c for a,b,c in diffs)
    roots=_roots([2*A,B,0.,-D,-2*E],lo,hi)
    if thick:
        for a,b,c in diffs:
            if a and c/a>0:
                r=math.sqrt(c/a)
                if lo<=r<=hi:roots.append(r)
    return roots

def _score(result):
    return max(v for k in ("working","test") for v in (result[k]["uf_vm"],result[k]["uf_tau"]) if v is not None)

def select_geometry(bounds,derived,loading):
    """Return validated inputs, result and governing geometry selection basis."""
    if derived=="t":
        od,idd=float(bounds["od"][0]),float(bounds["id"][1])
        raw=validate_inputs(dict(loading,od=od,id=idd))
        return raw,calculate_case(raw),"Legacy minimum OD / maximum ID"
    kind="od" if derived=="id" else "id"
    dlo,dhi=map(float,bounds[kind]);tlo,thi=map(float,bounds["t"])
    if min(dlo,tlo)<=0 or dhi<dlo or thi<tlo or (kind=="od" and dlo<=2*thi):
        raise ValueError("All permitted diameter/thickness combinations must have positive bore and wall thickness.")
    # Exact alternative inputs use decimal dimensional arithmetic, just as
    # the original interface would receive the resulting explicit OD/ID.
    if bounds[kind][0]==bounds[kind][1] and bounds["t"][0]==bounds["t"][1]:
        d,t=bounds[kind][0],bounds["t"][0]
        od,idd=(d,d-2*t) if kind=="od" else (d+2*t,d)
        raw=validate_inputs(dict(loading,od=float(od),id=float(idd)))
        return raw,calculate_case(raw),"Exact diameter/thickness geometry"
    # Validate loading before evaluating a finite geometry.
    def geom(d,t):
        return (d,d-2*t) if kind=="od" else (d+2*t,d)
    od,idd=geom(dlo,tlo)
    base=validate_inputs(dict(loading,od=od,id=idd))
    external=base["pressure_type"]=="external";capped=base["end_condition"]=="capped"
    F=base["axial_load"]
    shift=-.5 if kind=="od" else .5
    def ratio(d,t):return d/(2*t)+shift
    candidates=set()
    def add(d,t):
        d=min(dhi,max(dlo,d));t=min(thi,max(tlo,t))
        candidates.add((d,t))
    for d in (dlo,dhi):
        for t in (tlo,thi):add(d,t)
    for edge,fixed,lo,hi in [("t",t,ratio(dlo,t),ratio(dhi,t)) for t in (tlo,thi)]+[(kind,d,ratio(d,thi),ratio(d,tlo)) for d in (dlo,dhi)]:
        def at(x):
            return (2*fixed*(x-shift),fixed) if edge=="t" else (fixed,fixed/(2*(x-shift)))
        for thick in (True,False):
            a,b=(lo,min(hi,10.)) if thick else (max(lo,10.),hi)
            if a>b or (not thick and b<=10):continue
            xs=[a,b]
            # Include both sides of the piecewise threshold; the original
            # dispatcher, rather than a forced method, evaluates every point.
            if a<=10<=b:
                xs.extend([10-1e-10,10+1e-10])
            for p in (base["working_pressure"],base["test_pressure"]):
                diffs=_stress_coeff(fixed,edge,fixed,thick,external,capped,p,F)
                xs.extend(_stationary(a,b,diffs,thick))
            for x in xs:
                if lo<=x<=hi:add(*at(x))
    best=None
    for d,t in sorted(candidates):
        od,idd=geom(d,t)
        raw=validate_inputs(dict(base,od=od,id=idd))
        result=calculate_case(raw)
        score=_score(result)
        if not math.isfinite(score):raise ValueError("Non-finite stress result.")
        if best is None or score>best[0]:best=(score,raw,result)
    return best[1],best[2],"Physical diameter/thickness geometry governing maximum utilisation"
