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

/* Sidebar (Gemini Style) */
.sidebar {
  width: 260px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  gap: 8px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
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

.nav-btn:hover {
  background: var(--bg-surface-elevated);
  color: var(--text-primary);
}

.nav-btn.active {
  background: #004a77;
  color: #c2e7ff;
}

/* Main Area */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  height: 100vh;
  background: radial-gradient(circle at 50% 10%, #1e1f20 0%, #131314 60%);
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
  padding: 24px 20px 100px;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}

.content-pane.active {
  display: flex;
}

/* Chat Bubbles */
.chat-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
}

.chat-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.chat-row.user {
  justify-content: flex-end;
}

.user-bubble {
  background: var(--bg-surface-elevated);
  padding: 14px 20px;
  border-radius: 22px 22px 6px 22px;
  max-width: 75%;
  font-size: 15px;
  line-height: 1.6;
}

.ai-bubble {
  flex: 1;
  font-size: 15px;
  line-height: 1.7;
  color: #f0f0f0;
}

.ai-bubble h1, .ai-bubble h2, .ai-bubble h3 { margin: 12px 0 6px; color: var(--accent-blue); }
.ai-bubble p { margin-bottom: 10px; }
.ai-bubble ul, .ai-bubble ol { margin-left: 20px; margin-bottom: 10px; }

/* Floating Gemini Input */
.input-floating-bar {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: min(840px, 92%);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 30px;
  display: flex;
  align-items: center;
  padding: 6px 12px 6px 22px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  backdrop-filter: blur(10px);
}

.input-floating-bar input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  padding: 10px 0;
}

.send-action {
  background: var(--gemini-gradient);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  font-size: 18px;
  transition: transform 0.2s;
}

.send-action:hover { transform: scale(1.05); }

/* Realistic Image Studio */
.image-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.image-card textarea {
  width: 100%;
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  color: #fff;
  padding: 14px;
  border-radius: 12px;
  font-size: 15px;
  resize: vertical;
  outline: none;
}

.gen-btn {
  background: var(--gemini-gradient);
  color: #fff;
  border: none;
  padding: 14px 28px;
  border-radius: 30px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
  transition: opacity 0.2s;
}

.gen-btn:hover { opacity: 0.9; }

.img-preview-box {
  width: 100%;
  min-height: 420px;
  background: #000;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  margin-top: 10px;
}

.img-preview-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 16px;
}

/* Movie Factory Cinema */
.theater-screen {
  width: 100%;
  max-width: 800px;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 18px;
  position: relative;
  overflow: hidden;
  border: 1px solid #444;
  margin: 18px auto;
  box-shadow: 0 10px 40px rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
}

.theater-screen img { width: 100%; height: 100%; object-fit: cover; }
.subtitles-banner {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  background: rgba(15,15,20,0.85);
  backdrop-filter: blur(8px);
  padding: 12px 18px;
  border-radius: 12px;
  text-align: center;
  font-size: 15px;
  border: 1px solid rgba(255,255,255,0.1);
}

/* Live Voice Orb */
.voice-hero {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
}

.gemini-orb {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #4285f4, #9b72cb 60%, #1e1f20);
  box-shadow: 0 0 50px rgba(66,133,244,0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 55px;
  transition: all 0.3s;
}

.gemini-orb.active {
  animation: pulse-gemini 1.5s infinite;
  box-shadow: 0 0 80px rgba(217,101,112,0.8);
}

@keyframes pulse-gemini {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); filter: brightness(1.3); }
  100% { transform: scale(1); }
}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="brand">✨ ARGON Gemini</div>
  <button class="nav-btn active" onclick="navigate('chat')">💬 चैट (Chat)</button>
  <button class="nav-btn" onclick="navigate('image')">📷 अल्ट्रा-रियलिस्टिक फोटो</button>
  <button class="nav-btn" onclick="navigate('movie')">🎬 4K मूवी स्टूडियो</button>
  <button class="nav-btn" onclick="navigate('voice')">🎙️ लाइव वॉइस मोड</button>
</aside>

<div class="main-wrapper">
  <div class="top-bar">
    <div id="paneTitle">ARGON AI V7000 Enterprise</div>
    <div>Architected by <b>Kaushik Raj</b></div>
  </div>

  <!-- CHAT PANE -->
  <div class="content-pane active" id="pane-chat">
    <div class="chat-container" id="chatArea">
      <div class="chat-row ai">
        <div class="ai-bubble">नमस्ते! मैं ARGON AI हूँ (Powered by Gemini Engine)। मैं आज आपकी क्या सहायता कर सकता हूँ?</div>
      </div>
    </div>
  </div>

  <!-- IMAGE PANE -->
  <div class="content-pane" id="pane-image">
    <div class="image-card">
      <h2>🎨 8K अल्ट्रा-रियलिस्टिक इमेज इंजन</h2>
      <p style="color:var(--text-secondary);font-size:14px;">असली फोटो जैसा रिज़ल्ट पाने के लिए अपनी कल्पना लिखें (जैसे: Hyper-realistic Indian soldier in Himalayas, cinematic sunlight, 8k resolution):</p>
      <textarea id="imgPrompt" rows="3" placeholder="यहाँ प्रॉम्प्ट लिखें..."></textarea>
      <button class="gen-btn" onclick="generateRealisticImage()">✨ रियलिस्टिक फोटो बनाएँ</button>
      <div class="img-preview-box" id="imgBox">
        <span style="color:#666;">आपकी अल्ट्रा-रियलिस्टिक फ़ोटो यहाँ दिखेगी</span>
      </div>
    </div>
  </div>

  <!-- MOVIE PANE -->
  <div class="content-pane" id="pane-movie">
    <div class="image-card">
      <h2>🎬 4K सिनेमा मूवी फैक्ट्री</h2>
      <textarea id="movieTopic" rows="2" placeholder="मूवी की कहानी का विषय लिखें (उदा: Mars Exploration mission 2040)..."></textarea>
      <button class="gen-btn" onclick="createFullMovie()">🎥 मूवी तैयार करें और चलाएँ</button>
      <div id="theaterContainer" style="display:none;">
        <div class="theater-screen">
          <img id="theaterFrame" src="" alt="Cinema Scene">
          <div class="subtitles-banner" id="theaterSubtitles">सीन लोड हो रहा है...</div>
        </div>
        <p id="movieStatusTxt" style="text-align:center;color:var(--accent-blue);font-weight:600;margin-top:10px;"></p>
      </div>
    </div>
  </div>

  <!-- VOICE PANE -->
  <div class="content-pane" id="pane-voice">
    <div class="voice-hero">
      <div class="gemini-orb" id="voiceOrb" onclick="toggleLiveVoice()">🎙️</div>
      <h2 id="voiceLabel" style="margin-top:24px;">Gemini Live शुरू करने के लिए टैप करें</h2>
      <p style="color:var(--text-secondary);margin-top:8px;">बोलकर सवाल पूछें, ARGON तुरंत हिंदी में उत्तर देगा</p>
    </div>
  </div>

  <!-- FLOATING CHAT INPUT -->
  <div class="input-floating-bar" id="chatInputBar">
    <input type="text" id="userMsgInput" placeholder="ARGON से कुछ भी पूछें..." onkeydown="if(event.key==='Enter')handleSend()">
    <button class="send-action" onclick="handleSend()">➔</button>
  </div>
</div>

<script>
function navigate(tab) {
  document.querySelectorAll('.content-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('pane-' + tab).classList.add('active');
  event.target.classList.add('active');

  const bar = document.getElementById('chatInputBar');
  bar.style.display = (tab === 'chat') ? 'flex' : 'none';

  const titles = {
    chat: 'ARGON Chat - Gemini 2.5 Engine',
    image: 'ARGON Realistic Photolab',
    movie: 'ARGON Cinematic Movie Studio',
    voice: 'ARGON Gemini Live Voice'
  };
  document.getElementById('paneTitle').innerText = titles[tab];
}

async function queryBackend(text) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: text})
  });
  const data = await resp.json();
  if(!resp.ok) throw new Error(data.detail || "त्रुटि आई");
  return data.answer;
}

async function handleSend() {
  const inp = document.getElementById('userMsgInput');
  const msg = inp.value.trim();
  if(!msg) return;
  inp.value = '';

  const area = document.getElementById('chatArea');
  area.innerHTML += `<div class="chat-row user"><div class="user-bubble">${msg}</div></div>`;
  
  const aiRow = document.createElement('div');
  aiRow.className = 'chat-row ai';
  aiRow.innerHTML = `<div class="ai-bubble"><i>ARGON सोच रहा है...</i></div>`;
  area.appendChild(aiRow);
  area.scrollTop = area.scrollHeight;

  try {
    const reply = await queryBackend(msg);
    aiRow.querySelector('.ai-bubble').innerHTML = marked.parse(reply);
  } catch(err) {
    aiRow.querySelector('.ai-bubble').innerHTML = `<span style="color:#ff6b6b;">${err.message}</span>`;
  }
  area.scrollTop = area.scrollHeight;
}

function generateRealisticImage() {
  const rawPrompt = document.getElementById('imgPrompt').value.trim();
  const box = document.getElementById('imgBox');
  if(!rawPrompt) return;

  box.innerHTML = `<span style="color:var(--accent-blue);">⏳ 8K रियलिस्टिक फोटो रेंडर हो रही है...</span>`;

  // अल्ट्रा-रियलिज्म एनहांसर (कार्तूनिश लुक रोकने के लिए फोटोग्राफिक टैग्स)
  const realisticKeywords = "raw photo, 8k uhd, dslr, high quality, 35mm lens, sharp focus, cinematic lighting, photorealistic, masterwork, highly detailed skin texture, realism";
  const finalPrompt = encodeURIComponent(`${rawPrompt}, ${realisticKeywords}`);
  
  const imgUrl = `https://image.pollinations.ai/prompt/${finalPrompt}?width=1024&height=768&nologo=true&enhance=true&seed=` + Math.floor(Math.random() * 999999);

  const img = new Image();
  img.onload = () => {
    box.innerHTML = `<img src="${imgUrl}" alt="Photorealistic Image">`;
  };
  img.onerror = () => {
    box.innerHTML = `<span style="color:#ff6b6b;">इमेज लोड करने में समस्या आई।</span>`;
  };
  img.src = imgUrl;
}

function speakNarration(text) {
  return new Promise(resolve => {
    if(!('speechSynthesis' in window)) return resolve();
    window.speechSynthesis.cancel();
    const clean = text.replace(/[*#_`]/g, '');
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = 'hi-IN';
    u.rate = 0.92;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.speak(u);
  });
}

async function createFullMovie() {
  const topic = document.getElementById('movieTopic').value.trim();
  const box = document.getElementById('theaterContainer');
  const frame = document.getElementById('theaterFrame');
  const subs = document.getElementById('theaterSubtitles');
  const status = document.getElementById('movieStatusTxt');
  if(!topic) return;

  box.style.display = 'block';
  status.innerText = "⏳ स्टेप 1: Gemini सिनेमा स्क्रिप्ट तैयार कर रहा है...";
  subs.innerText = "कहानी तैयार हो रही है...";

  try {
    const prompt = `Write a dramatic 3-scene cinematic movie script about: "${topic}". Output ONLY a JSON array of 3 objects with "visual_prompt" (hyper-realistic cinematic photographic prompt in English) and "narration" (Hindi 2-line dramatic narration). Format: [{"visual_prompt": "cinematic photorealistic...", "narration": "..."}]`;
    const res = await queryBackend(prompt);
    let scenes;
    try {
      const match = res.match(/\\[[\\s\\S]*\\]/);
      scenes = JSON.parse(match ? match[0] : res);
    } catch(e) {
      scenes = [
        {visual_prompt: topic + " cinematic establishing shot, photorealistic, 8k", narration: topic + " की कहानी एक रोमांचक मोड़ से शुरू होती है।"},
        {visual_prompt: topic + " dramatic conflict scene, high detail, realistic lighting", narration: "सफर में अप्रत्याशित चुनौतियों का सामना करना पड़ा।"},
        {visual_prompt: topic + " victorious epic climax, photorealistic, masterpiece", narration: "और अंततः एक नई मिसाल कायम हुई।"}
      ];
    }

    status.innerText = "🎨 स्टेप 2: 8K सिनेमैटिक फ्रेम्स रेंडर हो रहे हैं...";
    for(let i=0; i<scenes.length; i++) {
      const p = encodeURIComponent(scenes[i].visual_prompt + ", cinematic, 8k, raw photo, realistic");
      scenes[i].url = `https://image.pollinations.ai/prompt/${p}?width=1280&height=720&nologo=true&seed=` + (8000 + i);
    }

    status.innerText = "▶️ स्टेप 3: मूवी चल रही है...";
    for(let i=0; i<scenes.length; i++) {
      frame.src = scenes[i].url;
      subs.innerText = `[सीन ${i+1}/${scenes.length}] ` + scenes[i].narration;
      await speakNarration(scenes[i].narration);
      await new Promise(r => setTimeout(r, 1000));
    }
    status.innerText = "✅ मूवी समाप्त!";
    subs.innerText = "प्रदर्शन पूरा हुआ।";
  } catch(err) {
    status.innerText = "त्रुटि: " + err.message;
  }
}

let voiceRec, isListening = false;
function toggleLiveVoice() {
  const orb = document.getElementById('voiceOrb');
  const lbl = document.getElementById('voiceLabel');
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("कृपया Chrome ब्राउज़र में खोलें।");
    return;
  }

  if(isListening) { voiceRec.stop(); return; }

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  voiceRec = new SpeechRec();
  voiceRec.lang = 'hi-IN';

  voiceRec.onstart = () => {
    isListening = true;
    orb.classList.add('active');
    lbl.innerText = "सुन रहा हूँ... बोलिए";
  };

  voiceRec.onresult = async (e) => {
    const speech = e.results[0][0].transcript;
    lbl.innerText = `सोच रहा हूँ: "${speech}"`;
    orb.classList.remove('active');
    isListening = false;

    try {
      const reply = await queryBackend("Give a direct, concise 1-2 sentence response in Hindi: " + speech);
      lbl.innerText = reply;
      await speakNarration(reply);
    } catch(err) {
      lbl.innerText = "त्रुटि: " + err.message;
    }
  };

  voiceRec.onerror = () => {
    orb.classList.remove('active');
    isListening = false;
    lbl.innerText = "माइक पर दोबारा क्लिक करें";
  };

  voiceRec.onend = () => {
    orb.classList.remove('active');
    isListening = false;
  };

  voiceRec.start();
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
    
    # आपके cURL से प्रमाणित सटीक एंडपॉइंट
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
