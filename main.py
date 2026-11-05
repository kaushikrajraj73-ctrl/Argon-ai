import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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
<title>ARGON AI V7000 - Nexus</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<style>
:root{--bg:#0a0b10;--bg-2:#12141c;--bg-3:#1a1d28;--bd:#252936;--tx:#e8eaf0;--tx2:#8b8fa3;--ac:#00ffcc;--gd:linear-gradient(135deg,#00ffcc,#ff007f);--ub:#1f2438;--ab:#121520}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden}
body{font-family:sans-serif;background:var(--bg);color:var(--tx);display:flex}
.sb{width:250px;background:var(--bg-2);border-right:1px solid var(--bd);display:flex;flex-direction:column;padding:16px 12px;flex-shrink:0}
.lg{font-weight:700;font-size:18px;background:var(--gd);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.ni{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;font-size:14px;color:var(--tx2);background:none;border:none;cursor:pointer;width:100%;text-align:left;transition:0.2s}
.ni.active, .ni:hover{background:var(--bg-3);color:var(--tx)}
.mn{flex:1;display:flex;flex-direction:column;min-width:0}
.hd{height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;border-bottom:1px solid var(--bd);background:var(--bg-2)}
.ht{font-size:16px;font-weight:600;color:var(--ac)}
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
.vo{width:130px;height:130px;border-radius:50%;background:var(--gd);display:flex;align-items:center;justify-content:center;font-size:45px;color:#fff;margin:30px auto;cursor:pointer}
.vo.recording{animation:pulse 1.2s infinite;background:#ff0055}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,0,85,0.7)}70%{box-shadow:0 0 0 25px rgba(255,0,85,0)}100%{box-shadow:0 0 0 0 rgba(255,0,85,0)}}
.movie-box{background:var(--bg-2);border:1px solid var(--bd);padding:20px;border-radius:12px;margin-top:15px;line-height:1.6}
.api-bar{display:flex;align-items:center;gap:10px}
.api-bar input{padding:6px 12px;font-size:12px;width:240px;background:#050510}
.video-screen{width:100%;max-width:640px;height:360px;background:#000;border:2px solid var(--ac);border-radius:10px;position:relative;overflow:hidden;margin:15px auto;display:flex;align-items:center;justify-content:center}
.video-screen img{width:100%;height:100%;object-fit:cover}
.subtitles{position:absolute;bottom:15px;left:10px;right:10px;background:rgba(0,0,0,0.8);color:#fff;padding:8px 12px;border-radius:6px;font-size:14px;text-align:center}
</style></head><body>
<aside class="sb">
  <div class="lg">ARGON AI V7000</div>
  <button class="ni active" onclick="switchTab('chat')">💬 चैट</button>
  <button class="ni" onclick="switchTab('image')">🎨 इमेज जनरेटर</button>
  <button class="ni" onclick="switchTab('movie')">🎬 मूवी फैक्ट्री</button>
  <button class="ni" onclick="switchTab('voice')">🎙️ लाइव वॉइस</button>
</aside>
<div class="mn">
  <div class="hd">
    <div class="ht" id="tabTitle">ARGON चैट (Architected by Kaushik Raj)</div>
    <div class="api-bar">
      <span style="font-size:12px;color:var(--tx2);">Gemini API Key:</span>
      <input type="password" id="clientApiKey" placeholder="API Key यहाँ डालें..." onchange="localStorage.setItem('argon_key', this.value)">
    </div>
  </div>
  <div class="ct">
    <!-- CHAT VIEW -->
    <div class="vw active" id="vw-chat" style="padding:0;">
      <div class="cs" id="chatArea" style="padding:20px;">
        <div class="mr ai"><div class="mbb">नमस्ते! मैं ARGON AI हूँ। ऊपर अपनी Gemini API Key डालकर कुछ भी पूछें।</div></div>
      </div>
      <div class="cw">
        <input type="text" id="chatInput" placeholder="संदेश लिखें..." onkeydown="if(event.key==='Enter')sendChat()">
        <button class="send-btn" onclick="sendChat()">भेजें</button>
      </div>
    </div>

    <!-- IMAGE VIEW -->
    <div class="vw" id="vw-image">
      <h3>🎨 AI इमेज स्टूडियो</h3>
      <textarea id="imgPrompt" rows="3" style="margin-top:10px;" placeholder="कैसी तस्वीर चाहिए? प्रॉम्प्ट लिखें (उदा: Cyberpunk neon warrior)"></textarea>
      <button class="send-btn" style="margin-top:10px;align-self:flex-start;" onclick="genImg()">✨ इमेज बनाएं</button>
      <div id="imgOut" style="margin-top:20px;display:flex;justify-content:center;"></div>
    </div>

    <!-- MOVIE VIEW -->
    <div class="vw" id="vw-movie">
      <h3>🎬 मूवी फैक्ट्री (Visual Storyboard + Voice Player)</h3>
      <textarea id="movieTopic" rows="2" style="margin-top:10px;" placeholder="मूवी का विषय लिखें (उदा: Future robot apocalypse)..."></textarea>
      <button class="send-btn" style="margin-top:10px;align-self:flex-start;" onclick="genMovie()">🎬 मूवी तैयार करें</button>
      
      <div id="videoContainer" style="display:none;margin-top:15px;">
        <div class="video-screen">
          <img id="movieFrame" src="" alt="Scene Frame">
          <div class="subtitles" id="movieSubtitles">सीन लोड हो रहा है...</div>
        </div>
        <div id="movieProgress" style="text-align:center;color:var(--ac);font-weight:bold;"></div>
      </div>
      <div id="movieScriptOut" class="movie-box" style="display:none;"></div>
    </div>

    <!-- VOICE VIEW -->
    <div class="vw" id="vw-voice" style="text-align:center;">
      <div class="vo" id="voiceOrb" onclick="toggleVoice()">🎙️</div>
      <h3 id="voiceStatus">माइक पर क्लिक करें और बोलें</h3>
      <p style="color:var(--tx2);margin-top:8px;">ARGON AI आपकी बात सुनकर तुरंत बोलकर जवाब देगा</p>
    </div>
  </div>
</div>

<script>
window.onload = () => {
  const k = localStorage.getItem('argon_key') || "";
  if(k) document.getElementById('clientApiKey').value = k;
};

function getApiKey(){
  return document.getElementById('clientApiKey').value.trim() || localStorage.getItem('argon_key') || "";
}

function switchTab(t){
  document.querySelectorAll('.vw').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.ni').forEach(n=>n.classList.remove('active'));
  document.getElementById('vw-'+t).classList.add('active');
  event.target.classList.add('active');
  const titles={chat:'ARGON चैट',image:'🎨 AI इमेज स्टूडियो',movie:'🎬 मूवी फैक्ट्री',voice:'🎙️ लाइव वॉइस मोड'};
  document.getElementById('tabTitle').innerText = titles[t] + " (Architected by Kaushik Raj)";
}

// कभी 'व्यस्त' न होने वाला स्मार्ट मल्टी-मॉडल फ़ॉलबैक इंजन
async function callGeminiDirect(promptText){
  const key = getApiKey();
  if(!key) throw new Error("कृपया पहले ऊपर दाईं तरफ अपनी Gemini API Key पेस्ट करें!");
  
  const models = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite"
  ];
  
  let lastErr = "";
  for(let m of models){
    try{
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${key}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          contents: [{ parts: [{ text: promptText }] }],
          systemInstruction: { parts: [{ text: "You are ARGON AI, created by Kaushik Raj. Provide clear, accurate answers directly in user's language." }] }
        })
      });
      
      const data = await res.json();
      if(res.status === 200 && data.candidates && data.candidates[0].content.parts[0].text){
        return data.candidates[0].content.parts[0].text;
      }
      
      // अगर 503 (Busy) या 429 (Rate Limit) आए, तो अगले मॉडल पर बढ़ें
      if(data.error){
        lastErr = data.error.message;
      }
    }catch(e){
      lastErr = e.message;
    }
    // छोटे पॉज़ के बाद दूसरा मॉडल ट्राई करें
    await new Promise(r => setTimeout(r, 600));
  }
  throw new Error("AI सर्वर पर अत्यधिक लोड है। 10 सेकंड बाद पुनः प्रयास करें या नई API Key बदलें। विवरण: " + lastErr);
}

async function sendChat(){
  const inp=document.getElementById('chatInput'), msg=inp.value.trim(), box=document.getElementById('chatArea');
  if(!msg)return;
  box.innerHTML+=`<div class="mr user"><div class="mbb">${msg}</div></div>`;
  inp.value='';
  box.scrollTop=box.scrollHeight;
  const aiBox=document.createElement('div');
  aiBox.className='mr ai';
  aiBox.innerHTML=`<div class="mbb">⏳ प्रोसेस हो रहा है...</div>`;
  box.appendChild(aiBox);
  box.scrollTop=box.scrollHeight;
  try{
    const ans = await callGeminiDirect(msg);
    aiBox.querySelector('.mbb').innerHTML=marked.parse(ans);
  }catch(e){aiBox.querySelector('.mbb').innerText='त्रुटि: '+e.message;}
  box.scrollTop=box.scrollHeight;
}

function genImg(){
  const p=document.getElementById('imgPrompt').value.trim(), out=document.getElementById('imgOut');
  if(!p)return;
  out.innerHTML='<p style="color:var(--ac);">⏳ इमेज जनरेट हो रही है...</p>';
  const cleanP = encodeURIComponent(p);
  const imgUrl = `https://image.pollinations.ai/prompt/${cleanP}?width=768&height=768&nologo=true&seed=`+Math.floor(Math.random()*99999);
  const img = new Image();
  img.onload = () => {
    out.innerHTML = `<img src="${imgUrl}" style="max-width:100%;max-height:480px;border-radius:12px;border:1px solid var(--bd);box-shadow:0 0 20px rgba(0,255,204,0.3);">`;
  };
  img.onerror = () => { out.innerHTML = '<p style="color:#ff5555;">इमेज लोड करने में समस्या आई। पुनः प्रयास करें।</p>'; };
  img.src = imgUrl;
}

function speakTextAsync(txt){
  return new Promise((resolve) => {
    if(!('speechSynthesis' in window)){ resolve(); return; }
    window.speechSynthesis.cancel();
    const clean = txt.replace(/[*#_`]/g, '');
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = 'hi-IN';
    u.rate = 0.95;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.speak(u);
  });
}

async function genMovie(){
  const t=document.getElementById('movieTopic').value.trim();
  const vCont=document.getElementById('videoContainer'), frame=document.getElementById('movieFrame'), sub=document.getElementById('movieSubtitles'), prog=document.getElementById('movieProgress'), scrOut=document.getElementById('movieScriptOut');
  if(!t)return;

  vCont.style.display='block';
  scrOut.style.display='none';
  prog.innerText = "⏳ स्टेप 1/3: AI 3-सीन विज़ुअल स्टोरीबोर्ड तैयार कर रहा है...";
  sub.innerText = "कहानी तैयार हो रही है...";

  try {
    const prompt = `Write a dramatic 3-scene mini movie script about: "${t}". Output ONLY a valid JSON array of 3 objects with "visual_prompt" (English descriptive image prompt) and "narration" (Hindi dialogue, 2 lines). Example: [{"visual_prompt": "cyberpunk city 2050 neon", "narration": "साल 2050 में शहर बदल चुका था।"}]`;
    const raw = await callGeminiDirect(prompt);
    let scenes;
    try {
      const match = raw.match(/\\[[\\s\\S]*\\]/);
      scenes = JSON.parse(match ? match[0] : raw);
    } catch(e) {
      scenes = [
        {visual_prompt: t + " dramatic opening scene cinematic", narration: t + " की शुरुआत एक रहस्यमयी घटना से हुई।"},
        {visual_prompt: t + " conflict battle scene cinematic", narration: "चारों तरफ चुनौतियां और खतरे बढ़ चुके थे।"},
        {visual_prompt: t + " victory futuristic climax cinematic", narration: "अंत में एक नए युग का उदय हुआ।"}
      ];
    }

    prog.innerText = "🎬 स्टेप 2/3: विज़ुअल फ्रेम्स रेंडर हो रहे हैं...";
    for(let i=0; i<scenes.length; i++){
      const cleanP = encodeURIComponent(scenes[i].visual_prompt);
      scenes[i].imgUrl = `https://image.pollinations.ai/prompt/${cleanP}?width=800&height=450&nologo=true&seed=`+(2000+i);
    }

    prog.innerText = "▶️ स्टेप 3/3: मूवी चल रही है...";
    for(let i=0; i<scenes.length; i++){
      frame.src = scenes[i].imgUrl;
      sub.innerText = `सीन ${i+1}/${scenes.length}: ` + scenes[i].narration;
      await speakTextAsync(scenes[i].narration);
      await new Promise(r => setTimeout(r, 800));
    }

    prog.innerText = "✅ मूवी समाप्त!";
    sub.innerText = "मूवी पूरी हुई। आप नीचे पूरी पटकथा भी पढ़ सकते हैं।";
    scrOut.style.display='block';
    scrOut.innerHTML = `<h4>पूरी मूवी पटकथा:</h4>` + scenes.map((s, idx)=>`<p style="margin-top:10px;"><b>सीन ${idx+1}:</b> ${s.narration}</p>`).join("");

  } catch(err) {
    prog.innerText = "त्रुटि: " + err.message;
  }
}

let rec, isRecording=false;
function toggleVoice(){
  const orb=document.getElementById('voiceOrb'), st=document.getElementById('voiceStatus');
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)){
    alert("कृपया Chrome ब्राउज़र का उपयोग करें।");
    return;
  }
  if(isRecording){ rec.stop(); return; }
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SpeechRec();
  rec.lang = 'hi-IN';
  rec.onstart = () => { isRecording=true; orb.classList.add('recording'); st.innerText="सुन रहा हूँ... बोलिए"; };
  rec.onresult = async (e) => {
    const text = e.results[0][0].transcript;
    st.innerText = 'सोच रहा हूँ: "' + text + '"';
    orb.classList.remove('recording');
    isRecording = false;
    try {
      const ans = await callGeminiDirect("Answer concisely in 1-2 lines in Hindi: " + text);
      st.innerText = ans;
      await speakTextAsync(ans);
    } catch(err) { st.innerText = "त्रुटि: " + err.message; }
  };
  rec.onerror = () => { orb.classList.remove('recording'); isRecording=false; st.innerText="माइक पर पुनः क्लिक करें"; };
  rec.onend = () => { orb.classList.remove('recording'); isRecording=false; };
  rec.start();
}
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX_HTML
    
