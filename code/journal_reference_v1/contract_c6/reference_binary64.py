"""Independent C6 candidate oracle. No production imports or observed expected values.
Run: python reference_binary64.py OUTPUT_DIRECTORY. Python stdlib only.
"""
from fractions import Fraction as Q
import math, struct, json, sys, platform, itertools
from pathlib import Path

def rn(x):
    """Exact rational -> IEEE binary64 round-to-nearest ties-to-even, gradual underflow."""
    x=Q(x)
    if not x: return Q(0)
    sign=-1 if x<0 else 1; x=abs(x)
    e=x.numerator.bit_length()-x.denominator.bit_length()
    if x<Q(2)**e: e-=1
    step=Q(2)**max(e-52,-1074)
    z=x/step; n,r=divmod(z.numerator,z.denominator)
    n+= (2*r>z.denominator or (2*r==z.denominator and n%2==1))
    y=sign*n*step
    if abs(y)>Q.from_float(sys.float_info.max): raise OverflowError('oracle finite domain')
    return y

def add(x,y): return rn(x+y)
def sub(x,y): return rn(x-y)
def mul(x,y): return rn(x*y)
def div(x,y): return rn(x/y)
def clip(x): return min(Q(1),max(Q(0),x))
A=Q('0.35'); EPS=Q('0.000001'); AB=rn(A); EB=rn(EPS)
K=('material','fairness','relationship','safety')

def real(v,q,a=A,e=EPS,d=Q(1)):
    v=Q(v);q=Q(q)
    current=clip((1-a)*v+a*q); delta=current-v
    h=max(e,abs(d-v) if delta>0 else v)
    u=(1 if delta>0 else -1)*min(Q(1),abs(delta)/h) if delta else Q(0)
    return current,delta,u

class Binary64:
    """Exact dyadic value plus the zero sign; bits never inferred from Fraction zero."""
    def __init__(self,value,negative_zero=False):
        original=Q(value);self.value=rn(original)
        self.negative_zero=(original<0 or negative_zero) if not self.value else False
    @classmethod
    def input(cls,x):
        if isinstance(x,cls): return x
        if isinstance(x,float):
            if not math.isfinite(x): raise ValueError('nonfinite binary64 input')
            return cls(Q.from_float(x),x==0 and math.copysign(1.,x)<0)
        return cls(x)
    @property
    def sign(self): return self.value<0 or (self.value==0 and self.negative_zero)
    def metadata(self):
        f=-0.0 if self.value==0 and self.negative_zero else float(self.value)
        return dict(fraction=str(self.value),float=f,hex=f.hex(),bits_hex=struct.pack('>d',f).hex(),sign_bit=int(self.sign))

def binary(op,x,y):
    x=Binary64.input(x);y=Binary64.input(y)
    if op=='add':
        r=x.value+y.value;neg=(not r and not x.value and not y.value and x.sign and y.sign)
    elif op=='sub':
        r=x.value-y.value;neg=(not r and not x.value and not y.value and x.sign and not y.sign)
    elif op=='mul': r=x.value*y.value;neg=x.sign!=y.sign
    elif op=='div': r=x.value/y.value;neg=x.sign!=y.sign
    else: raise ValueError(op)
    return Binary64(r,negative_zero=bool(neg and not r))

def babs(x): return Binary64(abs(x.value))
def bclip(x):
    # Literal min(1,max(+0,total)): equality selects first operand +0.
    if x.value<=0:return Binary64(0)
    return Binary64(1) if x.value>1 else x

def graph(v,q,identity=True,d=Q(1),e=EB):
    if not (0<=v<=1 and 0<=q<=1 and 0<=d<=1 and e>0): raise ValueError('invalid oracle projection domain')
    bv=Binary64.input(v);bq=Binary64.input(q);bd=Binary64.input(d);be=Binary64.input(e)
    ba=Binary64(AB);c=binary('sub',1,ba)
    same=bq.value==bv.value and identity
    nodes=dict(v=bv,q=bq,c=c)
    if same:
        nodes.update(current=bv,delta=Binary64(0),denominator=be,u=Binary64(0),u_abs=Binary64(0))
    else:
        left=binary('mul',c,bv);right=binary('mul',ba,bq);total=binary('add',left,right)
        current=bclip(total);delta=binary('sub',current,bv)
        distance=babs(binary('sub',bd,bv)) if delta.value>0 else bv
        denominator=be if be.value>=distance.value else distance
        ratio=binary('div',babs(delta),denominator) if delta.value else Binary64(0)
        magnitude=Binary64(1) if ratio.value>1 else ratio
        u=Binary64(-magnitude.value,negative_zero=magnitude.value==0) if delta.value<0 else magnitude if delta.value>0 else Binary64(0)
        nodes.update(left=left,right=right,total=total,current=current,delta=delta,denominator=denominator,ratio=ratio,u=u,u_abs=babs(u))
    return {**{k:x.value for k,x in nodes.items()},'identity':same,'ieee_nodes':{k:x.metadata() for k,x in nodes.items()}}

def native(v,q):
    v=float(v);q=float(q);a=float(AB);e=float(EB)
    cur=v if q==v else min(1.,max(0.,(1.-a)*v+a*q))
    delta=cur-v
    den=max(e,abs(1.-v) if delta>0 else v)
    u=math.copysign(min(1.,abs(delta)/den),delta) if delta else 0.
    return cur,delta,u

def record(x):
    b=Binary64.input(x)
    return b.metadata() | {'fraction':str(Q(x)),'displayed_binary64_fraction':str(b.value),'ieee_metadata_role':'display_rounding_of_exact_rational'}
def node_records(g): return g['ieee_nodes'] | {'identity':g['identity']}

def signed_zero_checks():
    rows=[];positive='0000000000000000';negative='8000000000000000'
    def check(path,label,v,q,expected_current_bits,expected_identity):
        g=graph(v,q);nodes=node_records(g)
        assert g['identity']==expected_identity
        assert nodes['current']['bits_hex']==expected_current_bits
        if v==0:
            assert nodes['v']['bits_hex']==(negative if math.copysign(1.,v)<0 else positive)
        for k in ['delta','u','u_abs']:assert nodes[k]['bits_hex']==positive,k
        native_values=native(v,q)
        assert struct.pack('>d',native_values[0]).hex()==expected_current_bits
        assert struct.pack('>d',native_values[1]).hex()==positive
        assert struct.pack('>d',native_values[2]).hex()==positive
        rb=real(Q.from_float(v),Q.from_float(q),AB,EB)
        bound=8*Q(2)**-52/EB
        assert abs(g['u']-rb[2])<=bound
        rows.append(dict(path=path,label=label,ideal_input_known=False,input_origin='binary64_hex_designated',actual_ideal_status='unavailable_no_known_preconversion_state',rounded_inputs={'v':Binary64.input(v).metadata(),'q':Binary64.input(q).metadata()},nodes=nodes,expected_bits={'current':expected_current_bits,'delta':positive,'u':positive,'u_abs':positive},real_on_rounded_inputs=record(rb[2]),arithmetic_error=record(g['u']-rb[2]),arithmetic_bound=record(bound),comparison='exact_bits_not_numeric_tolerance'))
    for path in ['candidate','realized_full']:
        for v,q in itertools.product([0.,-0.],repeat=2):
            check(path,'all_four_signed_zero_identity_pairs',v,q,negative if math.copysign(1.,v)<0 else positive,True)
    material=[]
    for v,q_raw in itertools.product([0.,-0.],repeat=2):
        # Bit-preserving F32 copy, never round/reconstruct from Fraction.
        q_star=v
        expected=negative if math.copysign(1.,v)<0 else positive
        check('realized_material_only_nonmaterial','F32_bit_preserving_copy',v,q_star,expected,True)
        for candidate_path in ['candidate_full','candidate_material_only']:
            check(candidate_path,'candidate_reads_raw_not_applied_target',v,q_raw,expected,True)
        material.append(dict(v=Binary64.input(v).metadata(),raw_q=Binary64.input(q_raw).metadata(),q_star=Binary64.input(q_star).metadata(),copied_bits_equal_v=True,raw_q_untouched=True,channels=['fairness','relationship','safety']))
    nonidentity=[(math.nextafter(1.,0.),1.),(math.nextafter(0.,1.),0.),(0.,math.nextafter(0.,1.)),(-0.,math.nextafter(0.,1.))]
    for path in ['candidate','realized_full']:
        for v,q in nonidentity:
            # First two current bits retain interior v; zero cases clip to +0.
            bits=struct.pack('>d',v).hex() if v else positive
            check(path,'nonidentity_zero_delta',v,q,bits,False)
    return dict(fixtures=rows,material_only_copy_checks=material,status='OWNER_SELF_CHECK_ONLY_NOT_INDEPENDENT_CLOSURE')
def ug(o,action,adapter):
    # Independently derived exact F31/F04 responder targets, no CSV/production import.
    balance=1-Q(abs(10-2*o),10)
    if action=='accept': return (Q(o,8),balance,Q(1),Q(1))
    return (Q(0),1-balance if adapter=='N' else Q(0) if adapter=='A' else Q(1,2),Q(1,2) if adapter=='B' else Q(0),1-Q(o,8))

def ug_exec(o,action,adapter):
    # Literal F31/F04 binary64 graph; exact game integers, every arithmetic node rounded.
    balance=sub(Q(1),div(abs(sub(Q(10),mul(Q(2),Q(o)))),Q(10)))
    resisted=sub(Q(1),balance)
    if action=='accept': return (div(Q(o),Q(8)),balance,Q(1),Q(1))
    return (Q(0),resisted if adapter=='N' else Q(0) if adapter=='A' else Q(1,2),Q(1,2) if adapter=='B' else Q(0),sub(Q(1),div(Q(o),Q(8))))

def vote(o,adapter,values,priorities):
    ca=[graph(v,q)['u'] for v,q in zip(values,ug_exec(o,'accept',adapter))]
    cr=[graph(v,q)['u'] for v,q in zip(values,ug_exec(o,'reject',adapter))]
    z=[(x>y)-(x<y) for x,y in zip(ca,cr)]
    terms=[mul(rn(p),Q(s)) for p,s in zip(priorities,z)]
    # Independent exact accumulator rounded once; runtime math.fsum qualification below.
    n=rn(sum(terms,Q(0)));p=rn(sum(map(rn,priorities),Q(0)));diagnostic=div(n,p)
    assert Q.from_float(math.fsum(float(t) for t in terms))==n
    assert Q.from_float(math.fsum(float(t) for t in map(rn,priorities)))==p
    return z,n,p,diagnostic,'accept' if n>0 else 'reject','positive' if n>0 else 'negative' if n<0 else 'tie_reject'

def candidate_diagnostics(o,adapter,values):
    data={}
    for action in ['accept','reject']:
        data[action]={}
        for k,v,q in zip(K,values,ug_exec(o,action,adapter)):
            g=graph(v,q);r=real(rn(v),q,AB,EB)[2]
            assert abs(g['u']-r)<=8*Q(2)**-52/EB
            data[action][k]={'real_on_rounded_inputs':record(r),'executable_B':g['ieee_nodes']['u'],'arithmetic_error':record(g['u']-r),'arithmetic_bound':record(8*Q(2)**-52/EB)}
    return data

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cases=[]; asserts=0
    def fixture(name,v,q,label,ideal=True):
        nonlocal asserts
        g=graph(v,q);rb=real(rn(v),rn(q),AB,EB)
        arith=g['u']-rb[2]
        eta=Q(2)**-52;bound=8*eta/EB
        assert abs(arith)<=bound
        assert Q(0)<=g['current']<=1 and abs(g['u'])<=1
        assert not (g['v']==1 and g['delta']>0) and not (g['v']==0 and g['delta']<0)
        assert abs(g['u'])<=AB+bound
        assert tuple(Q.from_float(x) for x in native(v,q))==(g['current'],g['delta'],g['u'])
        if rn(v)==rn(q): assert g['current']==rn(v) and g['delta']==0 and g['u']==0
        asserts+=6
        row=dict(id=name,label=label,ideal_input_known=ideal,input_origin='exact_decimal_or_rational_known' if ideal else 'binary64_hex_designated',rounded_inputs={'v':Binary64.input(v).metadata(),'q':Binary64.input(q).metadata(),'alpha':record(AB),'epsilon':record(EB)},nodes=node_records(g),real_on_rounded_inputs=record(rb[2]),arithmetic_error=record(arith),arithmetic_bound=record(bound))
        if ideal:
            ri=real(v,q);inp=rb[2]-ri[2];total=g['u']-ri[2];assert inp+arith==total
            emin=min(EPS,EB);amax=max(A,AB)
            input_bound=abs(AB-A)/emin+amax*abs(rn(q)-q)/emin+amax*abs(rn(v)-v)*(1/emin+1/emin**2)+amax*abs(EB-EPS)/emin**2
            assert abs(inp)<=input_bound and abs(total)<=input_bound+bound
            row.update(ideal_inputs={'v':str(v),'q':str(q),'alpha':str(A),'epsilon':str(EPS)},original_exact_tokens={'alpha':'0.35','epsilon':'0.000001','v_rational':str(v),'q_rational':str(q)},scientific_ideal=record(ri[2]),input_error=record(inp),total_error=record(total),input_bound=record(input_bound),total_bound=record(input_bound+bound))
        else:
            row['actual_ideal_status']='unavailable_no_known_preconversion_state'
            assert not any(k in row for k in ['ideal_inputs','scientific_ideal','input_error','total_error','input_bound','total_bound'])
        cases.append(row)
    fixture('near_epsilon_gain',1-EPS/2,Q(1),'legal_injected_UG_R_offer8_accept_material')
    fixture('near_epsilon_loss',EPS/2,Q(0),'legal_injected_UG_R_reject_material')
    for name,v,q in [('near_gain',1-EPS/2,Q(1)),('near_loss',EPS/2,Q(0))]:
        for direction in [-math.inf,math.inf]:
            fixture(f'{name}_neighbor_{direction}',Q.from_float(math.nextafter(float(rn(v)),direction)),q,'legal_injected_binary64_state',False)
    for name,v in [('zero',Q(0)),('one',Q(1)),('epsilon',EPS),('one_minus_epsilon',1-EPS),('half',Q(1,2))]:
        for direction in [-math.inf,math.inf]:
            b=Q.from_float(math.nextafter(float(rn(v)),direction))
            if 0<=b<=1:
                for q in (Q(0),Q(1),b): fixture(f'{name}_neighbor_{direction}_{q}',b,q,'legal_injected_binary64_state',False)
        for q in (Q(0),Q(1),v): fixture(f'{name}_{q}',v,q,'legal_injected')
    identity_witness=None
    for i in range(1,1000):
        v=Q(i,1000);g=graph(v,v,False)
        if g['delta']:
            identity_witness={'v':record(rn(v)),'literal_delta':record(g['delta']),'literal_u':record(g['u']),'identity_u':record(graph(v,v)['u'])};break
    assert identity_witness
    values=sorted(set([Q(0),Q(1),Q(1,2),rn(EPS/2),rn(1-EPS/2),Q(1,1000),Q.from_float(math.nextafter(1.,0.)),Q.from_float(math.nextafter(0.,1.))]))
    profiles=[(1,1,1,1),(Q(3,2),Q(1,2),Q(1,2),Q(1,2)),(Q(1,2),Q(3,2),Q(1,2),Q(1,2)),(Q(1,2),Q(1,2),Q(3,2),Q(1,2)),(Q(1,2),Q(1,2),Q(1,2),Q(3,2))]
    votes=[]
    for adapter in 'NAB':
        for o in range(2,9):
            target=[(x>y)-(x<y) for x,y in zip(ug(o,'accept',adapter),ug(o,'reject',adapter))]
            for v in values:
                for p in profiles:
                    z,n,den,d,action,category=vote(o,adapter,[v]*4,p); assert z==target
                    votes.append(dict(adapter=adapter,offer=o,v_hex=float(v).hex(),input_origin='binary64_hex_designated',ideal_input_known=False,actual_ideal_status='unavailable_no_known_preconversion_state',p=list(map(float,p)),z=z,N=record(n),P=record(den),D=record(d),action=action,category=category,candidate_appraisal_diagnostics=candidate_diagnostics(o,adapter,[v]*4)));asserts+=2
    neighbors=[]
    for p,label in [(profiles[2],'legal_tie'),((Q(1,2),Q.from_float(math.nextafter(1.5,-math.inf)),Q(1,2),Q(1,2)),'legal_fairness_lower'),((Q.from_float(math.nextafter(.5,math.inf)),Q(3,2),Q(1,2),Q(1,2)),'legal_material_upper')]:
        z,n,den,d,action,cat=vote(8,'N',[Q(1,2)]*4,p);neighbors.append(dict(label=label,N=record(n),D=record(d),action=action,category=cat))
    negative=rn(sum((Q(1,2),-Q.from_float(math.nextafter(1.5,math.inf)),Q(1,2),Q(1,2)),Q(0)))
    assert negative<0
    neighbors.append(dict(label='helper_only_fairness_above_pmax',N=record(negative),action='reject'))
    for row in neighbors:
        row.update(input_origin='binary64_hex_designated',ideal_input_known=False,actual_ideal_status='unavailable_no_known_preconversion_state')
    # Extremal one-step stagnation: literal fixed-alpha graph does NOT reach endpoints.
    sat=graph(Q.from_float(math.nextafter(1.,0.)),Q(1));assert sat['current']==Q.from_float(math.nextafter(1.,0.))
    low=graph(Q.from_float(math.nextafter(0.,1.)),Q(0));assert low['current']==Q.from_float(math.nextafter(0.,1.))
    # Wider helper only, current .6 > prev=desired=.5: clipped urgency=1.
    helper_delta=sub(rn(Q('0.6')),Q(1,2));helper_u=min(Q(1),div(helper_delta,EB));assert helper_u==1
    for terms in itertools.permutations((.5,-1.5,.5,.5)): assert math.fsum(terms)==0.
    # Independently exercise material_only realization; candidates always use raw targets.
    mv=[rn(Q('0.013'))]*4;raw=ug_exec(8,'accept','N')
    full=[graph(v,q) for v,q in zip(mv,raw)]
    applied=[raw[0],*mv[1:]];material=[graph(v,q) for v,q in zip(mv,applied)]
    assert material[0]==full[0]
    assert all(g['current']==v and g['delta']==0 and g['u']==0 for v,g in zip(mv[1:],material[1:]))
    candidate_full=[graph(v,q) for v,q in zip(mv,raw)]
    candidate_material_only=[graph(v,q) for v,q in zip(mv,raw)]
    assert candidate_full==candidate_material_only
    for v,q in [(Q(-1),Q(0)),(Q(0),Q(2)),(Q(2),Q(1))]:
        try: graph(v,q)
        except ValueError: pass
        else: raise AssertionError('domain rejection required')
    # RNE qualification: even/odd halfway, underflow tie and smallest subnormal.
    assert rn(1+Q(2)**-53)==1
    assert rn(1+3*Q(2)**-53)==1+Q(2)**-51
    assert rn(Q(2)**-1075)==0 and rn(3*Q(2)**-1075)==Q(2)**-1073
    zero=signed_zero_checks()
    ancillary_origin=dict(input_origin='binary64_hex_designated',ideal_input_known=False,actual_ideal_status='unavailable_no_known_preconversion_state',scope=['identity_witness','upper_stagnation','lower_stagnation','helper_saturation','branch_neighbors'],rule='executable witnesses only; no actual I, conversion or total residual fields')
    report=dict(status='OWNER_SELF_CHECK_ONLY_NOT_INDEPENDENT_R0',python=sys.version,platform=platform.platform(),float_info=str(sys.float_info),scalar_fixtures=len(cases),known_ideal_scalar_rows=sum(c['ideal_input_known'] for c in cases),unknown_ideal_scalar_rows=sum(not c['ideal_input_known'] for c in cases),vote_fixtures=len(votes),signed_zero_fixtures=len(zero['fixtures']),material_only_signed_copy_vectors=len(zero['material_only_copy_checks']),assertions=asserts,additional_checks=['endpoint_signs','24_fsum_permutations','material_only_four_channel_identity_and_material_equality','3_illegal_domains','4_RNE_halfway_subnormal_cases','exact_bit_signed_zero_checks'],identity_witness=identity_witness,upper_stagnation=node_records(sat),lower_stagnation=node_records(low),helper_saturation=record(helper_u),branch_neighbors=neighbors,empirical_pilot_full_runs=0,production_imports=0)
    (out/'ORACLE_FIXTURES_C6.json').write_text(json.dumps(cases,indent=2)+'\n')
    report['ancillary_input_origin']=ancillary_origin
    (out/'F35_FIXTURES_C6.json').write_text(json.dumps(votes,indent=2)+'\n')
    (out/'SELF_CHECK_C6.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SIGNED_ZERO_FIXTURES_C6.json').write_text(json.dumps(zero,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else '.')
