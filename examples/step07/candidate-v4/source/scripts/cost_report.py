"""Report recorded usage without any API request; estimates are not provider invoices."""
import argparse,json,collections
from policy_agent.common import ROOT,save,now
from policy_agent.cost import estimated_peak_usd,PRICE_SOURCE,PRICE_CHECKED
p=argparse.ArgumentParser();p.add_argument('--out',default='examples/cost-report.json');p.add_argument('--start-record',type=int,default=0);a=p.parse_args()
rows=[];invalid=[]
for i,line in enumerate((ROOT/'examples/model-usage.jsonl').read_text(encoding='utf-8').splitlines()):
 if i<a.start_record:continue
 try:rows.append(json.loads(line))
 except ValueError:invalid.append(i+1)
by_model={}
for model in sorted({x.get('model','unknown') for x in rows}):
 part=[x for x in rows if x.get('model','unknown')==model];by_model[model]={'recorded_attempts':len(part),'prompt_tokens':sum(x.get('usage',{}).get('prompt_tokens',0) for x in part),'completion_tokens':sum(x.get('usage',{}).get('completion_tokens',0) for x in part),'cache_hit_tokens':sum(x.get('usage',{}).get('prompt_cache_hit_tokens',0) for x in part),'estimated_usd_upper_bound':sum(map(estimated_peak_usd,part))}
r={'created_at':now(),'start_record_zero_based':a.start_record,'recorded_requests':len(rows),'requests_with_usage':sum(bool(x.get('usage')) for x in rows),'total_tokens':sum(x.get('usage',{}).get('total_tokens',0) for x in rows),'estimated_usd_upper_bound':sum(map(estimated_peak_usd,rows)),'by_model':by_model,'invalid_ledger_lines':invalid,'price_source':PRICE_SOURCE,'price_checked':PRICE_CHECKED,'not_provider_invoice':True,'limitations':['仅统计收到并写入账本的响应；终止时在途请求可能无法记录，不能据此推断免费。','旧报价字段保留，当前估算使用已核对价格、服务报告缓存及已知非高峰时段；未判断工作日节假日优惠，保持保守。','用户提供13元/628次/2527984tokens的账期未知，不与本账本简单相加或等同。']}
save(ROOT/a.out,r);print(json.dumps(r,ensure_ascii=False))
