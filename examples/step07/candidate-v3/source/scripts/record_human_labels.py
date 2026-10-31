"""Import an actual person's explicit labels. Never fabricate a reviewer."""
import argparse,json,datetime,math
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--labels',required=True);p.add_argument('--calibration-results',required=True);a=p.parse_args()
labels=json.loads(Path(a.labels).read_text(encoding='utf-8'));data=json.loads((R/'evaluation/calibration.json').read_text(encoding='utf-8'))
if not labels.get('reviewer') or not labels.get('confirmation_source') or not labels.get('confirmed_at'):raise ValueError('必须有真实审核人、确认来源和确认时间')
if set(labels['labels'])!={x['id'] for x in data}:raise ValueError('须明确标注全部校准样本')
if any(type(v) is not bool for v in labels['labels'].values()):raise ValueError('标签必须为true或false')
for x in data:x.update(human_label=labels['labels'][x['id']],human_reviewer=labels['reviewer'],human_confirmed_at=labels['confirmed_at'],confirmation_source=labels['confirmation_source'])
(R/'evaluation/calibration.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
results=Path(a.calibration_results);agreements=0;false_passes=[];errors=[]
for x in data:
 j=json.loads((results/(x['id']+'.json')).read_text(encoding='utf-8'));agreements+=j['pass']==x['human_label']
 if j['pass'] and not x['human_label']:false_passes.append(x['id'])
 if j.get('judge_error'):errors.append(x['id'])
report={'samples':len(data),'human_labels_complete':True,'human_agreement':agreements,'false_pass_ids':false_passes,'judge_errors':errors,'calibration_gate_passed':agreements>=math.ceil(.9*len(data)) and not false_passes and not errors,'confirmation':labels,'note':'保留原始模型评分文件不覆盖；本文件追加人工标签后的复核结果'}
(results/'human-confirmed-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
