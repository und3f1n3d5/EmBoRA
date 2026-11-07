"""Independent exact-RN frozen expectations and layered numeric negatives."""
import itertools
import math
import json
from fractions import Fraction as Q
import pytest
from journal_reference_v1.schema import *
from journal_reference_v1.numeric import channel_projection, bits
from journal_reference_v1.evidence import *
from journal_reference_v1.formulas import projection, directional_vote, reaction, focus
from journal_reference_v1.model import candidate_choice, validate_choice


SCALARS = json.loads((C6_CONTRACT/'ORACLE_FIXTURES_C6.json').read_text())
SIGNED = json.loads((C6_CONTRACT/'SIGNED_ZERO_FIXTURES_C6.json').read_text())['fixtures']
VOTES = json.loads((C6_CONTRACT/'F35_FIXTURES_C6.json').read_text())
SELECTIONS = dict(zip('NAB',REGISTRY['enums']['selected_adapter_convention']))


@pytest.mark.parametrize('row',SCALARS,ids=lambda r:r['id'])
def test_AT_URGENCY_all_C6_nodes_bounds_and_origin(row):
    v=row['rounded_inputs']['v']['float'];q=row['rounded_inputs']['q']['float']
    actual=channel_projection(v,q)
    assert actual['identity']==row['nodes']['identity']
    for k,node in actual['nodes'].items(): assert node==row['nodes'][k]
    ideal={'v':row['ideal_inputs']['v'],'q':row['ideal_inputs']['q']} if row['ideal_input_known'] else None
    evidence=channel_evidence(v,q,actual,ideal,row['input_origin'])
    validate_evidence(evidence)
    assert evidence['real_on_rounded_R']['exact_rational']==row['real_on_rounded_inputs']['fraction']
    assert evidence['arithmetic_residual_B_minus_R']['exact_rational']==row['arithmetic_error']['fraction']
    if ideal:
        assert evidence['ideal_I']['exact_rational']==row['scientific_ideal']['fraction']
        assert evidence['independently_derived_bounds']['input']['exact_rational']==row['input_bound']['fraction']
    else:
        assert all(k not in evidence for k in ('ideal_I','input_residual_R_minus_I','total_residual_B_minus_I','original_exact_tokens'))
        assert set(evidence['independently_derived_bounds'])=={'arithmetic'}


@pytest.mark.parametrize('row',SIGNED,ids=lambda r:r['path']+':'+r['label']+':'+r['rounded_inputs']['v']['bits_hex']+':'+r['rounded_inputs']['q']['bits_hex'])
def test_AT_URGENCY_signed_zero_nodes(row):
    actual=channel_projection(row['rounded_inputs']['v']['float'],row['rounded_inputs']['q']['float'])
    assert actual['identity']==row['nodes']['identity']
    for k,node in actual['nodes'].items():assert node==row['nodes'][k]
    for k,expected in row['expected_bits'].items():assert actual['nodes'][k]['bits_hex']==expected


@pytest.mark.parametrize('row',VOTES)
def test_AT_UG_CHOICE_all_840_frozen_integrated_projections(row):
    from journal_reference_v1.games import Adapter
    state=State((float.fromhex(row['v_hex']),)*4,(1.,)*4,tuple(row['p']),0.,0.,'neutral','neutral')
    before=state.to_dict()
    choice=candidate_choice(state,row['offer'],Adapter(SELECTIONS[row['adapter']],'sensitivity'))
    assert state.to_dict()==before
    assert tuple(choice['z'][k] for k in K)==tuple(row['z'])
    for actual_key,expected_key in [('N_VS','N'),('P_VS','P'),('D_VS','D')]:assert choice[actual_key]==row[expected_key]['float']
    assert choice['action']=={'name':row['action']}
    assert choice['category']==('positive_accept' if row['category']=='positive' else 'tie_reject')
    for action in ('accept','reject'):
        for k in K:
            expected=row['candidate_appraisal_diagnostics'][action][k]
            ev=choice['candidates'][action]['numeric_evidence'][k]
            assert ev['executable_B']==expected['executable_B']
            assert ev['arithmetic_residual_B_minus_R']['exact_rational']==expected['arithmetic_error']['fraction']


@pytest.mark.parametrize('values',[(0.,.013,1.,.9999995),(math.nextafter(0.,1.),math.nextafter(1.,0.),.5,.0000005),(.17,.83,.001,.92)])
@pytest.mark.parametrize('selection',list(SELECTIONS.values()))
def test_AT_UG_POLICY_heterogeneous_states_all_offers_profiles(values,selection):
    from journal_reference_v1.games import Adapter
    for offer in range(2,9):
        for p in REGISTRY['priority_profiles'].values():
            state=State(values,(1.,)*4,tuple(p),-.5,.9,'pessimistic','high')
            choice=candidate_choice(state,offer,Adapter(selection,'sensitivity'))
            adapter=next(k for k,v in SELECTIONS.items() if v==selection)
            z,n,den,d,action,cat=oracle.vote(offer,adapter,list(map(Q.from_float,values)),list(map(Q,p)))
            assert tuple(choice['z'][k] for k in K)==tuple(z)
            assert (choice['N_VS'],choice['P_VS'],choice['D_VS'],choice['action']['name'])==(float(n),float(den),float(d),action)


def test_AT_UG_CHOICE_24_map_permutations_and_neighbors():
    from journal_reference_v1.games import Adapter
    state=State((.013,)*4,(1.,)*4,(.5,1.5,.5,.5),0.,0.,'neutral','neutral')
    adapter=Adapter(SELECTIONS['N'],'structural_fixture'); expected=candidate_choice(state,8,adapter)
    for permutation in itertools.permutations(K):
        data=state.to_dict()
        for field in ('v','d','p','pbar'): data[field]={k:data[field][k] for k in permutation}
        assert candidate_choice(State.from_dict(data),8,adapter)==expected
    for p,n in [((.5,math.nextafter(1.5,-math.inf),.5,.5),2**-52),((math.nextafter(.5,math.inf),1.5,.5,.5),2**-53)]:
        s=State(state.v,state.d,p,0.,0.,'neutral','neutral'); choice=candidate_choice(s,8,adapter)
        assert choice['N_VS']==n and choice['action']=={'name':'accept'}
    assert directional_vote((.5,1.5,.5,.5),(1,-1,1,1))['N_VS']==0.
    bad=copy.deepcopy(expected);bad['D_VS']=1.
    with pytest.raises(TraceError):validate_choice(bad,state,8,adapter)


def test_AT_URGENCY_runtime_and_accumulator_qualification():
    check_fp_controls()
    assert oracle.rn(Q(1)+Q(2)**-53)==1
    assert oracle.rn(Q(1)+3*Q(2)**-53)==1+Q(2)**-51
    assert bits(float(oracle.rn(Q(2)**-1075)))==bits(0.)
    assert bits(float(oracle.rn(3*Q(2)**-1075)))==bits(math.ldexp(1.,-1073))
    for terms in itertools.permutations((.5,-1.5,.5,.5)):
        assert Q.from_float(math.fsum(terms))==oracle.rn(sum(map(Q.from_float,terms),Q(0)))==0
    assert reaction(1.,2.)==1.5 and reaction(-1.,2.)==-1.5  # wider-helper only


def test_AT_INVALID_evidence_nonfinite_lineage_bounds_and_tampering(monkeypatch):
    output=channel_projection(.5,1.)
    evidence=channel_evidence(.5,1.,output)
    for key,value in [('extra',1),('implementation_discrepancy_O_minus_B',1e-13),('input_origin','unknown')]:
        bad=copy.deepcopy(evidence);bad[key]=value
        with pytest.raises(TraceError):validate_evidence(bad)
    for value in (float('nan'),float('inf'),True,'0.5'):
        with pytest.raises(ContractError):channel_projection(value,1.)
    with pytest.raises(TraceError):channel_evidence(.5,1.,output,{'v':'0.4','q':'1'},'exact_decimal_or_rational_known')
    for value in (float('nan'),float('inf')):
        with pytest.raises(ContractError):compare_continuous(value,.5)
    import journal_reference_v1.evidence as ev
    monkeypatch.setattr(ev,'ARITHMETIC_BOUND',Q(0))
    with pytest.raises(TraceError):channel_evidence(.9999995,1.,channel_projection(.9999995,1.))


def test_AT_UG_CHOICE_uniform_gap_proof_pairs_and_642_static_checks():
    proof=json.loads((C6_CONTRACT/'GAP_SEPARATION_DERIVATION_C6.json').read_text())
    assert len(proof['pairs'])==84 and len(proof['static_boundary_identity_epsilon_checks'])==642
    minima={}
    for row in proof['pairs']:
        qa,qb=oracle.ug(row['offer'],'accept',row['adapter'])[K.index(row['channel'])],oracle.ug(row['offer'],'reject',row['adapter'])[K.index(row['channel'])]
        assert str(qa)==row['accept'] and str(qb)==row['reject']
        gap=abs(qa-qb);assert gap>0 and str(gap)==row['absolute_gap']
        minima[row['adapter']]=min(minima.get(row['adapter'],gap),gap)
    assert minima=={'N':Q(1,5),'A':Q(1,4),'B':Q(1,10)}
    eta=Q(2)**-52
    perturbation=8*eta/oracle.EB+4*oracle.AB*eta/oracle.EB
    for adapter,gap in minima.items():
        margin=oracle.AB*gap-2*perturbation
        assert margin>0 and str(margin)==proof['uniform_margins'][adapter]['fraction']
    for row in proof['static_boundary_identity_epsilon_checks']:
        qa=oracle.ug(row['offer'],'accept',row['adapter'])[K.index(row['channel'])]
        qr=oracle.ug(row['offer'],'reject',row['adapter'])[K.index(row['channel'])]
        v=Q(row['v']);difference=oracle.real(v,qa,oracle.AB,oracle.EB)[2]-oracle.real(v,qr,oracle.AB,oracle.EB)[2]
        assert str(difference)==row['signed_appraisal_gap']
        assert abs(difference)>=oracle.AB*abs(qa-qr)


def test_AT_URGENCY_known_negative_zero_token_lineage():
    output=channel_projection(-0.,0.)
    evidence=channel_evidence(-0.,0.,output,{'v':'-0.0','q':'0.0'},'exact_decimal_or_rational_known')
    validate_evidence(evidence)
    assert evidence['nodes']['current']['bits_hex']=='8000000000000000'
