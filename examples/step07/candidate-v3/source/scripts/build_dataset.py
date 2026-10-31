"""Build evaluation data exclusively from reviewed specifications and corpus."""
import json, re, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,v):
    f=ROOT/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
chunks={c['chunk_id']:c for c in load('data/processed/chunks.json')}
specs=load('evaluation/specifications.json')
all_data={}
for split,rows in specs.items():
    groups=[]
    for i,row in enumerate(rows,1):
        category,family,questions,ids,points,*extra=row
        status=extra[0] if extra else 'answered'
        detail=extra[1] if len(extra)>1 else None
        qs=questions if isinstance(questions,list) else [questions]
        fault=detail if category=='tool_failure' else None
        turns=[]
        for j,q in enumerate(qs):
            key=ids[j] if category=='context' and isinstance(ids,list) else ids
            if isinstance(key,str): units=[[k] for k in key.split(',') if k]
            else: units=key
            # General final provisions provide context, but do not prove an unstated priority relation.
            supporting=[]
            if category=='conflict':
                supporting=[u for u in units if u==['D20-C019']]
                units=[u for u in units if u!=['D20-C019']]
            ps=points[j] if category=='context' else points
            evidence=[{k:chunks[cid][k] for k in ['chunk_id','doc_id','title','article','version_date','pdf_pages','printed_pages','text']} for u in units+supporting for cid in u]
            persistent=fault and fault['mode']=='always'
            turns.append(dict(question=q,history_mode='previous_actual_turns' if category=='context' else 'independent',
                expected_status=status,required_points=[p for p in re.split('[;；]',ps) if p],
                evidence_units=units,evidence=evidence,
                answerable=status=='answered',
                search_evaluable=bool(units) and not(persistent and fault['tool']=='search'),
                read_evaluable=bool(units) and not persistent,
                allowed_actions=['search','read','query_rewrite','ask_confirmation','stop_with_truthful_status'],
                forbidden=['编造资料中的制度事实','引用未读取或不存在的片段','仅凭日期断定优先关系','工具失败却宣称查询成功'],
                criteria=['状态符合预期','必要要点全部满足','所有制度结论有实际读取证据','引用原文与页码一致','未触犯禁止项']))
        audit=[]
        if category=='insufficient':
            audit=[{'scope':'全部29份制度、229页页面清单和562片段','method':'Codex核查目录、关键词及相关制度全文；非人工审核','finding':points}]
        groups.append(dict(id=('DEV' if split=='dev' else 'TEST')+f'{i:02d}',category=category,family=family,
            mode='conversation' if category=='context' else ('variants' if category=='paraphrase' else 'single'),
            turns=turns,fault=fault,conflict_type=detail if category=='conflict' else None,
            absence_or_gap_audit=audit,review={'method':'Codex对照PDF提取原文逐项核对，程序验证证据定位','human_verified':False,'unresolved_label_disputes':[]}))
    save(f'evaluation/{split}.json',groups);all_data[split]=groups
manifest={'version':'dataset-v1.1','source_sha256':load('data/processed/manifest.json').get('sha256'),
 'files':{k:hashlib.sha256((ROOT/f'evaluation/{k}.json').read_bytes()).hexdigest() for k in all_data},
 'counts':{k:len(v) for k,v in all_data.items()},'formal_execution_started':False,
 'stability_ids':['TEST01','TEST02','TEST13','TEST16','TEST17','TEST19','TEST25','TEST31','TEST36','TEST38'],
 'split_rule':'同一事实或近似改写不跨开发/正式集合；同一制度的独立条款允许共享，不能声称跨制度泛化',
 'metrics_rule':'证据单元内多个ID是等价备选；单元之间均需覆盖。持续故障无法读取的题不计M02；无证据题不计M01/M02。名单运行前冻结。'}
save('evaluation/manifest.json',manifest)
save('evaluation/evidence-review.json',{'groups':[{'id':g['id'],'review':g['review'],'evidence_ids':sorted({e['chunk_id'] for t in g['turns'] for e in t['evidence']})} for gs in all_data.values() for g in gs]})
print(json.dumps(manifest,ensure_ascii=False))
