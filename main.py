import os, json, time, uuid, base64, logging, asyncio, tempfile, shutil, subprocess, math, textwrap
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import jwt, boto3, edge_tts
from botocore.client import Config as BotoConfig
from fastapi import FastAPI, Request, Response, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, Integer, select, update, delete

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ARGON")

# ============ CONFIG ============
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

# ✅ आपके बताए नए मॉडल्स (3.8)
CHAT_MODEL  = os.getenv("CHAT_MODEL",  "gemini-3.8-flash")
LIVE_MODEL  = os.getenv("LIVE_MODEL",  "gemini-3.8-live")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-001")

# ✅ बैकअप मॉडल्स (अगर 3.8 काम न करे तो)
FALLBACK_CHAT = "gemini-2.0-flash"
FALLBACK_LIVE = "gemini-2.0-flash-exp"

JWT_ALGORITHM = "HS256"
JWT_LIFETIME = 86400

if not GEMINI_API_KEY: raise RuntimeError("GEMINI_API_KEY missing")
if not DATABASE_URL: raise RuntimeError("DATABASE_URL missing")

# ============ DATABASE ============
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

# ============ STORAGE ============
def get_s3():
    return boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, config=BotoConfig(signature_version="s3v4"), region_name="auto")

def upload_file(filepath, key, content_type="application/octet-stream"):
    get_s3().upload_file(filepath, R2_BUCKET_NAME, key, ExtraArgs={'ContentType': content_type})
    return key

def presigned_url(key, expires_in=3600):
    return get_s3().generate_presigned_url("get_object", Params={"Bucket": R2_BUCKET_NAME, "Key": key}, ExpiresIn=expires_in)

# ============ AUTH ============
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

# ============ AI LOGIC (Fallback System) ============
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

async def gemini_chat_stream(history, message):
    contents = [{"role": "user" if i["role"]=="user" else "model", "parts":[{"text": i["content"]}]} for i in history]
    contents.append({"role": "user", "parts": [{"text": message}]})
    
    # ✅ Fallback System: पहले 3.8 ट्राई करेगा, फेल होने पर 2.0
    for model in [CHAT_MODEL, FALLBACK_CHAT]:
        try:
            response = await gemini_client.aio.models.generate_content_stream(
                model=model, contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="You are ARGON AI.", 
                    tools=[types.Tool(google_search=types.GoogleSearch())]))
            async for chunk in response:
                if chunk.text: yield chunk.text
            return # सफल होने पर बाहर निकल जाओ
        except Exception as e:
            log.warning(f"Model {model} failed: {e}. Trying fallback...")
            if model == FALLBACK_CHAT: # अगर बैकअप भी फेल हो जाए
                yield "\n\n⚠️ AI सर्वर से कनेक्ट नहीं हो पा रहा है। कृपया API Key और मॉडल एक्सेस चेक करें।"

async def gemini_image_bytes(prompt):
    try:
        result = await gemini_client.aio.models.generate_images(model=IMAGE_MODEL, prompt=prompt, config=types.GenerateImagesConfig(number_of_images=1))
        if result.generated_images: return result.generated_images[0].image.image_bytes
        raise RuntimeError("No image")
    except Exception as e:
        log.error(f"Image Error: {e}")
        raise HTTPException(500, "Image generation failed. API key or model issue.")

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

# ============ MOVIE FACTORY ============
async def run_movie_job(job_id, user_id, topic):
    async with AsyncSessionLocal() as db:
        await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(status="processing", progress=10, message="Starting..."))
        await db.commit()

    tmpdir = tempfile.mkdtemp()
    try:
        prompt = f'Create Hindi script about: {topic}. Return JSON: {{"scenes":[{{"text":"...","image_desc":"..."}}]}}. Exactly 3 scenes.'
        
        # ✅ Fallback System for Movie
        res = None
        for model in [CHAT_MODEL, FALLBACK_CHAT]:
            try:
                res = await gemini_client.aio.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                break
            except Exception as e:
                log.warning(f"Movie model {model} failed: {e}")
                
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
            await db.execute(update(MovieJob).where(MovieJob.job_id == job_id).values(status="failed", error="Video generation failed. Server error."))
            await db.commit()
    finally: shutil.rmtree(tmpdir, ignore_errors=True)

# ============ APP SETUP ============
@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Global Error: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# ============ ROUTES ============
class GoogleLogin(BaseModel): credential: str
class ChatInput(BaseModel): message: str; session_id: str
class ImageInput(BaseModel): prompt: str
class MovieInput(BaseModel): topic: str

@app.post("/auth/google")
async def auth_google(data: GoogleLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try: idinfo = id_token.verify_oauth2_token(data.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as e: 
        log.error(f"Login Error: {e}")
        raise HTTPException(401, "Invalid token")
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
    
    # ✅ Fallback for Live Voice
    cfg = types.LiveConnectConfig(response_modalities=["AUDIO"])
    session = None
    for model in [LIVE_MODEL, FALLBACK_LIVE]:
        try:
            session = await gemini_client.aio.live.connect(model=model, config=cfg).__aenter__()
            break
        except Exception as e:
            log.warning(f"Live model {model} failed: {e}")
    
    if not session:
        await ws.close(code=1008); return

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
        await ws.close()

# ============ FRONTEND HTML ============
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
.nc{width:100%;padding:12px;border-radius:12px;background:va
