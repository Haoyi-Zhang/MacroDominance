"""Fail-closed structural audit of the standalone research artifact."""
from __future__ import annotations
import argparse, ast, csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
from campaign import dominance_cases
from instances import _parse_core_bookshelf, core_public_case

EXPECTED_PUBLIC = {
    'hp': (11, 70, 16, 44),
    'n10': (10, 118, 26, 54),
    'apte': (9, 96, 18, 44),
    'xerox': (10, 182, 47, 182),
}


def read(path):
    return json.loads(path.read_text())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--campaign', default='results/dominance-campaign')
    args=p.parse_args(); campaign=ROOT/args.campaign

    py_files=sorted(ROOT.rglob('*.py'))
    for path in py_files:
        ast.parse(path.read_text(), filename=str(path))

    forbidden=[p for p in ROOT.rglob('*') if p.name=='__pycache__' or p.suffix in ('.pyc','.pyo')]
    assert not forbidden, forbidden

    cases,oracle_names=dominance_cases(ROOT)
    expected={c['name']:(json.dumps(c,sort_keys=True)+'\n').encode() for c in cases}
    actual={p.stem:p.read_bytes() for p in (campaign/'inputs').glob('*.json')}
    assert actual==expected

    summary=read(campaign/'summary.json'); records=read(campaign/'records.json'); oracles=read(campaign/'oracles.json')
    assert summary['cases']==77 and summary['jobs']==308 and summary['oracle_cases']==51
    assert summary['oracle_assignments']==176128 and summary['failure']==0
    assert len(records)==308 and len({(r['case'],r['mode']) for r in records})==308
    assert set(oracles)==oracle_names
    success=[r for r in records if r['status']=='success']; limits=[r for r in records if r['status']=='limit']
    assert len(success)==summary['success'] and len(limits)==summary['limit'] and len(success)+len(limits)==308
    certs={p.name for p in (campaign/'certificates').glob('*.json')}
    expected_certs={r['case']+'_'+r['mode']+'.json' for r in success}
    assert certs==expected_certs

    public={}
    for circuit,expected_counts in EXPECTED_PUBLIC.items():
        blocks,nets,edges=_parse_core_bookshelf(ROOT/'data/upstream/core',circuit)
        observed=(len(blocks),len(nets),len(edges),sum(edges.values()))
        assert observed==expected_counts,(circuit,observed,expected_counts)
        public[circuit]={'blocks':observed[0],'source_nets':observed[1],
                         'distinct_induced_edges':observed[2],
                         'induced_edge_multiplicity':observed[3]}

    ledger=list(csv.DictReader((ROOT/'claim_evidence_ledger.csv').open(newline='')))
    external=list(csv.DictReader((ROOT/'external_resources.csv').open(newline='')))
    references=list(csv.DictReader((ROOT/'reference-audit.csv').open(newline='')))
    reference_verification=list(csv.DictReader((ROOT/'reference-verification.csv').open(newline='')))
    calibration=list(csv.DictReader((ROOT/'literature-calibration.csv').open(newline='')))
    assert len(ledger)==len({r['claim_id'] for r in ledger}) and all(r['claim'] for r in ledger)
    assert len(external)==len({r['name'] for r in external}) and all(r['license'] and r['scholarly_or_official_url'].startswith('http') for r in external)
    assert len(references)==64==len({r['key'] for r in references})
    assert all(r['author'] and r['title'] and r['venue'] and r['year'].isdigit() and r['source'].startswith('http') and r['basis'] and r['claim'] for r in references)
    assert len(reference_verification)==64==len({r['key'] for r in reference_verification})
    assert {r['key'] for r in reference_verification}=={r['key'] for r in references}
    assert all(int(r['citation_count'])>0 and r['manuscript_lines'] and r['metadata_status'] and r['identifier_status'] and r['citation_context_status'] and r['scholarly_source'].startswith('http') and r['supported_clause'] for r in reference_verification)
    dois=[r['doi'].lower() for r in references if r['doi']]
    assert len(dois)==len(set(dois))
    assert len(calibration)==22==len({r['key'] for r in calibration})
    assert {r['key'] for r in calibration}<={r['key'] for r in references}
    groups={g:sum(r['group']==g for r in calibration) for g in {r['group'] for r in calibration}}
    assert groups=={'same-venue':12,'influential':5,'adjacent':5},groups

    milp=read(ROOT/'results/milp-oracle.json')
    assert len(milp['records'])==77
    assert milp['summary']['cases']==milp['summary']['optimal']==77
    assert milp['summary']['zero_gap']==milp['summary']['exact_witness_rechecks']==77
    assert milp['summary']['primal_dual_agreements']==77
    assert milp['summary']['truth_categories']=={'cartesian':51,'closed_form':26}
    assert milp['summary']['cartesian_assignments']==176128
    assert all(record['objective_upper_bound'] < 2**52 for record in milp['records'])
    milp_tests=read(ROOT/'results/milp-oracle-tests.json')
    assert milp_tests['campaign_cases']==77 and milp_tests['campaign_cartesian_checks']==51
    assert milp_tests['campaign_closed_form_checks']==26
    assert milp_tests['differential_fuzz_cases']==40 and milp_tests['differential_fuzz_assignments']==38737
    assert milp_tests['rejected_malformed']==6
    milp_validation=read(ROOT/'results/milp-oracle-validation.json')
    assert milp_validation['validated_cases']==77 and milp_validation['cartesian_assignments']==176128

    control_guard=read(ROOT/'results/control-oracle-guard.json')
    assert control_guard['frozen_controls_matched']==26
    assert control_guard['mutant_assignments_enumerated']==16
    assert control_guard['mutant_zero_witness_value']==46
    assert control_guard['mutant_true_optimum']==43
    assert control_guard['mutant_closed_form_rejected'] is True

    online_peak=read(ROOT/'results/online-frontier-peak.json')
    assert len(online_peak['rows'])==8
    for row in online_peak['rows']:
        k=row['k']; measured=row['measured']
        assert row['prediction_matched'] is True and row['optimum']==11
        assert measured['transitions']==k+5 and measured['final_s_max']==2
        if row['candidate_order']=='forward':
            assert measured['inside_peak']==k and measured['global_peak']==k
            assert measured['comparisons']==k*(k+1)+3
        else:
            assert measured['inside_peak']==1 and measured['global_peak']==2
            assert measured['comparisons']==k+3

    # The exact parser and closed-form path remain standard-library only.
    exact_tree=ast.parse((ROOT/'src/portfolio_exact.py').read_text())
    control_tree=ast.parse((ROOT/'tests/control_oracle.py').read_text())
    def imported_roots(tree):
        roots=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                roots.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                roots.add(node.module.split('.')[0])
        return roots
    assert not ({'numpy','scipy'} & imported_roots(exact_tree))
    assert not ({'numpy','scipy','milp_oracle'} & imported_roots(control_tree))

    actual_gap=read(ROOT/'results/actual-context-gap.json')
    assert actual_gap['cases']==33 and actual_gap['ordered_pairs']==1746
    assert actual_gap['actual_not_relaxed_pairs']==11
    assert actual_gap['actual_dominance_pairs']>=actual_gap['relaxed_dominance_pairs']
    assert actual_gap['mutual_actual_equivalences_not_relaxed']>=1
    order_invariance=read(ROOT/'results/order-invariance.json')
    assert order_invariance['cases']==23 and order_invariance['paired_comparisons']==92
    assert order_invariance['certificates_verified']==184 and order_invariance['invariance_failures']==0

    extension=ROOT/'results/public-portfolio-extension'
    extension_summary=read(extension/'summary.json')
    extension_records=read(extension/'records.json')
    extension_oracles=read(extension/'milp-oracles.json')
    expected_extension={}
    for circuit in EXPECTED_PUBLIC:
        for layout in ('balanced','netaware'):
            case=core_public_case(ROOT/'data/upstream/core',circuit,layout,'orientation4')
            expected_extension[case['name']]=(json.dumps(case,sort_keys=True)+'\n').encode()
    actual_extension={path.stem:path.read_bytes() for path in (extension/'inputs').glob('*.json')}
    assert actual_extension==expected_extension
    assert extension_summary['cases']==8 and extension_summary['jobs']==32
    assert extension_summary['success']==26 and extension_summary['limit']==6 and extension_summary['failure']==0
    assert extension_summary['milp_optimal']==8 and extension_summary['completed_leaf_response_pairs']==8
    assert extension_summary['response_fewer']==8 and extension_summary['ties']==extension_summary['response_greater']==0
    assert len(extension_records)==32 and len(extension_oracles)==8
    extension_success=[row for row in extension_records if row['status']=='success']
    extension_certs={path.name for path in (extension/'certificates').glob('*.json')}
    assert extension_certs=={row['case']+'_'+row['mode']+'.json' for row in extension_success}
    extension_validation=read(ROOT/'results/public-portfolio-extension-validation.json')
    assert extension_validation=={'accepted':26,'completed_leaf_response_pairs':8,
                                  'dominance_obligations':66570,'milp_oracles':8,
                                  'structural_caps':6}
    extension_reproduction_validation=read(ROOT/'results/public-portfolio-extension-reproduction/validation.json')
    extension_reproduction_comparison=read(ROOT/'results/public-portfolio-extension-reproduction/comparison.json')
    assert extension_reproduction_validation==extension_validation
    assert extension_reproduction_comparison=={'compared_jobs':32,'exact_certificates':26,
                                                'exact_inputs':8,'milp_cases':8,
                                                'solver_witness_choice_compared':False,
                                                'timing_compared':False}

    matched=ROOT/'results/public-portfolio-matched-control'
    matched_summary=read(matched/'summary.json')
    matched_records=read(matched/'records.json')
    matched_pairs=read(matched/'matched-pairs.json')
    matched_oracles=read(matched/'milp-oracles.json')
    matched_geometry=read(matched/'geometry-audit.json')
    matched_validation=read(matched/'validation.json')
    expected_matched={}
    for circuit in EXPECTED_PUBLIC:
        for layout in ('balanced','netaware'):
            case=core_public_case(ROOT/'data/upstream/core',circuit,layout,'orientation4_r0180')
            expected_matched[case['name']]=(json.dumps(case,sort_keys=True)+'\n').encode()
    actual_matched={path.stem:path.read_bytes() for path in (matched/'inputs').glob('*.json')}
    assert actual_matched==expected_matched
    assert matched_summary['case_pairs']==8 and matched_summary['subset_policy_jobs']==16
    assert matched_summary['subset_success']==16 and matched_summary['subset_limit']==0 and matched_summary['subset_failure']==0
    assert matched_summary['matched_geometry_verified']==matched_summary['four_le_two_verified']==8
    assert matched_summary['original_four_way_records_unchanged'] is True
    assert len(matched_records)==16 and all(row['status']=='success' for row in matched_records)
    matched_certs={path.name for path in (matched/'certificates').glob('*.json')}
    assert matched_certs=={row['case']+'_'+row['mode']+'.json' for row in matched_records}
    assert len(matched_pairs)==len(matched_oracles)==8
    assert all(row['matched_geometry_verified'] and row['four_le_two'] for row in matched_pairs)
    assert all(row['four_le_two'] and row['four_way']['optimum']<=row['matched_r0180']['optimum'] for row in matched_oracles)
    assert matched_geometry['hp_cmp3']=={'region':'cmp3','two_orientation_rectangular_grid_origin':[0,800],'four_way_square_grid_origin':[0,3404]}
    assert all(row['boxes_macros_pins_equal'] and row['weights_equal'] and row['tree_equal'] and row['candidate_subset_indices']==[0,2] for row in matched_geometry['cases'])
    assert matched_validation=={'accepted_subset_certificates':16,'dominance_obligations':876,'four_le_two_checks':8,'matched_case_pairs':8,'original_four_way_records_unchanged':True,'subset_structural_caps':0}
    matched_reproduction_validation=read(ROOT/'results/public-portfolio-matched-control-reproduction/validation.json')
    matched_reproduction_comparison=read(ROOT/'results/public-portfolio-matched-control-reproduction/comparison.json')
    assert matched_reproduction_validation==matched_validation
    assert matched_reproduction_comparison=={
        'compared_subset_jobs':16,'exact_geometry_audit':True,'exact_matched_pairs':8,
        'exact_subset_certificates':16,'exact_subset_inputs':8,'four_le_two_checks':8,
        'milp_pairs':8,'solver_witness_choice_compared':False,
        'timing_and_rss_compared':False}

    main_reproduction_validation=read(ROOT/'results/dominance-reproduction-validation.json')
    main_reproduction_comparison=read(ROOT/'results/dominance-reproduction-comparison.json')
    assert main_reproduction_validation['accepted']==293 and main_reproduction_validation['structural_caps']==15
    assert main_reproduction_validation['dominance_obligations']==114482
    assert main_reproduction_comparison=={'exact_jobs':308,'exact_inputs':77,
                                          'byte_equal_certificates':293,
                                          'timing_and_rss_compared':False}
    inherited_reproduction_validation=read(ROOT/'results/reproduction-validation.json')
    inherited_reproduction_comparison=read(ROOT/'results/reproduction-comparison.json')
    assert inherited_reproduction_validation['expected_jobs']==87
    assert inherited_reproduction_validation['rechecked_certificates']==63
    assert inherited_reproduction_validation['reproduced_structural_caps']==24
    assert inherited_reproduction_comparison['matched_jobs']==87
    assert inherited_reproduction_comparison['identical_certificates']==63
    null_reproduction_validation=read(ROOT/'results/null-reproduction-validation.json')
    null_reproduction_comparison=read(ROOT/'results/null-reproduction-comparison.json')
    assert null_reproduction_validation['expected_jobs']==29
    assert null_reproduction_validation['rechecked_certificates']==23
    assert null_reproduction_validation['reproduced_structural_caps']==6
    assert null_reproduction_comparison['matched_jobs']==29
    assert null_reproduction_comparison['identical_certificates']==23

    assert (ROOT/'licenses/SciPy-LICENSE').is_file() and (ROOT/'licenses/HiGHS-LICENSE').is_file()

    final_reproduction=read(ROOT/'results/final-clean-reproduction.json')
    assert final_reproduction['core_checks']['status']=='passed'
    assert final_reproduction['main_response_campaign']['records_compared']==308
    assert final_reproduction['inherited_three_method_campaign']['records_compared']==87
    assert final_reproduction['constant_net_control']['records_compared']==29
    assert final_reproduction['milp_cross_check']['cases_compared']==77
    assert final_reproduction['four_orientation_extension']['records_compared']==32
    assert final_reproduction['matched_square_r0180_control']['records_compared']==16
    assert final_reproduction['online_frontier_peak']['measured_rows']==8
    assert final_reproduction['closed_form_guard']['frozen_controls_matched']==26
    assert final_reproduction['closed_form_guard']['mutant_true_optimum']==43
    packaging=final_reproduction['final_packaging']
    assert packaging['status']=='passed'
    assert packaging['complete_project_archive']['root_entries']==[
        'CURRENT-STATE.md','artifact','paper','research-plan.md']
    assert packaging['standalone_repository_archive']['artifact_audit']=='passed'
    assert packaging['clean_project_paper_rebuild']['pages']==12
    assert packaging['clean_project_paper_rebuild']['bibliography_entries']==64
    assert packaging['clean_project_paper_rebuild']['distinct_cited_keys']==64
    assert packaging['clean_project_paper_rebuild']['uncited_entries']==0
    assert packaging['clean_project_paper_rebuild']['unknown_citations']==0
    assert packaging['clean_project_paper_rebuild']['unresolved_references']==0
    assert packaging['clean_project_paper_rebuild']['overfull_boxes']==0
    assert packaging['render_comparison']=={
        'changed_pages':0,'dpi':200,'pages_compared':12,'status':'passed'}
    assert packaging['delivery_hygiene']['forbidden_cache_or_bytecode_files']==0
    assert packaging['delivery_hygiene']['latex_intermediate_files']==0
    assert packaging['delivery_hygiene']['nested_archives']==0
    assert packaging['delivery_hygiene']['invented_repository_links']==0

    result={'python_files_parsed':len(py_files),'campaign_cases':77,'campaign_jobs':308,
            'campaign_success':len(success),'campaign_limits':len(limits),
            'oracle_cases':len(oracles),'oracle_assignments':sum(x['assignments'] for x in oracles.values()),
            'exact_input_bytes_compared':len(actual),'certificate_inventory':len(certs),
            'public_input_inventory':public,'reference_records':len(references),
            'reference_verification_records':len(reference_verification),
            'calibration_groups':groups,'external_resource_records':len(external),
            'claim_ledger_records':len(ledger),'forbidden_cache_files':0,
            'milp_oracle_cases':77,'milp_cartesian_cases':51,'milp_closed_form_cases':26,
            'public_orientation4_cases':8,'public_orientation4_jobs':32,
            'public_orientation4_success':26,'public_orientation4_limits':6,
            'public_matched_r0180_cases':8,'public_matched_r0180_jobs':16,
            'online_frontier_peak_rows':8,'closed_form_controls_guarded':26,
            'milp_differential_fuzz_cases':40,'milp_differential_fuzz_assignments':38737,
            'actual_context_pairs':1746,'actual_context_conservative_misses':11,
            'order_invariance_pairs':92,'order_invariance_certificates':184}
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()
