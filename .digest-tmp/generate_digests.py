import json, re, math, os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(os.environ.get('REPO_ROOT','.')).resolve()
OUT=Path(os.environ.get('OUT_DIR',str(ROOT/'data/digests')))
OUT.mkdir(parents=True,exist_ok=True)
profiles=json.load(open(os.environ['PROFILES_PATH']))
manifest={int(x['episode']):x for x in json.load(open(ROOT/'data/manifest.json'))}
guids={1:"https://lexfridman.com/?p=3661",2:"https://lexfridman.com/?p=3701",3:"https://lexfridman.com/?p=3763",4:"https://lexfridman.com/?p=3767",5:"https://lexfridman.com/?p=3771",6:"https://lexfridman.com/?p=3776",7:"https://lexfridman.com/?p=3781",8:"https://lexfridman.com/?p=3785",9:"https://lexfridman.com/?p=3789",10:"https://lexfridman.com/?p=3800",11:"https://lexfridman.com/?p=3804",12:"https://lexfridman.com/?p=3808",13:"https://lexfridman.com/?p=3815",14:"https://lexfridman.com/?p=3819",15:"https://lexfridman.com/?p=3828",16:"https://lexfridman.com/?p=3831",17:"https://lexfridman.com/?p=3841",18:"https://lexfridman.com/?p=3846",19:"https://lexfridman.com/?p=3851",20:"https://lexfridman.com/?p=3855",21:"https://lexfridman.com/?p=3872",22:"https://lexfridman.com/?p=3879",23:"https://lexfridman.com/?p=3904",24:"https://lexfridman.com/?p=3908",25:"https://lexfridman.com/?p=3920",26:"https://lexfridman.com/?p=3932",27:"https://lexfridman.com/?p=3936",28:"https://lexfridman.com/?p=3939",29:"https://lexfridman.com/?p=3942",30:"https://lexfridman.com/?p=3946",31:"https://lexfridman.com/?p=3949",32:"https://lexfridman.com/?p=3963",33:"https://lexfridman.com/?p=3966",34:"https://lexfridman.com/?p=3970",35:"https://lexfridman.com/?p=3974",36:"https://lexfridman.com/?p=3981",37:"https://lexfridman.com/?p=3985",38:"https://lexfridman.com/?p=3989",39:"https://lexfridman.com/?p=3993",40:"https://lexfridman.com/?p=3996",41:"https://lexfridman.com/?p=3999",42:"https://lexfridman.com/?p=4006",43:"https://lexfridman.com/?p=4009",44:"https://lexfridman.com/?p=4013",45:"https://lexfridman.com/?p=4026",46:"https://lexfridman.com/?p=4029",47:"https://lexfridman.com/?p=4033",48:"https://lexfridman.com/?p=4036",49:"https://lexfridman.com/?p=4043",50:"https://lexfridman.com/?p=4046",51:"https://lexfridman.com/?p=4051",52:"https://lexfridman.com/?p=4054",53:"https://lexfridman.com/?p=4057",54:"https://lexfridman.com/?p=4066",55:"https://lexfridman.com/?p=4069",56:"https://lexfridman.com/?p=4073",57:"https://lexfridman.com/?p=4076",58:"https://lexfridman.com/?p=4079",59:"https://lexfridman.com/?p=4083",60:"https://lexfridman.com/?p=4086",61:"https://lexfridman.com/?p=4091",62:"https://lexfridman.com/?p=4095",63:"https://lexfridman.com/?p=4099",64:"https://lexfridman.com/?p=4112",65:"https://lexfridman.com/?p=4115",66:"https://lexfridman.com/?p=4119",67:"https://lexfridman.com/?p=4122",68:"https://lexfridman.com/?p=4126",69:"https://lexfridman.com/?p=4129",70:"https://lexfridman.com/?p=4133",71:"https://lexfridman.com/?p=4137",72:"https://lexfridman.com/?p=4141",73:"https://lexfridman.com/?p=4145",74:"https://lexfridman.com/?p=4149",75:"https://lexfridman.com/?p=4152",76:"https://lexfridman.com/?p=4155",77:"https://lexfridman.com/?p=4159",78:"https://lexfridman.com/?p=4162",79:"https://lexfridman.com/?p=4166",80:"https://lexfridman.com/?p=4170",81:"https://lexfridman.com/?p=4176",82:"https://lexfridman.com/?p=4182",83:"https://lexfridman.com/?p=4190",84:"https://lexfridman.com/?p=4193",85:"https://lexfridman.com/?p=4196",86:"https://lexfridman.com/?p=4200",87:"https://lexfridman.com/?p=4203",88:"https://lexfridman.com/?p=4207",89:"https://lexfridman.com/?p=4210",90:"https://lexfridman.com/?p=4214",91:"https://lexfridman.com/?p=4223",92:"https://lexfridman.com/?p=4226",93:"https://lexfridman.com/?p=4230",94:"https://lexfridman.com/?p=4233",95:"https://lexfridman.com/?p=4237",96:"https://lexfridman.com/?p=4240",97:"https://lexfridman.com/?p=4244",98:"https://lexfridman.com/?p=4247",99:"https://lexfridman.com/?p=4251"}

STOP=set('''the a an and or but if then than of to in on at for from with by as is are was were be been being it its this that these those i you he she we they them their our your my me us do does did have has had can could would should may might will just so very really about into out up down over under more most less much many some any all one two three what when where why how who which there here because while also only not no yes like think know kind sort way thing things something anything people time make made making get got getting going go come comes came use uses using used work works working want wants wanted see look looking good right well actually basically probably maybe perhaps quite bit lot lots first second new old other another each both between through during before after even ever never always often sometimes still already such same different own itself ourselves himself herself yourself themselves very really just now today tomorrow yesterday'''.split())
BANNED_AD=[
 'cash app','masterclass','ziprecruiter','expressvpn','sponsor','sponsored','use code','promo code','download the app','patreon','subscribe','youtube channel','support this podcast','following is a conversation','this podcast','lex fridman podcast','please consider supporting','google play','app store','audible','athletic greens','blinkist','simpli safe','simplesafe','brilliant.org','skillshare','ridge wallet','cashapp'
]
HOST_PREFIXES=('let me ask','can you','could you','what do you','what is your','how do you','do you think','would you','so can you','tell me','you\'ve','you have')
GENERIC=set('ai artificial intelligence machine machines system systems future human humans research learning learn learned model models problem problems important world question questions conversation episode'.split())

def words(s):
    return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", s)]

def profile_terms(p):
    txt=' '.join([p['one_liner']]+p['summary']+[x['title']+' '+x['text'] for x in p['takeaways']]+p['topics'])
    freq={}
    for w in words(txt):
        if w not in STOP and w not in GENERIC:
            freq[w]=freq.get(w,0)+1
    for t in p['topics']:
        for w in words(t):
            if w not in STOP and w not in GENERIC:
                freq[w]=freq.get(w,0)+4
    return freq

def parse_transcript(path):
    text=path.read_text(errors='replace')
    fm={}
    m=re.match(r'^---\n(.*?)\n---\n',text,re.S)
    if m:
        for line in m.group(1).splitlines():
            if ': ' in line:
                k,v=line.split(': ',1)
                v=v.strip()
                if len(v)>=2 and v[0]==v[-1]=='"':
                    try: v=json.loads(v)
                    except: v=v[1:-1]
                fm[k]=v
        body=text[m.end():]
    else: body=text
    matches=list(re.finditer(r'\*\*\[(\d{2}:\d{2}:\d{2})\]\*\*\s*',body))
    blocks=[]
    for i,m0 in enumerate(matches):
        t=m0.group(1)
        start=m0.end(); end=matches[i+1].start() if i+1<len(matches) else len(body)
        chunk=body[start:end].strip()
        blocks.append((t,chunk))
    return fm, body, blocks

def sentence_candidates(blocks, p):
    weights=profile_terms(p)
    cands=[]
    for bi,(t,chunk) in enumerate(blocks):
        spans=list(re.finditer(r'(?s)(?:^|(?<=[.!?])\s+)([^\n].*?[.!?])(?=\s+|$)',chunk))
        if not spans and chunk:
            spans=[]
        for sm in spans:
            s=sm.group(1).strip()
            low=s.lower()
            ws=words(s); n=len(ws)
            if n<12 or n>58: continue
            if s.endswith('?'): continue
            if bi <= max(0, int(len(blocks)*0.025)): continue
            if any(x in low for x in BANNED_AD): continue
            if low.startswith(HOST_PREFIXES): continue
            if low.startswith(("as part of ", "he is ", "she is ", "he was ", "she was ", "he's ", "she's ", "so in your ", "but so from ", "and so the real question", "so the real question", "so that's probably at the core")): continue
            if sum(1 for w in ws if w in {"you","your","youre","you're","youve","you've"}) >= 3: continue
            grams=[' '.join(ws[i:i+4]) for i in range(max(0,len(ws)-3))]
            if len(grams) != len(set(grams)): continue
            if re.search(r'\b(thanks?|welcome) (for|to)\b',low): continue
            if len(set(ws))/max(1,len(ws)) < .52: continue
            if low.count(' i ') + low.startswith('i ') > 7: continue
            overlap=sum(weights.get(w,0) for w in set(ws))
            specificity=sum(1 for w in ws if len(w)>=7 and w not in STOP)
            score=overlap*4 + specificity*.35
            if 17<=n<=38: score+=5
            elif 13<=n<=48: score+=2
            if any(ch.isdigit() for ch in s): score+=1.5
            if s.startswith(('I think','I believe','The ','If ','When ','We ','There ','You ')): score+=1
            if score < 22: continue
            cands.append({'bi':bi,'time':t,'text':s,'score':score})
    return cands

def jaccard(a,b):
    A=set(words(a)); B=set(words(b));
    return len(A&B)/max(1,len(A|B))

def select_highlights(blocks,p,k=4):
    cands=sentence_candidates(blocks,p)
    if not cands:
        raise RuntimeError('no candidates')
    ranked=sorted(cands,key=lambda c:c['score'],reverse=True)
    selected=[]
    minsep=max(1,len(blocks)//10)
    for sep in [minsep,max(1,minsep//2),0]:
        for c in ranked:
            if len(selected)>=k: break
            if c in selected: continue
            if any(jaccard(c['text'],x['text'])>=.52 for x in selected): continue
            if sep and any(abs(c['bi']-x['bi'])<sep for x in selected): continue
            selected.append(c)
        if len(selected)>=k: break
    return sorted(selected[:k],key=lambda c:c['bi'])

def assign_contexts(hls,p):
    takeaways=p['takeaways']
    for h in hls:
        qw=set(words(h['text']))
        best=(-1,0)
        for i,t in enumerate(takeaways):
            tw=set(words(t['title']+' '+t['text']))
            overlap=len((qw & tw) - STOP - GENERIC)
            if overlap>best[0]: best=(overlap,i)
        h['context']=takeaways[best[1]]['title'].strip().rstrip('.')
    return hls

def jsonv(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))

records=[]
for ep in range(1,100):
    m=manifest[ep]; p=profiles[str(ep)]
    tp=ROOT/'data/transcripts'/m['file']
    fm, raw, blocks=parse_transcript(tp)
    hls=assign_contexts(select_highlights(blocks,p,4),p)
    slug=m['file'][4:-3]
    yid=parse_qs(urlparse(m.get('youtube_url','')).query).get('v',[''])[0]
    title=fm.get('title') or f"#{ep} – {m['title']}"
    guest=fm.get('guest') or m['guest']
    published=m.get('published','')
    if ep==84: published='2020-03-29'
    if ep==98: published='2020-05-23'
    guid=guids.get(ep,'__MISSING_GUID__')
    lines=['---',
      f'guid: {jsonv(guid)}',
      f'slug: {jsonv(slug)}',
      f'episode: {ep}',
      f'title: {jsonv(title)}',
      f'guest: {jsonv(guest)}',
      f'link: {jsonv(m.get("episode_url", ""))}',
      f'youtube_id: {jsonv(yid)}',
      f'published: {jsonv(published)}',
      f'summary_source: {jsonv("transcript")}',
      f'summarized_at: {jsonv("2026-08-19T20:55:00.000Z")}',
      f'topics: {jsonv(p["topics"])}','---','',
      '# One-liner','',p['one_liner'].strip(),'','# Summary','']
    for para in p['summary']:
        lines += [para.strip(),'']
    lines += ['# Takeaways','']
    for t in p['takeaways']:
        lines += [f"## {t['title'].strip()}",'',t['text'].strip(),'']
    lines += ['# Highlights','']
    for h in hls:
        lines += [f"## Conversation @ ({h['time']})",'']
        for qline in h['text'].splitlines(): lines.append('> '+qline)
        lines += ['', f"Context: {h['context']}", '']
    lines += ['# Chapters','', '- [00:00:00] Full conversation','']
    out='\n'.join(lines)
    (OUT/m['file']).write_text(out)
    records.append({'episode':ep,'file':m['file'],'highlights':hls,'guid':guid})
print('generated',len(records),'missing GUIDs',[r['episode'] for r in records if r['guid']=='__MISSING_GUID__'])
