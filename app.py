import streamlit as st
import sqlite3, os, re, tempfile, textwrap, json
from pathlib import Path
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent
DB=ROOT/'autocreator.db'
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)

def db():
 c=sqlite3.connect(DB); c.execute('CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, title TEXT, script TEXT, filepath TEXT, created TEXT, status TEXT DEFAULT "Draft")'); c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, video_id INTEGER, platform TEXT, url TEXT, status TEXT, created TEXT)'); c.commit(); return c

def font(size):
 for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf','C:/Windows/Fonts/arialbd.ttf']:
  if os.path.exists(f): return ImageFont.truetype(f,size)
 return ImageFont.load_default()

def render_frame(text, title, theme, idx, count):
 colors={'Midnight':((12,17,35),(76,130,245)),'Sunset':((47,20,52),(255,155,90)),'Forest':((10,39,36),(83,215,167))}
 bg,accent=colors[theme]; im=Image.new('RGB',(720,1280),bg); d=ImageDraw.Draw(im)
 for y in range(1280):
  t=y/1280; d.line((0,y,720,y),fill=tuple(int(bg[k]*(1-t*.45)+accent[k]*t*.45) for k in range(3)))
 d.rounded_rectangle((42,55,678,123),radius=22,fill=(255,255,255,30) if False else accent)
 d.text((65,74),title[:28],font=font(27),fill='white')
 words=text.split(); lines=[]; line=''
 for w in words:
  if len(line+' '+w)>22: lines.append(line); line=w
  else: line=(line+' '+w).strip()
 if line: lines.append(line)
 lines=lines[:10]; f=font(49 if len(lines)<7 else 38)
 heights=len(lines)*72; y=640-heights//2
 for line in lines:
  bb=d.textbbox((0,0),line,font=f); width=bb[2]-bb[0]; d.text(((720-width)//2,y),line,font=f,fill='white',stroke_width=1,stroke_fill=bg); y+=72
 d.rounded_rectangle((48,1165,672,1177),radius=6,fill=(80,90,110))
 d.rounded_rectangle((48,1165,48+int(624*(idx+1)/count),1177),radius=6,fill=accent)
 d.text((52,1200),f'{idx+1} / {count}',font=font(22),fill='white')
 return im

def make_video(title, script, theme, seconds):
 from moviepy.editor import ImageClip, concatenate_videoclips
 parts=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+',script) if s.strip()]
 if not parts: raise ValueError('Enter a script first')
 # Avoid excessively long renders on free machines.
 parts=parts[:24]
 per=max(1.5,min(8.0,seconds/max(1,len(parts))))
 clips=[]
 with tempfile.TemporaryDirectory() as td:
  for i,part in enumerate(parts):
   p=Path(td)/f'{i:03}.png'; render_frame(part,title,theme,i,len(parts)).save(p)
   clips.append(ImageClip(str(p)).set_duration(per))
  video=concatenate_videoclips(clips,method='compose')
  path=OUT/f'video_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.mp4'
  video.write_videofile(str(path),fps=12,codec='libx264',audio=False,preset='ultrafast',logger=None)
  video.close()
  for clip in clips: clip.close()
 return path

st.set_page_config(page_title='AutoCreator AI',page_icon='🎬',layout='wide')
st.title('🎬 AutoCreator AI')
st.caption('Free-first cloud creator studio • portrait MP4s • trend research • publishing tracker')
st.warning('Cloud demo: generated files and publishing history may be erased when the free host restarts. Download each MP4 immediately. This app does not auto-post.')
t1,t2,t3,t4=st.tabs(['🎥 Create video','📈 Trend research','📤 Publishing dashboard','📊 Analytics'])
with t1:
 st.subheader('Turn your script into a vertical video')
 st.info('This version generates real caption-slide MP4 videos (720 × 1280), without paid APIs. It does not yet generate cinematic AI footage or voiceovers.')
 title=st.text_input('Video title',value='3 surprising facts')
 script=st.text_area('Your script — one sentence per scene',height=180,value='Your brain uses energy even while you sleep.\nA short walk can help you feel more alert.\nSmall daily habits can add up over time.')
 c1,c2=st.columns(2)
 theme=c1.selectbox('Visual theme',['Midnight','Sunset','Forest'])
 seconds=c2.slider('Approximate duration (seconds)',10,90,30)
 if st.button('Generate MP4',type='primary'):
  try:
   with st.spinner('Rendering your video. This may take a minute...'):
    path=make_video(title,script,theme,seconds)
    c=db(); c.execute('INSERT INTO videos(title,script,filepath,created) VALUES (?,?,?,?)',(title,script,str(path),datetime.now().isoformat(timespec='seconds'))); c.commit(); c.close()
   st.success('Video created!')
   st.session_state['last_video'] = str(path)
   st.video(str(path))
  except Exception as e: st.error(f'Video generation failed: {e}')
 if st.session_state.get('last_video') and Path(st.session_state['last_video']).exists():
  last=Path(st.session_state['last_video'])
  st.download_button('⬇️ Download your latest MP4',data=last.read_bytes(),file_name=last.name,mime='video/mp4',key='latest_download')
with t2:
 st.subheader('Trend discovery')
 st.write('Search current public discussions with free external search links. The app does not claim to scrape real-time trends or predict earnings.')
 keyword=st.text_input('Your niche or keyword',value='satisfying AI videos')
 from urllib.parse import quote_plus
 q=quote_plus(keyword)
 st.markdown(f'- [Google Trends](https://trends.google.com/trends/explore?q={q})\n- [YouTube search](https://www.youtube.com/results?search_query={q})\n- [Reddit search](https://www.reddit.com/search/?q={q})\n- [Google News](https://news.google.com/search?q={q})')
 st.subheader('Content scoring worksheet')
 interest=st.slider('Audience interest (your estimate)',1,5,3)
 originality=st.slider('Originality',1,5,4)
 production=st.slider('Ease of production',1,5,4)
 st.metric('Opportunity score (subjective)',f'{(interest+originality+production)/15*100:.0f}/100')
 st.caption('This score is based only on your inputs; it is not live market intelligence.')
with t3:
 st.subheader('Your video library and publishing tracker')
 st.warning('Direct auto-posting requires official API access and platform authorization. This MVP lets you download and manually post, then record the post links.')
 c=db(); videos=c.execute('SELECT id,title,filepath,created,status FROM videos ORDER BY id DESC').fetchall()
 if not videos: st.info('Create your first video to see it here.')
 else:
  for vid,title,path,created,status in videos:
   with st.expander(f'#{vid} • {title} • {created}'):
    if Path(path).exists():
     with open(path,'rb') as f: st.download_button('Download MP4',f,file_name=Path(path).name,key=f'dl{vid}')
    platform=st.selectbox('Platform',['YouTube','Facebook','Instagram','TikTok','Snapchat','X'],key=f'pl{vid}')
    url=st.text_input('Published post URL',key=f'url{vid}')
    if st.button('Save published link',key=f'save{vid}'):
     if url.startswith('https://'):
      c.execute('INSERT INTO posts(video_id,platform,url,status,created) VALUES (?,?,?,?,?)',(vid,platform,url,'Published',datetime.now().isoformat(timespec='seconds'))); c.commit(); st.success('Saved')
     else: st.error('Enter a valid HTTPS post URL')
 c.close()
with t4:
 st.subheader('Publishing overview')
 c=db(); n=c.execute('SELECT COUNT(*) FROM videos').fetchone()[0]; p=c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
 a,b=st.columns(2); a.metric('Videos created',n); b.metric('Published links recorded',p)
 rows=c.execute('SELECT videos.title,posts.platform,posts.url,posts.created FROM posts JOIN videos ON videos.id=posts.video_id ORDER BY posts.id DESC').fetchall()
 if rows:
  import pandas as pd
  st.dataframe(pd.DataFrame(rows,columns=['Video','Platform','URL','Date']),use_container_width=True)
 st.caption('View counts and revenue cannot be verified without connected platform analytics APIs.')
 c.close()
