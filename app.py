import os, re, io, math, wave, asyncio, sqlite3, tempfile, textwrap, requests
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
# Compatibility for MoviePy 1.x with Pillow 10 and newer.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip

ROOT=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'autocreator_v3_outputs'; OUT.mkdir(exist_ok=True)
DB=OUT/'autocreator.db'
W,H=540,960

def db():
 c=sqlite3.connect(DB)
 c.execute('CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY,title TEXT,script TEXT,filepath TEXT,created TEXT,status TEXT DEFAULT "Draft")')
 c.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY,video_id INTEGER,platform TEXT,url TEXT,status TEXT,created TEXT)')
 c.commit(); return c

def font(size):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']:
  if Path(p).exists(): return ImageFont.truetype(p,size)
 return ImageFont.load_default()

def lines_fit(draw,text,ft,maxw):
 lines=[]; current=''
 for word in text.split():
  candidate=(current+' '+word).strip()
  if draw.textbbox((0,0),candidate,font=ft)[2]<=maxw: current=candidate
  else:
   if current: lines.append(current)
   current=word
 if current: lines.append(current)
 return lines

def fetch_pexels_photo(query, api_key, cache_dir, index):
 """Fetch a relevant portrait-oriented photo. Returns Pillow image or raises an explicit error."""
 if not api_key.strip():
  raise ValueError('A free Pexels API key is needed for automatic real photographs. Add it in the Visuals section, or upload your own photos.')
 terms=re.sub(r'[^a-zA-Z0-9 ]',' ',query)
 terms=' '.join(terms.split()[:9]) or 'cinematic landscape'
 try:
  response=requests.get('https://api.pexels.com/v1/search',headers={'Authorization':api_key.strip()},params={'query':terms,'per_page':8,'orientation':'portrait'},timeout=20)
  if response.status_code in (401,403): raise ValueError('Pexels rejected the API key. Please check that you copied the correct key.')
  response.raise_for_status()
  items=response.json().get('photos',[])
  if not items:
   # Search with broader keywords if a complete sentence has no results.
   response=requests.get('https://api.pexels.com/v1/search',headers={'Authorization':api_key.strip()},params={'query':' '.join(terms.split()[:3]) or 'nature','per_page':8,'orientation':'portrait'},timeout=20)
   response.raise_for_status();items=response.json().get('photos',[])
  if not items: raise ValueError('No matching Pexels photographs found for scene '+str(index+1)+'. Try simpler wording or upload your own photos.')
  item=items[index%len(items)]
  url=item.get('src',{}).get('large2x') or item.get('src',{}).get('large')
  if not url: raise ValueError('Photo service returned no usable image URL.')
  img_response=requests.get(url,timeout=25)
  img_response.raise_for_status()
  if len(img_response.content)>15_000_000: raise ValueError('Downloaded image was too large.')
  img=Image.open(io.BytesIO(img_response.content));img.load()
  return img.convert('RGB'),item.get('photographer','Pexels contributor'),item.get('url','')
 except requests.RequestException as ex:
  raise RuntimeError('Could not download scene photographs from Pexels: '+str(ex)) from ex

def scene_image(title,caption,index,total,style,theme,photo=None):
 colors={'Ocean':((9,19,52),(15,119,161)),'Sunset':((48,17,58),(245,114,85)),'Forest':((10,40,38),(75,166,122))}
 dark,bright=colors[theme]
 if photo is not None:
  im=ImageOps.fit(photo.convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)
  im=Image.blend(im,Image.new('RGB',(W,H),(8,10,22)),.38)
 else:
  # Original algorithmically generated cinematic-looking art; not photorealistic text-to-video AI.
  y=np.arange(H,dtype=np.float32)[:,None,None]
  x=np.arange(W,dtype=np.float32)[None,:,None]
  t=y/H
  base=np.array(dark)[None,None,:]*(1-t)+np.array(bright)[None,None,:]*t
  glow=np.exp(-(((x-W*(.3+.35*(index%3)/2))/(W*.55))**2+((y-H*.42)/(H*.38))**2))*35
  arr=np.clip(base+glow,0,255).astype('uint8')
  im=Image.fromarray(arr,'RGB')
  d=ImageDraw.Draw(im,'RGBA')
  for k in range(13):
   px=int((k*173+index*67)%W); py=int((k*239+index*101)%H)
   r=12+(k*13)%78
   d.ellipse((px-r,py-r,px+r,py+r),outline=(*bright,45),width=2)
  if style=='Cinematic motion':
   d.polygon([(0,730),(W*.38,530),(W,790),(W,H),(0,H)],fill=(*dark,125))
   d.ellipse((330,170,485,325),fill=(*bright,100))
 im=im.filter(ImageFilter.GaussianBlur(1.1))
 overlay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(overlay)
 d.rounded_rectangle((24,36,W-24,106),radius=17,fill=(0,0,0,150))
 head=title.strip()[:46] or 'AutoCreator AI'
 f=font(26)
 while d.textbbox((0,0),head,font=f)[2]>W-78 and len(head)>6: head=head[:-2]
 d.text((42,58),head,font=f,fill='white')
 for sz in [58,54,50,46,42,38,34,30,26]:
  ft=font(sz); ls=lines_fit(d,caption,ft,W-90)
  if len(ls)*int(sz*1.32)<500: break
 step=int(sz*1.32); height=len(ls)*step
 top=max(210,min(670-height,(H-height)//2))
 d.rounded_rectangle((20,top-30,W-20,top+height+26),radius=24,fill=(0,0,0,175))
 for j,line in enumerate(ls):
  width=d.textbbox((0,0),line,font=ft)[2]
  d.text(((W-width)/2,top+j*step),line,font=ft,fill='white',stroke_width=2,stroke_fill=(0,0,0))
 d.rounded_rectangle((30,879,W-30,892),radius=6,fill=(255,255,255,90))
 d.rounded_rectangle((30,879,30+int((W-60)*(index+1)/total),892),radius=6,fill=(*bright,255))
 d.text((32,908),f'{index+1} / {total}',font=font(18),fill='white')
 return Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')

async def speak_edge(text,path,voice):
 import edge_tts
 await edge_tts.Communicate(text,voice,rate='+0%').save(str(path))

def narrate(text,path,voice):
 try:
  asyncio.run(speak_edge(text,path,voice))
  if path.exists() and path.stat().st_size>1000: return
 except Exception as edge_error:
  try:
   from gtts import gTTS
   gTTS(text=text,lang='en').save(str(path))
   if path.exists() and path.stat().st_size>1000: return
  except Exception as fallback_error:
   raise RuntimeError('Voice services could not be reached. Check cloud network access and retry. '+str(fallback_error)) from edge_error
 raise RuntimeError('Voice generation returned no audio')

def music_wav(path,duration):
 # Original, quiet ambient tones; no copyrighted music tracks.
 rate=16000; count=int(duration*rate)
 with wave.open(str(path),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
  chunk=rate*3
  for start in range(0,count,chunk):
   t=np.arange(start,min(start+chunk,count))/rate
   envelope=np.minimum(1,np.minimum(t/1.5,(duration-t)/1.5).clip(0,1))
   a=(np.sin(2*np.pi*110*t)*.32+np.sin(2*np.pi*164.81*t)*.22+np.sin(2*np.pi*220*t)*.15)
   samples=(a*envelope*1800).astype('<i2')
   w.writeframes(samples.tobytes())

def make_video(title,script,style,theme,voice,add_music,photos,visual_source,pexels_key):
 parts=[p.strip() for p in re.split(r'(?<=[.!?])\s+|\n+',script.strip()) if p.strip()]
 if not parts: raise ValueError('Enter a script first')
 if len(parts)>8: raise ValueError('For free hosting, use up to 8 sentences per video.')
 clips=[]; audios=[]; music=None; combined=None; video=None; credits=[]
 with tempfile.TemporaryDirectory() as tmp:
  td=Path(tmp)
  try:
   for i,part in enumerate(parts):
    audio_path=td/f'voice_{i}.mp3'; narrate(part,audio_path,voice)
    aud=AudioFileClip(str(audio_path)); audios.append(aud)
    duration=max(1.5,aud.duration+.35)
    image_path=td/f'scene_{i}.jpg'
    photo=photos[i%len(photos)] if photos else None
    if visual_source=='Automatic real photographs':
     photo,creator,photo_url=fetch_pexels_photo(part,pexels_key,td,i)
     credits.append((creator,photo_url))
    elif visual_source=='My uploaded photos' and photo is None:
     raise ValueError('Please upload at least one photograph for this visual mode.')
    scene_image(title,part,i,len(parts),style,theme,photo).save(image_path,quality=90)
    # Small Ken Burns-style motion creates real moving frames from the original art or photo.
    still=ImageClip(str(image_path)).set_duration(duration)
    moving=still.resize(lambda t: 1.0+0.035*min(t/duration,1)).crop(x_center=W/2,y_center=H/2,width=W,height=H)
    moving=moving.set_audio(aud.set_start(0))
    clips.append(moving)
   video=concatenate_videoclips(clips,method='compose')
   if add_music:
    mp=td/'ambient.wav'; music_wav(mp,video.duration)
    music=AudioFileClip(str(mp)); combined=CompositeAudioClip([video.audio,music.volumex(.32)])
    video=video.set_audio(combined)
   path=OUT/f'autocreator_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.mp4'
   video.write_videofile(str(path),fps=12,codec='libx264',audio_codec='aac',audio_bitrate='96k',preset='ultrafast',threads=2,logger=None)
   return path, credits
  finally:
   if video: video.close()
   if combined: combined.close()
   if music: music.close()
   for c in clips: c.close()
   for a in audios: a.close()

st.set_page_config(page_title='AutoCreator AI v3',page_icon='🎬',layout='centered')
st.title('🎬 AutoCreator AI · Visuals upgrade')
st.caption('iPhone-friendly video studio • real scene photos • voice narration • large subtitles')
st.info('Choose Automatic real photographs to match images to each sentence using Pexels. These are licensed stock photos with animated camera motion, NOT newly AI-generated images or footage. Publishing remains manual.')
t1,t2,t3,t4=st.tabs(['🎥 Create','📈 Trends','📤 Publishing','📊 Analytics'])
with t1:
 title=st.text_input('Video title','3 surprising facts')
 script=st.text_area('Script (up to 8 sentences)',value='Your brain stays active even while you sleep. A short walk can help you feel more alert. Small daily habits add up over time.',height=160)
 style=st.radio('Video style',['Faceless storytelling','Cinematic motion'],horizontal=True)
 theme=st.selectbox('Visual theme',['Ocean','Sunset','Forest'])
 st.subheader('🖼️ Visuals')
 visual_source=st.radio('Where should scenes come from?',['Automatic real photographs','My uploaded photos','Abstract animated backgrounds'],horizontal=False)
 pexels_key=''
 if visual_source=='Automatic real photographs':
  pexels_key=st.text_input('Pexels API key (free)',value=st.secrets.get('PEXELS_API_KEY','') if 'PEXELS_API_KEY' in st.secrets else '',type='password',help='Get a free API key at pexels.com/api. It is used only for your video generation request.')
  st.markdown('[Get your free Pexels API key](https://www.pexels.com/api/)')
  st.caption('Scenes are searched from your script. Photo attribution is displayed after generation; keep credits when publishing.')
 voice=st.selectbox('Narrator',['en-US-AriaNeural','en-US-GuyNeural','en-GB-SoniaNeural'],format_func=lambda v:{'en-US-AriaNeural':'Female · American','en-US-GuyNeural':'Male · American','en-GB-SoniaNeural':'Female · British'}[v])
 add_music=st.checkbox('Add original ambient background music',value=True)
 uploads=st.file_uploader('Optional: upload your own JPG/PNG photos (used in My uploaded photos mode)',type=['jpg','jpeg','png'],accept_multiple_files=True)
 photos=[]
 for up in (uploads or [])[:8]:
  try:
   p=Image.open(io.BytesIO(up.getvalue()));p.load()
   if p.width*p.height>20000000: st.warning(f'{up.name} is too large; skipped')
   else: photos.append(p.convert('RGB'))
  except Exception: st.warning(f'Cannot read {up.name}')
 if st.button('🎬 Generate video with voice',type='primary',use_container_width=True):
  try:
   with st.spinner('Creating narration, scenes and MP4. Free cloud rendering can take several minutes...'):
    path,credits=make_video(title,script,style,theme,voice,add_music,photos,visual_source,pexels_key)
    st.session_state['last_credits']=credits
    c=db();c.execute('INSERT INTO videos(title,script,filepath,created) VALUES (?,?,?,?)',(title,script,str(path),datetime.now().isoformat(timespec='seconds')));c.commit();c.close()
    st.session_state['last_video']=str(path)
   st.success('Your narrated MP4 is ready!')
  except Exception as e: st.error(f'Could not generate video: {e}')
 if st.session_state.get('last_video') and Path(st.session_state['last_video']).exists():
  p=Path(st.session_state['last_video']);st.video(str(p));st.download_button('⬇️ Download MP4 to iPhone',p.read_bytes(),file_name=p.name,mime='video/mp4',use_container_width=True)
  if st.session_state.get('last_credits'):
   with st.expander('Photo credits — include when publishing'):
    for creator,url in st.session_state['last_credits']:
     st.write(f'Photo by {creator}: {url}')
 st.caption('Tip: start with 2–3 short sentences. Download immediately: free hosting may erase files after restart.')
with t2:
 st.subheader('Explore public trends')
 keyword=st.text_input('Topic or niche','satisfying faceless videos');q=quote_plus(keyword)
 st.markdown(f'[Google Trends](https://trends.google.com/trends/explore?q={q}) · [YouTube](https://www.youtube.com/results?search_query={q}) · [Reddit](https://www.reddit.com/search/?q={q}) · [Google News](https://news.google.com/search?q={q})')
 st.caption('These are research links, not an automatic real-time trend scanner.')
with t3:
 st.subheader('Video library and publishing tracker')
 st.caption('Upload MP4s manually. Direct posting requires official API authorization.')
 c=db();videos=c.execute('SELECT id,title,filepath,created FROM videos ORDER BY id DESC LIMIT 30').fetchall()
 for vid,name,path,created in videos:
  with st.expander(f'{name} · {created}'):
   if Path(path).exists(): st.download_button('Download video',Path(path).read_bytes(),file_name=Path(path).name,key=f'dl{vid}')
   platform=st.selectbox('Platform',['YouTube','Facebook','Instagram','TikTok','Snapchat','X'],key=f'pl{vid}')
   url=st.text_input('Published URL',key=f'url{vid}')
   if st.button('Save link',key=f'save{vid}'):
    if url.startswith('https://'):
     c.execute('INSERT INTO posts(video_id,platform,url,status,created) VALUES (?,?,?,?,?)',(vid,platform,url,'Published',datetime.now().isoformat(timespec='seconds')));c.commit();st.success('Saved')
    else: st.error('Enter an HTTPS URL')
 if not videos: st.info('Create a video to start your library.')
 c.close()
with t4:
 c=db();st.metric('Videos created',c.execute('SELECT COUNT(*) FROM videos').fetchone()[0]);st.metric('Published links recorded',c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]);c.close()
 st.caption('Live views and earnings require authorized platform analytics connections. Data is temporary on free hosting.')
