"""Reproducible extraction for the single approved PDF. No model-generated source text."""
from pathlib import Path
import hashlib,json,re,collections
import pdfplumber
from pdfplumber.utils import extract_text
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/source/personnel-policies.pdf'
OUT=ROOT/'data/processed'
STARTS=[1,4,8,13,16,19,23,28,31,34,47,50,56,72,122,149,154,158,163,167,170,173,175,178,184,186,189,206,224]
TITLES=['教师在职攻读博士学位管理办法（修订）','高层次人才引进工作实施办法（2022年版）','高层次人才科研建设专项经费管理办法（试行）','“双师双能型”教师认定办法','思想政治理论课教师和辅导员队伍联动融合发展实施办法（试行）','思想政治理论课教师选聘与退出管理办法（试行）','辅导员队伍建设实施办法（试行）','兼职辅导员队伍建设实施细则（试行）','班主任队伍建设实施细则（试行）','辅导员考核办法','辅导员“双线晋升”实施办法（试行）','特设岗位计划实施办法','岗位设置与聘用管理实施办法（2022年版）','职称和岗位晋升评审工作实施办法（2022年版）','教职工岗位考核实施办法（2022年版）','师德师风考核实施办法（2022年版）','教师师德负面清单及失范行为处理办法（2022年版）','关于加强和改进新时代师德师风建设的实施意见','教职工考勤与请假管理规定','教职工考勤与请假管理补充规定','退休返聘人员管理办法（试行）','高级专家延长退休年龄实施办法（修订）','临时用工管理办法','教职工校内申诉处理暂行办法（修订）','教师服务期及违约补偿暂行规定','管理服务人员工作作风问题处理办法（试行）','研究成果分类分级认定办法（2022年版）','岗位绩效工资发放办法','教职工荣休工作办法']
def dump(name,obj):
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def chars_text(chars):
 return extract_text(chars,x_tolerance=2,y_tolerance=2.5) if chars else ''
def inside(c,b):
 x=(c['x0']+c['x1'])/2;y=(c['top']+c['bottom'])/2
 return b[0]-.2<=x<=b[2]+.2 and b[1]-.2<=y<=b[3]+.2

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 pages=[];tables_all=[];qa=[]
 with pdfplumber.open(SOURCE) as pdf:
  for n,p in enumerate(pdf.pages,1):
   raw=p.extract_text() or ''
   chars=[];seen=set()
   for original in p.chars:
    c=dict(original);m=c.get('matrix')
    if m and abs(m[1])+abs(m[2])<1e-6:
     c['top']=p.height-m[5]-.8*c['size'];c['bottom']=c['top']+c['size'];c['doctop']=p.initial_doctop+c['top']
    key=(c['text'],round(c['x0'],1),round(c['top'],1))
    if key in seen:continue
    seen.add(key);chars.append(c)
   # Header/footer positions are verified for this source; front matter is retained separately.
   body=[c for c in chars if 58<c['top']<p.height-65] if n>=6 else chars
   candidates=[t for t in p.find_tables() if t.bbox[1]>58 and t.bbox[3]<p.height-60] if n>=6 else []
   assigned=set();blocks=[];page_tables=[]
   for ti,t in enumerate(candidates,1):
    rows=[];table_indices={i for i,c in enumerate(body) if inside(c,t.bbox)};cell_indices=set()
    if len(table_indices)<8:continue
    # Ignore a table fully contained in a previously accepted table.
    if table_indices and table_indices<=assigned:continue
    for row in t.rows:
     vals=[]
     for cell in row.cells:
      hits={i for i in table_indices if cell and inside(body[i],cell)};cell_indices.update(hits)
      vals.append(chars_text([body[i] for i in sorted(hits)]).replace('\n','') if cell else None)
     rows.append(vals)
    table={'table_id':f'P{n:03}-T{ti:02}','pdf_page':n,'printed_page':n-5,'bbox':list(t.bbox),'rows':rows,'cell_bboxes':[[list(cell) if cell else None for cell in row.cells] for row in t.rows],'source_char_count':len(table_indices),'unassigned_cell_chars':len(table_indices-cell_indices)}
    page_tables.append(table);tables_all.append(table);assigned.update(table_indices)
    text='\n'.join(' | '.join('' if c is None else c for c in row) for row in rows)
    blocks.append({'top':t.bbox[1],'text':text,'kind':'table','table_id':table['table_id']})
   outside=[c for i,c in enumerate(body) if i not in assigned]
   # Extract outside text in vertical bands around tables, preserving page reading order.
   boundaries=sorted(set([0,p.height]+[v for t in page_tables for v in [t['bbox'][1],t['bbox'][3]]]))
   for lo,hi in zip(boundaries,boundaries[1:]):
    band=[c for c in outside if lo<=(c['top']+c['bottom'])/2<hi]
    if band:blocks.append({'top':min(c['top'] for c in band),'text':chars_text(band),'kind':'text'})
   blocks.sort(key=lambda b:b['top']);text='\n'.join(b['text'] for b in blocks)
   for b in blocks:b['text']=re.sub(r'(?m)^辽宁科技大学制度汇编[^\n]*\n?','',b['text'])
   text='\n'.join(b['text'] for b in blocks)
   status='extracted' if text.strip() else ('cover_image_verified' if n==1 and len(p.images)==1 else 'no_text_layer')
   pages.append({'pdf_page':n,'printed_page':n-5 if n>=6 else None,'status':status,'raw_text':raw,'text':text,'blocks':blocks,'table_ids':[t['table_id'] for t in page_tables],'image_count':len(p.images),'margin_text':chars_text([c for c in chars if c not in body]),'body_chars':len(body),'assigned_chars':len(assigned)+len(outside),'replacement_characters':text.count('\ufffd')})
   qa.append({'pdf_page':n,'char_assignment_ok':len(assigned)+len(outside)==len(body),'text_chars':len(text),'tables':len(page_tables),'isolated_comparison_symbols':bool(re.search(r'(?m)^[≤≥<>＝]+$',text))})
   if n%25==0:print(f'processed {n}/{len(pdf.pages)}',flush=True)
 docs=[];chunks=[]
 for idx,(start,title) in enumerate(zip(STARTS,TITLES)):
  end=STARTS[idx+1]-1 if idx+1<len(STARTS) else 224
  selected=pages[start+4:end+5];did=f'D{idx+1:02}'
  first=selected[0]['text'];match=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',first[:800])
  date=f'{match[1]}-{int(match[2]):02}-{int(match[3]):02}' if match else None
  doc={'doc_id':did,'title':'辽宁科技大学'+title,'version_date':date,'date_source':'first_page_text' if match else 'unknown','pdf_pages':[start+5,end+5],'printed_pages':[start,end],'scope':None,'scope_note':'适用范围需读取正文，未自动推断','chunk_ids':[]}
  current=None;count=0
  def finish():
   nonlocal current,count
   if current and current['text'].strip():
    count+=1;current['chunk_id']=f'{did}-C{count:03}';current['text']=current['text'].strip();current['pdf_pages']=sorted(set(current['pdf_pages']));current['printed_pages']=[p-5 for p in current['pdf_pages']];current['title']=doc['title'];current['version_date']=date;chunks.append(current);doc['chunk_ids'].append(current['chunk_id'])
   current=None
  for page in selected:
   for block in page['blocks']:
    for line in block['text'].splitlines():
     # Articles are retained whole across pages. Long appendices are split by page/length only.
     am=re.match(r'^(第[一二三四五六七八九十百零〇]+条)\s*',line)
     if am or line.startswith('附件') or re.match(r'^附\s*[0-9一二三四五六七八九十]',line):finish()
     if current is None:current={'doc_id':did,'article':am[1] if am else '前言或附件','text':'','pdf_pages':[],'table_ids':[]}
     if not am and len(current['text'])+len(line)>1800:
      label=current['article'];finish();current={'doc_id':did,'article':label,'text':'','pdf_pages':[],'table_ids':[]}
     current['text']+=line+'\n';current['pdf_pages'].append(page['pdf_page'])
     if block['kind']=='table' and block['table_id'] not in current['table_ids']:current['table_ids'].append(block['table_id'])
  finish();docs.append(doc)
 for d in docs:
  dc=[c for c in chunks if c['doc_id']==d['doc_id']]
  for i,c in enumerate(dc):
   c['previous_chunk_id']=dc[i-1]['chunk_id'] if i else None
   c['next_chunk_id']=dc[i+1]['chunk_id'] if i+1<len(dc) else None
   c['related_table_chunks']=[q['chunk_id'] for q in dc if q['chunk_id']!=c['chunk_id'] and set(c['table_ids'])&set(q['table_ids'])]
 manifest={'source':'data/source/personnel-policies.pdf','sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pages':len(pages),'documents':len(docs),'chunks':len(chunks),'tables':len(tables_all),'extraction':'pdfplumber; baseline-normalized glyph coordinates; table cells retained; source-specific header/footer removal','printed_page_offset':5}
 dump('pages.json',pages);dump('documents.json',docs);dump('chunks.json',chunks);dump('tables.json',tables_all);dump('extraction_checks.json',qa);dump('manifest.json',manifest)
 (OUT/'fulltext.md').write_text('\n\n'.join(f"<!-- PDF {p['pdf_page']} / 印刷 {p['printed_page']} -->\n"+p['text'] for p in pages),encoding='utf8')
 print(json.dumps(manifest,ensure_ascii=True),flush=True)
if __name__=='__main__':main()
