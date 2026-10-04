"""Independent ordered RN formula substitutions; no observed expected values.

Only frozen registry data and the supplied exact-rational binary64 oracle are read.
Every elementary arithmetic operation rounds an exact rational independently.
"""
from fractions import Fraction as Q
from journal_reference_v1.schema import REGISTRY, C, K
from journal_reference_v1.evidence import oracle


def op(name,x,y):
    a=Q.from_float(float(x));b=Q.from_float(float(y))
    return float(oracle.rn({'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,'div':lambda:a/b}[name]()))
def add(x,y):return op('add',x,y)
def sub(x,y):return op('sub',x,y)
def mul(x,y):return op('mul',x,y)
def div(x,y):return op('div',x,y)
def fold(values):
    total=0.
    for x in values:total=add(total,x)
    return total
def clip(lo,hi,x):return min(hi,max(lo,x))


def derived(v,p,m,f):
    pc=[clip(.5,1.5,x) for x in p];den=fold(pc);pb=[div(x,den) for x in pc]
    w=fold(mul(a,b) for a,b in zip(pb,v));wt=clip(-1,1,sub(mul(2,w),1));r=sub(1,f)
    overall=sub(add(mul(C['lambda_W'],wt),mul(C['lambda_m'],m)),mul(C['lambda_f'],f))
    return {'pbar':dict(zip(K,pb)),'r':r,'W':w,'Wtilde':wt,'S':overall}


def impulse(pre,kind):
    if kind=='rational_only':return 0.
    x=add(add(mul(C['b_m'],pre['m']),mul(C['b_f'],pre['f'])),mul(C['b_W'],sub(pre['W'],C['W_center'])))
    return clip(-1.5,1.5,mul(REGISTRY['intensity_map'][pre['intensity']],x))


def threshold(pre):
    m=C['m_negative_offset'] if pre['m']<C['m_negative_cut'] else C['m_positive_offset'] if pre['m']>C['m_positive_cut'] else 0.
    r=C['resource_offset'] if pre['r']<C['resource_cut'] else 0.
    base=mul(REGISTRY['personality_map'][pre['personality']],sub(1,mul(C['a_f'],pre['f'])))
    return clip(.15,1.25,add(add(base,m),r))


def raw(game,actions,seat,selection):
    j=seat-1
    if game=='UG':
        o=actions[0]['offer'];accepted=actions[1]['name']=='accept'
        b=sub(1,div(abs(sub(10,mul(2,o))),10))
        fairness=b if accepted else sub(1,b) if selection.endswith('resisted_inequity_v1') else 0. if selection.endswith('zero_exchange_v1') else .5
        relation=1. if accepted else .5 if selection.endswith('neutral_no_exchange_v1') else 0.
        payoff=(10-o if seat==1 else o) if accepted else 0
        safety=sub(1,div(o-2,6)) if seat==1 and accepted else 1. if seat==1 else 1. if accepted else sub(1,div(o,8))
        return [div(payoff,8),fairness,relation,safety]
    tables={'PD':{('C','C'):(3,3),('C','D'):(0,5),('D','C'):(5,0),('D','D'):(1,1)},'BoS':{('O','O'):(3,2),('O','F'):(0,0),('F','O'):(0,0),('F','F'):(2,3)}}
    table=tables[game];names=tuple(a['name'] for a in actions);p=table[names];norm=[div(x,5 if game=='PD' else 3) for x in p]
    own=[x[j] for a,x in table.items() if a[j]==names[j]];others=[x[j] for a,x in table.items() if a[1-j]==names[1-j]]
    relationship=div(sub(p[j],min(own)),sub(max(own),min(own)))
    safety=sub(1,div(sub(max(others),p[j]),2 if game=='PD' else 3))
    return [norm[j],sub(1,abs(sub(norm[0],norm[1]))),relationship,safety]


def update(pre,q,kind,variant,aE,action):
    i=impulse(pre,kind);values=[pre['v'][k] for k in K]
    targets=[x if j==0 or variant!='material_only' else values[j] for j,x in enumerate(q)]
    g=[oracle.graph(v,t) for v,t in zip(values,targets)]
    vnew=[gk['ieee_nodes']['current']['float'] for gk in g];delta=[float(gk['delta']) for gk in g];signed=[float(gk['u']) for gk in g]
    pb=[pre['pbar'][k] for k in K];val=fold(mul(p,u) for p,u in zip(pb,signed));load=fold(mul(p,abs(u)) for p,u in zip(pb,signed))
    rho=clip(-1.5,1.5,mul(mul(REGISTRY['intensity_map'][pre['intensity']],C['kappa']),val))
    sigma=int(aE!=action);cost=mul(sigma,abs(i));applied=0. if variant=='no_suppression' else cost
    mood=add(mul(C['mood_decay'],pre['m']),div(rho,C['mood_scale']))
    fatigue=sub(add(add(add(pre['f'],mul(C['fatigue_load_rate'],load)),div(mul(C['fatigue_impulse_rate'],min(C['impulse_abs_max'],abs(i))),C['impulse_abs_max'])),mul(C['suppression_cost_rate'],applied)),mul(C['recovery_rate'],sub(1,min(1,load))))
    m=0. if variant=='no_mood' else clip(-.5,.5,mood);f=0. if variant=='no_fatigue' else clip(0,1,fatigue)
    post={**pre,'v':dict(zip(K,vnew)),'m':m,'f':f};post.update(derived(vnew,[pre['p'][k] for k in K],m,f))
    weights=[mul(p,abs(u)) for p,u in zip(pb,signed)];attention=None if all(w==0 for w in weights) else K[weights.index(max(weights))]
    return post,{'q_star':dict(zip(K,targets)),'delta':dict(zip(K,delta)),'u_signed':dict(zip(K,signed)),'u':dict(zip(K,map(abs,signed))),'V':val,'L':load,'rho':rho,'sigma':sigma,'Csup_raw':cost,'Csup_applied':applied,'mood_preclip':mood,'fatigue_preclip':fatigue,'k_star':attention}


def episode(config):
    """Three-round golden core, derived without any production policy/update call."""
    import copy
    a=next(x for x in config['agents'] if x['seat']==2);variant=a['variant'];game=config['game']
    pre=copy.deepcopy(a['initial_primary_state']);pre.update(personality=a['personality'],intensity=a['intensity'])
    for field in ('v','d','p'):pre[field]={k:float(x) for k,x in pre[field].items()}
    pre['m']=0. if variant=='no_mood' else float(pre['m']);pre['f']=0. if variant=='no_fatigue' else float(pre['f'])
    pre.update(derived([pre['v'][k] for k in K],[pre['p'][k] for k in K],pre['m'],pre['f']))
    records=[]
    for t in range(1,config['horizon']+1):
        i=impulse(pre,a['kind']);reference=threshold(pre)
        theta=clip(.15,1.25,REGISTRY['personality_map'][a['personality']]) if variant=='fixed_threshold' else reference
        if game=='PD':
            emotional={'name':'C' if i>=C['pd_emotional_cut'] else 'D'}
            rational={'name':'D' if a['kind']=='rational_only' else 'C' if pre['S']>=C['pd_rational_state_cut'] else 'D'}
            other={'name':'D'}
        elif game=='BoS':emotional=rational=other={'name':'O' if t%2 else 'F'}
        else:
            answer=oracle.vote(2,'N',[Q.from_float(pre['v'][k]) for k in K],[Q(pre['p'][k]) for k in K])[4]
            emotional={'name':answer};rational={'name':'accept'};other={'name':'offer','offer':2}
        branch='E' if a['kind']=='emotional_only' else 'R' if a['kind']=='rational_only' else 'E' if abs(i)>theta else 'R'
        actions=[other,emotional if branch=='E' else rational];q=raw(game,actions,2,config['selected_adapter_convention'])
        post,u=update(pre,q,a['kind'],variant,emotional,actions[1])
        records.append({'round':t,'pre':copy.deepcopy(pre),'actions':actions,'decision':{'iota':i,'theta_reference':reference,'theta':theta,'aE':emotional,'aR':rational,'selected_branch':branch},'raw_q':dict(zip(K,q)),'update':u,'post':post})
        pre=post
    return records
