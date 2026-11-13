# Sync check for voiced notebook reels: where do caption lines start vs where is the voice speaking?
# usage: python3 sync_check.py VIDEO.mp4 VOICE.m4a
import sys,subprocess,numpy as np,scipy.io.wavfile as wf,tempfile,os
from scipy.signal import fftconvolve
vid,voice=sys.argv[1],sys.argv[2];T=tempfile.mkdtemp()
subprocess.run(['ffmpeg','-v','error','-y','-i',vid,'-ac','1','-ar','16000',T+'/a.wav'],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',voice,'-ac','1','-ar','16000',T+'/v.wav'],check=True)
sr,a=wf.read(T+'/a.wav');a=a.astype(float);_,v=wf.read(T+'/v.wav');v=v.astype(float)
# voice phrases (pauses >= 0.3s)
fr=160;m=len(v)//fr;db=20*np.log10(np.sqrt((v[:m*fr].reshape(m,fr)**2).mean(1))+1e-9)
th=np.percentile(db,95)-28;sp=db>th;segs=[];i=0
while i<m:
    if sp[i]:
        j=i
        while j<m and sp[j]:j+=1
        segs.append([i/100,j/100]);i=j
    else:i+=1
mg=[]
for s in segs:
    if mg and s[0]-mg[-1][1]<0.15: mg[-1][1]=s[1]
    else: mg.append(s)
mg=[s for s in mg if s[1]-s[0]>0.35]
# place each phrase in the reel by its best match; drop phrases that are not in the reel (retakes, count-ins)
placed=[]
a2=np.concatenate([[0],np.cumsum(a*a)])
for s0,s1 in mg:
    c=v[int(s0*sr):int(s1*sr)];c=c-c.mean();L=len(c)
    r=fftconvolve(a,c[::-1],'valid');en=np.sqrt(np.maximum(a2[L:]-a2[:-L],1e-9))[:len(r)]
    q=np.abs(r)/(en*np.sqrt((c*c).sum())+1e-9);k=int(np.argmax(q))
    if q[k]>0.5: placed.append((k/sr,k/sr+L/sr))
placed.sort()
# caption box ink per frame -> line starts are where the ink drops sharply
p=subprocess.run(['ffmpeg','-v','error','-i',vid,'-vf','crop=920:150:80:1440,scale=230:38,format=gray','-f','rawvideo','-'],capture_output=True)
fr_=np.frombuffer(p.stdout,np.uint8).reshape(-1,38,230).astype(float)
ink=(fr_<110).sum((1,2));t=np.arange(len(ink))/30
starts=[0.0]+[t[i] for i in range(1,len(ink)) if ink[i-1]-ink[i]>max(25,0.45*ink[i-1])]
starts=[s for k,s in enumerate(starts) if k==0 or s-starts[k-1]>0.6]
dur=len(a)/sr
print(os.path.basename(vid),f'{dur:.1f}s','voice phrases:',[(round(x,2),round(y,2)) for x,y in placed])
print('  caption line starts:',[round(s,2) for s in starts])
issues=[]
# a phrase that runs well past a caption change = voice ahead/behind captions
for (x,y) in placed:
    for s in starts:
        if x+0.5<s<y-0.5: issues.append(f'voice {x:.1f}-{y:.1f}s keeps talking across a caption change at {s:.1f}s')
# a caption line with no voice under it
for k,s in enumerate(starts):
    e=starts[k+1] if k+1<len(starts) else dur
    if e-s>1.2 and not any(x<e-0.3 and y>s+0.3 for x,y in placed): issues.append(f'caption line {s:.1f}-{e:.1f}s has no voice')
print('  RESULT:', 'OK' if not issues else 'CHECK'); [print('   -',i) for i in issues]
# --- second pass: does each caption line get about the right amount of voice? (OCR the line, count syllables)
import re
def syl(w):
    w=re.sub(r'[^a-z]','',w.lower())
    if not w: return 0
    n=len(re.findall(r'[aeiouy]+',w))
    if w.endswith('e') and not w.endswith(('le','ee')) and n>1: n-=1
    return max(1,n)
def spoken(txt):
    txt=re.sub(r'(\d+)%',lambda m:m.group(1)+' percent',txt)
    out=0
    for tok in txt.split():
        if re.fullmatch(r'[\d,.$]+',tok): out+=max(2,len(re.sub(r'\D','',tok))+1)
        else: out+=syl(tok)
    return out
rows=[]
for k,s in enumerate(starts):
    e=starts[k+1] if k+1<len(starts) else dur
    tt=max(s,e-0.15);subprocess.run(['ffmpeg','-v','error','-y','-ss',str(tt),'-i',vid,'-frames:v','1','-vf','crop=920:150:80:1440,scale=1840:300,format=gray',T+'/c.png'],check=True)
    txt=subprocess.run(['tesseract',T+'/c.png','-','--psm','6'],capture_output=True,text=True).stdout.strip().replace('\n',' ')
    S=spoken(txt);W=sum(max(0,min(y,e)-max(x,s)) for x,y in placed)
    rows.append((s,e,S,W,txt))
    flag=''
    if S>=6 and W<0.4: flag='  <-- no voice under this line'
    elif W>0.4 and S/W>7: flag='  <-- too little voice for this line (line may be missing from recording)'
    elif S>2 and W>1.0 and S/W<1.6: flag='  <-- too much voice for this line (voice may belong to another line)'
    print(f'   line {s:5.1f}-{e:5.1f}s  syl {S:2d}  voice {W:4.1f}s  {txt[:60]}{flag}')
