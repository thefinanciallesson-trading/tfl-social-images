import json,re
P=json.load(open('all.json'))
ch={'6ac6ee1c6a5c39ccb649e2c9':'TT','6ac6edb96a5c39ccb649de82':'IGm','6adff4b52f1f5ed648e2c005':'IGt'}
CTA=re.compile(r'^(Follow|Want to learn|Tap the link|Comment|Save this|Full lessons|Free guide)',re.I)
DIS=re.compile(r'^(Educational content only|Educational only|Education only|Not financial advice|Trading involves|Futures trading involves|Numbers shown|Simulated results)',re.I)
def sents(t):
    parts=re.split(r'(?<=[.!?])\s+(?=[A-Z$0-9"\(])',t.strip())
    return [p.strip() for p in parts if p.strip()]
def fix(text, trading):
    paras=[p for p in text.split('\n\n')]
    tags=[]
    while paras and paras[-1].strip().startswith('#'): tags.insert(0,paras.pop().strip())
    topics=[]
    if paras and (paras[-1].startswith('Topics:') or (paras[-1].count(',')>=3 and '.' not in paras[-1])):
        topics=[paras.pop().strip()]
    flat=' '.join(p.replace('\n',' ') for p in paras)
    ss=sents(flat)
    body=[];cta=[];dis=[]
    for s in ss:
        if DIS.match(s): dis.append(s)
        elif CTA.match(s): cta.append(s)
        else: body.append(s)
    # normalize disclaimer
    d=' '.join(dis)
    if trading: d='Educational content only. Not financial advice. Trading involves risk of loss.'
    elif 'Numbers shown are an example' in d: d='Educational content only. Not financial advice. Numbers shown are an example.'
    else: d='Educational content only. Not financial advice.'
    out=[]
    if body:
        h=1
        if len(body)>1:
            b0,b1=body[0],body[1]
            if b0.endswith('.') and b1.endswith('?') and len(b1)<60: h=2
            elif b1.startswith('True or false'): h=2
            elif len(b0)<25 and len(b1)<70: h=2
            elif len(b1)<=40 and b1[0] not in '$0123456789' and not b1.startswith('Say'): h=2
        out.append(' '.join(body[:h]))
        if len(body)>h: out.append(' '.join(body[h:]))
    merged=[]
    for c in cta:
        if merged and merged[-1].endswith('?') and c.startswith('Tap the link'): merged[-1]+=' '+c
        else: merged.append(c)
    order=lambda c: 0 if re.match(r'^(Save this|Comment)',c) else 1 if c.startswith(('Want to learn','Tap the link')) else 2 if c.startswith('Follow') else 3
    merged.sort(key=order)
    if merged: out.append('\n'.join(merged))
    out.append(d)
    out+=topics+tags
    return '\n\n'.join(out)
res=[]
for p in P:
    c=ch[p['channelId']]
    if c!='TT': 
        # flag IG captions where Follow is mid-line
        if re.search(r'[^\n]Follow @',p['text']) or re.search(r'\. (Want to learn|Comment|Save this)',p['text']): print('IG check', p['id'])
        continue
    src=p['assets'][0]['source'] if p['assets'] else ''
    trading='/tfl/' in src
    new=fix(p['text'],trading)
    if new!=p['text']: res.append(dict(id=p['id'],due=p['dueAt'],old=p['text'],new=new,src=src.split('/main/')[1]))
json.dump(res,open('respace.json','w'),indent=1)
print(len(res),'TT changes')
import random
for r in [res[0],res[5],res[30],res[60],res[90]]+[x for x in res if 'pf_reels' in x['src']][:1]+[x for x in res if 'explainers_vo' in x['src']][:1]:
    print('=====',r['src']); print(r['new'])
