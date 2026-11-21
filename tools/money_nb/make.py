# Build money notebook posts (1080x1350 PNG) and their animated reels (1080x1920 MP4)
# from a JSON spec, in the approved money notebook style.
# Usage: python3 make.py posts.json OUTDIR [ids...]
import sys, os, json, html, subprocess, numpy as np
from PIL import Image, ImageFilter, ImageDraw
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = open(os.path.join(HERE, 'template.html')).read()
E = html.escape

ICONS = {
 'card': '<svg width="130" height="100" viewBox="0 0 130 100"><rect x="6" y="14" width="118" height="76" rx="12" fill="#A9DDF7" stroke="#1F2340" stroke-width="6"/><rect x="6" y="32" width="118" height="14" fill="#1F2340"/><rect x="22" y="60" width="60" height="14" rx="7" fill="#fff" stroke="#1F2340" stroke-width="4"/><rect x="22" y="60" width="20" height="14" rx="7" fill="#C8423B"/></svg>',
 'calendar': '<svg width="110" height="110" viewBox="0 0 110 110"><rect x="8" y="16" width="94" height="86" rx="10" fill="#fff" stroke="#1F2340" stroke-width="6"/><rect x="8" y="16" width="94" height="26" rx="10" fill="#F28B82" stroke="#1F2340" stroke-width="6"/><line x1="32" y1="6" x2="32" y2="26" stroke="#1F2340" stroke-width="7" stroke-linecap="round"/><line x1="78" y1="6" x2="78" y2="26" stroke="#1F2340" stroke-width="7" stroke-linecap="round"/><circle cx="34" cy="64" r="7" fill="#1F2340"/><circle cx="56" cy="64" r="7" fill="#1F2340"/><circle cx="78" cy="64" r="7" fill="#FFDD45" stroke="#1F2340" stroke-width="3"/><circle cx="34" cy="84" r="7" fill="#1F2340"/></svg>',
 'bank': '<svg width="120" height="110" viewBox="0 0 120 110"><path d="M10 40 L60 10 L110 40 Z" fill="#FFDD45" stroke="#1F2340" stroke-width="6" stroke-linejoin="round"/><rect x="22" y="46" width="12" height="40" fill="#fff" stroke="#1F2340" stroke-width="5"/><rect x="54" y="46" width="12" height="40" fill="#fff" stroke="#1F2340" stroke-width="5"/><rect x="86" y="46" width="12" height="40" fill="#fff" stroke="#1F2340" stroke-width="5"/><rect x="10" y="90" width="100" height="12" rx="3" fill="#1F2340"/></svg>',
 'gift': '<svg width="110" height="110" viewBox="0 0 110 110"><rect x="12" y="44" width="86" height="58" rx="6" fill="#F28B82" stroke="#1F2340" stroke-width="6"/><rect x="6" y="30" width="98" height="20" rx="5" fill="#FFB3BA" stroke="#1F2340" stroke-width="6"/><rect x="47" y="30" width="16" height="72" fill="#FFDD45" stroke="#1F2340" stroke-width="5"/><path d="M55 30 C40 6 18 16 30 30 M55 30 C70 6 92 16 80 30" fill="none" stroke="#1F2340" stroke-width="6" stroke-linecap="round"/></svg>',
 'cart': '<svg width="120" height="110" viewBox="0 0 120 110"><path d="M6 12 H24 L36 74 H98 L110 30 H30" fill="#BFE9B0" stroke="#1F2340" stroke-width="6" stroke-linejoin="round"/><circle cx="44" cy="94" r="9" fill="#1F2340"/><circle cx="90" cy="94" r="9" fill="#1F2340"/></svg>',
 'chart': '<svg width="120" height="110" viewBox="0 0 120 110"><rect x="8" y="8" width="104" height="94" rx="10" fill="#fff" stroke="#1F2340" stroke-width="6"/><polyline points="22,80 44,62 62,70 84,40 100,28" fill="none" stroke="#1E8A43" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 'shield': '<svg width="100" height="116" viewBox="0 0 100 116"><path d="M50 6 L92 22 V56 C92 84 72 102 50 110 C28 102 8 84 8 56 V22 Z" fill="#A9DDF7" stroke="#1F2340" stroke-width="6" stroke-linejoin="round"/><polyline points="30,58 45,73 72,44" fill="none" stroke="#1F2340" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 'receipt': '<svg width="96" height="120" viewBox="0 0 96 120"><path d="M10 6 H86 V112 L74 104 L62 112 L50 104 L38 112 L26 104 L10 112 Z" fill="#fff" stroke="#1F2340" stroke-width="6" stroke-linejoin="round"/><line x1="24" y1="30" x2="72" y2="30" stroke="#1F2340" stroke-width="6" stroke-linecap="round"/><line x1="24" y1="50" x2="72" y2="50" stroke="#1F2340" stroke-width="6" stroke-linecap="round"/><line x1="24" y1="70" x2="56" y2="70" stroke="#C8423B" stroke-width="6" stroke-linecap="round"/></svg>',
 'piggy': '<svg width="130" height="110" viewBox="0 0 130 110"><ellipse cx="64" cy="58" rx="48" ry="36" fill="#FFB3BA" stroke="#1F2340" stroke-width="6"/><rect x="40" y="86" width="12" height="18" rx="4" fill="#FFB3BA" stroke="#1F2340" stroke-width="5"/><rect x="76" y="86" width="12" height="18" rx="4" fill="#FFB3BA" stroke="#1F2340" stroke-width="5"/><rect x="52" y="18" width="26" height="7" rx="3" fill="#1F2340"/><circle cx="92" cy="50" r="5" fill="#1F2340"/><ellipse cx="114" cy="62" rx="9" ry="11" fill="#FFB3BA" stroke="#1F2340" stroke-width="5"/></svg>',
}

def blocks(p):
    out = []
    col = []
    col.append(f'<div class="blk kick">{E(p["kicker"])}</div>')
    col.append(f'<div class="blk"><div class="t1">{E(p["t1"])}</div><div class="t2">{E(p["t2"])}</div></div>')
    if p.get('intro'):
        col.append(f'<div class="blk intro">{p["intro"]}</div>')
    for it in p['items']:
        if p['kind'] == 'steps':
            col.append(f'<div class="blk step"><div class="num">{it.get("n","")}</div><div><div class="h">{E(it["h"])}</div><div class="p">{E(it["p"])}</div></div></div>')
        else:
            box = ''
            if it.get('w'):
                box = f'<div class="box" style="width:{it["w"]}px;height:{it.get("bh",110)}px;background:{it.get("fill","#BFE9B0")}"></div>'
            col.append(f'<div class="blk row"><div class="lab"><div class="big {it.get("c","blue")}"{" style=\"font-size:30px\"" if len(it["big"])>7 else ""}>{E(it["big"])}</div><div class="sm">{E(it.get("sm",""))}</div></div>{box}<div class="txt"><div class="big">{E(it["rb"])}</div><div class="sm">{E(it.get("rs",""))}</div></div></div>')
    col.append(f'<div class="blk tip"><div class="h">{E(p["tip"]["h"])}</div><div class="p">{E(p["tip"]["p"])}</div></div>')
    out.append('<div style="position:absolute;left:140px;right:64px;top:62px;height:%dpx;display:flex;flex-direction:column;justify-content:space-between">' % p.get('colh', 1040) + ''.join(col).replace('class="blk', 'style="position:relative;left:0;right:0" class="blk') + '</div>')
    if p.get('icon'):
        out.append(f'<div class="blk icon" style="transform:rotate(6deg)">{ICONS[p["icon"]]}</div>')
    out.append('<div class="blk foot" style="top:1196px"><svg width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="none" stroke="#1F2340" stroke-width="4"/><circle cx="32" cy="25" r="10" fill="none" stroke="#1F2340" stroke-width="4"/><path d="M14 52 C18 40 46 40 50 52" fill="none" stroke="#1F2340" stroke-width="4"/></svg><div><div class="h">@THEFINANCIALLESSON</div><div class="p">Follow for one money lesson at a time</div><div class="q">Education only, not financial advice.</div></div></div>')
    out.append('<div class="blk sticky" style="top:1136px"><svg width="30" height="38" viewBox="0 0 30 38" style="margin-top:16px"><path d="M4 2 H26 V36 L15 27 L4 36 Z" fill="#C8423B" stroke="#1F2340" stroke-width="3"/></svg><div class="a">SAVE THIS</div><div class="b">for later</div></div>')
    return '\n'.join(out)

def render_layers(pg, p, d):
    doc = TPL.replace('__BLOCKS__', blocks(p))
    f = os.path.join(HERE, '_tmp.html'); open(f, 'w').write(doc)
    pg.goto('file://' + f); pg.wait_for_timeout(250)
    pg.evaluate('document.fonts.ready')
    n = pg.evaluate("document.querySelectorAll('.blk').length")
    # full static post
    pg.screenshot(path=f'{d}/post.png')
    pg.evaluate("document.body.className='paperonly'")
    pg.add_style_tag(content='body.paperonly{background:#FCFBF6 repeating-linear-gradient(#FCFBF6 0 51px,#D1DDF2 51px 53px,#FCFBF6 53px 54px);background-position:0 1px} body.paperonly .blk{visibility:hidden}')
    pg.screenshot(path=f'{d}/blank.png')
    pg.evaluate("document.body.className='layer'")
    for i in range(n):
        pg.evaluate(f"document.querySelectorAll('.blk').forEach((b,j)=>b.classList.toggle('on',j=={i}))")
        pg.screenshot(path=f'{d}/L{i:02d}.png', omit_background=True)
    return n

def animate(d, n, out):
    FPS = 30; T = 7.0; N = int(T * FPS)
    blank = np.asarray(Image.open(f'{d}/blank.png').convert('RGB')).astype(np.float32)
    H, W = blank.shape[:2]
    L = [np.asarray(Image.open(f'{d}/L{i:02d}.png').convert('RGBA')).astype(np.float32) for i in range(n)]
    # order: column blocks top-down, icon rides with the title, then footer, sticky last
    # layer order in DOM: kick, title, [intro], items..., tip, icon, foot, sticky
    idx = list(range(n))
    icon_i = n - 3 if os.path.exists(f'{d}/has_icon') else None
    seq = [i for i in idx[:-1] if i != icon_i]
    groups = [[i] for i in seq]
    if icon_i is not None: groups[0].append(icon_i)  # icon arrives with the kicker
    groups.append([n - 1])
    start, dur_in, POP = 0.45, 0.38, 4.05
    step = (3.45 - start) / max(1, len(groups) - 2)
    times = [start + i * step for i in range(len(groups) - 1)] + [POP]
    CW, CH = 1080, 1920; TAN = (201, 174, 134)
    bg = Image.new('RGB', (CW, CH), TAN)
    noise = np.random.RandomState(4).rand(CH, CW, 1) * 14 - 7
    bg = Image.fromarray(np.clip(np.asarray(bg).astype(np.float32) + noise, 0, 255).astype(np.uint8))
    S = (CW - 80) / W; PX, PY = 40, (CH - int(H * S)) // 2
    sh = Image.new('L', (CW, CH), 0); ImageDraw.Draw(sh).rectangle([PX + 6, PY + 14, PX + int(W * S) + 6, PY + int(H * S) + 14], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(16)); bg = Image.composite(Image.new('RGB', (CW, CH), (90, 65, 30)), bg, sh)
    fr = f'{d}/fr'; os.makedirs(fr, exist_ok=True)
    ease = lambda t: 1 - (1 - t) ** 3
    for f in range(N):
        t = f / FPS; page = blank.copy()
        for g, t0 in zip(groups, times):
            if t <= t0: continue
            for li in g:
                lay = L[li]
                if t0 == POP:
                    pp = min(1, (t - t0) / 0.25); e2 = pp * pp
                    sc = 1.28 - 0.28 * e2; offx = -110 * (1 - e2); offy = -130 * (1 - e2); rot = 5 * (1 - e2); op = 0.35 + 0.65 * min(1, pp * 1.6)
                    a = lay[..., 3]; ys = np.where(a.max(1) > 0)[0]; xs = np.where(a.max(0) > 0)[0]
                    a0, a1, b0, b1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
                    spr = Image.fromarray(lay[a0:a1, b0:b1].astype(np.uint8), 'RGBA')
                    spr = spr.resize((int((b1 - b0) * sc), int((a1 - a0) * sc)), Image.LANCZOS).rotate(rot, resample=Image.BICUBIC, expand=True)
                    sp = np.asarray(spr).astype(np.float32); nh, nw = sp.shape[:2]
                    cy, cx = (a0 + a1) / 2 + offy, (b0 + b1) / 2 + offx
                    y0p = max(0, int(cy - nh / 2)); x0p = max(0, int(cx - nw / 2)); y1p = min(H, y0p + nh); x1p = min(W, x0p + nw)
                    cr = sp[:y1p - y0p, :x1p - x0p]; ar = cr[..., 3:] / 255 * op
                    page[y0p:y1p, x0p:x1p] = page[y0p:y1p, x0p:x1p] * (1 - ar) + cr[..., :3] * ar
                else:
                    p = min(1, (t - t0) / dur_in); e = ease(p); dx = int((1 - e) * -60)
                    seg = np.roll(lay, dx, 1) if dx else lay
                    a = seg[..., 3:] / 255 * e
                    page = page * (1 - a) + seg[..., :3] * a
        pg = Image.fromarray(page.clip(0, 255).astype(np.uint8)).resize((int(W * S), int(H * S)), Image.LANCZOS)
        c = bg.copy(); c.paste(pg, (PX, PY))
        tp = Image.new('RGBA', (200, 52), (236, 226, 190, 200)); c.paste(tp, (CW // 2 - 100, PY - 26), tp)
        c.save(f'{fr}/f{f:04d}.jpg', quality=93)
    aud = os.path.join(HERE, '..', 'nb_audio.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', f'{fr}/f%04d.jpg', '-i', aud, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
    subprocess.run(['rm', '-rf', fr])

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1])); outdir = sys.argv[2]; ids = sys.argv[3:]
    os.makedirs(outdir, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1080, 'height': 1350})
        for p in spec:
            if ids and p['id'] not in ids: continue
            d = f'/home/claude/work/mnb_{p["id"]}'; os.makedirs(d, exist_ok=True)
            if p.get('icon'): open(f'{d}/has_icon', 'w').close()
            elif os.path.exists(f'{d}/has_icon'): os.remove(f'{d}/has_icon')
            n = render_layers(pg, p, d)
            Image.open(f'{d}/post.png').convert('RGB').save(f'{outdir}/NB_{p["id"]}.png')
            animate(d, n, f'{outdir}/NBR_{p["id"]}.mp4')
            print('done', p['id'], n, 'layers', flush=True)
        b.close()
