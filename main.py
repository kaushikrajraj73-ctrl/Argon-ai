import os, json, time, base64, asyncio, tempfile
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

app = FastAPI(title="ARGON AI V7000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

INDEX_HTML = """<!DOCTYPE html>
<html lang="hi"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARGON AI V7000</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<style>
:root{--bg:#0a0b10;--bg-2:#12141c;--bg-3:#1a1d28;--bd:#252936;--tx:#e8eaf0;--tx2:#8b8fa3;--gd:linear-gradient(135deg,#7c9cff,#a855f7);--ub:#2a3050;--ab:#14171f}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden}
body{font-family:sans-serif;background:var(--bg);color:var(--tx);display:flex}
.sb{width:250px;background:var(--bg-2);border-right:1px solid var(--bd);display:flex;flex-direction:column;padding:16px 12px;flex-shrink:0}
.lg{font-weight:700;font-size:18px;background:var(--gd);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.ni{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;font-size:14px;color:var(--tx2);background:none;border:none;cursor:pointer;width:100%;text-align:left;transition:0.2s}
.ni.active, .ni:hover{background:var(--bg-3);color:var(--tx)}
.mn{flex:1;display:flex;flex-direction:column;min-width:0}
.hd{height:60px;display:flex;align-items:center;padding:0 20px;border-bottom:1px solid var(--bd);background:var(--bg-2)}
.ct{flex:1;overflow-y:auto;position:relative}
.vw{display:none;height:100%;flex-direction:column;padding:20px}.vw.active{display:flex}
.cs{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:12px;margin-bottom:15px}
.mr{display:flex;gap:10px;max-width:85%}
.mr.user{align-self:flex-end;flex-direction:row-reverse}
.mr.ai{align-self:flex-start}
.mbb{padding:12px 16px;border-radius:14px;font-size:14px;line-height:1.5}
.mr.user .mbb{background:var(--ub)}
.mr.ai .mbb{background:var(--ab);border:1px solid var(--bd)}
.cw{padding:16px;background:var(--bg-2);border-top:1px solid var(--bd);display:flex;gap:10px}
input, textarea{width:100%;background:var(--bg);border:1px solid var(--bd);color:#fff;padding:12px;border-radius:8px;outline:none}
button.send-btn{background:var(--gd);color:#fff;border:none;padding:12px 24px;border-radius:8px;font-weight:600;cursor:pointer}
.vo{width:130px;height:130px;border-radius:50%;background:var(--gd);display:flex;align-items:center;justify-content:center;font-size:45px;color:#fff;margin:30px auto;cursor:pointer;transition:transform 0.2s}
.vo.recording{animation:pulse 1.2s infinite;background:#ff0055}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,0,85,0.7)}70%{box-shadow:0 0 0 25px rgba(255,0,85,0)}100%{box-shadow:0 0 0 0 rgba(255,0,85,0)}}
.movie-box{background:var(--bg-2);border:1px solid var(--bd);padding:20px;border-radius:12px;margin-top:15px;line-height:1.6}
</style></head><body>
<aside class="sb">
  <div class="lg">ARGON AI V7000</div>
  <button class="ni active" onclick="switchTab('chat')">💬 चैट</button>
  <button class="ni" onclick="switchTab('image')">🎨 इमेज जनरेटर</button>
  <button class="ni" onclick="switchTab('movie')">🎬 मूवी फैक्ट्री</button>
  <button class="ni" onclick="switchTab('voice')">🎙️ लाइव वॉइस</button>
</aside>
<div class="mn">
  <div class="hd"><h3 id="tabTitle">ARGON चैट</h3></div>
  <div class="ct">
    <!-- CHAT VIEW -->
    <div class="vw active" id="vw-chat" style="padding:0;">
      <div class="cs" id="chatArea" style="padding:20px;">
        <div class="mr ai"><div class="mbb">नमस्ते! मैं ARGON AI हूँ (Architected by Kaushik Raj)। क्या सहायता करूँ?</div></div>
      </div>
      <div class="cw">
        <input type="text" id="chatInput" placeholder="संदेश लिखें..." onkeydown="if(event.key==='Enter')sendChat()">
        <button class="send-btn" onclick="sendChat()">भेजें</button>
      </div>
    </div>

    <!-- IMAGE VIEW -->
    <div class="vw" id="vw-image">
      <h3>🎨 AI इमेज स्टूडियो</h3>
      <textarea id="imgPrompt" rows="3" style="margin-top:10px;" placeholder="कैसी तस्वीर चाहिए? प्रॉम्प्ट लिखें (उदा: A futuristic cyberpunk sports car in neon city)"></textarea>
      <button class="send-btn" style="margin-top:10px;align-self:flex-start;" onclick="genImg()">✨ इमेज बनाएं</button>
      <div id="imgOut" style="margin-top:20px;display:flex;justify-content:center;"></div>
    </div>

    <!-- MOVIE VIEW -->
    <div class="vw" id="vw-movie">
      <h3>🎬 मूवी फैक्ट्री (AI 3-Scene Screenplay & Director)</h3>
      <textarea id="movieTopic" rows="2" style="margin-top:10px;" placeholder="मूवी का विषय लिखें (उदा: AI takeover in 2050)"></textarea>
      <button class="send-btn" style="margin-top:10px;align-self:flex-start;" onclick="genMovie()">🎬 मूवी तैयार करें</button>
      <div id="movieOut" class="movie-box" style="display:none;"></div>
    </div>

    <!-- VOICE VIEW -->
    <div class="vw" id="vw-voice" style="text-align:center;">
      <div class="vo" id="voiceOrb" onclick="toggleVoice()">🎙️</div>
      <h3 id="voiceStatus">माइक पर क्लिक करें और बोलें</h3>
      <p id="voiceSub" style="color:var(--tx2);margin-top:8px;">ARGON AI आपकी आवाज़ सुनेगा और बोलकर जवाब देगा</p>
      <audio id="audioPlayer" autoplay style="display:none;"></audio>
    </div>
  </div>
</div>

<script>
function switchTab(t){
  document.querySelectorAll('.vw').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.ni').forEach(n=>n.classList.remove('active'));
  document.getElementById('vw-'+t).classList.add('active');
  event.target.classList.add('active');
  const titles={chat:'ARGON चैट',image:'🎨 AI इमेज स्टूडियो',movie:'🎬 मूवी फैक्ट्री',voice:'🎙️ लाइव वॉइस मोड'};
  document.getElementById('tabTitle').innerText = titles[t];
}

async function sendChat(){
  const inp=document.getElementById('chatInput'), msg=inp.value.trim(), box=document.getElementById('chatArea');
  if(!msg)return;
  box.innerHTML+=`<div class="mr user"><div class="mbb">${msg}</div></div>`;
  inp.value='';
  box.scrollTop=box.scrollHeight;
  const aiBox=document.createElement('div');
  aiBox.className='mr ai';
  aiBox.innerHTML=`<div class="mbb">⏳ सोच रहा हूँ...</div>`;
  box.appendChild(aiBox);
  box.scrollTop=box.scrollHeight;
  try{
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const d=await res.json();
    aiBox.querySelector('.mbb').innerHTML=marked.parse(d.answer||d.detail||'कोई उत्तर नहीं मिला');
  }catch(e){aiBox.querySelector('.mbb').innerText='त्रुटि: '+e.message;}
  box.scrollTop=box.scrollHeight;
}

async function genImg(){
  const p=document.getElementById('imgPrompt').value.trim(), out=document.getElementById('imgOut');
  if(!p)return;
  out.innerHTML='<p style="color:var(--ac);">⏳ इमेज जनरेट हो रही है...</p>';
  try{
    const res=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
    const d=await res.json();
    if(d.image_url){
      out.innerHTML=`<img src="${d.image_url}" style="max-width:100%;max-height:480px;border-radius:12px;border:1px solid var(--bd);box-shadow:0 0 20px rgba(0,0,0,0.6);">`;
    }else{
      out.innerHTML='<p style="color:#ff5555;">इमेज नहीं बन सकी: '+(d.detail||'कृपया पुनः प्रयास करें')+'</p>';
    }
  }catch(e){out.innerHTML='<p style="color:#ff5555;">त्रुटि: '+e.message+'</p>';}
}

async function genMovie(){
  const t=document.getElementById('movieTopic').value.trim(), out=document.getElementById('movieOut');
  if(!t)return;
  out.style.display='block';
  out.innerHTML='⏳ मूवी स्क्रिप्ट, सीन्स और वॉइसओवर तैयार हो रहे हैं...';
  try{
    const res=await fetch('/api/movie',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:t})});
    const d=await res.json();
    out.innerHTML=marked.parse(d.screenplay);
    if(d.audio_base64){
      const player=document.getElementById('audioPlayer');
      player.src="data:audio/mp3;base64,"+d.audio_base64;
      player.play();
    }
  }catch(e){out.innerText='त्रुटि: '+e.message;}
}

let rec, isRecording=false;
async function toggleVoice(){
  const orb=document.getElementById('voiceOrb'), st=document.getElementById('voiceStatus');
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)){
    alert("आपके ब्राउज़र में वॉइस रिकग्निशन सपोर्ट नहीं है। Chrome इस्तेमाल करें।");
    return;
  }
  if(isRecording){
    rec.stop();
    return;
  }
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SpeechRec();
  rec.lang = 'hi-IN';
  rec.interimResults = false;
  
  rec.onstart = () => {
    isRecording = true;
    orb.classList.add('recording');
    st.innerText = "सुन रहा हूँ... बोलिए";
  };
  rec.onresult = async (e) => {
    const text = e.results[0][0].transcript;
    st.innerText = "सोच रहा हूँ: \\"" + text + "\\"";
    orb.classList.remove('recording');
    isRecording = false;
    try {
      const res = await fetch('/api/voice', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text})
      });
      const d = await res.json();
      st.innerText = d.answer;
      if(d.audio_base64){
        const player = document.getElementById('audioPlayer');
        player.src = "data:audio/mp3;base64," + d.audio_base64;
        player.play();
      }
    } catch(err) {
      st.innerText = "त्रुटि: " + err.message;
    }
  };
  rec.onerror = () => {
    orb.classList.remove('recording');
    isRecording = false;
    st.innerText = "माइक पर फिर से क्लिक करें";
  };
  rec.onend = () => {
    orb.classList.remove('recording');
    isRecording = false;
  };
  rec.start();
}
</script></body></html>"""

class ChatReq(BaseModel): message: str
class ImageReq(BaseModel): prompt: str
class MovieReq(BaseModel): topic: str

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML

@app.post("/api/chat")
async def chat_api(req: ChatReq):
    if not GEMINI_API_KEY: raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    cfg = types.GenerateContentConfig(
        system_instruction="You are ARGON AI, created by Kaushik Raj. Reply in user's language."
    )
    for model_name in [CHAT_MODEL, "gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            res = gemini_client.models.generate_content(model=model_name, contents=req.message, config=cfg)
            return {"answer": res.text}
        except Exception:
            continue
    raise HTTPException(503, "AI सर्वर व्यस्त है। कृपया पुनः प्रयास करें।")

@app.post("/api/image")
async def image_api(req: ImageReq):
    if not GEMINI_API_KEY: raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    try:
        result = gemini_client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=req.prompt,
            config=dict(number_of_images=1, output_mime_type="image/jpeg")
        )
        for img in result.generated_images:
            b64 = base64.b64encode(img.image.image_bytes).decode('utf-8')
            return {"image_url": f"data:image/jpeg;base64,{b64}"}
    except Exception:
        safe_prompt = req.prompt.replace(" ", "%20")
        return {"image_url": f"https://image.pollinations.ai/prompt/{safe_prompt}?width=768&height=768&nologo=true"}

@app.post("/api/movie")
async def movie_api(req: MovieReq):
    if not GEMINI_API_KEY: raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    prompt = f"Write a dramatic 3-scene documentary script about: {req.topic}. Include Scene 1, Scene 2, Scene 3, and narration script in Hindi/Hinglish."
    res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    script_text = res.text
    
    clean_narration = script_text[:400].replace("*", "").replace("#", "")
    tts = edge_tts.Communicate(clean_narration, "hi-IN-MadhurNeural")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    await tts.save(tmp_path)
    with open(tmp_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode('utf-8')
    os.remove(tmp_path)
    
    return {"screenplay": script_text, "audio_base64": audio_b64}

@app.post("/api/voice")
async def voice_api(req: ChatReq):
    if not GEMINI_API_KEY: raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    cfg = types.GenerateContentConfig(
        system_instruction="You are ARGON AI, created by Kaushik Raj. Keep voice responses short, natural, and conversational in Hindi/Hinglish."
    )
    res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=req.message, config=cfg)
    reply_text = res.text
    
    tts = edge_tts.Communicate(reply_text[:500], "hi-IN-MadhurNeural")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    await tts.save(tmp_path)
    with open(tmp_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode('utf-8')
    os.remove(tmp_path)
    
    return {"answer": reply_text, "audio_base64": audio_b64}
    
