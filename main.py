import os, json, urllib.request, urllib.error
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ARGON AI V7000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

INDEX_HTML = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARGON AI V7000</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
body { background: #121316; color: #e1e3e6; padding: 10px; display: flex; flex-direction: column; min-height: 100vh; }
.header { font-size: 20px; font-weight: bold; padding: 10px; color: #00ffcc; text-align: center; border-bottom: 1px solid #2a2d35; }
.nav { display: flex; gap: 8px; justify-content: center; margin: 12px 0; flex-wrap: wrap; }
.tab-btn { background: #22252e; color: #fff; border: 1px solid #3c404d; padding: 10px 16px; border-radius: 20px; cursor: pointer; font-size: 14px; font-weight: 500; }
.tab-btn.active { background: #0077ff; border-color: #00a2ff; }
.tab-content { display: none; flex: 1; flex-direction: column; max-width: 800px; width: 100%; margin: 0 auto; }
.tab-content.active { display: flex; }

/* चैट इनपुट सबसे ऊपर ताकि टैबलेट पर कभी न कटे */
.chat-bar { display: flex; gap: 8px; margin-bottom: 15px; }
.chat-bar input { flex: 1; background: #1c1e26; border: 1px solid #3a3e4a; color: #fff; padding: 12px; border-radius: 10px; font-size: 16px; outline: none; }
.chat-bar button { background: #0077ff; color: #fff; border: none; padding: 12px 20px; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; }
.chat-box { flex: 1; background: #181a20; border: 1px solid #2a2d35; border-radius: 12px; padding: 15px; min-height: 350px; max-height: 550px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.msg { padding: 10px 14px; border-radius: 10px; line-height: 1.5; font-size: 15px; max-width: 85%; }
.msg.user { background: #005bb5; align-self: flex-end; }
.msg.ai { background: #22252e; align-self: flex-start; border: 1px solid #3a3e4a; }

/* मीडिया व वॉइस */
textarea { width: 100%; background: #1c1e26; border: 1px solid #3a3e4a; color: #fff; padding: 12px; border-radius: 10px; font-size: 15px; outline: none; margin-bottom: 10px; }
.action-btn { background: #00a86b; color: #fff; border: none; padding: 12px 22px; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; align-self: flex-start; }
.screen { width: 100%; aspect-ratio: 16/9; background: #000; border: 1px solid #3a3e4a; border-radius: 10px; margin-top: 15px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.screen img { width: 100%; height: 100%; object-fit: cover; }
.subs { position: absolute; bottom: 8px; left: 8px; right: 8px; background: rgba(0,0,0,0.85); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 14px; text-align: center; }

.voice-wrap { text-align: center; padding: 30px 10px; }
.v-btn { width: 110px; height: 110px; border-radius: 50%; background: #0077ff; border: none; font-size: 40px; color: #fff; cursor: pointer; margin: 15px auto; display: block; box-shadow: 0 0 25px rgba(0,119,255,0.4); }
.v-btn.rec { background: #e60049; box-shadow: 0 0 35px rgba(230,0,73,0.8); }
</style>
</head>
<body>

<div class="header">ARGON AI V7000 (By Kaushik Raj)</div>

<div class="nav">
  <button class="tab-btn active" onclick="showTab('chat')">💬 चैट (Chat)</button>
  <button class="tab-btn" onclick="showTab('voice')">🎙️ लाइव वॉइस (Voice)</button>
  <button class="tab-btn" onclick="showTab('movie')">🎬 मूवी फैक्ट्री (Video)</button>
  <button class="tab-btn" onclick="showTab('image')">🎨 8K फोटो (Image)</button>
</div>

<!-- 1. CHAT -->
<div class="tab-content active" id="tab-chat">
  <div class="chat-bar">
    <input type="text" id="chatInput" placeholder="यहाँ मैसेज लिखें..." onkeydown="if(event.key==='Enter')chatSend()">
    <button onclick="chatSend()">भेजें</button>
  </div>
  <div class="chat-box" id="chatLogs">
    <div class="msg ai">नमस्ते Kaushik! मैं ARGON AI हूँ। ऊपर बॉक्स में सवाल लिखकर 'भेजें' दबाएँ।</div>
  </div>
</div>

<!-- 2. VOICE -->
<div class="tab-content" id="tab-voice">
  <div class="voice-wrap">
    <button class="v-btn" id="voiceBtn" onclick="toggleVoice()">🎙️</button>
    <h3 id="vStatus" style="margin-top:15px;">माइक दबाकर बोलें</h3>
    <p id="vOutput" style="margin-top:12px; color:#a0a6b5; font-size:16px;">ARGON सुनकर बोलकर जवाब देगा</p>
  </div>
</div>

<!-- 3. MOVIE -->
<div class="tab-content" id="tab-movie">
  <textarea id="movieTopic" rows="3" placeholder="मूवी का विषय लिखें (उदा: Mars Exploration 2050 या Mahabharat)..."></textarea>
  <button class="action-btn" onclick="startMovie()">🎥 मूवी बनाएं</button>
  <div id="moviePlayer" style="display:none;">
    <div class="screen">
      <img id="mImg" src="">
      <div class="subs" id="mCaption">लोड हो रहा है...</div>
    </div>
    <p id="mInfo" style="text-align:center; color:#00ffcc; margin-top:10px; font-weight:bold;"></p>
  </div>
</div>

<!-- 4. IMAGE -->
<div class="tab-content" id="tab-image">
  <textarea id="imgPrompt" rows="3" placeholder="8K फोटो का प्रॉम्प्ट लिखें..."></textarea>
  <button class="action-btn" onclick="makePhoto()">✨ फोटो बनाएं</button>
  <div class="screen" id="imgBox" style="margin-top:15px;">
    <span style="color:#666;">तस्वीर यहाँ लोड होगी</span>
  </div>
</div>

<script>
function showTab(name) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}

async function askAI(prompt) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: prompt})
  });
  const data = await res.json();
  if(!res.ok) throw new Error(data.detail || "त्रुटि");
  return data.answer;
}

async function chatSend() {
  const inp = document.getElementById('chatInput');
  const txt = inp.value.trim();
  if(!txt) return;
  inp.value = '';

  const box = document.getElementById('chatLogs');
  box.innerHTML += `<div class="msg user">${txt}</div>`;
  const aiBox = document.createElement('div');
  aiBox.className = 'msg ai';
  aiBox.innerHTML = '<i>ARGON सोच रहा है...</i>';
  box.appendChild(aiBox);
  box.scrollTop = box.scrollHeight;

  try {
    const ans = await askAI(txt);
    aiBox.innerHTML = marked.parse(ans);
  } catch(e) {
    aiBox.innerHTML = `<span style="color:#ff5555;">${e.message}</span>`;
  }
  box.scrollTop = box.scrollHeight;
}

function speak(text) {
  return new Promise(resolve => {
    if(!('speechSynthesis' in window)) return resolve();
    window.speechSynthesis.cancel();
    const clean = text.replace(/[*#_`]/g, '');
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = 'hi-IN';
    u.rate = 0.95;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.speak(u);
  });
}

async function startMovie() {
  const topic = document.getElementById('movieTopic').value.trim();
  if(!topic) return;

  const player = document.getElementById('moviePlayer');
  const img = document.getElementById('mImg');
  const cap = document.getElementById('mCaption');
  const info = document.getElementById('mInfo');

  player.style.display = 'block';
  info.innerText = "⏳ स्टेप 1: कहानी लिखी जा रही है...";
  cap.innerText = "तैयार हो रहा है...";

  try {
    const prompt = `Write a dramatic 3-scene story on "${topic}". Output ONLY a JSON array of 3 items with keys: "scene_prompt" (English visual prompt) and "narration" (Hindi 2 lines). Example: [{"scene_prompt": "...", "narration": "..."}]`;
    const res = await askAI(prompt);
    let scenes;
    try {
      const match = res.match(/\\[[\\s\\S]*\\]/);
      scenes = JSON.parse(match ? match[0] : res);
    } catch(err) {
      scenes = [
        {scene_prompt: topic + " cinematic dramatic opening, 8k", narration: topic + " की शुरुआत एक रहस्यमयी मोड़ से हुई।"},
        {scene_prompt: topic + " conflict and battle scene, dramatic light", narration: "रास्ते में कई भयानक चुनौतियाँ सामने आईं।"},
        {scene_prompt: topic + " victory finale scene, 8k photorealistic", narration: "और अंत में विजय प्राप्त हुई।"}
      ];
    }

    info.innerText = "🎨 स्टेप 2: 8K फ्रेम्स रेंडर हो रहे हैं...";
    for(let i=0; i<scenes.length; i++) {
      const p = encodeURIComponent(scenes[i].scene_prompt + ", cinematic, 8k, photorealistic");
      scenes[i].url = `https://image.pollinations.ai/prompt/${p}?width=1280&height=720&nologo=true&seed=` + (3000 + i);
    }

    info.innerText = "▶️ स्टेप 3: मूवी चल रही है...";
    for(let i=0; i<scenes.length; i++) {
      img.src = scenes[i].url;
      cap.innerText = `[सीन ${i+1}/${scenes.length}] ` + scenes[i].narration;
      await speak(scenes[i].narration);
      await new Promise(r => setTimeout(r, 900));
    }
    info.innerText = "✅ मूवी समाप्त!";
    cap.innerText = "प्रदर्शन पूरा हुआ।";
  } catch(e) {
    info.innerText = "त्रुटि: " + e.message;
  }
}

let rec, isRec = false;
function toggleVoice() {
  const btn = document.getElementById('voiceBtn');
  const st = document.getElementById('vStatus');
  const out = document.getElementById('vOutput');

  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("कृपया Google Chrome ब्राउज़र का उपयोग करें।");
    return;
  }
  if(isRec) { rec.stop(); return; }

  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new Speech();
  rec.lang = 'hi-IN';

  rec.onstart = () => {
    isRec = true;
    btn.classList.add('rec');
    st.innerText = "सुन रहा हूँ... बोलिए";
    out.innerText = "बोलना पूरा करने के बाद रुकें...";
  };

  rec.onresult = async (e) => {
    const userText = e.results[0][0].transcript;
    st.innerText = `सुना: "${userText}"`;
    btn.classList.remove('rec');
    isRec = false;
    out.innerText = "ARGON सोच रहा है...";

    try {
      const ans = await askAI("1-2 वाक्य में हिंदी में उत्तर दें: " + userText);
      out.innerText = ans;
      await speak(ans);
      st.innerText = "माइक दबाकर बोलें";
    } catch(err) {
      out.innerText = "त्रुटि: " + err.message;
    }
  };

  rec.onerror = () => { btn.classList.remove('rec'); isRec = false; st.innerText = "माइक दबाकर दोबारा बोलें"; };
  rec.onend = () => { btn.classList.remove('rec'); isRec = false; };
  rec.start();
}

function makePhoto() {
  const p = document.getElementById('imgPrompt').value.trim();
  const box = document.getElementById('imgBox');
  if(!p) return;

  box.innerHTML = `<span style="color:#00ffcc;">⏳ 8K फोटो बन रही है...</span>`;
  const pFinal = encodeURIComponent(p + ", 8k uhd, photorealistic, cinematic lighting, raw photograph");
  const url = `https://image.pollinations.ai/prompt/${pFinal}?width=1024&height=768&nologo=true&seed=` + Math.floor(Math.random()*888888);

  const img = new Image();
  img.onload = () => { box.innerHTML = `<img src="${url}">`; };
  img.onerror = () => { box.innerHTML = `<span style="color:#ff5555;">फोटो लोड नहीं हुई।</span>`; };
  img.src = url;
}
</script>
</body>
</html>
"""

class ChatReq(BaseModel):
    message: str

def call_gemini(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "GEMINI_API_KEY सेट नहीं है।"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data = json.dumps(payload).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": key
    }
    
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        return f"AI सर्वर त्रुटि HTTP {e.code}: {e.read().decode('utf-8')}"
    except Exception as e:
        return f"त्रुटि: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML

@app.post("/api/chat")
async def chat_api(req: ChatReq):
    return {"answer": call_gemini(req.message)}
    
