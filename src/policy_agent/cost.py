"""Pinned peak-price upper estimate using provider-reported cache hits, not a bill."""
import datetime
PRICE_SOURCE='https://api-docs.deepseek.com/quick_start/pricing/'
PRICE_CHECKED='2026-10-31'
def estimated_peak_usd(entry):
 u=entry.get('usage')
 if not u:return entry.get('estimated_usd_upper_bound',0)
 rates={'deepseek-flash':(.006,.3,1.2),'deepseek-v4-pro':(.044,1.32,3.96)}.get(entry.get('model'))
 if rates is None:return entry.get('estimated_usd_upper_bound',0)
 prompt=max(0,u.get('prompt_tokens',0));hit=max(0,min(prompt,u.get('prompt_cache_hit_tokens',0)))
 factor=1.0
 try:
  stamp=datetime.datetime.fromisoformat(entry['time'].replace('Z','+00:00')).astimezone(datetime.timezone.utc)
  # Weekday public holidays are conservatively charged as ordinary weekdays.
  if stamp.weekday()>=5 or not (1<=stamp.hour<4 or 6<=stamp.hour<10):factor=.5
 except (KeyError,ValueError,TypeError):pass
 return factor*(hit*rates[0]+(prompt-hit)*rates[1]+max(0,u.get('completion_tokens',0))*rates[2])/1e6
