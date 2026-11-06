import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>ARGON AI - Gemini UI</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background: #131314; color: #e3e3e3; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

/* Top Navbar */
.nav-header {
  height: 55px;
  background: #1e1f20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}
.brand-name {
  font-weight: 700;
  font-size: 18px;
  background: linear-gradient(135deg, #4285f4, #9b72cb, #d96570);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.tab-row {
  display: flex;
  gap: 6px;
  background: #1e1f20;
  padding: 8px 12px;
  border-bottom: 1px solid #2a2b2e;
  overflow-x: auto;
  flex-shrink: 0;
}
.t-btn {
  background: #282a2c;
  color: #c4c7c5;
  border: 1px solid #3c4043;
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}
.t-btn.active {
  background: #004a77;
  color: #c2e7ff;
  border-color: #7cacf8;
  font-weight: 600;
}

/* Content Area */
.view-area {
  flex: 1;
  overflow-y: auto;
  display: none;
  flex-direction: column;
  padding: 16px;
  -webkit-overflow-scrolling: touch;
}
.view-area.active { display: flex; }

/* Chat Section */
.chat-messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 10px;
}
.msg { padding: 12px 16px; border-radius: 16px; max-width: 85%; font-size: 15px; line-height: 1.5; word-break: break-word; }
.msg.user { background: #282a2c; align-self: flex-end; border-bottom-right-radius: 4px; }
.msg.ai { background: #1e1f20; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid #333; }

/* Fixed Bottom Chat Bar */
.bottom-chat-bar {
  display: flex;
  background: #1e1f20;
  padding: 10px 14px;
  border-top: 1px solid #333;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}
.bottom-chat-bar input {
  flex: 1;
  background: #131314;
  border: 1px solid #444;
  color: #fff;
  padding: 12px 16px;
  border-radius: 25px;
  font-size: 15px;
  outline: none;
}
.bottom-chat-bar button {
  background: linear-gradient(135deg, #4285f4, #9b72cb);
  color: #fff;
  border: none;
  padding: 12px 20px;
  border-radius: 25px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}

/* Studio & Movie Styles */
.box-card {
  background: #1e1f20;
  border: 1px solid #333;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
textarea {
  width: 100%;
  background: #131314;
  border: 1px solid #444;
  color: #fff;
  padding: 12px;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  resize: none;
}
.btn-action {
  background: linear-gradient(135deg, #4285f4, #9b72cb);
  color: #fff;
  border: none;
  padding: 12px 20px;
  border-radius: 25px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
}
.display-frame {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-top: 8px;
}
.display-frame img { width: 100%; height: 100%; object-fit: cover; }
.caption-bar {
  position: absolute;
  bottom: 8px;
  left: 8px;
  right: 8px;
  background: rgba(0,0,0,0.85);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
}

/* Voice Orb */
.voice-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  gap: 16px;
}
.v-orb {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, #4285f4, #9b72cb);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 45px;
  cursor: pointer;
  box-shadow: 0 0 35px rgba(66,133,244,0.5);
}
.v-orb.listening { animation: pulse 1s infinite alternate; }
@keyframes pulse {
  0% { transform: scale(1); box-shadow: 0 0 25px #d96570; }
  100% { transform: scale(1.15); box-shadow: 0 0 60px #d96570; }
}
</style>
</head>
<body>

<div class="nav-header">
  <div class="brand-name">✨ ARGON AI V7000</div>
  <div style="font-size: 12px; color: #aaa;">By Kaushik Raj</div>
</div>

<div class="tab-row">
  <button class="t-btn active" onclick="setTab('chat')">💬 चैट (Chat)</button>
  <button class="t-btn" onclick="setTab('movie')">🎬 मूवी फैक्ट्री (Video)</button>
  <button class="t-btn" onclick="setTab('voice')">🎙️ लाइव वॉइस (Live)</button>
  <button class="t-btn" onclick="setTab('image')">🎨 8K फोटो (Image)</button>
</div>

<!-- 1. CHAT TAB -->
<div class="view-area active" id="sec-chat">
  <div class="chat-messages" id="chatList">
    <div class="msg ai">नमस्ते Kaushik! मैं ARGON AI हूँ। नीचे बॉक्स में लिखकर कोई भी सवाल पूछें।</div>
  </div>
</div>

<!-- FIXED CHAT INPUT BAR (हमेशा स्क्रीन पर दिखेगा) -->
<div class="bottom-chat-bar" id="chatInputBar">
  <input type="text" id="chatTextInput" placeholder="यहाँ मैसेज लिखें..." onkeydown="if(event.key==='Enter')doChatSend()">
  <button onclick="doChatSend()">भेजें</button>
</div>

<!-- 2. MOVIE TAB -->
<div class="view-area" id="sec-movie">
  <div class="box-card">
    <h3>🎬 मूवी फैक्ट्री (Visual Scenes + Voiceover)</h3>
    <textarea id="mvText" rows="3" placeholder="मूवी का विषय लिखें (उदा: Mars 2050 Space Mission या Mahabharat War)..."></textarea>
    <button class="btn-action" onclick="makeMovie()">🎥 मूवी बनाएं</button>
    
    <div id="mvPlayer" style="display:none; margin-top:10px;">
      <div class="display-frame">
        <img id="mvImg" src="" alt="Movie Scene">
        <div class="caption-bar" id="mvCaption">सीन तैयार हो रहा है...</div>
      </div>
      <p id="mvInfo" style="text-align:center; color:#a8c7fa; font-size:14px; margin-top:8px; font-weight:bold;"></p>
    </div>
  </div>
</div>

<!-- 3. VOICE TAB -->
<div class="view-area" id="sec-voice">
  <div class="voice-box">
    <div class="v-orb" id="orbBtn" onclick="runVoice()">🎙️</div>
    <h3 id="voiceStatusText">माइक बटन दबाएं और बोलें</h3>
    <p style="color:#aaa; font-size:14px;" id="voiceAnswerText">ARGON आपकी आवाज़ सुनकर तुरंत बोलकर जवाब देगा</p>
  </div>
</div>

<!-- 4. IMAGE TAB -->
<div class="view-area" id="sec-image">
  <div class="box-card">
    <h3>🎨 8K रियलिस्टिक फोटो स्टूडियो</h3>
    <textarea id="imgPromptText" rows="3" placeholder="फोटो का प्रॉम्प्ट लिखें..."></textarea>
    <button class="btn-action" onclick="makePhoto()">✨ फोटो बनाएं</button>
    <div class="display-frame" id="imgResultBox">
      <span style="color:#666;">फ़ोटो यहाँ लोड होगी</span>
    </div>
  </div>
</div>

<script>
function setTab(tab) {
  document.querySelectorAll('.view-area').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.t-btn').forEach(e => e.classList.remove('active'));
  document.getElementById('sec-' + tab).classList.add('active');
  event.target.classList.add('active');
  
  // चैट बार केवल चैट वाले टैब में साफ़ दिखेगा
  document.getElementById('chatInputBar').style.display = (tab === 'chat') ? 'flex' : 'none';
}

async function fetchAI(msg) {
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg})
  });
  const data = await r.json();
  if(!r.ok) throw new Error(data.detail || "त्रुटि आई");
  return data.answer;
}

async function doChatSend() {
  const inp = document.getElementById('chatTextInput');
  const txt = inp.value.trim();
  if(!txt) return;
  inp.value = '';

  const list = document.getElementById('chatList');
  list.innerHTML += `<div class="msg user">${txt}</div>`;
  
  const aiBox = document.createElement('div');
  aiBox.className = 'msg ai';
  aiBox.innerHTML = '<i>ARGON सोच रहा है...</i>';
  list.appendChild(aiBox);
  
  const container = document.getElementById('sec-chat');
  container.scrollTop = container.scrollHeight;

  try {
    const ans = await fetchAI(txt);
    aiBox.innerHTML = marked.parse(ans);
  } catch(e) {
    aiBox.innerHTML = `<span style="color:#ff6b6b;">${e.message}</span>`;
  }
  container.scrollTop = container.scrollHeight;
}

function speakVoice(text) {
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

async function makeMovie() {
  const topic = document.getElementById('mvText').value.trim();
  if(!topic) return;

  const player = document.getElementById('mvPlayer');
  const img = document.getElementById('mvImg');
  const cap = document.getElementById('mvCaption');
  const info = document.getElementById('mvInfo');

  player.style.display = 'block';
  info.innerText = "⏳ स्टेप 1: AI पटकथा (Script) लिख रहा है...";
  cap.innerText = "कहानी तैयार हो रही है...";

  try {
    const prompt = `Write a dramatic 3-scene story on "${topic}". Output ONLY a JSON array of 3 items with keys: "scene_prompt" (hyperrealistic cinematic image description in English) and "narration" (2 lines Hindi dramatic narration). Example: [{"scene_prompt": "...", "narration": "..."}]`;
    const res = await fetchAI(prompt);
    let scenes;
    try {
      const match = res.match(/\\[[\\s\\S]*\\]/);
      scenes = JSON.parse(match ? match[0] : res);
    } catch(err) {
      scenes = [
        {scene_prompt: topic + " cinematic dramatic opening, 8k, photorealistic", narration: topic + " की कहानी का आरम्भ हुआ।"},
        {scene_prompt: topic + " epic conflict and intense action, cinematic lighting", narration: "सफर में अप्रत्याशित और भयंकर चुनौतियाँ सामने आईं।"},
        {scene_prompt: topic + " victorious climax ending, photorealistic, masterpiece", narration: "और अंततः एक नए युग की विजय गाथा लिखी गई।"}
      ];
    }

    info.innerText = "🎨 स्टेप 2: 8K सिनेमैटिक दृश्य रेंडर हो रहे हैं...";
    for(let i=0; i<scenes.length; i++) {
      const p = encodeURIComponent(scenes[i].scene_prompt + ", cinematic, 8k, photorealistic, raw photo");
      scenes[i].url = `https://image.pollinations.ai/prompt/${p}?width=1280&height=720&nologo=true&seed=` + (7000 + i);
    }

    info.innerText = "▶️ स्टेप 3: मूवी चल रही है...";
    for(let i=0; i<scenes.length; i++) {
      img.src = scenes[i].url;
      cap.innerText = `[सीन ${i+1}/${scenes.length}] ` + scenes[i].narration;
      await speakVoice(scenes[i].narration);
      await new Promise(r => setTimeout(r, 900));
    }
    info.innerText = "✅ मूवी समाप्त!";
    cap.innerText = "प्रदर्शन पूरा हुआ।";
  } catch(e) {
    info.innerText = "त्रुटि: " + e.message;
  }
}

let voiceRec, isRecording = false;
function runVoice() {
  const orb = document.getElementById('orbBtn');
  const st = document.getElementById('voiceStatusText');
  const ansTxt = document.getElementById('voiceAnswerText');

  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("कृपया Google Chrome ब्राउज़र का उपयोग करें।");
    return;
  }
  if(isRecording) { voiceRec.stop(); return; }

  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  voiceRec = new Speech();
  voiceRec.lang = 'hi-IN';

  voiceRec.onstart = () => {
    isRecording = true;
    orb.classList.add('listening');
    st.innerText = "सुन रहा हूँ... बोलिए";
    ansTxt.innerText = "बोलना समाप्त करने के बाद थोड़ा इंतज़ार करें...";
  };

  voiceRec.onresult = async (e) => {
    const userSaid = e.results[0][0].transcript;
    st.innerText = `सुना: "${userSaid}"`;
    orb.classList.remove('listening');
    isRecording = false;
    ansTxt.innerText = "ARGON सोच रहा है...";

    try {
      const reply = await fetchAI("Give a direct, concise 1-2 sentence response in Hindi: " + userSaid);
      ansTxt.innerText = reply;
      await speakVoice(reply);
      st.innerText = "माइक बटन दबाएं और बोलें";
    } catch(err) {
      ansTxt.innerText = "त्रुटि: " + err.message;
    }
  };

  voiceRec.onerror = () => {
    orb.classList.remove('listening');
    isRecording = false;
    st.innerText = "माइक पर दोबारा क्लिक करें";
  };
  voiceRec.onend = () => {
    orb.classList.remove('listening');
    isRecording = false;
  };
  voiceRec.start();
}

function makePhoto() {
  const p = document.getElementById('imgPromptText').value.trim();
  const box = document.getElementById('imgResultBox');
  if(!p) return;

  box.innerHTML = `<span style="color:#7cacf8;">⏳ 8K फोटो बन रही है...</span>`;
  const realisticTags = "hyperrealistic, raw photo, 8k uhd, dslr quality, cinematic lighting, ultra detailed";
  const finalPrompt = encodeURIComponent(p + ", " + realisticTags);
  const url = `https://image.pollinations.ai/prompt/${finalPrompt}?width=1024&height=768&nologo=true&seed=` + Math.floor(Math.random()*999999);

  const img = new Image();
  img.onload = () => { box.innerHTML = `<img src="${url}">`; };
  img.onerror = () => { box.innerHTML = `<span style="color:#ff6b6b;">फोटो लोड नहीं हुई।</span>`; };
  img.src = url;
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
    
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI सर्वर त्रुटि: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML

@app.post("/api/chat")
async def chat_api(req: ChatReq):
    ans = call_gemini_backend(req.message)
    return {"answer": ans}
