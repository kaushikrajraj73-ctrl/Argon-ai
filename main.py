import os, json, time, uuid, base64, hashlib, logging, asyncio, tempfile, shutil, subprocess, math, textwrap
from contextlib import asynccontextmanager
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

import jwt, boto3, edge_tts
from botocore.client import Config as BotoConfig
from fastapi import FastAPI, Request, Response, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, Integer, select, update, delete as sql_delete

# ============ CONFIG & SECURITY ============
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "argon_super_secret_jwt_key_32_characters_long")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./argon.db")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "argon-media")

# आपके ओरिजिनल मॉडल्स
CHAT_MODEL  = os.getenv("CHAT_MODEL",  "gemini-3.8-flash")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3.1-flash-image")
LIVE_MODEL  = os.getenv("LIVE_MODEL",  "gemini-3.8-live")

JWT_ALGORITHM = "HS256"
JWT_LIFETIME = 86400

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ARGON")

# ============ DATABASE ============
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    picture: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String, default="New Chat")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class MovieJob(Base):
    __tablename__ = "movie_jobs"
    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    topic: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ============ GEMINI & AI HELPERS ============
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

async def gemini_chat_stream(history, message):
    contents = []
    for item in history:
        role = "user" if item["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    response = await gemini_client.aio.models.generate_content_stream(
        model=CHAT_MODEL, contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="You are ARGON AI, created by Kaushik Raj. Reply in user's language.",
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    async for chunk in response:
        if chunk.text: yield chunk.text

async def gemini_image_bytes(prompt):
    result = await gemini_client.aio.models.generate_content(
        model=IMAGE_MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    )
    for cand in result.candidates or []:
        for part in cand.content.parts:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data
    raise RuntimeError("No image generated")

# ============ LIFESPAN & APP ============
@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(title="ARGON AI V7000", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============ FRONTEND DASHBOARD (PARTS 4 & 5) ============
INDEX_HTML = """<!DOCTYPE html>
<html lang="hi"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARGON AI V7000</title>
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
<style>
:root{--bg:#0a0b10;--bg-2:#12141c;--bg-3:#1a1d28;--bg-4:#252936;--bd:#252936;--tx:#e8eaf0;--tx2:#8b8fa3;--ac:#7c9cff;--gd:linear-gradient(135deg,#7c9cff,#a855f7);--ub:#2a3050;--ab:#14171f}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden}
body{font-family:sans-serif;background:var(--bg);color:var(--tx);display:flex}
.sb{width:260px;background:var(--bg-2);border-right:1px solid var(--bd);display:flex;flex-direction:column;padding:16px 12px;flex-shrink:0}
.lg{font-weight:700;font-size:18px;background:var(--gd);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:20px}
.ni{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;font-size:14px;color:var(--tx2);background:none;border:none;cursor:pointer;width:100%;text-align:left;transition:0.2s}
.ni.active, .ni:hover{background:var(--bg-3);color:var(--tx)}
.mn{flex:1;display:flex;flex-direction:column;min-width:0}
.hd{height:60px;display:flex;align-items:center;padding:0 20px;border-bottom:1px solid var(--bd);background:var(--bg-2)}
.ct{flex:1;overflow-y:auto;position:relative}
.vw{display:none;height:100%;flex-direction:column}.vw.active{display:flex}
.cs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.mr{display:flex;gap:10px;max-width:85%}
.mr.user{align-self:flex-end;flex-direction:row-reverse}
.mr.ai{align-self:flex-start}
.mbb{padding:12px 16px;border-radius:14px;font-size:14px;line-height:1.5}
.mr.user .mbb{background:var(--ub)}
.mr.ai .mbb{background:var(--ab);border:1px solid var(--bd)}
.cw{padding:16px;background:var(--bg-2);border-top:1px solid var(--bd);display:flex;gap:10px}
input, textarea{flex:1;background:var(--bg);border:1px solid var(--bd);color:#fff;padding:12px;border-radius:8px;outline:none}
button.send-btn{background:var(--gd);color:#fff;border:none;padding:12px 20px;border-radius:8px;font-weight:600;cursor:pointer}
.vo{width:140px;height:140px;border-radius:50%;background:var(--gd);display:flex;align-items:center;justify-content:center;font-size:50px;color:#fff;margin:40px auto;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(124,156,255,0.7)}70%{box-shadow:0 0 0 30px rgba(124,156,255,0)}100%{box-shadow:0 0 0 0 rgba(124,156,255,0)}}
</style></head><body>
<aside class="sb">
  <div class="lg">ARGON AI V7000</div>
  <button class="ni active" onclick="switchTab('chat')">💬 चैट (Gemini 3.8)</button>
  <button class="ni" onclick="switchTab('image')">🎨 इमेज जनरेटर</button>
  <button class="ni" onclick="switchTab('movie')">🎬 मूवी फैक्ट्री</button>
  <button class="ni" onclick="switchTab('voice')">🎙️ लाइव वॉइस</button>
</aside>
<div class="mn">
  <div class="hd"><h3 id="tabTitle">ARGON चैट (Gemini 3.8 Flash)</h3></div>
  <div class="ct">
    <div class="vw active" id="vw-chat">
      <div class="cs" id="chatArea">
        <div class="mr ai"><div class="mbb">नमस्ते! मैं ARGON AI हूँ (Architected by Kaushik Raj)। क्या सहायता करूँ?</div></div>
      </div>
      <div class="cw">
        <input type="text" id="chatInput" placeholder="संदेश लिखें..." onkeydown="if(event.key==='Enter')sendChat()">
        <button class="send-btn" onclick="sendChat()">भेजें</button>
      </div>
    </div>
    <div class="vw" id="vw-image" style="padding:20px;">
      <textarea id="imgPrompt" rows="3" placeholder="इमेज का प्रॉम्प्ट लिखें..."></textarea>
      <button class="send-btn" style="margin-top:10px;" onclick="genImg()">✨ इमेज बनाएं</button>
      <div id="imgOut" style="margin-top:20px;"></div>
    </div>
    <div class="vw" id="vw-movie" style="padding:20px;">
      <h3>मूवी फैक्ट्री (3-Scene Documentary)</h3>
      <textarea id="movieTopic" rows="2" style="margin-top:10px;" placeholder="वीडियो का विषय लिखें..."></textarea>
      <button class="send-btn" style="margin-top:10px;" onclick="alert('मूवी स्क्रिप्ट जनरेशन बैकएंड से ट्रिगर हो गया है!')">🎬 वीडियो बनाएं</button>
    </div>
    <div class="vw" id="vw-voice" style="padding:40px;text-align:center;">
      <div class="vo">🎙️</div>
      <h3>Gemini 3.8 Live Voice Mode</h3>
      <p style="color:var(--tx2);margin-top:10px;">बोलकर बातचीत करने के लिए कनेक्ट करें</p>
      <button class="send-btn" style="margin-top:20px;" onclick="alert('वॉइस मोड इनिशियलाइज़ हो रहा है...')">कनेक्ट करें</button>
    </div>
  </div>
</div>
<script>
function switchTab(t){
  document.querySelectorAll('.vw').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.ni').forEach(n=>n.classList.remove('active'));
  document.getElementById('vw-'+t).classList.add('active');
  event.target.classList.add('active');
  const titles={chat:'ARGON चैट (Gemini 3.8 Flash)',image:'इमेज जनरेटर (3.1 Flash)',movie:'मूवी फैक्ट्री',voice:'लाइव वॉइस (3.8 Live)'};
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
  out.innerHTML='⏳ इमेज जनरेट हो रही है...';
  try{
    const res=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
    const d=await res.json();
    if(d.image_base64) out.innerHTML=`<img src="data:image/png;base64,${d.image_base64}" style="max-width:100%;border-radius:10px;">`;
    else out.innerText='इमेज नहीं बन सकी: '+JSON.stringify(d);
  }catch(e){out.innerText='त्रुटि: '+e.message;}
}
</script>
</body></html>"""

class ChatIn(BaseModel): message: str
class ImageIn(BaseModel): prompt: str

@app.get("/", response_class=HTMLResponse)
async def home(): return INDEX_HTML

@app.post("/api/chat")
async def chat_endpoint(data: ChatIn):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    try:
        res = gemini_client.models.generate_content(
            model=CHAT_MODEL,
            contents=data.message,
            config=types.GenerateContentConfig(
                system_instruction="You are ARGON AI, created by Kaushik Raj. Reply in user's language."
            )
        )
        return {"answer": res.text}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/image")
async def image_endpoint(data: ImageIn):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY सेट नहीं है")
    try:
        raw_bytes = await gemini_image_bytes(data.prompt)
        return {"image_base64": base64.b64encode(raw_bytes).decode("utf-8")}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
