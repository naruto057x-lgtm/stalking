import asyncio
import io
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands
import motor.motor_asyncio
from playwright.async_api import async_playwright

# ==================== تأكيد البدء ====================
print("🚀 Descord.py script started (Unified Selfbot - HTTP embeds)", flush=True)

# ==================== الإعدادات الأساسية ====================
USER_TOKEN = os.getenv("USER_TOKEN")
if not USER_TOKEN:
    print("❌ USER_TOKEN is required! Exiting.", flush=True)
    sys.exit(1)

TARGET_USER_IDS = [
    "1249754394417696801",
    "1378070979401486391"
]

ACTIVITY_CHANNEL_ID = 1535834292502929468
ONLINE_CHANNEL_ID   = 1535834924958089286
CHANGES_CHANNEL_ID  = 1509353152724340846
COMMANDS_CHANNEL_ID = 1509464730509643846

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

# ==================== دوال مساعدة ====================
def get_egypt_time(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    cairo = ZoneInfo("Africa/Cairo")
    local = dt.astimezone(cairo)
    return local.strftime("%I:%M %p, %A, %B %d, %Y (GMT+3)")

# ==================== دوال HTTP لإرسال/تعديل Embeds ====================
BASE_API = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": USER_TOKEN,
    "Content-Type": "application/json"
}

async def send_embed(channel_id: int, embed: discord.Embed) -> int:
    """إرسال Embed إلى قناة عبر HTTP وإرجاع message_id"""
    url = f"{BASE_API}/channels/{channel_id}/messages"
    payload = {"embeds": [embed.to_dict()]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                logger.info(f"Sent embed to channel {channel_id}, msg id {data['id']}")
                return int(data["id"])
            else:
                text = await resp.text()
                logger.error(f"Failed to send embed: {resp.status} {text}")
                return 0

async def edit_embed(channel_id: int, message_id: int, embed: discord.Embed):
    """تعديل رسالة موجودة ب Embed جديد"""
    url = f"{BASE_API}/channels/{channel_id}/messages/{message_id}"
    payload = {"embeds": [embed.to_dict()]}
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                logger.info(f"Edited message {message_id} in channel {channel_id}")
            else:
                text = await resp.text()
                logger.error(f"Failed to edit message: {resp.status} {text}")

async def send_embed_with_file(channel_id: int, embed: discord.Embed, file_bytes: io.BytesIO, filename: str):
    """إرسال Embed مع ملف (سكرين شوت)"""
    url = f"{BASE_API}/channels/{channel_id}/messages"
    form = aiohttp.FormData()
    form.add_field("embeds", json.dumps([embed.to_dict()]), content_type="application/json")
    form.add_field("file", file_bytes.getvalue(), filename=filename, content_type="image/png")
    headers = {"Authorization": USER_TOKEN}  # no Content-Type, aiohttp sets multipart
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=form) as resp:
            if resp.status == 200:
                logger.info("Sent embed with file")
            else:
                text = await resp.text()
                logger.error(f"Failed to send file: {resp.status} {text}")

# ==================== إعداد البوت (Selfbot) ====================
bot = commands.Bot(command_prefix="!", self_bot=True)
bot.remove_command("help")

# MongoDB
try:
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client["discord_monitor"]
    profile_cache_col = db["profile_cache"]
    online_msgs_col = db["online_messages"]
    activity_msgs_col = db["activity_messages"]
    last_seen_col = db["last_seen"]
    last_activity_col = db["last_activity"]
    logger.info("✅ MongoDB client initialized")
except Exception as e:
    logger.error(f"❌ MongoDB initialization failed: {e}")
    sys.exit(1)

# ذاكرة مؤقتة (نخزن IDs فقط بدلاً من كائنات الرسالة)
active_online_msgs = {}      # user_id -> message_id
active_activity_msgs = {}    # user_id -> {activity_name: message_id}
current_activities = {}      # user_id -> [dicts]
screenshot_queue = asyncio.Queue()

async def fetch_user_data(user_id: str) -> dict | None:
    url = f"{BASE_API}/users/{user_id}"
    headers = {"Authorization": USER_TOKEN}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
    return None

async def take_profile_screenshot(user_id: str) -> io.BytesIO:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=2,
            )
            page = await context.new_page()
            await page.set_extra_http_headers({"Authorization": USER_TOKEN})
            await page.goto(f"https://discord.com/users/{user_id}", wait_until="networkidle")
            await page.wait_for_selector("div[class*='profile']", timeout=15000)
            screenshot = await page.screenshot(full_page=True)
            await browser.close()
            return io.BytesIO(screenshot)
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return io.BytesIO(b'')

# ==================== أحداث البوت ====================
@bot.event
async def on_ready():
    logger.info(f"👤 Selfbot logged in as {bot.user}")

    # رسالة بدء التشغيل في قناة الأوامر
    embed = discord.Embed(
        title="⚡ Discord Monitor System Online",
        description=f"**Selfbot:** {bot.user.mention}\nAll systems ready.\nUse `!help` in this channel.",
        color=0x00FF00,
        timestamp=datetime.now(timezone.utc)
    )
    await send_embed(COMMANDS_CHANNEL_ID, embed)

    # بدء المهام الخلفية
    bot.loop.create_task(profile_check_loop())
    bot.loop.create_task(screenshot_worker())

    # رسالة بدء المراقبة في قناة التغييرات
    embed2 = discord.Embed(title="🔄 Profile Monitoring Started", description="Checking profiles every minute.", color=0x00FF00)
    await send_embed(CHANGES_CHANNEL_ID, embed2)

# ==================== الأوامر ====================
@bot.command(name="status")
async def status_check(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    embed = discord.Embed(title="📊 System Status", color=0x7289DA, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Selfbot", value="✅ Connected", inline=False)
    channels = {
        "Activity": ACTIVITY_CHANNEL_ID,
        "Online": ONLINE_CHANNEL_ID,
        "Changes": CHANGES_CHANNEL_ID,
        "Commands": COMMANDS_CHANNEL_ID
    }
    channels_status = "\n".join([f"{'✅' if bot.get_channel(cid) else '❌'} {name} channel" for name, cid in channels.items()])
    embed.add_field(name="Channels", value=channels_status, inline=False)
    try:
        await mongo_client.admin.command("ping")
        embed.add_field(name="MongoDB", value="✅ Connected", inline=False)
    except:
        embed.add_field(name="MongoDB", value="❌ Error", inline=False)
    target_statuses = []
    for uid in TARGET_USER_IDS:
        data = await fetch_user_data(uid)
        target_statuses.append(f"{'✅' if data else '❌'} <@{uid}>")
    embed.add_field(name="Target Users", value="\n".join(target_statuses), inline=False)
    await send_embed(ctx.channel.id, embed)

@bot.command(name="help", aliases=["commands"])
async def custom_help(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    embed = discord.Embed(title="📖 Available Commands", color=0x7289DA)
    embed.add_field(name="!profile [user_id]", value="Show full profile info", inline=False)
    embed.add_field(name="!about [user_id]", value="Show about me section", inline=False)
    embed.add_field(name="!ss [user_id]", value="Take a profile screenshot", inline=False)
    embed.add_field(name="!activity [user_id]", value="Current activity and duration", inline=False)
    embed.add_field(name="!lastseen [user_id]", value="Last online/offline", inline=False)
    embed.add_field(name="!lastactivity [user_id]", value="Last completed activity", inline=False)
    embed.add_field(name="!status", value="Full system diagnostics", inline=False)
    embed.set_footer(text="All times in Egypt (GMT+3)")
    await send_embed(ctx.channel.id, embed)

@bot.command(name="profile")
async def _profile(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    elif user_id not in TARGET_USER_IDS:
        return await ctx.send("❌ User not monitored.")
    data = await fetch_user_data(user_id)
    if not data:
        return await ctx.send("❌ Could not fetch profile.")
    username = data.get("username", "Unknown")
    global_name = data.get("global_name") or "None"
    bio = data.get("bio") or "*No bio*"
    avatar_hash = data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{'gif' if avatar_hash.startswith('a_') else 'png'}?size=1024" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
    banner_hash = data.get("banner")
    banner_url = None
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"
    clan = data.get("clan")
    clan_str = "*Not in a Clan*"
    if clan:
        tag = clan.get("tag", "No tag")
        clan_str = f"**₊ {tag}**"
    deco = data.get("avatar_decoration_data")
    deco_str = "*None*"
    if deco:
        asset = deco.get("asset")
        deco_str = f"[Preview](https://cdn.discordapp.com/avatar-decorations/{asset}.png)"
    creation_str = get_egypt_time(datetime.fromtimestamp(((int(user_id) >> 22) + 1420070400000) / 1000, tz=timezone.utc))
    embed = discord.Embed(title=f"👤 Profile: @{username}", color=data.get("accent_color") or 0x7289DA, timestamp=datetime.now(timezone.utc))
    embed.set_thumbnail(url=avatar_url)
    if banner_url:
        embed.set_image(url=banner_url)
    embed.add_field(name="Username", value=f"`{username}`", inline=True)
    embed.add_field(name="Display Name", value=global_name, inline=True)
    embed.add_field(name="ID", value=f"`{user_id}`", inline=True)
    embed.add_field(name="Created", value=creation_str, inline=False)
    embed.add_field(name="Clan", value=clan_str, inline=False)
    embed.add_field(name="Avatar Decoration", value=deco_str, inline=False)
    embed.add_field(name="Bio", value=bio, inline=False)
    embed.set_footer(text=f"Requested at {get_egypt_time()}")
    await send_embed(ctx.channel.id, embed)

@bot.command(name="about")
async def _about(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    data = await fetch_user_data(user_id)
    if not data:
        return await ctx.send("❌ Failed to fetch.")
    bio = data.get("bio") or "*No about me section*"
    await ctx.send(f"📝 **About Me for <@{user_id}>:**\n{bio}")

@bot.command(name="ss")
async def _ss(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    await ctx.send("📸 Taking screenshot, please wait...")
    await screenshot_queue.put((ctx, user_id))

@bot.command(name="activity")
async def _activity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    acts = current_activities.get(user_id, [])
    if not acts:
        return await ctx.send("❌ No current activity.")
    desc = ""
    for act in acts:
        started = act.get("start_time")
        if started:
            elapsed = datetime.now(timezone.utc) - started
            dur = str(elapsed).split(".")[0]
        else:
            dur = "Unknown"
        desc += f"🎮 **{act['name']}** — Since {get_egypt_time(started)} (elapsed: {dur})\n"
    embed = discord.Embed(title="🎯 Current Activity", description=desc, color=0x00FF00)
    await send_embed(ctx.channel.id, embed)

@bot.command(name="lastseen")
async def _lastseen(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    doc = await last_seen_col.find_one({"_id": user_id})
    if not doc:
        return await ctx.send("❌ No data.")
    last_online = doc.get("last_online")
    last_offline = doc.get("last_offline")
    msg = ""
    if last_online:
        msg += f"🟢 Last online: {get_egypt_time(last_online)}\n"
    if last_offline:
        msg += f"🔴 Last offline: {get_egypt_time(last_offline)}"
    embed = discord.Embed(title="⏱️ Last Seen", description=msg, color=0x7289DA)
    await send_embed(ctx.channel.id, embed)

@bot.command(name="lastactivity")
async def _lastactivity(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    if not user_id:
        user_id = TARGET_USER_IDS[0]
    doc = await last_activity_col.find_one({"_id": user_id})
    if not doc:
        return await ctx.send("❌ No previous activity recorded.")
    name = doc.get("activity_name", "Unknown")
    start = doc.get("start")
    end = doc.get("end")
    duration = doc.get("duration", "Unknown")
    desc = f"🎮 **{name}**\nStarted: {get_egypt_time(start)}\nEnded: {get_egypt_time(end)}\nDuration: {duration}"
    embed = discord.Embed(title="📜 Last Activity", description=desc, color=0x7289DA)
    await send_embed(ctx.channel.id, embed)

# ==================== مراقبة الحالة والأنشطة ====================
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if str(after.id) not in TARGET_USER_IDS:
        return
    user_id = str(after.id)
    now = datetime.now(timezone.utc)

    # تتبع الأونلاين/أوفلاين
    if before.status != after.status:
        if after.status == discord.Status.online:
            embed = discord.Embed(title="🟢 Online", description=f"<@{user_id}> is now online.\n🕒 {get_egypt_time(now)}", color=0x57F287)
            embed.set_thumbnail(url=after.display_avatar.url)
            msg_id = await send_embed(ONLINE_CHANNEL_ID, embed)
            if msg_id:
                active_online_msgs[user_id] = msg_id
                await online_msgs_col.update_one({"_id": user_id}, {"$set": {"msg_id": msg_id}}, upsert=True)
            await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_online": now}}, upsert=True)
        elif after.status == discord.Status.offline:
            if user_id in active_online_msgs:
                msg_id = active_online_msgs.pop(user_id)
                # نحتاج وقت البداية من قاعدة البيانات؟ سنحتفظ به في online_msgs_col
                doc = await online_msgs_col.find_one({"_id": user_id})
                start_time = doc.get("start_time") if doc else None
                if not start_time:
                    # يمكننا تقدير وقت البدء بأنه وقت إرسال الرسالة (ناقص مدة غير معروفة)
                    # لكن الأفضل نعيد كتابة: عند إرسال رسالة أونلاين نخزن وقتها
                    # لذا نحتاج لتعديل هيكل البيانات
                    pass
                # سنستخدم توقيت الرسالة القديمة إن أمكن
                # لكن مؤقتًا سنستخدم now كبداية (وهذا غير دقيق)
                # سنصلح لاحقًا بتخزين start_time في online_msgs_col
                dur_str = "unknown"
                new_embed = discord.Embed(
                    title="🔴 Offline",
                    description=f"<@{user_id}> went offline.\n"
                                f"🟢 Was online from: ?\n"
                                f"🔴 Offline at: {get_egypt_time(now)}\n"
                                f"⏱️ Session duration: {dur_str}",
                    color=0x747F8D
                )
                new_embed.set_thumbnail(url=after.display_avatar.url)
                await edit_embed(ONLINE_CHANNEL_ID, msg_id, new_embed)
                await online_msgs_col.delete_one({"_id": user_id})
            await last_seen_col.update_one({"_id": user_id}, {"$set": {"last_offline": now}}, upsert=True)

    # تتبع الأنشطة
    before_acts = {act.name: act for act in before.activities if act.type != discord.ActivityType.custom}
    after_acts = {act.name: act for act in after.activities if act.type != discord.ActivityType.custom}
    started_acts = set(after_acts.keys()) - set(before_acts.keys())
    ended_acts = set(before_acts.keys()) - set(after_acts.keys())

    for name in started_acts:
        act = after_acts[name]
        start = act.start or now
        embed = discord.Embed(title="🎮 Activity Started", description=f"<@{user_id}> started **{act.name}**\n🕒 Since: {get_egypt_time(start)}", color=0x5865F2)
        embed.set_thumbnail(url=after.display_avatar.url)
        msg_id = await send_embed(ACTIVITY_CHANNEL_ID, embed)
        if msg_id:
            if user_id not in active_activity_msgs:
                active_activity_msgs[user_id] = {}
            active_activity_msgs[user_id][name] = msg_id
            await activity_msgs_col.insert_one({"user_id": user_id, "activity_key": name, "msg_id": msg_id, "start_time": start})
        if user_id not in current_activities:
            current_activities[user_id] = []
        current_activities[user_id].append({"name": name, "start_time": start})

    for name in ended_acts:
        if user_id in active_activity_msgs and name in active_activity_msgs[user_id]:
            msg_id = active_activity_msgs[user_id].pop(name)
            doc = await activity_msgs_col.find_one({"user_id": user_id, "activity_key": name})
            if doc:
                start_time = doc.get("start_time")
                end_time = now
                duration = end_time - start_time
                dur_str = str(duration).split(".")[0]
                new_embed = discord.Embed(
                    title="✅ Activity Ended",
                    description=f"<@{user_id}> finished **{name}**\n"
                                f"🕒 Started: {get_egypt_time(start_time)}\n"
                                f"🏁 Ended: {get_egypt_time(end_time)}\n"
                                f"⏱️ Duration: {dur_str}",
                    color=0xED4245
                )
                new_embed.set_thumbnail(url=after.display_avatar.url)
                await edit_embed(ACTIVITY_CHANNEL_ID, msg_id, new_embed)
                await activity_msgs_col.delete_one({"user_id": user_id, "activity_key": name})
                await last_activity_col.update_one(
                    {"_id": user_id},
                    {"$set": {"activity_name": name, "start": start_time, "end": end_time, "duration": dur_str}},
                    upsert=True
                )
        if user_id in current_activities:
            current_activities[user_id] = [a for a in current_activities[user_id] if a["name"] != name]

# ==================== حلقات الخلفية ====================
async def profile_check_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for uid in TARGET_USER_IDS:
            data = await fetch_user_data(uid)
            if not data:
                continue
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
                        changes.append(f"🔹 **{key.replace('_', ' ').title()}** changed: `{cached.get(key)}` → `{new_cache[key]}`")
            if changes or not cached:
                if not cached:
                    changes.append("🆕 Initial profile cached.")
                await profile_cache_col.update_one({"_id": uid}, {"$set": new_cache}, upsert=True)
                embed = discord.Embed(
                    title="🔄 Profile Update Detected",
                    description=f"<@{uid}> profile changed:\n" + "\n".join(changes),
                    color=0xFFA500,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text=f"Detected at {get_egypt_time()}")
                screenshot = await take_profile_screenshot(uid)
                file_bytes = screenshot
                embed.set_image(url="attachment://profile.png")  # سيتم استبدال الرابط عند الرفع
                await send_embed_with_file(CHANGES_CHANNEL_ID, embed, file_bytes, f"profile_{uid}.png")
        await asyncio.sleep(60)

async def screenshot_worker():
    while True:
        ctx, user_id = await screenshot_queue.get()
        try:
            screenshot = await take_profile_screenshot(user_id)
            if screenshot.getbuffer().nbytes == 0:
                await ctx.send("❌ Failed to capture screenshot.")
            else:
                embed = discord.Embed(title="📸 Profile Screenshot", color=0x5865F2)
                embed.set_image(url="attachment://ss.png")
                embed.set_footer(text=f"Requested by {ctx.author} • {get_egypt_time()}")
                await send_embed_with_file(ctx.channel.id, embed, screenshot, f"ss_{user_id}.png")
        except Exception as e:
            await ctx.send(f"❌ Failed to take screenshot: {e}")
        finally:
            screenshot_queue.task_done()

# ==================== التشغيل ====================
if __name__ == "__main__":
    try:
        bot.run(USER_TOKEN)
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
