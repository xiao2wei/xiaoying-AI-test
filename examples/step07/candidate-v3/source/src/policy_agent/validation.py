import re
STATUSES={'answered','needs_confirmation','insufficient_evidence','tool_error','limit_reached','model_error','validation_failed'}
def normal(s):return re.sub(r'\s+','',s)
def validate(out,read):
 errors=[]
 if out.get('status') not in STATUSES:errors.append('invalid_status')
 if not isinstance(out.get('claims'),list) or not isinstance(out.get('gaps'),list):return ['invalid_schema']
 if out.get('status')=='answered' and not out['claims']:errors.append('answered_without_claims')
 for i,c in enumerate(out['claims']):
  if not isinstance(c,dict) or not isinstance(c.get('text'),str) or not c['text'].strip() or not isinstance(c.get('citations'),list):errors.append('invalid_claim');continue
  if not c['citations']:errors.append(f'uncited_claim:{i}')
  for ref in c['citations']:
   if not isinstance(ref,dict):errors.append('invalid_citation');continue
   cid=ref.get('chunk_id');quote=ref.get('quote')
   if cid not in read:errors.append('unread_citation:'+str(cid));continue
   if not isinstance(quote,str) or len(normal(quote))<3 or normal(quote) not in normal(read[cid]['text']):errors.append('quote_mismatch:'+str(cid));continue
   ref.update(title=read[cid].get('title'),article=read[cid].get('article'),doc_id=read[cid]['doc_id'],pdf_pages=read[cid]['pdf_pages'],printed_pages=read[cid]['printed_pages'],version_date=read[cid]['version_date'])
  quoted=[normal(q['quote']) for q in c.get('citations',[]) if isinstance(q,dict) and isinstance(q.get('quote'),str)]
  for number in re.findall(r'〔[0-9]{4}〕[0-9]+号',normal(c['text'])):
   if not any(number in q for q in quoted):errors.append('document_number_not_in_cited_quote:'+number)
 if out.get('status')!='answered' and not out['gaps']:errors.append('non_answer_missing_reason')
 return errors
def failure(status,reason):return {'status':status,'claims':[],'gaps':[reason],'answer':reason}
def finish(out):
 out['answer']='\n'.join([c['text'] for c in out['claims']]+out['gaps']);return out
