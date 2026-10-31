"""Conservative JSON framing recovery; no value repair or action selection."""
import json

def decode_object(text):
 decoder=json.JSONDecoder();text=text.strip();first,pos=decoder.raw_decode(text)
 if not isinstance(first,dict):raise ValueError('JSON应为对象')
 tail=text[pos:].strip();repairs=[]
 while tail:
  if set(tail)<=set('} \t\r\n'):
   repairs.append('redundant_closing_braces');break
  nxt,end=decoder.raw_decode(tail)
  if not isinstance(nxt,dict) or nxt!=first:raise ValueError('多个不同JSON对象，不能猜测当前动作')
  repairs.append('identical_duplicate_object');tail=tail[end:].strip()
 return first,repairs
