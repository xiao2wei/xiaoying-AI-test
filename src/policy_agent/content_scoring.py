"""Content-first post-evaluation; preserve legacy judgments and actual model outputs."""
import argparse,json,copy
from pathlib import Path
from .common import ROOT,load,save,sha
CORRECT={'correct','correct_with_citation_note','correct_handling'}

def classify_turn(actual,strict,review=None):
    status=actual['output']['status']
    if strict.get('pass'):
        outcome='correct_handling' if status in {'tool_error','limit_reached'} else 'correct'
        return {'outcome':outcome,'citation_issue':False,'reason':'原严格评审已通过；新口径沿用该判定。' if outcome=='correct' else '按本场景预设要求如实停止；工具导致业务未完成，不是错误制度答案。','method':'inherited_strict_pass','review_evidence':[]}
    if review is None:
        return {'outcome':'unverified','citation_issue':None,'reason':'原严格判定未通过，尚无内容核对记录；不得自动改为正确。','method':'needs_source_review','review_evidence':[]}
    verdict=review.get('verdict')
    if verdict not in {'correct','incorrect','incomplete','unverified'}:raise ValueError('Invalid content verdict')
    if not review.get('reason'):raise ValueError('A documented rationale is required')
    if verdict=='correct' and not review.get('evidence'):raise ValueError('Correct content must have verified PDF support; missing citations alone do not prove correctness')
    if verdict=='incomplete' and status not in {'tool_error','limit_reached','model_error','validation_failed'}:raise ValueError('Do not silently mark an actual substantive answer incomplete')
    outcome='correct_with_citation_note' if verdict=='correct' and review.get('citation_issue') else verdict
    return {'outcome':outcome,'citation_issue':bool(review.get('citation_issue')),'reason':review['reason'],'method':'codex_source_review_under_user_policy','review_evidence':copy.deepcopy(review.get('evidence',[]))}

def group_outcome(turns):
    states={t['outcome'] for t in turns}
    for state in ['incorrect','unverified','incomplete']:
        if state in states:return state
    if not states or not states<=CORRECT:raise ValueError('Invalid or empty result group')
    if 'correct_with_citation_note' in states:return 'correct_with_citation_note'
    if states=={'correct_handling'}:return 'correct_handling'
    return 'correct'

def summarize(groups):
    n=len(groups)
    counts={s:sum(g['outcome']==s for g in groups) for s in ['correct','correct_with_citation_note','correct_handling','incorrect','incomplete','unverified']}
    return {'groups':n,'turns':sum(len(g['turns']) for g in groups),'correct_handling_rate':sum(g['outcome'] in CORRECT for g in groups)/n if n else None,'incorrect_answer_groups':counts['incorrect'],'incomplete_groups':counts['incomplete'],'unverified_groups':counts['unverified'],'outcome_counts':counts,'citation_note_turns':sum(bool(t['citation_issue']) for g in groups for t in g['turns'])}

def evaluate(out):
    out=Path(out)
    if out.exists():raise ValueError('Use a new output directory; preserve prior assessments')
    b=ROOT/'examples/step08/v4';s=b/'human-reviewed-r1'
    policy=load(ROOT/'evaluation/content-policy-v1.json');annotations=load(ROOT/'evaluation/content-review-v1.json');migration=load(ROOT/'evaluation/source-path-migration.json')
    assert sha(ROOT/migration['new_path'])==annotations['source_pdf_sha256']==migration['sha256']
    chunks={c['chunk_id']:c for c in load(ROOT/'data/processed/chunks.json')}
    reviews={r['key']:r for r in annotations['items']}
    if len(reviews)!=len(annotations['items']):raise ValueError('Duplicate review keys')
    source_hashes={};results={};summaries={};used=set()
    for mode in ['agent','baseline','stability']:
        dataset=b/'stability-dataset.json' if mode=='stability' else ROOT/'evaluation/formal.json'
        mode_rows=[];old_passed=0
        for g in load(dataset):
            rp=b/(mode+'-runs')/(g['id']+'.json');sp=s/(mode+'-scores')/(g['id']+'.json');run=load(rp);strict=load(sp)
            source_hashes[rp.relative_to(ROOT).as_posix()]=sha(rp);source_hashes[sp.relative_to(ROOT).as_posix()]=sha(sp)
            old_passed+=strict['pass'];turns=[]
            assert len(g['turns'])==len(run['turns'])==len(strict['turns'])
            for i,(gold,a,old) in enumerate(zip(g['turns'],run['turns'],strict['turns'])):
                key=mode+'/'+g['id']+'/'+str(i+1);review=reviews.get(key)
                if review:
                    used.add(key)
                    if review['run_sha256']!=sha(rp) or review['strict_score_sha256']!=sha(sp):raise ValueError('Review source changed: '+key)
                    for e in review['evidence']:
                        c=chunks[e['chunk_id']]
                        assert e['text']==c['text'] and e['pdf_pages']==c['pdf_pages']
                        assert e['originally_read']==(e['chunk_id'] in a['read_ids'])
                assessed=classify_turn(a,old,review)
                turns.append({'turn':i+1,'key':key,'question':a['question'],'actual_status':a['output']['status'],'legacy_strict_pass':old['pass'],**assessed})
            mode_rows.append({'id':g['id'],'category':g['category'],'legacy_strict_pass':strict['pass'],'outcome':group_outcome(turns),'turns':turns})
        results[mode]=mode_rows;summaries[mode]=summarize(mode_rows)
        summaries[mode]['legacy_strict_pass_rate']=old_passed/len(mode_rows)
        summaries[mode]['category_summary']={c:summarize([r for r in mode_rows if r['category']==c]) for c in sorted({r['category'] for r in mode_rows})}
    if used!=set(reviews):raise ValueError('Unused or mistyped review item')
    for p,h in source_hashes.items():assert sha(ROOT/p)==h
    for mode,rows in results.items():save(out/(mode+'-assessments.json'),rows)
    summary={'policy_version':policy['version'],'scope':'对既有真实运行按用户授权新口径重分类；非模型改进、非新增独立测试','modes':summaries,'new_model_requests':0,'legacy_scores_and_answers_unchanged':True,'source_pdf_sha256':migration['sha256'],'source_hashes':source_hashes,'human_item_labels_added':False}
    save(out/'summary.json',summary);print(json.dumps({'modes':{k:{x:v[x] for x in ['correct_handling_rate','incorrect_answer_groups','incomplete_groups','unverified_groups','citation_note_turns']} for k,v in summaries.items()},'new_model_requests':0},ensure_ascii=False))
    return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();evaluate(a.out)
