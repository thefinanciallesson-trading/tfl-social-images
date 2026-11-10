import sys,os,shutil,subprocess
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.abspath(__file__));out=sys.argv[1];T=7.0;FPS=30
fr=D+'/fr';shutil.rmtree(fr,ignore_errors=True);os.makedirs(fr)
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={'width':1080,'height':1920})
    pg.goto(f'file://{D}/story.html');pg.evaluate('document.fonts.ready');pg.wait_for_timeout(500)
    for i in range(int(T*FPS)):
        pg.evaluate(f'render({i/FPS})');pg.screenshot(path=f'{fr}/f{i:04d}.jpg',type='jpeg',quality=93)
    pg.evaluate('render(6.9)');pg.screenshot(path=D+'/story_still.png')
    b.close()
subprocess.run(['ffmpeg','-v','error','-y','-framerate','30','-i',f'{fr}/f%04d.jpg','-i',D+'/../nbanim/nb_audio.wav','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',out],check=True)
shutil.rmtree(fr)
