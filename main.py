import os, json, urllib.request, urllib.error
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ARGON AI V7000 - Gemini Edition")
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
<title>ARGON AI - Gemini Experience</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg-main: #131314;
  --bg-surface: #1e1f20;
  --bg-surface-elevated: #282a2c;
  --text-primary: #e3e3e3;
  --text-secondary: #c4c7c5;
  --accent-blue: #a8c7fa;
  --gemini-gradient: linear-gradient(135deg, #4285f4, #9b72cb, #d96570);
  --border-subtle: #333538;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Google Sans', 'Inter', sans-serif;
  background: var(--bg-main);
  color: var(--text-primary);
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  gap: 8px;
  flex-shrink: 0;
}

.brand {
  padding: 8px 12px 18px;
  font-size: 19px;
  font-weight: 700;
  background: var(--gemini-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 28px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.nav-btn:hover { background: var(--bg-surface-elevated); color: var(--text-primary); }
.nav-btn.active { background: #004a77; color: #c2e7ff; }

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  height: 100vh;
}

.top-bar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  font-size: 14px;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.content-pane {
  flex: 1;
  overflow-y: auto;
  display: none;
  flex-direction: column;
  padding: 24px 20px 120px;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}

.content-pane.active { display: flex; }

.chat-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.chat-row { display: flex; gap: 16px; width: 100%; }
.chat-row.user { justify-content: flex-end; }
.user-bubble {
  background: var(--bg-surface-elevated);
  padding: 12px 18px;
  border-radius: 20px 20px 4px 20px;
  max-width: 75%;
  font-size: 15px;
  line-height: 1.5;
}
.ai-bubble {
  flex: 1;
  font-size: 15px;
  line-height: 1.6;
  color: #f0f0f0;
}

.chat-input-wrapper {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: min(840px, 92%);
  background: var(--bg-surface);
  border: 1px solid #444;
  border-radius: 30px;
  display: flex;
  align-items: center;
  padding: 6px 10px 6px 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  z-index: 100;
}

.chat-input-wrapper input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  padding: 10px 0;
}

.send-btn-circle {
  background: var(--gemini-gradient);
  border: none;
  border-radius: 50%;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
}

.card-box {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
textarea {
  width: 100%;
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  color: #fff;
  padding: 12px;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
}
.action-btn {
  background: var(--gemini-gradient);
  color: #fff;
  border: none;
  padding: 12px 24px;
  border-radius: 25px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
}
.preview-screen {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-top: 10px;
}
.preview-screen img { width: 100%; height: 100%; object-fit: cover; }
.subs {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  background: rgba(0,0,0,0.8);
  padding: 10px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
}

.voice-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  text-align: center;
}
.voice-ball {
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: radial-gradient(circle, #4285f4, #9b72cb);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 45px;
  cursor: pointer;
  box-shadow: 0 0 40px rgba(66,133,244,0.5);
}
.voice-ball.active {
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  0% { transform: scale(1); box-shadow: 0 0 30px #d96570; }
  50% { transform: scale(1.1); box-shadow: 0 0 70px #d96570; }
  100% { transform: scale(1); box-shadow: 0 0 30px #d96570; }
}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="brand">✨ ARGON Gemini</div>
  <button class="nav-btn active" onclick="switchTab('chat')">💬 चैट (Chat)</button>
  <button class="nav-btn" onclick="switchTab('image')">📷 8K रियलिस्टिक फोटो</button>
  <button class="nav-btn" onclick="switchTab('movie')">🎬 मूवी फैक्ट्री</button>
  <button class="nav-btn" onclick="switchTab('voice')">🎙️ लाइव वॉइस मोड</button>
</aside>

<div class="main-wrapper">
  <div class="top-bar">
    <div id="tabTitle">ARGON AI - Gemini 2.5 Engine</div>
    <div>Architected by <b>Kaushik Raj</b></div>
  </div>

  <div class="content-pane active" id="pane-chat">
    <div class="chat-container" id="chatArea">
      <div class="chat-row ai">
        <div class="ai-bubble">नमस्ते! मैं ARGON AI हूँ। नीचे बॉक्स में अपना सवाल लिखकर भेजें।</div>
      </div>
    </div>
  </div>

  <div class="content-pane" id="pane-image">
    <div class="card-box">
      <h3>📷 8K अल्ट्रा-रियलिस्टिक फोटो लैब</h3>
      <textarea id="imgPrompt" rows="3" placeholder="कैसी तस्वीर चाहिए? प्रॉम्प्ट लिखें (उदा: Realistic Indian king sitting on throne, royal lighting, 8k)..."></textarea>
      <button class="action-btn" onclick="generatePhoto()">✨ फोटो बनाएं</button>
      <div class="preview-screen" id="imgBox">
        <span style="color:#777;">फ़ोटो यहाँ लोड होगी</span>
      </div>
    </div>
  </div>

  <div class="content-pane" id="pane-movie">
    <div class="card-box">
      <h3>🎬 मूवी फैक्ट्री (दृश्य + आवाज़)</h3>
      <textarea id="moviePrompt" rows="2" placeholder="मूवी का विषय लिखें..."></textarea>
      <button class="action-btn" onclick="playMovie()">🎥 मूवी तैयार करें</button>
      <div id="movieContainer" style="display:none;">
        <div class="preview-screen">
          <img id="movieFrame" src="" alt="Movie Scene">
          <div class="subs" id="movieSubs">सीन लोड हो रहा है...</div>
        </div>
        <p id="movieStatus" style="text-align:center;color:var(--accent-blue);margin-top:10px;font-weight:600;"></p>
      </div>
    </div>
  </div>

  <div class="content-pane" id="pane-voice">
    <div class="voice-area">
      <div class="voice-ball" id="voiceBall" onclick="startVoice()">🎙️</div>
      <h3 id="voiceStatus" style="margin-top:20px;">माइक पर क्लिक करें और बोलें</h3>
      <p style="color:var(--text-secondary);margin-top:6px;">ARGON सीधे सुनकर जवाब देगा</p>
    </div>
  </div>

  <div class="chat-input-wrapper" id="chatBar">
    <input type="text" id="chatInput" placeholder="ARGON से कुछ भी पूछें..." onkeydown="if(event.key==='Enter')sendChat()">
    <button class="send-btn-circle" onclick="sendChat()">➔</button>
  </div>
</div>

<script>
function switchTab(t) {
  document.querySelectorAll('.content-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('pane-' + t).classList.add('active');
  event.target.classList.add('active');
  document.getElementById('chatBar').style.display = (t === 'chat') ? 'flex' : 'none';
}

async function askServer(msg) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg})
  });
  const data = await res.json();
  if(!res.ok) throw new Error(data.detail || "सर्वर से रिस्पॉन्स नहीं मिला");
  return data.answer;
}

async function sendChat() {
  const inp = document.getElementById('chatInput');
  const txt = inp.value.trim();
  if(!txt) return;
  inp.value = '';

  const area = document.getElementById('chatArea');
  area.innerHTML += `<div class="chat-row user"><div class="user-bubble">${txt}</div></div>`;

  const aiRow = document.createElement('div');
  aiRow.className = 'chat-row ai';
  aiRow.innerHTML = `<div class="ai-bubble"><i>ARGON सोच रहा है...</i></div>`;
  area.appendChild(aiRow);
  area.scrollTop = area.scrollHeight;

  try {
    const ans = await askServer(txt);
    aiRow.querySelector('.ai-bubble').innerHTML = marked.parse(ans);
  } catch(e) {
    aiRow.querySelector('.ai-bubble').innerHTML = `<span style="color:#ff6b6b;">${e.message}</span>`;
  }
  area.scrollTop = area.scrollHeight;
}

function generatePhoto() {
  const p = document.getElementById('imgPrompt').value.trim();
  const box = document.getElementById('imgBox');
  if(!p) return;

  box.innerHTML = `<span style="color:var(--accent-blue);">⏳ 8K रियलिस्टिक फोटो रेंडर हो रही है...</span>`;
  const realisticTags = "photorealistic, hyperrealistic, 8k uhd, dslr quality, cinematic lighting, ultra sharp focus, 35mm photograph";
  const finalP = encodeURIComponent(p + ", " + realisticTags);
  const url = `https://image.pollinations.ai/prompt/${finalP}?width=1024&height=768&nologo=true&seed=` + Math.floor(Math.random()*888888);

  const img = new Image();
  img.onload = () => { box.innerHTML = `<img src="${url}">`; };
  img.onerror = () => { box.innerHTML = `<span style="color:#ff6b6b;">इमेज लोड नहीं हो सकी।</span>`; };
  img.src = url;
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

async function playMovie() {
  const topic = document.getElementById('moviePrompt').value.trim();
  const c = document.getElementById('movieContainer');
  const frame = document.getElementById('movieFrame');
  const subs = document.getElementById('movieSubs');
  const status = document.getElementById('movieStatus');
  if(!topic) return;

  c.style.display = 'block';
  status.innerText = "⏳ स्टेप 1: Gemini मूवी की पटकथा तैयार कर रहा है...";
  subs.innerText = "स्क्रिप्टिंग...";

  try {
    const prompt = `Write a dramatic 3-scene mini movie on: "${topic}". Output ONLY JSON array of 3 objects with "visual_prompt" (hyperrealistic cinematic image description in English) and "narration" (Hindi 2-line dramatic narration). Format: [{"visual_prompt": "...", "narration": "..."}]`;
    const res = await askServer(prompt);
    let scenes;
    try {
      const match = res.match(/\\[[\\s\\S]*\\]/);
      scenes = JSON.parse(match ? match[0] : res);
    } catch(e) {
      scenes = [
        {visual_prompt: topic + " cinematic establishing scene, photorealistic, 8k", narration: topic + " की कहानी का आरम्भ हुआ।"},
        {visual_prompt: topic + " dramatic action scene, cinematic lighting, sharp", narration: "चारों ओर चुनौतियाँ बढ़ने लगी थीं।"},
        {visual_prompt: topic + " triumphant finale scene, masterpiece, photorealistic", narration: "और अंततः सब कुछ बदल गया।"}
      ];
    }

    status.innerText = "🎨 स्टेप 2: 8K फ्रेम्स रेंडर हो रहे हैं...";
    for(let i=0; i<scenes.length; i++) {
      const ep = encodeURIComponent(scenes[i].visual_prompt + ", cinematic, 8k, raw photograph");
      scenes[i].imgUrl = `https://image.pollinations.ai/prompt/${ep}?width=1280&height=720&nologo=true&seed=` + (5000+i);
    }

    status.innerText = "▶️ स्टेप 3: मूवी चल रही है...";
    for(let i=0; i<scenes.length; i++) {
      frame.src = scenes[i].imgUrl;
      subs.innerText = `[सीन ${i+1}/${scenes.length}] ` + scenes[i].narration;
      await speak(scenes[i].narration);
      await new Promise(r => setTimeout(r, 900));
    }
    status.innerText = "✅ मूवी समाप्त!";
    subs.innerText = "पूरी हुई।";
  } catch(err) {
    status.innerText = "त्रुटि: " + err.message;
  }
}

let rec, isRec = false;
function startVoice() {
  const ball = document.getElementById('voiceBall');
  const st = document.getElementById('voiceStatus');
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("कृपया Chrome का उपयोग करें।");
    return;
  }
  if(isRec) { rec.stop(); return; }

  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new Speech();
  rec.lang = 'hi-IN';
  rec.onstart = () => { isRec = true; ball.classList.add('active'); st.innerText = "सुन रहा हूँ... बोलिए"; };
  rec.onresult = async (e) => {
    const speech = e.results[0][0].transcript;
    st.innerText = `सोच रहा हूँ: "${speech}"`;
    ball.classList.remove('active');
    isRec = false;
    try {
      const ans = await askServer("1-2 वाक्य में संक्षिप्त उत्तर दें: " + speech);
      st.innerText = ans;
      await speak(ans);
    } catch(err) { st.innerText = "त्रुटि: " + err.message; }
  };
  rec.onerror = () => { ball.classList.remove('active'); isRec = false; st.innerText = "माइक पर दोबारा क्लिक करें"; };
  rec.onend = () => { ball.classList.remove('active'); isRec = false; };
  rec.start();
}
</script>
</body>
</html>
"""

class ChatReq(BaseModel):
    message: str

def call_gemini_backend(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "GEMINI_API_KEY सेट नहीं है।"
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
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
        err_body = e.read().decode("utf-8")
        return f"AI सर्वर त्रुटि HTTP {e.code}: {err_body}"
    except Exception as e:
        return f"त्रुटि: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML

@app.post("/api/chat")
async def chat_api(req: ChatReq):
    ans = call_gemini_backend(req.message)
    return {"answer": ans}
