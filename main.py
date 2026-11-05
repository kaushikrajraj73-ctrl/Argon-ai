import os, json, time, uuid, base64, logging, asyncio, tempfile, shutil, subprocess, math, textwrap
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import jwt, boto3, edge_tts
from botocore.client import Config as BotoConfig
from fastapi import FastAPI, Request, Response, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, Integer, select, update

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ARGON")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "argon-ai-secret-key-change-it-32-chars")
DATABASE_URL = os.getenv("DATABASE_URL", "")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "argon-media")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

CHAT_MODEL  = os.getenv("CHAT_MODEL",  "gemini-3.8-flash")
LIVE_MODEL  = os.getenv("LIVE_MODEL",  "gemini-3.8-live")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-001")

FALLBACK_CHAT = "gemini-2.0-flash"
FALLBACK_LIVE = "gemini-2.0-flash-exp"

JWT_ALGORITHM = "HS256"
JWT_LIFETIME = 86400

if not GEMINI_API_KEY: raise RuntimeError("GEMINI_API_KEY missing")
if not DATABASE_URL: raise RuntimeError("DATABASE_URL missing")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    picture: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="New Chat")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String, primary_key=True)
    expires_at: Mapped[float] = mapped_column(Float)

class MediaAsset(Base):
    __tablename__ = "media_assets"
    filename: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class MovieJob(Base):
    __tablename__ = "movie_jobs"
    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

async def get_db():
    async with AsyncSessionLocal() as session: yield session

def get_s3():
    return boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, config=BotoConfig(signature_version="s3v4"), region_name="auto")

def upload_file(filepath, key, content_type="application/octet-stream"):
    get_s3().upload_file(filepath, R2_BUCKET_NAME, key, ExtraArgs={'ContentType': content_type})
    return key

def presigned_url(key, expires_in=3600):
    return get_s3().generate_presigned_url("get_object", Params={"Bucket": R2_BUCKET_NAME, "Key": key}, ExpiresIn=expires_in)

def make_jwt(user_id):
    now = int(time.time())
    return jwt.encode({"sub": user_id, "jti": str(uuid.uuid4()), "iat": now, "exp": now + JWT_LIFETIME}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

async def verify_jwt(token, db):
    try: payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except: raise HTTPException(401, "Invalid token")
    res = await db.execute(select(RevokedToken).where(RevokedToken.jti == payload["jti"]))
    if res.scalar_one_or_none(): raise HTTPException(401, "Revoked")
    return payload

async def current_user(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("argon_session")
    if not token: raise HTTPException(401, "Login required")
    return await verify_jwt(token, db)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

async def gemini_chat_stream(history, message):
    contents = [{"role": "user" if i["role"]=="user" else "model", "parts":[{"text": i["content"]}]} for i in history]
    contents.append({"role": "user", "parts": [{"text": message}]})
    for model in [CHAT_MODEL, FALLBACK_CHAT]:
        try:
            response = await gemini_client.aio.models.generate_content_stream(
                model=model, contents=contents,
                config=types.GenerateContentConfig(system_instruction="You are ARGON AI.", tools=[types.Tool(google_search=types.GoogleSearch())]))
            async for chunk in response:
                if chunk.text: yield chunk.text
            return
        except Exception as e:
            log.warning(f"Model {model} failed: {e}. Trying fallback...")
            if model == FALLBACK_CHAT:
                yield "\n\n⚠️ AI सर्वर से कनेक्ट नहीं हो पा रहा है।"

async def gemini_image_bytes(prompt):
    try:
        result = await gemini_client.aio.models.generate_images(model=IMAGE_MODEL, prompt=prompt, config=types.GenerateImagesConfig(number_of_images=1))
        if result.generated_images: return result.generated_images[0].image.image_bytes
        raise RuntimeError("No image")
    except Exception as e:
        log.error(f"Image Error: {e}")
        raise HTTPException(500, "Image generation failed.")

async def synthesize_voice(text):
    c = edge_tts.Communicate(text, "hi-IN-MadhurNeural"); buf = b""
    async for chunk in c.stream():
        if chunk["type"] == "audio": buf += chunk["data"]
    return buf

def run_ffmpeg(cmd):
    try: subprocess.run(cmd, check=True, timeout=600, capture_output=True)
    except subprocess.CalledProcessError as e: log.error(e.stderr.decode()[:500]); raise

def get_audio_duration(filepath):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath], timeout=20).decode().strip()
    return float(out)

def srt_timestamp(seconds):
    ms = round(seconds * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

async def run_movie_job(job_id, user_id, topic):
    async with AsyncSessionLocal() as db:
        await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(status="processing", progress=10, message="Starting..."))
        await db.commit()

    tmpdir = tempfile.mkdtemp()
    try:
        prompt = f'Create Hindi script about: {topic}. Return JSON: {{"scenes":[{{"text":"...","image_desc":"..."}}]}}. Exactly 3 scenes.'
        res = None
        for model in [CHAT_MODEL, FALLBACK_CHAT]:
            try:
                res = await gemini_client.aio.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                break
            except Exception as e: log.warning(f"Movie model {model} failed: {e}")
                
        if not res: raise RuntimeError("All models failed")
        
        scenes = json.loads(res.text).get("scenes", [])[:3]
        video_paths = []

        for i, scene in enumerate(scenes):
            text = '\n'.join(textwrap.wrap(scene.get("text", "").replace('\n', ' '), width=40))
            prog = int(10 + ((i) / 3) * 70)
            async with AsyncSessionLocal() as db:
                await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(progress=prog, message=f"Scene {i+1}/3..."))
                await db.commit()

            a_path = os.path.join(tmpdir, f"s_{i}.mp3")
            with open(a_path, "wb") as f: f.write(await synthesize_voice(scene.get("text", "")))
            dur = get_audio_duration(a_path)

            img_bytes = await gemini_image_bytes(scene.get("image_desc", ""))
            i_path = os.path.join(tmpdir, f"s_{i}.png")
            with open(i_path, "wb") as f: f.write(img_bytes)

            srt_path = os.path.join(tmpdir, f"s_{i}.srt")
            with open(srt_path, "w", encoding="utf-8") as f: f.write(f"1\n{srt_timestamp(0)} --> {srt_timestamp(dur)}\n{text}\n")

            v_path = os.path.join(tmpdir, f"s_{i}.mp4")
            srt_escaped = srt_path.replace('\\', '/').replace(':', '\\:')
            await asyncio.to_thread(run_ffmpeg, ["ffmpeg", "-y", "-loop", "1", "-i", i_path, "-i", a_path, "-vf", f"scale=1280:720,subtitles='{srt_escaped}'", "-c:v", "libx264", "-c:a", "aac", "-shortest", v_path])
            video_paths.append(v_path)

        final = os.path.join(tmpdir, "final.mp4")
        cf = os.path.join(tmpdir, "concat.txt")
        with open(cf, "w") as f:
            for v in video_paths: f.write(f"file '{v}'\n")
        await asyncio.to_thread(run_ffmpeg, ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cf, "-c", "copy", final])

        filename = f"movies/{job_id}.mp4"
        await asyncio.to_thread(upload_file, final, filename, "video/mp4")

        async with AsyncSessionLocal() as db:
            db.add(MediaAsset(filename=filename, user_id=user_id, media_type="video"))
            await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(status="completed", progress=100, message="Ready", filename=filename))
            await db.commit()
    except Exception as ex:
        log.error(f"Movie err: {ex}")
        async with AsyncSessionLocal() as db:
            await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(status="failed", error="Video generation failed."))
            await db.commit()
    finally: shutil.rmtree(tmpdir, ignore_errors=True)

@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class GoogleLogin(BaseModel): credential: str
class ChatInput(BaseModel): message: str; session_id: str
class ImageInput(BaseModel): prompt: str
class MovieInput(BaseModel): topic: str

@app.post("/auth/google")
async def auth_google(data: GoogleLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try: idinfo = id_token.verify_oauth2_token(data.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except: raise HTTPException(401, "Invalid token")
    email = idinfo["email"]; user_id = idinfo["sub"]
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if not user:
        user = User(user_id=user_id, email=email, name=idinfo.get("name","User"), picture=idinfo.get("picture",""))
        db.add(user)
    await db.commit()
    response.set_cookie("argon_session", make_jwt(user_id), httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=JWT_LIFETIME)
    return {"success": True}

@app.get("/api/me")
async def api_me(user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.user_id == user["sub"]))
    u = res.scalar_one_or_none()
    return {"name": u.name if u else "User", "picture": u.picture if u else ""}

@app.get("/api/chat/sessions")
async def get_sessions(user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ChatSession).where(ChatSession.user_id == user["sub"]).order_by(ChatSession.created_at.desc()))
    return {"sessions": [{"id": s.session_id, "title": s.title} for s in res.scalars().all()]}

@app.post("/api/chat/session")
async def new_session(user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    sid = str(uuid.uuid4())
    db.add(ChatSession(session_id=sid, user_id=user["sub"], title="New Chat"))
    await db.commit()
    return {"session_id": sid}

@app.get("/api/chat/history/{session_id}")
async def chat_history(session_id: str, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Chat).where(Chat.user_id == user["sub"], Chat.session_id == session_id).order_by(Chat.created_at.asc()))
    return {"history": [{"role": r.role, "content": r.content} for r in res.scalars().all()]}

@app.post("/api/chat")
async def api_chat(data: ChatInput, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Chat).where(Chat.session_id == data.session_id).order_by(Chat.created_at.desc()).limit(20))
    history = [{"role": r.role, "content": r.content} for r in reversed(res.scalars().all())]
    db.add(Chat(id=str(uuid.uuid4()), session_id=data.session_id, user_id=user["sub"], role="user", content=data.message))
    await db.commit()

    async def stream_generator():
        full_text = ""
        async for text in gemini_chat_stream(history, data.message):
            full_text += text; yield f"data: {json.dumps({'text': text})}\n\n"
        async with AsyncSessionLocal() as session:
            session.add(Chat(id=str(uuid.uuid4()), session_id=data.session_id, user_id=user["sub"], role="model", content=full_text))
            await session.commit()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/api/image")
async def api_image(data: ImageInput, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ib = await gemini_image_bytes(data.prompt)
    filename = f"images/{uuid.uuid4().hex}.png"
    get_s3().put_object(Bucket=R2_BUCKET_NAME, Key=filename, Body=ib, ContentType="image/png")
    db.add(MediaAsset(filename=filename, user_id=user["sub"], media_type="image"))
    await db.commit()
    return {"filename": filename}

@app.post("/api/movie/start")
async def api_movie_start(data: MovieInput, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job_id = uuid.uuid4().hex[:12]
    db.add(MovieJob(job_id=job_id, user_id=user["sub"], topic=data.topic, status="pending"))
    await db.commit()
    asyncio.create_task(run_movie_job(job_id, user["sub"], data.topic))
    return {"job_id": job_id}

@app.get("/api/movie/status/{job_id}")
async def api_movie_status(job_id: str, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MovieJob).where(MovieJob.job_id == job_id))
    job = res.scalar_one_or_none()
    return {"status": job.status, "progress": job.progress, "message": job.message, "filename": job.filename, "error": job.error} if job else HTTPException(404)

@app.get("/media/{path:path}")
async def get_media(path: str): return {"url": presigned_url(path)}

@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket):
    token = ws.cookies.get("argon_session")
    if not token: await ws.close(code=1008); return
    await ws.accept()
    cfg = types.LiveConnectConfig(response_modalities=["AUDIO"])
    session = None
    for model in [LIVE_MODEL, FALLBACK_LIVE]:
        try:
            session = await gemini_client.aio.live.connect(model=model, config=cfg).__aenter__()
            break
        except Exception as e: log.warning(f"Live model {model} failed: {e}")
    if not session: await ws.close(code=1008); return

    try:
        async def b2g():
            while True:
                msg = await ws.receive_json()
                if msg.get("type") == "audio":
                    raw = base64.b64decode(msg["data"])
                    if len(raw) <= 64000: await session.send_realtime_input(audio=types.Blob(data=raw, mime_type="audio/pcm;rate=16000"))
        async def g2b():
            async for resp in session.receive():
                c = getattr(resp, "server_content", None)
                if c and getattr(c, "model_turn", None):
                    for p in c.model_turn.parts:
                        if p.inline_data: await ws.send_json({"type":"audio","data":base64.b64encode(p.inline_data.data).decode("ascii")})
        t = [asyncio.create_task(b2g()), asyncio.create_task(g2b())]
        await asyncio.wait(t, return_when=asyncio.FIRST_COMPLETED)
        for x in t: x.cancel()
    except Exception: pass
    finally:
        await session.__aexit__(None, None, None)
        await ws.close;

INDEX_HTML = """
<!DOCTYPE html><html lang="hi"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARGON AI</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.5/purify.min.js"></script>
<style>
:root{--bg:#0a0b10;--bg2:#12141c;--bg3:#1a1d28;--tx:#e8eaf0;--tx2:#8b8fa3;--gd:linear-gradient(135deg,#7c9cff,#a855f7)}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:var(--bg);color:var(--tx);display:flex;height:100vh;overflow:hidden}
.sb{width:260px;background:var(--bg2);border-right:1px solid #252936;padding:16px;display:flex;flex-direction:column}
.nc{width:100%;padding:12px;border-radius:12px;background:var(--bg3);color:var(--tx);border:none;cursor:pointer;font-weight:bold;margin-bottom:20px}
.ni{display:block;width:100%;text-align:left;padding:10px;color:var(--tx2);border:none;background:none;cursor:pointer;margin-top:5px;border-radius:8px}
.ni:hover,.ni.active{background:var(--bg3);color:var(--tx)}
.mn{flex:1;display:flex;flex-direction:column}
.hd{padding:20px;border-bottom:1px solid #252936;font-weight:bold;font-size:18px}
.cs{flex:1;overflow-y:auto;padding:20px}
.mr{display:flex;margin-bottom:15px;gap:10px;animation:fi .3s}.mr.user{flex-direction:row-reverse}
@keyframes fi{from{opacity:0}}
.ma{width:32px;height:32px;border-radius:50%;background:var(--gd);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;flex-shrink:0}
.mbb{padding:12px 16px;border-radius:16px;background:var(--bg3);max-width:80%;line-height:1.5;overflow-x:auto}
.mbb pre{background:#000;padding:10px;border-radius:8px}
.cw{padding:20px}
.cb{display:flex;background:var(--bg2);padding:10px;border-radius:12px;border:1px solid #252936}
.cb textarea{flex:1;background:none;border:none;color:var(--tx);outline:none;resize:none;font-size:15px}
.sd{background:var(--gd);color:#fff;border:none;padding:10px 15px;border-radius:8px;cursor:pointer;font-weight:bold}
.ao{position:fixed;inset:0;background:rgba(0,0,0,0.9);display:flex;align-items:center;justify-content:center;z-index:100}
.ao.hide{display:none}.ac2{background:var(--bg2);padding:40px;border-radius:20px;text-align:center}
.vv{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%}
.vo{width:120px;height:120px;border-radius:50%;background:var(--gd);display:flex;align-items:center;justify-content:center;font-size:40px;margin-bottom:20px}
</style></head><body>

<aside class="sb">
  <div style="font-size:20px;font-weight:800;margin-bottom:20px;">ARGON AI</div>
  <button class="nc" onclick="newChat()">+ नई बातचीत</button>
  <button class="ni active" onclick="switchView('chat')">💬 चैट</button>
  <button class="ni" onclick="switchView('movie')">🎬 मूवी</button>
  <button class="ni" onclick="switchView('voice')">🎙️ वॉइस</button>
  <div style="margin-top:30px;font-size:12px;color:var(--tx2)">हाल की बातें</div>
  <div id="sessionsList" style="flex:1;overflow-y:auto;font-size:13px;margin-top:10px"></div>
</aside>

<div class="mn">
  <div class="hd" id="ht">चैट</div>
  <div class="cs" id="cs"><div id="ci"></div></div>
  <div class="cw" id="chatArea"><div class="cb">
    <textarea id="chatInput" rows="1" placeholder="संदेश लिखें..."></textarea>
    <button class="sd" onclick="sendChat()">➤</button>
  </div></div>
  <div class="cw" id="movieArea" style="display:none">
    <div class="cb">
      <textarea id="movieTopic" rows="1" placeholder="मूवी का विषय लिखें..."></textarea>
      <button class="sd" onclick="startMovie()">बनाएं</button>
    </div>
    <div id="movieStatus" style="margin-top:10px;font-size:14px;color:var(--tx2)"></div>
  </div>
  <div class="vv" id="voiceArea" style="display:none">
    <div class="vo">🎤</div>
    <button class="sd" onclick="toggleVoice()" id="voiceBtn">Start Voice</button>
  </div>
</div>

<div class="ao" id="ao">
  <div class="ac2">
    <h2>Welcome to ARGON AI</h2>
    <p style="margin:20px 0;color:var(--tx2)">जारी रखने के लिए लॉगिन करें</p>
    <div id="g_id_onload" data-client_id="__GOOGLE_CLIENT_ID__" data-callback="handleCredentialResponse"></div>
    <div class="g_id_signin" data-type="standard" data-theme="filled_black" data-size="large" data-shape="pill"></div>
  </div>
</div>

<script>
let currentSessionId = "", isSending = false;
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/me').then(r => { if(r.ok) { hideAuth(); loadSessions(); } else showAuth(); }).catch(showAuth);
});
function showAuth(){document.getElementById('ao').classList.remove('hide')}
function hideAuth(){document.getElementById('ao').classList.add('hide')}
function handleCredentialResponse(r){fetch('/auth/google',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({credential:r.credential})}).then(x=>x.json()).then(d=>{if(d.success){hideAuth();loadSessions();}else alert('Login Failed')})}
function switchView(v) {
    document.getElementById('chatArea').style.display='none';
    document.getElementById('movieArea').style.display='none';
    document.getElementById('voiceArea').style.display='none';
    document.getElementById('cs').style.display='none';
    if(v === 'chat') { document.getElementById('chatArea').style.display='block'; document.getElementById('cs').style.display='block'; document.getElementById('ht').innerText='चैट'; }
    if(v === 'movie') { document.getElementById('movieArea').style.display='block'; document.getElementById('ht').innerText='मूवी फैक्ट्री'; }
    if(v === 'voice') { document.getElementById('voiceArea').style.display='flex'; document.getElementById('ht').innerText='लाइव वॉइस'; }
}
async function loadSessions() {
    const r = await fetch('/api/chat/sessions'); const d = await r.json();
    const list = document.getElementById('sessionsList'); list.innerHTML = '';
    if(d.sessions.length === 0) return newChat();
    d.sessions.forEach(s => {
        const div = document.createElement('div'); div.className = 'ni'; div.innerText = s.title;
        div.onclick = () => { currentSessionId = s.id; loadHistory(); };
        list.appendChild(div);
        if(!currentSessionId) { currentSessionId = s.id; loadHistory(); }
    });
}
async function newChat() {
    const r = await fetch('/api/chat/session', {method: 'POST'}); const d = await r.json();
    currentSessionId = d.session_id; document.getElementById('ci').innerHTML = ''; loadSessions();
}
async function loadHistory() {
    const r = await fetch('/api/chat/history/' + currentSessionId); const d = await r.json();
    const c = document.getElementById('ci'); c.innerHTML = '';
    d.history.forEach(h => {
        const div = document.createElement('div'); div.className = 'mr ' + (h.role === 'user' ? 'user' : 'ai');
        div.innerHTML = `<div class="ma">${h.role === 'user' ? 'U' : 'A'}</div><div class="mbb">${h.role==='model'?DOMPurify.sanitize(marked.parse(h.content)):h.content}</div>`;
        c.appendChild(div);
    });
    document.getElementById('cs').scrollTop = document.getElementById('cs').scrollHeight;
}
async function sendChat() {
    if(isSending || !currentSessionId) return;
    const input = document.getElementById('chatInput'), msg = input.value.trim();
    if(!msg) return; isSending = true; input.value = '';
    const c = document.getElementById('ci');
    c.innerHTML += `<div class="mr user"><div class="ma">U</div><div class="mbb">${msg}</div></div>`;
    const aiDiv = document.createElement('div'); aiDiv.className = 'mr ai';
    aiDiv.innerHTML = `<div class="ma">A</div><div class="mbb" id="aiBubble">...</div>`;
    c.appendChild(aiDiv); document.getElementById('cs').scrollTop = document.getElementById('cs').scrollHeight;
    try {
        const res = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg, session_id:currentSessionId})});
        if(!res.ok) throw new Error('Server Error ' + res.status);
        const reader = res.body.getReader(); const decoder = new TextDecoder();
        let fullText = "", buffer = "";
        while(true) {
            const {done, value} = await reader.read(); if(done) break;
            buffer += decoder.decode(value, {stream:true});
            let lines = buffer.split('\n\n'); buffer = lines.pop();
            for(let line of lines) {
                if(line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if(data.error) throw new Error(data.error);
                        if(data.text) {
                            fullText += data.text;
                            document.getElementById('aiBubble').innerHTML = DOMPurify.sanitize(marked.parse(fullText));
                            document.getElementById('cs').scrollTop = document.getElementById('cs').scrollHeight;
                        }
                    } catch(e) {}
                }
            }
        }
    } catch(e) { document.getElementById('aiBubble').innerText = "❌ " + e.message; }
    isSending = false;
}
async function startMovie() {
    const topic = document.getElementById('movieTopic').value.trim(); if(!topic) return;
    document.getElementById('movieStatus').innerText = "⏳ शुरू हो रहा है...";
    const r = await fetch('/api/movie/start', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic})});
    if(!r.ok) { document.getElementById('movieStatus').innerText = "❌ API Error"; return; }
    const d = await r.json();
    const timer = setInterval(async () => {
        const s = await (await fetch('/api/movie/status/' + d.job_id)).json();
        document.getElementById('movieStatus').innerText = `${s.message || s.status} (${s.progress}%)`;
        if(s.status === 'completed') {
            clearInterval(timer);
            const url = await (await fetch('/media/' + s.filename)).json();
            document.getElementById('movieStatus').innerHTML = `<br><video src="${url.url}" controls width="100%"></video>`;
        }
        if(s.status === 'failed') { clearInterval(timer); document.getElementById('movieStatus').innerText = "❌ " + s.error; }
    }, 3000);
}
let ws, audioCtx, isVoice = false;
function toggleVoice() {
    if(isVoice) { isVoice = false; ws.close(); audioCtx.close(); document.getElementById('voiceBtn').innerText = 'Start Voice'; return; }
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws/voice`);
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    ws.onopen = async () => {
        isVoice = true; document.getElementById('voiceBtn').innerText = 'Stop Voice';
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});
        const source = audioCtx.createMediaStreamSource(stream);
        const processor = audioCtx.createScriptProcessor(512, 1, 1);
        processor.onaudioprocess = (e) => {
            if(!isVoice) return;
            const input = e.inputBuffer.getChannelData(0);
            const pcm16 = new Int16Array(input.length);
            for(let i=0; i<input.length; i++) { let x = Math.max(-1, Math.min(1, input[i])); pcm16[i] = x < 0 ? x * 0x8000 : x * 0x7FFF; }
            ws.send(JSON.stringify({type: 'audio', data: btoa(String.fromCharCode(...new Uint8Array(pcm16.buffer)))}));
        };
        source.connect(processor); processor.connect(audioCtx.destination);
    };
    ws.onmessage = (e) => {
        const m = JSON.parse(e.data);
        if(m.type === 'audio') {
            const raw = atob(m.data), arr = new Uint8Array(raw.length);
            for(let i=0; i<raw.length; i++) arr[i] = raw.charCodeAt(i);
            const buf = audioCtx.createBuffer(1, arr.length/2, 24000), d = buf.getChannelData(0), v = new DataView(arr.buffer);
            for(let i=0; i<d.length; i++) d[i] = v.getInt16(i*2, true) / 32768;
            const src = audioCtx.createBufferSource(); src.buffer = buf; src.connect(audioCtx.destination); src.start();
        }
    };
}
</script></body></html>
"""
