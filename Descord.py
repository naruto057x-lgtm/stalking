import asyncio
import io
import json
import logging
import os
import sys
import traceback
import random # 👈 تم الإضافة لإعطاء طابع بشري للسكربت
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

# رابط قاعدة البيانات
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://...")

# ==================== نظام التسجيل ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

# ==================== دوال الوقت ====================
def get_egypt_time(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    cairo = ZoneInfo("Africa/Cairo")
    local = dt.astimezone(cairo)
    return local.strftime("%I:%M %p, %A, %B %d, %Y (GMT+3)")

# ==================== دوال HTTP مع التصميم الاحترافي ====================
BASE_API = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": USER_TOKEN,
    "Content-Type": "application/json"
}

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
    await human_delay() # 👈 حماية ضد السبام
    url = f"{BASE_API}/channels/{channel_id}/messages"
    payload = {"content": embed_to_text(embed)}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                logger.info(f"✅ Sent message to channel {channel_id}")
                return int(data["id"])
            else:
                text = await resp.text()
                logger.error(f"❌ Failed to send message: {resp.status} {text}")
                return 0

async def edit_message(channel_id: int, message_id: int, embed: discord.Embed):
    """تعديل رسالة موجودة بنص جديد"""
    await human_delay()
    url = f"{BASE_API}/channels/{channel_id}/messages/{message_id}"
    payload = {"content": embed_to_text(embed)}
    
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                logger.info(f"✏️ Edited message {message_id}")
            else:
                text = await resp.text()
                logger.error(f"❌ Failed to edit message: {resp.status} {text}")

async def send_message_with_file(channel_id: int, embed: discord.Embed, file_bytes: io.BytesIO, filename: str):
    """إرسال رسالة مع صورة (لقطة الشاشة)"""
    await human_delay()
    url = f"{BASE_API}/channels/{channel_id}/messages"
    form = aiohttp.FormData()
    
    payload = {"content": embed_to_text(embed)}
    form.add_field("payload_json", json.dumps(payload), content_type="application/json")
    form.add_field("file", file_bytes.getvalue(), filename=filename, content_type="image/png")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={"Authorization": USER_TOKEN}, data=form) as resp:
            if resp.status == 200:
                logger.info("📸 Sent message with screenshot file")
            else:
                text = await resp.text()
                logger.error(f"❌ Failed to send file: {resp.status} {text}")

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
    url = f"{BASE_API}/users/{user_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
    return None

async def take_profile_screenshot(user_id: str) -> io.BytesIO:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=2,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto("https://discord.com/login", wait_until="networkidle")
            await page.evaluate("(token) => window.localStorage.setItem('token', JSON.stringify(token))", USER_TOKEN)
            await page.goto("https://discord.com/channels/@me", wait_until="networkidle")
            await page.goto(f"https://discord.com/users/{user_id}", wait_until="networkidle")
            try:
                await page.wait_for_selector("div[class*='profile']", timeout=15000)
            except Exception:
                logger.warning(f"Profile screenshot selector timeout for user {user_id}")
            screenshot = await page.screenshot(full_page=True)
            await browser.close()
            return io.BytesIO(screenshot)
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
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

    await edit_message(ONLINE_CHANNEL_ID, online_data["msg_id"], embed)
    active_online_msgs.pop(user_id, None)
    pending_offline_tasks.pop(user_id, None)
    await online_msgs_col.delete_one({"_id": user_id})
    await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_offline": end_time}}, upsert=True)

# ==================== أحداث البوت الأساسية ====================
@bot.event
async def on_ready():
    logger.info(f"👤 Selfbot logged in as {bot.user}")

    embed = discord.Embed(
        title="⚡ Discord Monitor System Online",
        description=f"**Selfbot:** {bot.user.mention}\nAll systems are fully operational with Anti-Ban active.\nUse `!help` in this channel for commands."
    )
    embed.set_footer(text="System Initialized")
    await send_message(COMMANDS_CHANNEL_ID, embed)

    bot.loop.create_task(profile_check_loop())
    bot.loop.create_task(screenshot_worker())

@bot.event
async def on_message(message: discord.Message):
    if message.author.id != bot.user.id:
        return
    if message.channel.id != COMMANDS_CHANNEL_ID:
        return
    await bot.process_commands(message)

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
    embed.add_field(name="`!profile [user_id]`", value="Show full formatted profile details.", inline=False)
    embed.add_field(name="`!about [user_id]`", value="Extract and show just the About Me section.", inline=False)
    embed.add_field(name="`!ss [user_id]`", value="Capture a live screenshot of the user's profile.", inline=False)
    embed.add_field(name="`!activity [user_id]`", value="Check what the user is currently doing.", inline=False)
    embed.add_field(name="`!lastseen [user_id]`", value="Check the exact time they last came online or went offline.", inline=False)
    embed.add_field(name="`!lastactivity [user_id]`", value="Check the details of the last app/game they played.", inline=False)
    embed.add_field(name="`!status`", value="Run system diagnostics.", inline=False)
    embed.set_footer(text="🕒 All times displayed in Egypt Time (GMT+3)")
    await send_message(ctx.channel.id, embed)

@bot.command(name="profile")
async def _profile(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    if user_id not in TARGET_USER_IDS:
        return await ctx.send("❌ This user is not in the target list.")
        
    data = await fetch_user_data(user_id)
    if not data:
        return await ctx.send("❌ Could not fetch profile data from Discord API.")

    username = data.get("username", "Unknown")
    global_name = data.get("global_name") or "None"
    bio = data.get("bio") or "*No bio written*"
    
    clan = data.get("clan")
    clan_str = "*Not in a Clan*"
    if clan: clan_str = f"**₊ {clan.get('tag', 'No tag')}**"
    
    deco = data.get("avatar_decoration_data")
    deco_str = "*None*"
    if deco: deco_str = f"[Preview Link](https://cdn.discordapp.com/avatar-decorations/{deco.get('asset')}.png)"
    
    creation_str = get_egypt_time(datetime.fromtimestamp(((int(user_id) >> 22) + 1420070400000) / 1000, tz=timezone.utc))
    
    embed = discord.Embed(title=f"👤 Profile Overview: @{username}")
    embed.add_field(name="Identification", value=f"**Display Name:** {global_name}\n**Username:** `{username}`\n**User ID:** `{user_id}`", inline=False)
    embed.add_field(name="Account Details", value=f"**Created On:** {creation_str}\n**Clan:** {clan_str}\n**Decoration:** {deco_str}", inline=False)
    embed.add_field(name="About Me", value=bio, inline=False)
    embed.set_footer(text=f"Fetched at {get_egypt_time()}")
    
    await send_message(ctx.channel.id, embed)

@bot.command(name="about")
async def _about(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    data = await fetch_user_data(user_id)
    if not data: return await ctx.send("❌ Failed to fetch user data.")
    
    bio = data.get("bio") or "*This user hasn't written an about me section.*"
    embed = discord.Embed(title=f"📝 About Me for <@{user_id}>", description=bio)
    await send_message(ctx.channel.id, embed)

@bot.command(name="ss")
async def _ss(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    await ctx.send(f"📸 `Initiating screenshot capture for <@{user_id}>... Please wait.`")
    await screenshot_queue.put((ctx, user_id))

@bot.command(name="activity")
async def _activity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    acts = current_activities.get(user_id, [])
    if not acts:
        return await ctx.send(f"💤 `<@{user_id}> is not doing any detectable activity right now.`")
        
    embed = discord.Embed(title=f"🎯 Live Activities for <@{user_id}>")
    for act in acts:
        started = act.get("start_time")
        elapsed = str(datetime.now(timezone.utc) - started).split(".")[0] if started else "Unknown"
        embed.add_field(name=act['name'], value=f"Started at: {get_egypt_time(started)}\nElapsed: **{elapsed}**", inline=False)
        
    await send_message(ctx.channel.id, embed)

@bot.command(name="lastseen")
async def _lastseen(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    doc = await last_seen_col.find_one({"_id": user_id})
    if not doc: return await ctx.send("❌ No historical tracking data available for this user yet.")
    
    embed = discord.Embed(title=f"⏱️ Last Seen Tracker for <@{user_id}>")
    if doc.get("last_online"):
        embed.add_field(name="🟢 Last Online", value=get_egypt_time(doc.get("last_online")), inline=False)
    if doc.get("last_offline"):
        embed.add_field(name="🔴 Last Offline", value=get_egypt_time(doc.get("last_offline")), inline=False)
        
    await send_message(ctx.channel.id, embed)

@bot.command(name="lastactivity")
async def _lastactivity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID: return
    user_id = user_id or TARGET_USER_IDS[0]
    
    doc = await last_activity_col.find_one({"_id": user_id})
    if not doc: return await ctx.send("❌ No previous activities have been recorded.")
    
    embed = discord.Embed(title=f"📜 Last Completed Activity for <@{user_id}>")
    embed.add_field(name="Activity Name", value=f"🎮 **{doc.get('activity_name', 'Unknown')}**", inline=False)
    embed.add_field(name="Timeline", value=f"**Start:** {get_egypt_time(doc.get('start'))}\n**End:** {get_egypt_time(doc.get('end'))}", inline=False)
    embed.add_field(name="Total Duration", value=f"⏳ {doc.get('duration', 'Unknown')}", inline=False)
    
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
            if user_id in pending_offline_tasks:
                pending_offline_tasks[user_id].cancel()
                pending_offline_tasks.pop(user_id, None)

            if user_id not in active_online_msgs:
                avatar_url = None
                try:
                    avatar_url = str(after.display_avatar.url)
                except Exception:
                    avatar_url = None

                embed = discord.Embed(
                    title="🟢 User is Online",
                    description=f"<@{user_id}> has connected to Discord.\n\n🕒 **Started at:** {get_egypt_time(now)}"
                )
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)
                embed.set_footer(text=f"Tracking online session for <@{user_id}>")

                msg_id = await send_message(ONLINE_CHANNEL_ID, embed)
                if msg_id:
                    active_online_msgs[user_id] = {
                        "msg_id": msg_id,
                        "start_time": now,
                        "avatar_url": avatar_url,
                        "username": after.display_name
                    }
                    await online_msgs_col.update_one(
                        {"_id": user_id},
                        {"$set": {"msg_id": msg_id, "start_time": now}},
                        upsert=True
                    )
            await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_online": now}}, upsert=True)

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
    
    startup_embed = discord.Embed(title="🔄 Profile Surveillance Activated", description="Checking target profiles stealthily (~ every 60s).")
    await send_message(CHANGES_CHANNEL_ID, startup_embed)
    
    while not bot.is_closed():
        for uid in TARGET_USER_IDS:
            await asyncio.sleep(random.uniform(1.5, 3.5)) # 👈 تأخير بين فحص كل شخص والتاني
            
            data = await fetch_user_data(uid)
            if not data: continue
            
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
                    
                await profile_cache_col.update_one({"_id": uid}, {"$set": new_cache}, upsert=True)
                
                embed = discord.Embed(
                    title="⚠️ Profile Update Detected", 
                    description=f"Changes found for <@{uid}>:\n\n" + "\n".join(changes)
                )
                embed.set_footer(text=f"Change recorded at {get_egypt_time()}")
                
                screenshot = await take_profile_screenshot(uid)
                if screenshot.getbuffer().nbytes > 0:
                    await send_message_with_file(CHANGES_CHANNEL_ID, embed, screenshot, f"update_{uid}.png")
                else:
                    await send_message(CHANGES_CHANNEL_ID, embed)
                    
        # 👈 السر في الحماية: التكرار عشوائي بين 58 و 85 ثانية بدل 60 ثانية بالضبط
        cooldown = random.randint(58, 85)
        await asyncio.sleep(cooldown)

async def screenshot_worker():
    """مدير طابور التقاط الشاشة للأوامر اليدوية"""
    while True:
        ctx, user_id = await screenshot_queue.get()
        try:
            screenshot = await take_profile_screenshot(user_id)
            if screenshot.getbuffer().nbytes == 0:
                await ctx.send("❌ `Capture failed: Received empty image.`")
            else:
                embed = discord.Embed(title="📸 Live Profile Capture")
                embed.set_footer(text=f"Requested by User • {get_egypt_time()}")
                await send_message_with_file(ctx.channel.id, embed, screenshot, f"capture_{user_id}.png")
        except Exception as e:
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
