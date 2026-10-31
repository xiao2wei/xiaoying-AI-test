"""Pinned peak-price upper estimate using provider-reported cache hits, not a bill."""
PRICE_SOURCE='https://api-docs.deepseek.com/quick_start/pricing/'
PRICE_CHECKED='2026-10-31'
def estimated_peak_usd(entry):
 u=entry.get('usage')
 if not u:return entry.get('estimated_usd_upper_bound',0)
 rates={'deepseek-flash':(.006,.3,1.2),'deepseek-v4-pro':(.044,1.32,3.96)}.get(entry.get('model'))
 if rates is None:return entry.get('estimated_usd_upper_bound',0)
 prompt=max(0,u.get('prompt_tokens',0));hit=max(0,min(prompt,u.get('prompt_cache_hit_tokens',0)))
 return (hit*rates[0]+(prompt-hit)*rates[1]+max(0,u.get('completion_tokens',0))*rates[2])/1e6
