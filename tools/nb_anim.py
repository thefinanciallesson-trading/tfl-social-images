# Animate a static notebook post: rebuild the blank grid paper, split the ink into vertical groups,
# then slide each group in one after another on a 1080x1920 reel canvas.
import sys,os,subprocess,numpy as np
from PIL import Image,ImageFilter,ImageDraw
from scipy import ndimage
src,out=sys.argv[1],sys.argv[2]; FPS=30
im=np.asarray(Image.open(src).convert('RGB')).astype(np.float32); H,W,_=im.shape
g=im.mean(2)
# grid period from autocorrelation of column/row darkness on a light area
def period(sig):
    s=sig-sig.mean(); ac=np.correlate(s,s,'full')[len(s)-1:]; ac[:20]=-1e9
    return int(np.argmax(ac[:120]))
def period2(prof):
    d=np.where(prof<prof.max()-12)[0]
    starts=d[np.r_[True,np.diff(d)>2]]
    return int(np.median(np.diff(starts)))
px=period2(np.median(g[:,120:],axis=0)); py=period2(np.median(g,axis=1)); px=py
# blank tile = per-phase median over the whole image (ink is a minority)
LEFT=118
tile=np.zeros((py,px,3),np.float32)
for yy in range(py):
    rows=im[yy::py]
    for xx in range(px):
        tile[yy,xx]=np.median(rows[:, xx+((LEFT//px)+1)*px::px].reshape(-1,3),axis=0)
blank=np.tile(tile,(H//py+2,W//px+2,1))[:H,:W].copy()
blank[:,:LEFT]=np.median(im[:,:LEFT],axis=0)[None]  # margin column (red line)
blank[:,:LEFT]=im[:,:LEFT]                             # keep holes + margin exactly
diff=np.abs(im-blank).max(2); ink=diff>16
ink[:,:LEFT]=False
ink=ndimage.binary_opening(ink,iterations=1)
ink=ndimage.binary_closing(ink,iterations=2)
ink=ndimage.binary_fill_holes(ink)
lab,n=ndimage.label(ndimage.binary_dilation(ink,iterations=7))
comps=[]
for k,sl in enumerate(ndimage.find_objects(lab),1):
    m=(lab==k)&ink
    if m.sum()<150: continue
    if sl[0].stop-sl[0].start>420:
        # very tall group (title touching a card): cut it once, at its widest empty row gap
        def cut(mm):
            rows=mm.any(1);ys=np.where(rows)[0];y0,y1=ys[0],ys[-1]
            if y1-y0<=420: return [mm]
            best=(0,None);g=0
            for y in range(y0,y1):
                g=g+1 if not rows[y] else 0
                if g>best[0]: best=(g,y)
            if best[0]<4: return [mm]
            c=best[1]; top=mm.copy();top[c:]=False;bot=mm.copy();bot[:c]=False
            return cut(top)+cut(bot)
        for m2 in cut(m):
            ys2=np.where(m2.any(1))[0];xs2=np.where(m2.any(0))[0]
            if m2.sum()>=150: comps.append((ys2[0],xs2[0],m2))
        continue
    comps.append((sl[0].start,sl[1].start,m))
# small icons (like the profile icon) ride with the text beside them
def bb(m):
    ys=np.where(m.any(1))[0];xs=np.where(m.any(0))[0];return ys[0],ys[-1],xs[0],xs[-1]
changed=True
while changed:
    changed=False
    for i,(y0,x0,m) in enumerate(comps):
        a0,a1,b0,b1=bb(m)
        if b1-b0<130 and a1-a0<130:
            best=None
            for j,(_,_,m2) in enumerate(comps):
                if j==i: continue
                c0,c1,d0,d1=bb(m2)
                if c0<=a1 and c1>=a0:
                    gap=max(d0-b1,b0-d1,0)
                    if gap<160 and (best is None or gap<best[0]): best=(gap,j)
            if best:
                j=best[1];yy,xx,m2=comps[j];comps[j]=(min(yy,y0),min(xx,x0),m2|m);comps.pop(i);changed=True;break
comps.sort(key=lambda c:(c[0]//45,c[1]))
sticker=[c for c in comps if c[1]>W*0.6 and c[0]>H*0.72]
if sticker:
    st=max(sticker,key=lambda c:c[0]); comps=[c for c in comps if c is not st]+[st]
alpha_all=ndimage.gaussian_filter(ndimage.binary_dilation(ink,iterations=2).astype(np.float32),1.0).clip(0,1)
mb=[]
for y0,x0,m in comps:
    mm=ndimage.binary_dilation(m,iterations=3)
    ys=np.where(mm.any(1))[0]
    mb.append((ys[0],ys[-1]+1,(mm*alpha_all)))
print(os.path.basename(src),'grid',px,py,'groups',len(mb))
# reel canvas
CW,CH=1080,1920; TAN=(201,174,134)
bg=Image.new('RGB',(CW,CH),TAN)
noise=(np.random.RandomState(4).rand(CH,CW,1)*14-7)
bg=Image.fromarray(np.clip(np.asarray(bg).astype(np.float32)+noise,0,255).astype(np.uint8))
PX,PY=40,(CH-int(H*(CW-80)/W))//2; S=(CW-80)/W
sh=Image.new('L',(CW,CH),0);ImageDraw.Draw(sh).rectangle([PX+6,PY+14,PX+int(W*S)+6,PY+int(H*S)+14],fill=110)
sh=sh.filter(ImageFilter.GaussianBlur(16)); bg=Image.composite(Image.new('RGB',(CW,CH),(90,65,30)),bg,sh)
start=0.45; dur_in=0.38; POP=4.05
step=(3.45-start)/max(1,len(mb)-2)
T=7.0; N=int(T*FPS)
fr=f'/tmp/nbfr_{os.getpid()}';os.makedirs(fr,exist_ok=True)
times=[start+i*step for i in range(len(mb)-1)]+[POP]
def ease(t): return 1-(1-t)**3
for f in range(N):
    t=f/FPS; page=blank.copy()
    for (y0,y1,am),t0 in zip(mb,times):
        p=(t-t0)/dur_in
        if p<=0: continue
        p=min(1,p); e=ease(p); dx=int((1-e)*-60)
        if t0==POP:
            # drop-in like the money reels: starts bigger, up-left and see-through, falls into place on the boom (~4.30s)
            pp=min(1,(t-t0)/0.25); e2=pp*pp
            sc=1.28-0.28*e2; offx=-110*(1-e2); offy=-130*(1-e2); rot=5*(1-e2); op=0.35+0.65*min(1,pp*1.6)
            ys=np.where(am.any(1))[0];xs=np.where(am.any(0))[0];a0,a1,b0,b1=ys[0],ys[-1]+1,xs[0],xs[-1]+1
            cy,cx=(a0+a1)/2+offy,(b0+b1)/2+offx
            rgba=np.dstack([im[a0:a1,b0:b1],am[a0:a1,b0:b1]*255]).clip(0,255).astype(np.uint8)
            spr=Image.fromarray(rgba,'RGBA');spr=spr.resize((int((b1-b0)*sc),int((a1-a0)*sc)),Image.LANCZOS).rotate(rot,resample=Image.BICUBIC,expand=True)
            sp=np.asarray(spr).astype(np.float32);nh,nw=sp.shape[:2]
            y0p=max(0,int(cy-nh/2));x0p=max(0,int(cx-nw/2));y1p=min(H,y0p+nh);x1p=min(W,x0p+nw)
            cr=sp[:y1p-y0p,:x1p-x0p];ar=cr[...,3:]/255*op
            page[y0p:y1p,x0p:x1p]=page[y0p:y1p,x0p:x1p]*(1-ar)+cr[...,:3]*ar
            continue
        a=am[y0:y1]*e; seg=im[y0:y1]
        if dx: seg=np.roll(seg,dx,1); a=np.roll(a,dx,1)
        page[y0:y1]=page[y0:y1]*(1-a[...,None])+seg*a[...,None]
    pg=Image.fromarray(page.clip(0,255).astype(np.uint8)).resize((int(W*S),int(H*S)),Image.LANCZOS)
    c=bg.copy();c.paste(pg,(PX,PY))
    # tape
    tp=Image.new('RGBA',(200,52),(236,226,190,200));c.paste(tp,(CW//2-100,PY-26),tp)
    c.save(f'{fr}/f{f:04d}.jpg',quality=93)
import shutil; shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)),'nb_audio.wav'),f'{fr}/a.wav')
subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',f'{fr}/f%04d.jpg','-i',f'{fr}/a.wav','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-preset','medium','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',out],check=True)
subprocess.run(['rm','-rf',fr])
print('done',out,round(T,1),'s')
