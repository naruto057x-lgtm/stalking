import asyncio
import io
import json
import logging
import os
import sys
import traceback
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands
import motor.motor_asyncio
from playwright.async_api import async_playwright

# ==================== تأكيد البدء ====================
print("🚀 Descord.py script started (Unified Selfbot - Ultimate Design - AntiBan Edition)", flush=True)

# ==================== الإعدادات الأساسية ====================
USER_TOKEN = os.getenv("USER_TOKEN")
if not USER_TOKEN:
    print("❌ USER_TOKEN is required! Exiting.", flush=True)
    sys.exit(1)

# ضع هنا أيديهات الأشخاص اللي بتراقبهم
TARGET_USER_IDS = [
    "1249754394417696801",
    "1378070979401486391"
]

# أيديهات الرومات
ACTIVITY_CHANNEL_ID = 1535834292502929468
ONLINE_CHANNEL_ID   = 1535834924958089286
CHANGES_CHANNEL_ID  = 1509353152724340846
COMMANDS_CHANNEL_ID = 1509464730509643846
SERVER_ID = 1516638407919669290

# رابط قاعدة البيانات
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://...")

# ==================== نظام التسجيل ====================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug.log", mode='a')
    ]
)
logger = logging.getLogger("descord_selfbot")
logger.setLevel(logging.DEBUG)


def log_step(step: str, message: str, **details):
    detail_text = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    if detail_text:
        logger.info("[DEBUG] %s | %s | %s", step, message, detail_text)
    else:
        logger.info("[DEBUG] %s | %s", step, message)


def log_exception(context: str, exc: Exception, **details):
    detail_text = " | ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    if detail_text:
        logger.exception("[ERROR] %s | %s | %s", context, exc, detail_text)
    else:
        logger.exception("[ERROR] %s | %s", context, exc)

# ==================== دوال الوقت ====================
def get_egypt_time(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    cairo = ZoneInfo("Africa/Cairo")
    local = dt.astimezone(cairo)
    return local.strftime("%I:%M %p, %A, %B %d, %Y (GMT+3)")

# ==================== دوال HTTP مع التصميم الاحترافي ====================
BASE_API = "https://discord.com/api/v10"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "Authorization": USER_TOKEN,
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT,
    "Accept": "application/json"
}
UPLOAD_HEADERS = {
    "Authorization": USER_TOKEN,
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9"
}

DEBUG_DUMP_DIR = os.getenv("DEBUG_DUMP_DIR", "debug_dumps")
os.makedirs(DEBUG_DUMP_DIR, exist_ok=True)

async def save_page_debug_screenshot(page, label: str, user_id: str):
    try:
        filename = os.path.join(DEBUG_DUMP_DIR, f"page_{label}_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.png")
        await page.screenshot(path=filename, full_page=True)
        logger.info(f"DEBUG_PAGESHOT_SAVED | {filename}")
    except Exception as exc:
        log_exception("save_page_debug_screenshot", exc, user_id=user_id, label=label)

async def capture_page_debug_state(page, label: str, user_id: str):
    try:
        url = page.url
        title = await page.title()
        cookies = await page.context.cookies()
        content_snippet = await page.content()
        try:
            local_storage = await page.evaluate(
                "() => {\n"
                "  try {\n"
                "    return JSON.stringify(Object.fromEntries(Object.entries(window.localStorage)));\n"
                "  } catch (e) {\n"
                "    return `LOCAL_STORAGE_ERROR:${e.message}`;\n"
                "  }\n"
                "}"
            )
        except Exception as storage_exc:
            local_storage = f"LOCAL_STORAGE_EVAL_FAILED:{storage_exc}"

        try:
            storage_state = await page.context.storage_state()
            storage_state = json.dumps(storage_state, default=str)
        except Exception as state_exc:
            storage_state = f"STORAGE_STATE_FAILED:{state_exc}"

        debug_text = (
            f"--- DEBUG STATE [{label}] ---\n"
            f"user_id={user_id}\n"
            f"url={url}\n"
            f"title={title}\n"
            f"cookies={json.dumps(cookies, default=str)}\n"
            f"localStorage={local_storage}\n"
            f"storageState={storage_state}\n"
            f"content_snippet={content_snippet[:2500]}\n"
        )
        filename = os.path.join(DEBUG_DUMP_DIR, f"debug_{label}_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.txt")
        with open(filename, "w", encoding="utf-8") as dump_file:
            dump_file.write(debug_text)
        logger.info(f"DEBUG_DUMP_SAVED | {filename}")
    except Exception as exc:
        log_exception("capture_page_debug_state", exc, user_id=user_id, label=label)

async def capture_page_summary(page, label: str, user_id: str):
    try:
        url = page.url
        title = await page.title()
        local_storage = "unavailable"
        try:
            raw_ls = await page.evaluate(
                "() => { try { return JSON.stringify(Object.fromEntries(Object.entries(window.localStorage))); } catch (e) { return `LOCAL_STORAGE_ERROR:${e.message}`; } }"
            )
            if raw_ls and raw_ls.startswith("LOCAL_STORAGE_ERROR"):
                local_storage = raw_ls
            else:
                parsed = json.loads(raw_ls or "{}")
                local_storage = f"keys={len(parsed)} names={list(parsed.keys())[:6]}"
        except Exception as storage_exc:
            local_storage = f"LOCAL_STORAGE_EVAL_FAILED:{storage_exc}"

        logger.info(
            f"DEBUG_SUMMARY | {label} | user={user_id} | url={url} | title={title} | localStorage={local_storage}"
        )
    except Exception as exc:
        log_exception("capture_page_summary", exc, user_id=user_id, label=label)


def embed_to_text(embed: discord.Embed) -> str:
    """تحويل بيانات الـ Embed إلى تصميم نصي (Markdown) احترافي مدعوم للـ Selfbot"""
    lines = []
    
    if embed.title:
        lines.append(f"### {embed.title}")
        
    if embed.description:
        lines.append(embed.description)
        
    if embed.fields:
        lines.append("")
        for f in embed.fields:
            val = str(f.value).replace('\n', '\n> ')
            lines.append(f"**{f.name}**\n> {val}\n")
            
    if embed.footer:
        lines.append(f"-# {embed.footer.text}")
        
    return "\n".join(lines).strip()

async def human_delay():
    """محاكاة تأخير بشري قبل إرسال الرسائل (من 1.5 إلى 4 ثواني)"""
    delay = random.uniform(1.5, 4.0)
    await asyncio.sleep(delay)

async def send_message(channel_id: int, embed: discord.Embed) -> int:
    """إرسال الرسالة المنسقة إلى القناة مع تأخير بشري"""
    log_step("HTTP_SEND", "Preparing to send embed message", channel_id=channel_id, embed_title=getattr(embed, "title", None))
    try:
        await human_delay()
        url = f"{BASE_API}/channels/{channel_id}/messages"
        payload = {"content": embed_to_text(embed)}
        log_step("HTTP_SEND", "Sending embed payload", channel_id=channel_id, payload_length=len(payload["content"]))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    message_id = int(data.get("id", 0) or 0)
                    logger.info(f"✅ Sent message to channel {channel_id} | message_id={message_id}")
                    log_step("HTTP_SEND", "Embed message sent successfully", channel_id=channel_id, message_id=message_id)
                    return message_id
                else:
                    text = await resp.text()
                    logger.error(f"❌ Failed to send message: {resp.status} {text}")
                    log_step("HTTP_SEND", "Embed message send failed", channel_id=channel_id, status=resp.status, response=text)
                    return 0
    except Exception as exc:
        log_exception("send_message", exc, channel_id=channel_id)
        return 0

async def edit_message(channel_id: int, message_id: int, embed: discord.Embed):
    """تعديل رسالة موجودة بنص جديد"""
    log_step("HTTP_EDIT", "Preparing to edit existing message", channel_id=channel_id, message_id=message_id)
    try:
        await human_delay()
        url = f"{BASE_API}/channels/{channel_id}/messages/{message_id}"
        payload = {"content": embed_to_text(embed)}
        log_step("HTTP_EDIT", "Editing payload", channel_id=channel_id, message_id=message_id, payload_length=len(payload["content"]))
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=HEADERS, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"✏️ Edited message {message_id}")
                    log_step("HTTP_EDIT", "Message edited successfully", channel_id=channel_id, message_id=message_id)
                else:
                    text = await resp.text()
                    logger.error(f"❌ Failed to edit message: {resp.status} {text}")
                    log_step("HTTP_EDIT", "Message edit failed", channel_id=channel_id, message_id=message_id, status=resp.status, response=text)
    except Exception as exc:
        log_exception("edit_message", exc, channel_id=channel_id, message_id=message_id)

async def send_message_with_file(channel_id: int, embed: discord.Embed, file_bytes: io.BytesIO, filename: str):
    """إرسال رسالة مع صورة (لقطة الشاشة)"""
    log_step("HTTP_FILE", "Preparing to send file message", channel_id=channel_id, filename=filename, file_size=file_bytes.getbuffer().nbytes)
    try:
        await human_delay()
        url = f"{BASE_API}/channels/{channel_id}/messages"
        form = aiohttp.FormData()
        
        payload = {"content": embed_to_text(embed)}
        form.add_field("payload_json", json.dumps(payload), content_type="application/json")
        form.add_field("file", file_bytes.getvalue(), filename=filename, content_type="image/png")
        log_step("HTTP_FILE", "Uploading file payload", channel_id=channel_id, filename=filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=UPLOAD_HEADERS, data=form) as resp:
                response_text = await resp.text()
                if resp.status in (200, 201):
                    try:
                        data = json.loads(response_text)
                        message_id = int(data.get("id", 0) or 0)
                    except Exception:
                        message_id = 0
                    logger.info(f"📸 Sent message with screenshot file | channel={channel_id} | filename={filename} | bytes={file_bytes.getbuffer().nbytes} | message_id={message_id}")
                    log_step("HTTP_FILE", "File message sent successfully", channel_id=channel_id, filename=filename, bytes=file_bytes.getbuffer().nbytes, message_id=message_id)
                    return message_id
                else:
                    logger.error(f"❌ File upload failed | status={resp.status} | channel={channel_id} | filename={filename}")
                    log_step("HTTP_FILE", "File message send failed", channel_id=channel_id, filename=filename, status=resp.status, response=response_text[:1000])
                    logger.error(f"HTTP_FILE_RESPONSE | {response_text[:1000]}")
                    return 0
    except Exception as exc:
        log_exception("send_message_with_file", exc, channel_id=channel_id, filename=filename)
        return 0

async def send_text_message(channel_id: int, text: str) -> int:
    """إرسال رسالة نصية بسيطة عبر HTTP"""
    log_step("HTTP_TEXT", "Preparing to send text message", channel_id=channel_id, text_length=len(text))
    try:
        await human_delay()
        url = f"{BASE_API}/channels/{channel_id}/messages"
        payload = {"content": text}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                raw = await resp.text()
                if resp.status in (200, 201):
                    try:
                        data = json.loads(raw)
                        message_id = int(data.get("id", 0) or 0)
                    except Exception:
                        message_id = 0
                    logger.info(f"💬 Sent text message to channel {channel_id} | message_id={message_id}")
                    log_step("HTTP_TEXT", "Text message sent successfully", channel_id=channel_id, message_id=message_id)
                    return message_id
                else:
                    logger.error(f"❌ Failed to send text message: {resp.status} {raw}")
                    log_step("HTTP_TEXT", "Text message send failed", channel_id=channel_id, status=resp.status, response=raw)
                    return 0
    except Exception as exc:
        log_exception("send_text_message", exc, channel_id=channel_id)
        return 0

class SimpleCommandContext:
    def __init__(self, message: discord.Message):
        self.message = message
        self.channel = message.channel
        self.author = message.author
        self.guild = getattr(message, "guild", None)
        self.bot = bot

    async def send(self, content: str = None, *, embed: discord.Embed = None):
        if embed is not None:
            await send_message(self.channel.id, embed)
            return
        if content is None:
            return
        await send_text_message(self.channel.id, str(content))

# ==================== إعداد البوت و MongoDB ====================
try:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.presences = True
    intents.guilds = True
    intents.members = True
except AttributeError:
    intents = None
    logger.warning("discord.Intents is unavailable in this environment; continuing without explicit intents.")

bot_kwargs = {"command_prefix": "!", "self_bot": True}
if intents is not None:
    bot_kwargs["intents"] = intents

bot = commands.Bot(**bot_kwargs)
bot.remove_command("help")

try:
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client["discord_monitor"]
    profile_cache_col = db["profile_cache"]
    online_msgs_col = db["online_messages"]
    activity_msgs_col = db["activity_messages"]
    last_seen_col = db["last_seen"]
    last_activity_col = db["last_activity"]
    logger.info("✅ MongoDB client initialized successfully")
except Exception as e:
    logger.error(f"❌ MongoDB initialization failed: {e}")
    sys.exit(1)

active_online_msgs = {}
active_activity_msgs = {}
current_activities = {}
current_status = {}
pending_offline_tasks = {}
screenshot_queue = asyncio.Queue()

# ==================== دوال جلب البيانات ====================
async def fetch_user_data(user_id: str) -> dict | None:
    log_step("USER_FETCH", "Attempting to fetch user profile data", user_id=user_id)
    endpoints = [
        f"{BASE_API}/users/{user_id}/profile",
        f"{BASE_API}/users/{user_id}"
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                async with session.get(endpoint, headers=HEADERS) as resp:
                    status = resp.status
                    body = await resp.text()
                    log_step("USER_FETCH", "Received profile response", user_id=user_id, endpoint=endpoint, status=status)
                    if status == 200:
                        payload = json.loads(body) if body else {}
                        if endpoint.endswith("/profile"):
                            payload = payload.get("user") or payload
                        if isinstance(payload, dict):
                            return {
                                "id": str(payload.get("id") or user_id),
                                "username": payload.get("username"),
                                "global_name": payload.get("global_name"),
                                "bio": payload.get("bio") or payload.get("about") or None,
                                "avatar": payload.get("avatar") or None,
                                "banner": payload.get("banner") or None,
                                "clan": payload.get("clan") or None,
                                "avatar_decoration_data": payload.get("avatar_decoration_data") or None,
                            }
                    else:
                        log_step("USER_FETCH", "Profile request failed", user_id=user_id, endpoint=endpoint, status=status, response=body[:500])
            except Exception as exc:
                log_exception("fetch_user_data", exc, user_id=user_id, endpoint=endpoint)
    return None


def normalize_user_id(user_id: str | None) -> str | None:
    if not user_id:
        return None
    candidate = user_id.strip()
    lowered = candidate.lower()
    if lowered in {"all", "both"}:
        return "all"
    if candidate.startswith("<@") and candidate.endswith(">"):
        candidate = candidate.replace("<@", "").replace("!", "").replace(">", "")
    return candidate


def get_command_user_ids(user_id: str | None) -> list[str]:
    normalized = normalize_user_id(user_id)
    if not normalized or normalized == "all":
        return TARGET_USER_IDS[:]
    if normalized in TARGET_USER_IDS:
        return [normalized]
    return [normalized]


def get_server_member(user_id: str) -> discord.Member | None:
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        return None
    try:
        return guild.get_member(int(user_id))
    except Exception:
        return None

async def take_profile_screenshot(user_id: str) -> io.BytesIO:
    try:
        log_step("SCREENSHOT", "Start capture process", user_id=user_id)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            log_step("SCREENSHOT", "Browser launched", user_id=user_id)

            storage_state = {
                "cookies": [],
                "origins": [
                    {
                        "origin": "https://discord.com",
                        "localStorage": [
                            {"name": "token", "value": f'"{USER_TOKEN}"'}
                        ]
                    }
                ]
            }

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=2,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                storage_state=storage_state
            )
            log_step("SCREENSHOT", "Browser context created with storage_state", user_id=user_id)

            stealth_script = (
                "() => {"
                "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
                "window.chrome = { runtime: {} };"
                "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});"
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});"
                "const originalQuery = navigator.permissions.query.bind(navigator.permissions);"
                "navigator.permissions.query = parameters => parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters);"
                "};"
            )
            await context.add_init_script(script=stealth_script)

            auth_token_json = json.dumps(f'"{USER_TOKEN}"')
            await context.add_init_script(f"window.localStorage.setItem('token', {auth_token_json});")
            log_step("SCREENSHOT", "Injected Discord auth token init script", user_id=user_id)

            page = await context.new_page()
            log_step("SCREENSHOT", "Page created", user_id=user_id)

            await page.goto("https://discord.com/channels/@me", wait_until="networkidle", timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await capture_page_summary(page, "initial_navigate", user_id)

            if "discord.com/login" in page.url or page.url.endswith("/login"):
                logger.info(f"SCREENSHOT | Login page detected after initial navigation, retrying profile navigation | user={user_id} | url={page.url}")
                await page.evaluate(f"window.localStorage.setItem('token', {auth_token_json});")
                await page.goto(f"https://discord.com/users/{user_id}", wait_until="networkidle", timeout=60000)
            else:
                await page.goto(f"https://discord.com/users/{user_id}", wait_until="networkidle", timeout=60000)

            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await capture_page_summary(page, "profile_page_navigate", user_id)

            if "discord.com/login" in page.url or page.url.endswith("/login"):
                logger.warning(f"STORAGE_STATE_FAILED | login page still visible after profile navigation | user={user_id} | url={page.url}")
                await capture_page_debug_state(page, "storage_state_login_failure", user_id)
                await save_page_debug_screenshot(page, "storage_state_login_failure", user_id)
                raise RuntimeError(f"Authentication failed after storage_state injection for user {user_id}")

            try:
                await page.locator("div[class*='profile']").first.wait_for(timeout=20000)
                log_step("SCREENSHOT", "Profile area detected", user_id=user_id, page_url=page.url)
            except Exception as selector_exc:
                logger.warning(f"Profile area not detected for {user_id}; may still be login or page changed | url={page.url}")
                log_exception("SCREENSHOT_SELECTOR_TIMEOUT", selector_exc, user_id=user_id, page_url=page.url)
                await capture_page_summary(page, "profile_selector_missing", user_id)

            screenshot = await page.screenshot(full_page=True)
            screenshot_length = len(screenshot)
            log_step("SCREENSHOT", "Screenshot taken", user_id=user_id, size=screenshot_length, page_url=page.url)

            if screenshot_length == 0:
                logger.error(f"SCREENSHOT_EMPTY_IMAGE | user={user_id} | url={page.url}")
                await save_page_debug_screenshot(page, "empty_screenshot_failure", user_id)
                await capture_page_debug_state(page, "empty_screenshot_failure", user_id)
                await browser.close()
                return io.BytesIO(b'')

            await browser.close()
            log_step("SCREENSHOT", "Capture completed successfully", user_id=user_id, size=screenshot_length)
            return io.BytesIO(screenshot)
    except Exception as e:
        log_exception("take_profile_screenshot", e, user_id=user_id)
        return io.BytesIO(b'')

async def schedule_offline_confirmation(user_id: str, started: datetime):
    await asyncio.sleep(600)
    if current_status.get(user_id) != discord.Status.offline:
        return
    online_data = active_online_msgs.get(user_id)
    if not online_data:
        return

    end_time = datetime.now(timezone.utc)
    duration = str(end_time - started).split(".")[0]
    embed = discord.Embed(
        title="🔴 Session Confirmed Ended",
        description=f"<@{user_id}> remained offline for 10 minutes and the session has ended."
    )
    embed.add_field(name="Session Started", value=get_egypt_time(started), inline=False)
    embed.add_field(name="Session Ended", value=get_egypt_time(end_time), inline=False)
    embed.add_field(name="Total Duration", value=f"⏱️ **{duration}**", inline=False)
    if online_data.get("avatar_url"):
        embed.set_thumbnail(url=online_data["avatar_url"])
    if online_data.get("username"):
        embed.set_footer(text=f"{online_data['username']} • Last checked {get_egypt_time()}")

    if online_data.get("msg_id"):
        await edit_message(ONLINE_CHANNEL_ID, online_data["msg_id"], embed)
    else:
        await send_message(ONLINE_CHANNEL_ID, embed)

    active_online_msgs.pop(user_id, None)
    pending_offline_tasks.pop(user_id, None)
    await online_msgs_col.delete_one({"_id": user_id})
    await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_offline": end_time}}, upsert=True)

# ==================== أحداث البوت الأساسية ====================
@bot.before_invoke
async def log_command_start(ctx):
    log_step("COMMAND", "Command invocation started", command=ctx.command.name if ctx.command else "unknown", author=ctx.author.id if ctx.author else None, channel=ctx.channel.id if ctx.channel else None, content=ctx.message.content)

@bot.after_invoke
async def log_command_end(ctx):
    log_step("COMMAND", "Command invocation completed", command=ctx.command.name if ctx.command else "unknown", author=ctx.author.id if ctx.author else None, channel=ctx.channel.id if ctx.channel else None)

@bot.event
async def on_command_error(ctx, error):
    logger.exception("[COMMAND] Command raised an exception | command=%s | author=%s | channel=%s | error=%s", ctx.command.name if ctx.command else "unknown", ctx.author.id if ctx.author else None, ctx.channel.id if ctx.channel else None, error)

@bot.event
async def on_ready():
    logger.info(f"👤 Selfbot logged in as {bot.user}")
    log_step("READY", "Bot is ready; sending startup notification", user=str(bot.user))

    try:
        embed = discord.Embed(
            title="⚡ Discord Monitor System Online",
            description=f"**Selfbot:** {bot.user.mention}\nAll systems are fully operational with Anti-Ban active.\nUse `!help` in this channel for commands."
        )
        embed.set_footer(text="System Initialized")
        await send_message(COMMANDS_CHANNEL_ID, embed)
    except Exception as exc:
        log_exception("on_ready startup message", exc)

    log_step("READY", "Starting background tasks", profile_loop=True, screenshot_worker=True)
    try:
        bot.loop.create_task(profile_check_loop())
        bot.loop.create_task(screenshot_worker())
    except Exception as exc:
        log_exception("on_ready background task start", exc)

@bot.event
async def on_message(message: discord.Message):
    log_step("MESSAGE", "Received message event", author_id=message.author.id if message.author else None, channel_id=message.channel.id if message.channel else None, content=message.content)

    try:
        if message.author.bot:
            log_step("MESSAGE", "Ignored message because the author is a bot or system account", author_id=message.author.id if message.author else None)
            return

        if message.channel.id != COMMANDS_CHANNEL_ID:
            log_step("MESSAGE", "Ignored message because channel is not the commands channel", channel_id=message.channel.id if message.channel else None, expected_channel_id=COMMANDS_CHANNEL_ID)
            return

        if not message.content.startswith("!"):
            log_step("MESSAGE", "Ignored message because it does not start with the command prefix", content=message.content)
            return

        content = message.content.strip()
        parts = content.split()
        command_name = parts[0][1:].lower()
        args = parts[1:]

        log_step("MESSAGE", "Routing command manually", command=command_name, args=args, author_id=message.author.id if message.author else None)

        ctx = SimpleCommandContext(message)

        if command_name in {"help", "commands", "cmd"}:
            log_step("COMMAND_ROUTE", "Executing help command", command=command_name, author_id=message.author.id)
            await custom_help(ctx)
        elif command_name == "status":
            log_step("COMMAND_ROUTE", "Executing status command", command=command_name, author_id=message.author.id)
            await status_check(ctx)
        elif command_name == "profile":
            log_step("COMMAND_ROUTE", "Executing profile command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _profile(ctx, args[0] if args else None)
        elif command_name == "about":
            log_step("COMMAND_ROUTE", "Executing about command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _about(ctx, args[0] if args else None)
        elif command_name == "ss":
            log_step("COMMAND_ROUTE", "Executing ss command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _ss(ctx, args[0] if args else None)
        elif command_name == "activity":
            log_step("COMMAND_ROUTE", "Executing activity command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _activity(ctx, args[0] if args else None)
        elif command_name == "lastseen":
            log_step("COMMAND_ROUTE", "Executing lastseen command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _lastseen(ctx, args[0] if args else None)
        elif command_name == "lastactivity":
            log_step("COMMAND_ROUTE", "Executing lastactivity command", command=command_name, author_id=message.author.id, user_id=args[0] if args else None)
            await _lastactivity(ctx, args[0] if args else None)
        else:
            log_step("COMMAND_ROUTE", "Unknown command received", command=command_name, author_id=message.author.id)
            await ctx.send(f"❌ Unknown command: `!{command_name}`")
    except Exception as exc:
        log_exception("on_message command handling", exc, command=content)

# ==================== الأوامر ====================
@bot.command(name="status")
async def status_check(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    
    embed = discord.Embed(title="📊 System Status Diagnostics")
    embed.add_field(name="🌐 Selfbot Connection", value="✅ Connected & Listening (Stealth Mode)", inline=False)
    
    channels = {
        "Activity Channel": ACTIVITY_CHANNEL_ID,
        "Online/Offline Channel": ONLINE_CHANNEL_ID,
        "Profile Changes Channel": CHANGES_CHANNEL_ID,
        "Commands Channel": COMMANDS_CHANNEL_ID
    }
    channels_status = "\n".join([f"{'✅' if bot.get_channel(cid) else '❌'} {name}" for name, cid in channels.items()])
    embed.add_field(name="📺 Channels Status", value=channels_status, inline=False)
    
    try:
        await mongo_client.admin.command("ping")
        embed.add_field(name="🗄️ MongoDB Database", value="✅ Connected successfully", inline=False)
    except:
        embed.add_field(name="🗄️ MongoDB Database", value="❌ Connection Error", inline=False)
        
    embed.set_footer(text=f"Requested at {get_egypt_time()}")
    await send_message(ctx.channel.id, embed)

@bot.command(name="help", aliases=["commands", "cmd"])
async def custom_help(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    
    embed = discord.Embed(title="📖 Available Monitoring Commands")
    embed.description = "اكتب أي أمر في القناة المخصصة للأوامر فقط. هذا البوت يتابع الأونلاين/أوفلاين والنشاطات والتغيرات في البروفايل."
    embed.add_field(name="`!profile [user_id]`", value="عرض تفاصيل كاملة عن البروفايل المراقب، مع معلومات الحساب الحالية.", inline=False)
    embed.add_field(name="`!about [user_id]`", value="عرض نص الـ About Me فقط لحساب المستخدم المطلوب.", inline=False)
    embed.add_field(name="`!ss [user_id]`", value="التقاط سكرين شوت حيّ لصفحة بروفايل المستخدم وإرسالها كصورة.", inline=False)
    embed.add_field(name="`!activity [user_id]`", value="عرض النشاطات الحالية للمستخدم ومدة كل نشاط.", inline=False)
    embed.add_field(name="`!lastseen [user_id]`", value="عرض آخر مرة كان المستخدم أونلاين فيها.", inline=False)
    embed.add_field(name="`!lastactivity [user_id]`", value="عرض آخر نشاط للمستخدم ومدة النشاط وزمن البداية والنهاية.", inline=False)
    embed.add_field(name="`!status`", value="عرض حالة البوت والرومات المتاحة.", inline=False)
    embed.set_footer(text="🕒 جميع الأوقات بتوقيت مصر GMT+3")
    await send_message(ctx.channel.id, embed)

@bot.command(name="profile")
async def _profile(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    embed = discord.Embed(title="👥 Profile Overview for Monitored Targets")
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")
    any_success = False

    for uid in user_ids:
        data = await fetch_user_data(uid)
        if not data:
            embed.add_field(name=f"<@{uid}>", value="❌ Failed to fetch profile data.", inline=False)
            continue

        any_success = True
        username = data.get("username", "Unknown")
        global_name = data.get("global_name") or "None"
        bio = data.get("bio") or "*No bio written*"

        clan = data.get("clan")
        clan_str = "*Not in a Clan*"
        if clan:
            clan_str = f"**₊ {clan.get('tag', 'No tag')}**"

        deco = data.get("avatar_decoration_data")
        deco_str = "*None*"
        if deco:
            deco_str = f"[Preview Link](https://cdn.discordapp.com/avatar-decorations/{deco.get('asset')}.png)"

        creation_str = get_egypt_time(datetime.fromtimestamp(((int(uid) >> 22) + 1420070400000) / 1000, tz=timezone.utc))
        member = get_server_member(uid)
        status_str = f"**Status:** {getattr(member, 'status', 'Unknown')}" if member else "**Status:** Unknown (server member not cached)"

        embed.add_field(
            name=f"<@{uid}> • {username}",
            value=f"{status_str}\n**Display Name:** {global_name}\n**Created On:** {creation_str}\n**Clan:** {clan_str}\n**Decoration:** {deco_str}\n\n**About:** {bio}",
            inline=False
        )

    if not any_success:
        return await ctx.send("❌ Could not fetch profile data for any requested user.")

    await send_message(ctx.channel.id, embed)

@bot.command(name="about")
async def _about(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    embed = discord.Embed(title="📝 About Me for Monitored Targets")
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")
    any_success = False

    for uid in user_ids:
        data = await fetch_user_data(uid)
        if not data:
            embed.add_field(name=f"<@{uid}>", value="❌ Failed to fetch about info.", inline=False)
            continue

        any_success = True
        bio = data.get("bio") or "*This user hasn't written an about me section.*"
        embed.add_field(name=f"<@{uid}>", value=bio, inline=False)

    if not any_success:
        return await ctx.send("❌ Could not fetch about information for any requested user.")

    await send_message(ctx.channel.id, embed)

@bot.command(name="ss")
async def _ss(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    for uid in user_ids:
        await ctx.send(f"📸 `Initiating screenshot capture for <@{uid}>... Please wait.`")
        await screenshot_queue.put((ctx, uid))

@bot.command(name="activity")
async def _activity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    embed = discord.Embed(title="🎯 Live Activity Status for Monitored Targets")
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")
    any_activity = False

    for uid in user_ids:
        acts = current_activities.get(uid, [])
        member = get_server_member(uid)
        if member and member.activities:
            act_list = [act for act in member.activities if act.type != discord.ActivityType.custom]
            if act_list:
                acts = act_list

        if not acts:
            embed.add_field(name=f"<@{uid}>", value="💤 No detectable activity right now.", inline=False)
            continue

        any_activity = True
        text_lines = []
        for act in acts:
            started = getattr(act, 'start', None) or datetime.now(timezone.utc)
            elapsed = str(datetime.now(timezone.utc) - started).split(".")[0] if started else "Unknown"
            text_lines.append(f"**{getattr(act, 'name', str(act))}**\nStarted at: {get_egypt_time(started)}\nElapsed: **{elapsed}**")

        embed.add_field(name=f"<@{uid}>", value="\n\n".join(text_lines), inline=False)

    if not any_activity and len(embed.fields) == 0:
        embed.add_field(name="Activity", value="No activities detected for the requested users.", inline=False)

    await send_message(ctx.channel.id, embed)

@bot.command(name="lastseen")
async def _lastseen(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    embed = discord.Embed(title="⏱️ Last Seen Status for Monitored Targets")
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")

    for uid in user_ids:
        member = get_server_member(uid)
        if member:
            status = getattr(member, 'status', 'Unknown')
            embed.add_field(name=f"<@{uid}>", value=f"Current status: **{status}**", inline=False)
            continue

        doc = await last_seen_col.find_one({"_id": uid})
        if not doc:
            embed.add_field(name=f"<@{uid}>", value="❌ No historical tracking data available yet.", inline=False)
            continue

        lines = []
        if doc.get("last_online"):
            lines.append(f"🟢 Last Online: {get_egypt_time(doc.get("last_online"))}")
        if doc.get("last_offline"):
            lines.append(f"🔴 Last Offline: {get_egypt_time(doc.get("last_offline"))}")
        embed.add_field(name=f"<@{uid}>", value="\n".join(lines) or "No last-seen history found.", inline=False)

    await send_message(ctx.channel.id, embed)

@bot.command(name="lastactivity")
async def _lastactivity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    user_ids = get_command_user_ids(user_id)
    if any(uid not in TARGET_USER_IDS for uid in user_ids):
        return await ctx.send("❌ One or more requested users are not in the target list.")

    embed = discord.Embed(title="📜 Last Activity History for Monitored Targets")
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")
    any_success = False

    for uid in user_ids:
        doc = await last_activity_col.find_one({"_id": uid})
        if not doc:
            embed.add_field(name=f"<@{uid}>", value="❌ No previous activities have been recorded.", inline=False)
            continue

        embed.add_field(
            name=f"<@{uid}>",
            value=f"🎮 **{doc.get('activity_name', 'Unknown')}**\n**Start:** {get_egypt_time(doc.get('start'))}\n**End:** {get_egypt_time(doc.get('end'))}\n**Duration:** ⏳ {doc.get('duration', 'Unknown')}",
            inline=False
        )

    await send_message(ctx.channel.id, embed)

# ==================== مراقبة الحالة والأنشطة (Live Monitoring) ====================
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    user_id = str(after.id)
    if user_id not in TARGET_USER_IDS: return
    now = datetime.now(timezone.utc)
    current_status[user_id] = after.status

    # 1. تتبع الأونلاين/أوفلاين
    if before.status != after.status:
        if after.status == discord.Status.online:
            # cancel any pending offline confirmation
            if user_id in pending_offline_tasks:
                try:
                    pending_offline_tasks[user_id].cancel()
                except Exception as e:
                    log_exception("CANCEL_PENDING_OFFLINE", e, user_id=user_id)
                pending_offline_tasks.pop(user_id, None)

            # only announce new online sessions once
            if user_id not in active_online_msgs:
                avatar_url = None
                try:
                    avatar_url = str(after.display_avatar.url)
                except Exception as e:
                    log_exception("AVATAR_URL_RESOLVE", e, user_id=user_id)
                    avatar_url = None

                embed = discord.Embed(
                    title="🟢 User is Online",
                    description=f"<@{user_id}> has connected to Discord.\n\n🕒 **Started at:** {get_egypt_time(now)}"
                )
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)
                embed.set_footer(text=f"Tracking online session for <@{user_id}>")

                # Primary send attempt
                try:
                    msg_id = await send_message(ONLINE_CHANNEL_ID, embed)
                    log_step("SEND_ONLINE", "Primary send_message returned", user_id=user_id, channel=ONLINE_CHANNEL_ID, msg_id=msg_id)
                except Exception as e:
                    msg_id = 0
                    log_exception("SEND_ONLINE_EXCEPTION", e, user_id=user_id, channel=ONLINE_CHANNEL_ID)

                # Fallback if primary send failed (msg_id is falsy)
                if not msg_id:
                    try:
                        text = f"🟢 <@{user_id}> is online • {get_egypt_time(now)}"
                        text_msg_id = await send_text_message(ONLINE_CHANNEL_ID, text)
                        msg_id = text_msg_id or msg_id
                        logger.warning(f"ONLINE_FALLBACK_TEXT_SENT | user={user_id} | channel={ONLINE_CHANNEL_ID} | message_id={text_msg_id}")
                    except Exception as e:
                        log_exception("SEND_ONLINE_FALLBACK", e, user_id=user_id, channel=ONLINE_CHANNEL_ID)

                # record session locally even if msg_id is falsy so we can later confirm
                active_online_msgs[user_id] = {
                    "msg_id": msg_id or None,
                    "start_time": now,
                    "avatar_url": avatar_url,
                    "username": after.display_name
                }
                try:
                    await online_msgs_col.update_one(
                        {"_id": user_id},
                        {"$set": {"msg_id": msg_id or None, "start_time": now}},
                        upsert=True
                    )
                except Exception as e:
                    log_exception("DB_UPDATE_ONLINE_MSG", e, user_id=user_id, msg_id=msg_id)

            # always update last seen time
            try:
                await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_online": now}}, upsert=True)
            except Exception as e:
                log_exception("DB_UPDATE_LAST_ONLINE", e, user_id=user_id, last_online=now)

        elif after.status == discord.Status.offline:
            online_data = active_online_msgs.get(user_id)
            if online_data:
                if user_id in pending_offline_tasks:
                    pending_offline_tasks[user_id].cancel()

                task = asyncio.create_task(schedule_offline_confirmation(user_id, online_data["start_time"]))
                pending_offline_tasks[user_id] = task
            else:
                await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_offline": now}}, upsert=True)
    before_acts = {act.name: act for act in before.activities if act.type != discord.ActivityType.custom}
    after_acts = {act.name: act for act in after.activities if act.type != discord.ActivityType.custom}
    
    started_acts = set(after_acts.keys()) - set(before_acts.keys())
    ended_acts = set(before_acts.keys()) - set(after_acts.keys())

    for name in started_acts:
        start = after_acts[name].start or now
        embed = discord.Embed(
            title="🎮 Activity Started",
            description=f"<@{user_id}> started playing **{name}**\n\n🕒 **Since:** {get_egypt_time(start)}"
        )
        msg_id = await send_message(ACTIVITY_CHANNEL_ID, embed)
        if msg_id:
            if user_id not in active_activity_msgs:
                active_activity_msgs[user_id] = {}
            active_activity_msgs[user_id][name] = msg_id
            await activity_msgs_col.insert_one({"user_id": user_id, "activity_key": name, "msg_id": msg_id, "start_time": start})
            
        if user_id not in current_activities: current_activities[user_id] = []
        current_activities[user_id].append({"name": name, "start_time": start})

    for name in ended_acts:
        doc = await activity_msgs_col.find_one({"user_id": user_id, "activity_key": name})
        dur_str = "unknown"
        start_time = None
        if doc:
            start_time = doc.get("start_time")
            dur_str = str(now - start_time).split(".")[0]

        embed = discord.Embed(
            title="🏁 Activity Ended",
            description=f"<@{user_id}> finished **{name}**"
        )
        if start_time: embed.add_field(name="Started", value=get_egypt_time(start_time), inline=False)
        embed.add_field(name="Ended", value=get_egypt_time(now), inline=False)
        embed.add_field(name="Time Spent", value=f"⏱️ **{dur_str}**", inline=False)

        if user_id in active_activity_msgs and name in active_activity_msgs[user_id]:
            msg_id = active_activity_msgs[user_id].pop(name)
            await edit_message(ACTIVITY_CHANNEL_ID, msg_id, embed)
            await activity_msgs_col.delete_one({"user_id": user_id, "activity_key": name})
            
        await last_activity_col.update_one(
            {"_id": user_id},
            {"$set": {"activity_name": name, "start": start_time, "end": now, "duration": dur_str}},
            upsert=True
        )
        if user_id in current_activities:
            current_activities[user_id] = [a for a in current_activities[user_id] if a["name"] != name]

# ==================== حلقات عمل الخلفية (Background Loops) ====================
async def profile_check_loop():
    """يفحص البروفايل بفترات عشوائية (حوالي دقيقة) لحماية الحساب من الحظر"""
    await bot.wait_until_ready()
    log_step("PROFILE_LOOP", "Profile surveillance loop started")
    
    try:
        startup_embed = discord.Embed(title="🔄 Profile Surveillance Activated", description="Checking target profiles stealthily (~ every 60s).")
        await send_message(CHANGES_CHANNEL_ID, startup_embed)
    except Exception as exc:
        log_exception("profile_check_loop startup notification", exc)
    
    while not bot.is_closed():
        for uid in TARGET_USER_IDS:
            log_step("PROFILE_LOOP", "Starting profile check cycle", user_id=uid)
            try:
                await asyncio.sleep(random.uniform(1.5, 3.5))
                data = await fetch_user_data(uid)
                if not data:
                    log_step("PROFILE_LOOP", "Profile fetch returned no data", user_id=uid)
                    continue
                
                log_step("PROFILE_LOOP", "Profile data fetched", user_id=uid, username=data.get("username"))
                cached = await profile_cache_col.find_one({"_id": uid})
                new_cache = {
                    "username": data.get("username"),
                    "global_name": data.get("global_name"),
                    "bio": data.get("bio"),
                    "avatar": data.get("avatar"),
                    "banner": data.get("banner"),
                    "clan_tag": data.get("clan", {}).get("tag") if data.get("clan") else None,
                    "avatar_decoration": data.get("avatar_decoration_data", {}).get("asset") if data.get("avatar_decoration_data") else None
                }

                changes = []
                if cached:
                    for key in new_cache:
                        if new_cache[key] != cached.get(key):
                            title = key.replace('_', ' ').title()
                            changes.append(f"**{title}**\n> 🛑 Old: `{cached.get(key)}`\n> ✅ New: `{new_cache[key]}`\n")
                            
                if changes or not cached:
                    if not cached:
                        changes.append("*System cached the initial profile data successfully.*")
                        log_step("PROFILE_LOOP", "No previous cache found; initial cache created", user_id=uid)
                        
                    await profile_cache_col.update_one({"_id": uid}, {"$set": new_cache}, upsert=True)
                    log_step("PROFILE_LOOP", "Profile cache updated", user_id=uid, changes_count=len(changes))
                    
                    embed = discord.Embed(
                        title="⚠️ Profile Update Detected", 
                        description=f"Changes found for <@{uid}>:\n\n" + "\n".join(changes)
                    )
                    embed.set_footer(text=f"Change recorded at {get_egypt_time()}")
                    log_step("PROFILE_LOOP", "Preparing profile change notification", user_id=uid, change_text="\n".join(changes))
                    
                    screenshot = await take_profile_screenshot(uid)
                    if screenshot.getbuffer().nbytes > 0:
                        log_step("PROFILE_LOOP", "Sending profile screenshot notification", user_id=uid)
                        await send_message_with_file(CHANGES_CHANNEL_ID, embed, screenshot, f"update_{uid}.png")
                    else:
                        log_step("PROFILE_LOOP", "Sending text-only profile notification", user_id=uid)
                        await send_message(CHANGES_CHANNEL_ID, embed)
            except Exception as exc:
                log_exception("profile_check_loop cycle", exc, user_id=uid)
                
        cooldown = random.randint(58, 85)
        log_step("PROFILE_LOOP", "Sleeping before next profile cycle", cooldown=cooldown)
        await asyncio.sleep(cooldown)

async def screenshot_worker():
    """مدير طابور التقاط الشاشة للأوامر اليدوية"""
    log_step("SCREENSHOT_WORKER", "Screenshot worker started")
    while True:
        ctx, user_id = await screenshot_queue.get()
        queue_size = screenshot_queue.qsize()
        log_step("SCREENSHOT_WORKER", "Processing screenshot request", user_id=user_id, channel_id=ctx.channel.id if ctx.channel else None, queue_size=queue_size)
        try:
            screenshot = await take_profile_screenshot(user_id)
            if screenshot.getbuffer().nbytes == 0:
                log_step("SCREENSHOT_WORKER", "Screenshot capture returned empty bytes", user_id=user_id)
                await ctx.send("❌ `Capture failed: Received empty image.`")
            else:
                embed = discord.Embed(title="📸 Live Profile Capture")
                embed.set_footer(text=f"Requested by User • {get_egypt_time()}")
                log_step("SCREENSHOT_WORKER", "Sending captured screenshot", user_id=user_id)
                await send_message_with_file(ctx.channel.id, embed, screenshot, f"capture_{user_id}.png")
        except Exception as e:
            log_exception("screenshot_worker capture", e, user_id=user_id)
            await ctx.send(f"❌ `Fatal error during capture: {str(e)}`")
        finally:
            screenshot_queue.task_done()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        # لو بتستخدم مكتبة discord.py-self، شغّل مباشرةً بالتوكن فقط
        bot.run(USER_TOKEN)
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
