"""PaataGuess: Gradio host, YouTube audio, no login needed to play.

The server looks up a YouTube video for each song (YouTube Data API, key stays on the server)
and the browser plays it with the YouTube IFrame Player, cutting the clip at 1s, 2s, 4s...

Set YOUTUBE_API_KEY (env var / Hugging Face Space secret), then run `python app.py`.
To pin a song to a specific video, add its YouTube ID as a third item in that SONGS line.
"""
import inspect
import json
import os
import re
import threading

import gradio as gr
import httpx

YT_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "video_ids.json")

# [title, film, optional YouTube video ID]
SONGS = [
    ['Naatu Naatu', 'RRR'],
    ['Dosti', 'RRR'],
    ['Komma Uyyala', 'RRR'],
    ['Etthara Jenda', 'RRR'],
    ['Janani', 'RRR'],
    ['Srivalli', 'Pushpa: The Rise'],
    ['Saami Saami', 'Pushpa: The Rise'],
    ['Oo Antava', 'Pushpa: The Rise'],
    ['Eyy Bidda Idhi Naa Adda', 'Pushpa: The Rise'],
    ['Peelings', 'Pushpa 2: The Rule'],
    ['Kissik', 'Pushpa 2: The Rule'],
    ['Sooseki', 'Pushpa 2: The Rule'],
    ['Ramuloo Ramulaa', 'Ala Vaikunthapurramuloo'],
    ['Butta Bomma', 'Ala Vaikunthapurramuloo'],
    ['Samajavaragamana', 'Ala Vaikunthapurramuloo'],
    ['Mind Block', 'Sarileru Neekevvaru'],
    ['Daang Daang', 'Sarileru Neekevvaru'],
    ['Suryudivo Chandrudivo', 'Sarileru Neekevvaru'],
    ['Inkem Inkem Inkem Kaavaale', 'Geetha Govindam'],
    ['Vachindamma', 'Geetha Govindam'],
    ['Hosanna', 'Ye Maaya Chesave'],
    ['Nee Kallu Neeli Samudram', 'Uppena'],
    ['Dhak Dhak', 'Uppena'],
    ['Neeli Neeli Aakasam', '30 Rojullo Preminchadam Ela'],
    ['Pillaa Raa', 'RX 100'],
    ['Jigelu Rani', 'Rangasthalam'],
    ['Yentha Sakkagunnave', 'Rangasthalam'],
    ['Rangamma Mangamma', 'Rangasthalam'],
    ['Ee Raathale', 'Radhe Shyam'],
    ['Oh Sita Hey Rama', 'Sita Ramam'],
    ['Inthandam', 'Sita Ramam'],
    ['Kurchi Madathapetti', 'Guntur Kaaram'],
    ['Dum Masala', 'Guntur Kaaram'],
    ['Boss Party', 'Waltair Veerayya'],
    ['Poonakaalu Loading', 'Waltair Veerayya'],
    ['Chuttamalle', 'Devara'],
    ['Daavudi', 'Devara'],
    ['Gaali Vaaluga', 'Agnyaathavaasi'],
    ['Padi Padi Leche Manasu', 'Padi Padi Leche Manasu'],
    ['Maate Vinadhuga', 'Taxiwaala'],
    ['Adbhutam', 'Lover'],
    ['Saiyaan', 'Mehbooba'],
    ['Inthe Inthena', 'Nannu Dochukunduvate'],
    ['Ghal Ghal', 'Nuvvostanante Nenoddantana'],
    ['Nuvvostanante Nenoddantana', 'Nuvvostanante Nenoddantana'],
    ['Nuvvu Nenu', 'Nuvvu Nenu'],
    ['Oka Laila Kosam', 'Oka Laila Kosam'],
    ['Nelluri Nerajana', 'Oke Okkadu'],
    ['Dai Dai Dhamma', 'Indra'],
    ['Ammaye', 'Kushi'],
    ['Aradhya', 'Kushi'],
    ['Hayirabba', 'Jeans'],
    ['Cheliya Cheliya', 'Gharshana'],
    ['Bangala Kathamulo', 'Badri'],
    ['Hrudayam Ekkadunnadi', 'Ghajini'],
    ['Bunny Bunny', 'Bunny'],
    ['Nuvvasthanante', 'Varsham'],
    ['Andamaina Kundanala Bomma', 'Sampangi'],
    ['Ramma Chilakamma', 'Choodalani Undi'],
    ['Nuvvu Vijilesthey', 'Simhadri'],
    ['Tooneega', 'Manasantha Nuvve'],
    ['Ranu Ranu', 'Jayam'],
    ['Nee Kosam', 'Neekosam'],
    ['Sirimalle Puvvaa', 'Padaharella Vayasu'],
    ['Muthyamantha', 'Muthayalu Muggu'],
    ['O Priya Priya', 'Geethanjali'],
    ['Jallanta Kavvintha', 'Geethanjali'],
    ['Vedam Anuvanuvuna Nadam', 'Sagara Sangamam'],
    ['Sankara Naada Sareera Paraa', 'Sankarabharanam'],
    ['Omkara Naadanu', 'Sankarabharanam'],
    ['Whattey Beauty', 'Bheeshma'],
    ['Chamkeela Angeelesi', 'Dasara'],
    ['Saranga Dariya', 'Love Story'],
    ['Ooru Palletooru', 'Balagam'],
    ['Kalaavathi', 'Sarkaru Vaari Paata'],
    ['Ma Ma Mahesha', 'Sarkaru Vaari Paata'],
    ['Lala Bheemla', 'Bheemla Nayak'],
    ['Bhairava Anthem', 'Kalki 2898 AD'],
    ['Priyathama Priyathama', 'Majili'],
    ['Madhurame', 'Arjun Reddy'],
    ['A Ante Amalapuram', 'Arya'],
    ['Ringa Ringa', 'Arya 2'],
    ['Dheera Dheera', 'Magadheera'],
    ['Panchadara Bomma', 'Magadheera'],
    ['Jorsuga Husharuga', 'Magadheera'],
    ['Bangaru Kodipetta', 'Magadheera'],
    ['Pacha Bottesina', 'Baahubali: The Beginning'],
    ['Manohari', 'Baahubali: The Beginning'],
    ['Dandalayya', 'Baahubali: The Beginning'],
    ['Saahore Baahubali', 'Baahubali 2: The Conclusion'],
    ['Hamsa Naava', 'Baahubali 2: The Conclusion'],
    ['Kanna Nidurinchara', 'Baahubali 2: The Conclusion'],
    ['Bommani Geesthe', 'Bommarillu'],
    ['Nammaka Thappani', 'Bommarillu'],
    ['Cheppave Chirugali', 'Okkadu'],
    ['Aaradugula Bullet', 'Attarintiki Daredi'],
    ['Kaatama Rayuda', 'Attarintiki Daredi'],
    ['Kevvu Keka', 'Gabbar Singh'],
    ['Akasam Ammayiaite', 'Gabbar Singh'],
    ['Cinema Chupista Mama', 'Race Gurram'],
    ['Ammadu Lets Do Kummudu', 'Khaidi No. 150'],
    ['Vaana Vaana Velluvaye', 'Gang Leader'],
    ['Abbanee Tiyyani Debba', 'Jagadeka Veerudu Athiloka Sundari'],
    ['Vachinde', 'Fidaa'],
    ['Seeti Maar', 'DJ: Duvvada Jagannadham'],
    ['Ninnila Ninnila', 'Tholi Prema'],
    ['Telusa Telusa', 'Sarrainodu'],
    ['Blockbuster', 'Sarrainodu'],
    ['Top Lechipoddi', 'Iddarammayilatho'],
    ['Pimple Dimple', 'Yevadu'],
    ['Girra Girra', 'F2: Fun and Frustration'],
    ['Naa Pedavulu Nuvvaithe', 'Ready'],
    ['O Manmadhuda', 'King'],
    ['Aakasam Badhalaina', 'Perfect'],
    ['Chinni Chinni Aasa', 'Roja'],
    ['Gala Gala', 'Pokiri'],
    ['Samayama', 'Hi Nanna'],
    ['Chitti', 'Jathi Ratnalu'],
    ['Bhoom Bhaddhal', 'Krack'],
    ['Maguva Maguva', 'Vakeel Saab'],
    ['Chikiri Chikiri', 'Peddi'],
    ['Aaya Sher', 'The Paradise'],
    ['Rubaroo', 'Dacoit'],
    ['Collar Ey Etthara', 'Ustaad Bhagat Singh'],
]


# ---------------- video lookup ----------------
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _dice(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ga = [a[i:i + 2] for i in range(len(a) - 1)]
    gb = [b[i:i + 2] for i in range(len(b) - 1)]
    pool, hit = list(gb), 0
    for g in ga:
        if g in pool:
            pool.remove(g)
            hit += 1
    return 2 * hit / (len(ga) + len(gb)) if (ga or gb) else 0.0


_BAD = re.compile(r"\b(cover|remix|reaction|karaoke|instrumental|ringtone|status|shorts|trailer|teaser|making|mashup|slowed|reverb|8d|dance tutorial)\b", re.I)
_GOOD = re.compile(r"video song|lyrical|full song|audio|official", re.I)


def _pick(items, title, film):
    """Choose the most likely official upload from YouTube search results."""
    best, best_score = "", -9.0
    for it in items:
        vid = (it.get("id") or {}).get("videoId")
        name = (it.get("snippet") or {}).get("title", "")
        if not vid:
            continue
        score = 1.0 if _norm(title) in _norm(name) else _dice(name, title)
        if len(_norm(film)) >= 3 and _norm(film)[:5] in _norm(name):
            score += 0.3
        if _GOOD.search(name):
            score += 0.2
        if _BAD.search(name):
            score -= 0.8
        if score > best_score:
            best, best_score = vid, score
    return best


_cache, _lock = {}, threading.Lock()
try:
    with open(CACHE_FILE, encoding="utf-8") as f:
        _cache.update(json.load(f))
except Exception:
    pass


def _save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def clip(i: int) -> str:
    """Return a YouTube video ID for song number i, or 'ERR:reason'."""
    try:
        song = SONGS[int(i)]
    except Exception:
        return "ERR:unknown song"
    title, film = song[0], song[1]
    if len(song) > 2 and song[2]:
        return song[2]
    key = title + "|" + film
    with _lock:
        if key in _cache:
            return _cache[key]
    if not YT_KEY:
        return "ERR:the server has no YOUTUBE_API_KEY set"
    try:
        r = httpx.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet", "type": "video", "maxResults": 8,
                "videoEmbeddable": "true", "videoSyndicated": "true",
                "regionCode": "IN", "q": f"{title} {film} video song", "key": YT_KEY,
            },
            timeout=10,
        )
    except Exception:
        return "ERR:could not reach YouTube"
    if r.status_code != 200:
        if r.status_code == 403:
            return "ERR:YouTube quota is used up for today, try again tomorrow"
        return f"ERR:YouTube API error {r.status_code}"
    vid = _pick(r.json().get("items", []), title, film)
    with _lock:
        _cache[key] = vid
        _save_cache()
    return vid


# ---------------- page ----------------
CSS = r"""/* palette: black + white, in the spirit of GitHub / X dark mode */
:root{
  color-scheme:dark;
  --bg:#000000; --surface:#16181C; --surface2:#202327; --line:#2F3336;
  --text:#E7E9EA; --muted:#8B949E;
  --accent:#EFF3F4; --on-accent:#0F1419; --accent-soft:#EFF3F4; --accent-ink:#0F1419;
  --focus:#1D9BF0; --good:#00BA7C; --bad:#F4212E;
}
body,.gradio-container,.gradio-container .main,.gradio-container .wrap{background:var(--bg) !important}
footer{display:none !important}
.gradio-container{padding:0 !important;max-width:none !important}
.block,.gradio-container .block{background:transparent !important;border:none !important;box-shadow:none !important;padding:0 !important}

#sl{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,'Anek Telugu',sans-serif;
  color:var(--text);width:100%;max-width:480px;margin:0 auto;padding:40px 20px 64px;
  box-sizing:border-box;font-size:16px;line-height:1.4;

  header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:28px}
  h1{margin:0;font-size:24px;font-weight:700;letter-spacing:-.01em;color:var(--text);text-wrap:balance}
  .sub{margin:4px 0 0;color:var(--muted);font-size:14px}
  .modes{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:2px;flex:none}
  .modes button{background:none;border:0;color:var(--muted);padding:6px 12px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;border-radius:999px}
  .modes button:hover{color:var(--text)}
  .modes button[aria-pressed=true]{background:var(--accent);color:var(--on-accent)}
  button:focus-visible,input:focus-visible{outline:2px solid var(--focus);outline-offset:2px}

  .ytbox{position:relative;width:200px;height:200px;margin:0 auto 24px;border-radius:16px;overflow:hidden;background:var(--surface);border:1px solid var(--line)}
  .ytbox iframe,.ytbox #ytp{width:198px;height:198px;display:block;border:0}
  .cover{position:absolute;inset:0;background:var(--surface);display:grid;place-items:center;font-size:64px;font-weight:300;color:var(--text);transition:opacity .5s}
  .cover.lift{opacity:0;pointer-events:none}

  .strip{position:relative;display:flex;gap:3px;height:34px;margin:0 0 18px}
  .seg{position:relative;border-radius:6px;background:var(--surface);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:var(--muted);overflow:hidden;transition:background .25s,color .25s}
  .seg.open{background:var(--accent-soft);border-color:var(--accent-soft);color:var(--accent-ink)}
  .head{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--focus);border-radius:2px;left:0;pointer-events:none}

  .row{display:flex;align-items:center;gap:14px;margin-bottom:20px}
  #play{width:52px;height:52px;border-radius:50%;border:0;background:var(--accent);color:var(--on-accent);font-size:18px;cursor:pointer;flex:none;display:grid;place-items:center;transition:transform .1s,opacity .2s}
  #play:hover:not(:disabled){opacity:.9}
  #play:disabled{opacity:.3;cursor:not-allowed}
  #play:active:not(:disabled){transform:scale(.95)}
  .status{font-size:15px;line-height:1.35}
  .status small{display:block;color:var(--muted);font-size:13px;margin-top:2px}

  .guessbox{position:relative;display:flex;gap:8px;margin-bottom:8px}
  #q{flex:1;min-width:0;background:var(--bg);border:1px solid var(--line);color:var(--text);padding:12px 14px;border-radius:12px;font:inherit;font-size:16px}
  #q::placeholder{color:var(--muted)}
  #q:focus{border-color:var(--focus)}
  .btn{background:transparent;border:1px solid var(--line);color:var(--text);border-radius:12px;padding:0 16px;font:inherit;font-weight:600;cursor:pointer}
  .btn:hover:not(:disabled){background:var(--surface)}
  .btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
  .btn.primary:hover:not(:disabled){background:var(--accent);opacity:.9}
  .btn:disabled{opacity:.3;cursor:not-allowed}
  #list{position:absolute;left:0;right:0;top:100%;z-index:5;margin:6px 0 0;padding:4px;list-style:none;background:var(--bg);border:1px solid var(--line);border-radius:12px;max-height:260px;overflow:auto;display:none;box-shadow:0 8px 28px rgba(255,255,255,.08)}
  #list li{padding:9px 10px;border-radius:8px;cursor:pointer;display:flex;justify-content:space-between;gap:10px;font-size:15px}
  #list li span{color:var(--muted);font-size:13px;text-align:right}
  #list li[aria-selected=true],#list li:hover{background:var(--surface)}
  .skiprow{display:flex;justify-content:space-between;color:var(--muted);font-size:13px;margin-bottom:20px}
  .skiprow button{background:none;border:0;color:var(--text);font:inherit;font-weight:600;cursor:pointer;padding:0;text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--line)}
  .skiprow button:disabled{opacity:.3;cursor:not-allowed}

  ol{list-style:none;margin:0 0 24px;padding:0}
  ol li{min-height:42px;padding:10px 4px;display:flex;align-items:center;gap:12px;color:var(--muted);border-bottom:1px solid var(--line);font-size:15px}
  ol li b{width:18px;text-align:center;flex:none;font-weight:700}
  ol li.wrong{color:var(--text)} ol li.wrong b{color:var(--bad)}
  ol li.skip b{color:var(--muted)}
  ol li.right{color:var(--text);font-weight:600} ol li.right b{color:var(--good)}

  .result{display:none;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px}
  .result.show{display:block}
  .result h2{margin:0 0 2px;font-size:20px;font-weight:700}
  .result p{margin:0 0 14px;color:var(--muted);font-size:14px}
  .result .acts{display:flex;gap:8px;flex-wrap:wrap}
  .result .btn{padding:9px 14px;text-decoration:none;display:inline-block;font-size:14px}
  .result .btn.primary{color:var(--on-accent)}
  .foot{margin-top:28px;color:var(--muted);font-size:12px;line-height:1.5}
  .credit{margin:10px 0 0;color:var(--muted);font-size:12px;opacity:.6}
}
#sl *{box-sizing:border-box}
@media (prefers-reduced-motion:reduce){#sl *{transition:none !important}}
"""

HEAD = r"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anek+Telugu:wght@300..800&display=swap" rel="stylesheet">
<script>
(function(){
function main(){

/* ---------- Song list: [title, film, optionalPreviewUrl] ----------
   Add songs by adding a line. Titles are transliterated, so the matcher
   is fuzzy. If a song picks the wrong audio, paste a 30s preview URL as
   the third item and it will be used directly. */
const SONGS = __SONGS__;

/* ---------- constants ---------- */
const STEPS = [1,2,4,7,11,16];        // seconds unlocked per attempt
const MAX = STEPS.length;
const $ = id => document.querySelector('#sl [id="'+id+'"]');
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g,'');
const bigrams = s => { const o=new Map(); for(let i=0;i<s.length-1;i++){const b=s.slice(i,i+2); o.set(b,(o.get(b)||0)+1);} return o; };
function dice(a,b){
  a=norm(a); b=norm(b); if(!a||!b) return 0; if(a===b) return 1;
  const A=bigrams(a), B=bigrams(b); let hit=0, tot=0;
  A.forEach((n,k)=>{tot+=n; if(B.has(k)) hit+=Math.min(n,B.get(k));}); B.forEach(n=>tot+=n);
  return tot? 2*hit/tot : 0;
}

/* ---------- state ---------- */
let mode='daily', target=-1, clip=null, attempt=0, guesses=[], done=false, won=false, raf=0, stopAt=0;
const clipCache = new Map();
let sel=-1, hi=-1, matches=[];

/* ---------- storage (safe) ---------- */
const store = {
  get(k){ try{ return JSON.parse(localStorage.getItem(k)); }catch(e){ return null; } },
  set(k,v){ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} }
};
const todayKey = () => { const d=new Date(); return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate(); };
const dayNumber = () => { const d=new Date(); return Math.floor(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())/864e5); };

/* ---------- YouTube player + video lookup (server finds the video) ---------- */
const START_SEC = 0;   // seconds into each video where the clip starts
let yt=null, ytReady=null, cueRes=null, cueRej=null, waiting=false, playing=false, wallStart=0;
const idCache = new Map();

function onYtState(e){
  if(e.data===5 && cueRes){ const r=cueRes; cueRes=null; cueRej=null; r(); }
  else if(e.data===1 && waiting){ waiting=false; wallStart=performance.now(); startTick(); }
  else if(e.data===1 && !waiting && !playing){ hardPause(); }   // YouTube resumed on its own: shut it up
  else if(e.data===0 && playing){ stop(); }
}
function onYtError(e){
  if(cueRej){ const r=cueRej; cueRes=null; cueRej=null; r(new Error('embed '+e.data)); }
  else { stop(); setStatus('This video will not play here.','Press Skip, or start a new round.'); }
}
function loadYouTube(){
  if(ytReady) return ytReady;
  ytReady = new Promise((resolve,reject)=>{
    const t=setTimeout(()=>reject(new Error('YouTube player did not load')),15000);
    window.onYouTubeIframeAPIReady = () => {
      yt = new YT.Player($('ytp'), {width:200, height:200,
        playerVars:{playsinline:1, controls:0, disablekb:1, rel:0, modestbranding:1, iv_load_policy:3},
        events:{ onReady:()=>{ clearTimeout(t); resolve(true); }, onStateChange:onYtState, onError:onYtError }});
    };
    const s=document.createElement('script'); s.src='https://www.youtube.com/iframe_api';
    s.onerror=()=>{ clearTimeout(t); reject(new Error('could not load YouTube')); };
    document.head.appendChild(s);
  });
  return ytReady;
}
function ytCue(id){
  return new Promise((res,rej)=>{
    cueRes=res; cueRej=rej;
    yt.cueVideoById({videoId:id, startSeconds:START_SEC});
    setTimeout(()=>{ if(cueRej){ const r=cueRej; cueRes=null; cueRej=null; r(new Error('cue timeout')); } }, 7000);
  });
}
async function resolveId(i){
  const r = await fetch('/gradio_api/call/clip', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({data:[i]})});
  if(!r.ok) throw new Error('server '+r.status);
  const {event_id} = await r.json();
  const txt = await (await fetch('/gradio_api/call/clip/'+event_id)).text();
  const m = txt.match(/event: complete\s*\r?\ndata: (.*)/);
  if(!m) throw new Error('video lookup failed');
  const v = JSON.parse(m[1])[0];
  if(typeof v==='string' && v.startsWith('ERR:')) throw new Error(v.slice(4));
  return v;
}
async function findClip(i){
  await loadYouTube();
  let id = idCache.get(i);
  if(id===undefined){ id = await resolveId(i); idCache.set(i,id); }
  if(!id) return null;
  try{ await ytCue(id); }catch(e){ idCache.set(i,''); return null; }
  return {id};
}

/* ---------- UI helpers ---------- */
function buildStrip(){
  const s=$('strip'); s.innerHTML='';
  let prev=0;
  STEPS.forEach((t,i)=>{
    const d=document.createElement('div'); d.className='seg'; d.style.flex=(t-prev)+' 1 0'; d.textContent=t+'s'; d.dataset.i=i; s.appendChild(d); prev=t;
  });
  const h=document.createElement('div'); h.className='head'; h.id='head'; s.appendChild(h);
}
function paintStrip(){
  document.querySelectorAll('.seg').forEach(el=>{
    const i=+el.dataset.i;
    el.classList.toggle('open', done || i<=attempt);
    el.classList.toggle('next', !done && i===attempt+1);
  });
}
function paintGuesses(){
  const ol=$('guesses'); ol.innerHTML='';
  for(let i=0;i<MAX;i++){
    const li=document.createElement('li'); const g=guesses[i];
    if(g){
      if(g.type==='skip'){ li.className='skip'; li.innerHTML='<b>–</b>Skipped'; }
      else if(g.type==='right'){ li.className='right'; li.innerHTML='<b>✓</b>'; li.append(SONGS[g.i][0]+' · '+SONGS[g.i][1]); }
      else { li.className='wrong'; li.innerHTML='<b>✕</b>'; li.append(SONGS[g.i][0]+' · '+SONGS[g.i][1]); }
    } else { li.innerHTML='<b></b>'; }
    ol.appendChild(li);
  }
  $('tries').textContent = done ? (won?'Solved in '+guesses.length:'Out of guesses') : 'Guess '+(attempt+1)+' of '+MAX;
  const nextStep = STEPS[Math.min(attempt+1,MAX-1)]-STEPS[attempt];
  $('skip').textContent = 'Skip (+'+nextStep+'s)';
  $('skip').disabled = done || !clip;
}
function setStatus(main, small){ $('status').innerHTML = main + (small?'<small>'+small+'</small>':''); }
function setEnabled(on){ $('play').disabled=!on; $('q').disabled=!on; $('guess').disabled=!on; }

/* ---------- playback ---------- */
const LEAD = 0.2;   // cut a touch early: YouTube keeps sounding ~0.2s after pauseVideo
let pauseTimer=0, guardTimer=0, beginTok=0;
const wallElapsed = () => (performance.now()-wallStart)/1000;
function mediaElapsed(){
  try{ const t=yt.getCurrentTime()-START_SEC; return isFinite(t)?Math.max(0,t):wallElapsed(); }
  catch(e){ return wallElapsed(); }
}
// YouTube can ignore a pause that arrives while buffering, so keep re-pausing until it sticks.
function hardPause(){
  if(!yt) return;
  try{ yt.pauseVideo(); }catch(e){}
  clearInterval(pauseTimer);
  let n=0;
  pauseTimer=setInterval(()=>{
    if(playing || waiting || ++n>20){ clearInterval(pauseTimer); return; }   // a new clip took over, or give up
    let s=-1; try{ s=yt.getPlayerState(); }catch(e){}
    if(s===1 || s===3){ try{ yt.pauseVideo(); }catch(e){} } else { clearInterval(pauseTimer); }
  }, 100);
}
function stop(){
  playing=false; waiting=false;
  cancelAnimationFrame(raf); clearInterval(guardTimer);
  $('play').textContent='▶';
  hardPause();
}
function startTick(){
  playing=true; $('play').textContent='■';
  cancelAnimationFrame(raf); clearInterval(guardTimer);
  guardTimer=setInterval(guard, 40);
  raf=requestAnimationFrame(tick);
}
// Stop on the player's real position, not a wall clock, so buffering stalls and seek lag cannot stretch the clip.
function guard(){
  if(!playing) return;
  const w=wallElapsed(), m=mediaElapsed();
  if((w>=0.3 && m>=stopAt-LEAD) || w>=stopAt+3){ stop(); }   // w>=0.3 ignores a stale position right after a seek
}
function tick(){
  if(!playing) return;
  const total = done ? 30 : STEPS[MAX-1];
  $('head').style.left = Math.min(100, mediaElapsed()/total*100)+'%';
  raf=requestAnimationFrame(tick);
}
async function begin(limitSec){
  stopAt=limitSec; waiting=true;
  const tok=++beginTok;
  try{ yt.seekTo(START_SEC, true); yt.playVideo(); }catch(e){ waiting=false; throw e; }
  setTimeout(()=>{ if(waiting && tok===beginTok){ waiting=false; setStatus('Audio did not start.','Tap play again.'); } }, 5000);
}
function play(){ if(!clip) return; stop(); begin(done?9999:STEPS[attempt]).catch(e=>setStatus('Could not start playback.', String(e.message||e))); }
// timers are unreliable in background tabs, so never keep a clip playing there
document.addEventListener('visibilitychange', ()=>{ if(document.hidden && (playing||waiting)) stop(); });
$('play').onclick=()=>{ if(playing) stop(); else play(); };


/* ---------- search box ---------- */
function renderList(){
  const q=norm($('q').value); const ul=$('list');
  if(!q){ ul.style.display='none'; $('q').setAttribute('aria-expanded','false'); matches=[]; return; }
  matches=[];
  SONGS.forEach((s,i)=>{ if(norm(s[0]).includes(q)||norm(s[1]).includes(q)) matches.push(i); });
  matches=matches.slice(0,40); hi=matches.length?0:-1;
  ul.innerHTML='';
  matches.forEach((i,k)=>{
    const li=document.createElement('li'); li.setAttribute('role','option'); li.setAttribute('aria-selected',k===hi);
    li.innerHTML='<div></div><span></span>'; li.firstChild.textContent=SONGS[i][0]; li.lastChild.textContent=SONGS[i][1];
    li.onmousedown=e=>{ e.preventDefault(); choose(i); };
    ul.appendChild(li);
  });
  ul.style.display=matches.length?'block':'none';
  $('q').setAttribute('aria-expanded',matches.length?'true':'false');
}
function choose(i){ sel=i; $('q').value=SONGS[i][0]+' · '+SONGS[i][1]; $('list').style.display='none'; $('q').setAttribute('aria-expanded','false'); }
$('q').addEventListener('input',()=>{ sel=-1; renderList(); });
$('q').addEventListener('keydown',e=>{
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    if(!matches.length) return; e.preventDefault();
    hi=(hi+(e.key==='ArrowDown'?1:-1)+matches.length)%matches.length;
    [...$('list').children].forEach((li,k)=>li.setAttribute('aria-selected',k===hi));
    $('list').children[hi].scrollIntoView({block:'nearest'});
  } else if(e.key==='Enter'){
    e.preventDefault();
    if(sel<0 && matches.length && hi>=0) choose(matches[hi]);
    else submit();
  } else if(e.key==='Escape'){ $('list').style.display='none'; }
});
$('q').addEventListener('blur',()=>setTimeout(()=>{$('list').style.display='none';},120));

/* ---------- game flow ---------- */
function submit(){
  if(done||sel<0) { if(!done) setStatus('Pick a song from the list.'); return; }
  const right = sel===target;
  guesses.push({type: right?'right':'wrong', i:sel});
  sel=-1; $('q').value='';
  if(right){ finish(true); } else advance();
}
function skip(){ if(done) return; guesses.push({type:'skip'}); advance(); }
function advance(){
  if(attempt>=MAX-1){ finish(false); return; }
  attempt++; paintStrip(); paintGuesses(); persist();
  setStatus('Wrong. Clip is now '+STEPS[attempt]+' seconds.', attempt>=3?'Film hint: '+SONGS[target][1]:'');
  play();
}
function finish(w){
  done=true; won=w; stop(); paintStrip(); paintGuesses(); persist(); recordStats();
  const [t,f]=SONGS[target];
  $('r-title').textContent = w ? 'Got it' : 'It was '+t;
  $('r-sub').textContent = t+' · '+f;
  $('r-yt').href='https://www.youtube.com/results?search_query='+encodeURIComponent(t+' '+f+' song');
  $('result').classList.add('show'); $('cover').classList.add('lift');
  $('q').disabled=true; $('guess').disabled=true;
  setStatus(w?'Solved on guess '+guesses.length+'.':'Out of guesses.', 'The video is revealed. Play the full song below.');
}
function persist(){
  if(mode!=='daily') return;
  store.set('slt_daily_'+todayKey(),{guesses,attempt,done,won});
}
function recordStats(){
  if(mode!=='daily') return;
  const k='slt_stats'; const s=store.get(k)||{played:0,won:0,streak:0,last:''};
  const today=todayKey(); if(s.last===today){ return; }
  s.played++; if(won){ s.won++; s.streak++; } else s.streak=0; s.last=today; store.set(k,s); showStats();
}
function showStats(){
  const s=store.get('slt_stats'); const n=SONGS.length;
  $('foot').textContent = (s? 'Daily: played '+s.played+', won '+s.won+', streak '+s.streak+'. ' : '') + n+' songs. Audio comes from YouTube videos picked automatically; a song with no playable video is skipped.';
}

async function startRound(){
  stop(); done=false; won=false; attempt=0; guesses=[]; clip=null; sel=-1;
  $('result').classList.remove('show'); $('cover').classList.remove('lift'); $('q').value=''; setEnabled(false);
  setStatus('Finding a clip…'); paintStrip(); paintGuesses();
  const N=SONGS.length;
  let idx = mode==='daily' ? (Math.imul(dayNumber(),2654435761)>>>0)%N : Math.floor(Math.random()*N);
  try{
    for(let tries=0; tries<8; tries++){
      const c=await findClip(idx);
      if(c){ target=idx; clip=c; break; }
      idx=(idx+1)%N;
    }
  }catch(e){
    setStatus('Could not load a song.', 'Details: '+(e&&e.message||'unknown')+'.');
    return;
  }
  if(!clip){ setStatus('No playable clips found.','Try Random mode or reload.'); return; }
  
  const saved = mode==='daily' ? store.get('slt_daily_'+todayKey()) : null;
  if(saved){ guesses=saved.guesses; attempt=saved.attempt; done=saved.done; won=saved.won; }
  setEnabled(true); paintStrip(); paintGuesses();
  if(done){ finishRestore(); return; }
  setStatus('Press play to hear '+STEPS[attempt]+' second'+(STEPS[attempt]>1?'s':'')+'.', mode==='daily'?'Same song for everyone today.':'');
}
function finishRestore(){
  const [t,f]=SONGS[target];
  $('r-title').textContent = won ? 'Got it' : 'It was '+t; $('r-sub').textContent=t+' · '+f;
  $('r-yt').href='https://www.youtube.com/results?search_query='+encodeURIComponent(t+' '+f+' song');
  $('result').classList.add('show'); $('cover').classList.add('lift'); $('q').disabled=true; $('guess').disabled=true;
  setStatus('Today\u2019s song is done.','Come back tomorrow, or try Random.');
}

$('guess').onclick=submit; $('skip').onclick=skip;
$('r-play').onclick=()=>{ stop(); begin(9999).catch(()=>{}); };
$('r-next').onclick=()=>{ setMode('random'); };
$('r-share').onclick=()=>{
  const marks=guesses.map(g=>g.type==='right'?'🟩':g.type==='skip'?'⬛':'🟥').join('')+'⬜'.repeat(MAX-guesses.length);
  const txt='PaataGuess '+(mode==='daily'?todayKey():'(random)')+'\n'+marks;
  (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject()).then(()=>{$('r-share').textContent='Copied';setTimeout(()=>$('r-share').textContent='Copy result',1500);}).catch(()=>prompt('Copy your result',txt));
};
function setMode(m){
  mode=m; $('m-daily').setAttribute('aria-pressed',m==='daily'); $('m-random').setAttribute('aria-pressed',m==='random'); startRound();
}
$('m-daily').onclick=()=>setMode('daily'); $('m-random').onclick=()=>setMode('random');

async function boot(){ buildStrip(); showStats(); startRound(); }
boot();
}
// Gradio draws the page after this script runs, so wait for the game markup before starting.
const waitForUi = setInterval(()=>{
  if(document.querySelector('#sl [id="strip"]') && document.querySelector('#sl [id="play"]')){ clearInterval(waitForUi); main(); }
}, 100);
})();
</script>""".replace("__SONGS__", json.dumps(SONGS, ensure_ascii=False))

BODY = r"""<div id="sl">
  <header>
    <div>
      <h1>Telugu paatani guess cheyyi</h1>
      <p class="sub">తెలుగు పాట · guess the song from a few seconds</p>
    </div>
    <div class="modes" role="group" aria-label="Game mode">
      <button id="m-daily" aria-pressed="true">Daily</button>
      <button id="m-random" aria-pressed="false">Random</button>
    </div>
  </header>

  <div class="ytbox"><div id="ytp"></div><div class="cover" id="cover" aria-hidden="true"><span>?</span></div></div>
  <div class="strip" id="strip" aria-hidden="true"></div>

  <div class="row">
    <button id="play" aria-label="Play clip" disabled>▶</button>
    <div class="status" id="status" aria-live="polite">Finding a song…</div>
  </div>

  <div class="guessbox">
    <input id="q" type="text" placeholder="Search a song or film" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="list" disabled>
    <button class="btn primary" id="guess" disabled>Guess</button>
    <ul id="list" role="listbox"></ul>
  </div>
  <div class="skiprow">
    <span id="tries">Guess 1 of 6</span>
    <button id="skip" disabled>Skip (+1s)</button>
  </div>

  <ol id="guesses"></ol>

  <section class="result" id="result" aria-live="polite">
    <h2 id="r-title"></h2>
    <p id="r-sub"></p>
    <div class="acts">
      <button class="btn" id="r-play">Play full preview</button>
      <a class="btn" id="r-yt" target="_blank" rel="noopener">Find on YouTube</a>
      <button class="btn" id="r-share">Copy result</button>
      <button class="btn primary" id="r-next">Play another</button>
    </div>
  </section>

  <p class="foot" id="foot"></p>
  <p class="credit">built by Abhiram</p>
</div>"""

# Gradio 5 takes css/head on Blocks(); Gradio 6 takes them on launch(). Support both.
_blocks_params = inspect.signature(gr.Blocks.__init__).parameters
_opts = {"css": CSS, "head": HEAD}
_blocks_kw = {k: v for k, v in _opts.items() if k in _blocks_params}
_launch_kw = {k: v for k, v in _opts.items() if k not in _blocks_params}

with gr.Blocks(title="PaataGuess", **_blocks_kw) as demo:
    gr.HTML(BODY)
    gr.api(clip, api_name="clip", api_visibility="undocumented")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        **_launch_kw,
    )
