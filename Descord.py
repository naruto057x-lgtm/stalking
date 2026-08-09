import requests
import time
import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import threading
from zoneinfo import ZoneInfo  # للتوقيتات (Python 3.9+)

# ==================== الإعدادات الأساسية ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables!")

TARGET_USER_IDS = [
    "1249754394417696801",
    "1378070979401486391"   # أضف أي ID إضافي هنا
]
WEBHOOK_URL = "https://discord.com/api/webhooks/1509353177663803522/OMdWhlsdCCU0rlTrVs-pWGt0Vhqnb81PYrJ9Q0IEOlhjs0ackASANAB59YOwfEuU-Bg7"
COMMANDS_CHANNEL_ID = 1509464730509643846
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True          # ضروري لتتبع الأونلاين/أوفلاين
discord_bot = commands.Bot(command_prefix="!", intents=intents)

headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

# كاش البروفايل لكل حساب
profile_cache = {}  # {user_id: {data...}}

# تتبع الأونلاين/أوفلاين لكل حساب (بيانات الجلسات)
presence_tracker = {}  # {user_id: {"last_online": datetime, "last_offline": datetime, "offline_start": datetime}}

def get_cache(user_id):
    if user_id not in profile_cache:
        profile_cache[user_id] = {
            "username": None,
            "global_name": None,
            "bio": None,
            "avatar": None,
            "banner": None,
            "clan_tag": None,
            "avatar_decoration": None
        }
    return profile_cache[user_id]

def get_egypt_time(dt: datetime = None):
    """يحول أي وقت إلى توقيت مصر UTC+3"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    cairo_tz = ZoneInfo("Africa/Cairo")
    local_dt = dt.astimezone(cairo_tz)
    return local_dt.strftime("%I:%M %p, %A, %B %d, %Y (GMT+3)")

def get_discord_user_data(user_id):
    url = f"https://discord.com/api/v10/users/{user_id}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        else:
            print(f"❌ Failed to fetch data for {user_id}. Status code: {res.status_code}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    return None

def send_to_webhook(user_data, user_id, changes_made=None, event_type="profile"):
    username = user_data.get("username", "Unknown")
    global_name = user_data.get("global_name") or "No display name"
    bio_text = user_data.get("bio") or "*This user has no bio.*"
    accent_color = user_data.get("accent_color") or 0x7289DA
    now_str = get_egypt_time()

    # تاريخ إنشاء الحساب
    try:
        snowflake_id = int(user_id)
        timestamp = ((snowflake_id >> 22) + 1420070400000) / 1000
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        creation_str = get_egypt_time(creation_date)
    except:
        creation_str = "Unable to calculate"

    # أفاتار
    avatar_hash = user_data.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=1024"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    # بانر
    banner_hash = user_data.get("banner")
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"
        banner_status = f"[Click to open banner]({banner_url})"
    else:
        banner_url = None
        banner_status = "*No banner set*"

    # Clan
    clan_data = user_data.get("clan")
    if clan_data:
        clan_tag = clan_data.get("tag", "No tag")
        clan_id = clan_data.get("identity_guild_id") or clan_data.get("guild_id") or "Unknown"
        clan_status = f"**₊ {clan_tag}**\n🆔 **ID:** `{clan_id}`"
    else:
        clan_status = "*Not in any Clan*"

    # Decoration
    deco_data = user_data.get("avatar_decoration_data")
    if deco_data:
        asset_hash = deco_data.get("asset")
        deco_url = f"https://cdn.discordapp.com/avatar-decorations/{asset_hash}.png"
        deco_status = f"[Click to preview decoration]({deco_url})"
    else:
        deco_status = "*No avatar decoration*"

    # بناء الـ Embed
    if event_type == "profile_update":
        title = f"🔥 Profile Change Detected for: @{username}"
        description = f"**Changes spotted instantly:**\n{changes_made}\n\n🕒 Detected at: {now_str}"
        embed_color = 0xFF0000
    elif event_type == "presence":
        title = f"👀 Online/Offline Update for: @{username}"
        description = changes_made if changes_made else "Status changed"
        embed_color = 0x00FF00 if "online" in changes_made.lower() else 0x808080
    else:  # بدء المراقبة
        title = f"⚙️ Monitoring Started for: @{username}"
        description = f"Radar is now active 24/7. Profile will be checked every minute.\n🕒 Started at: {now_str}"
        embed_color = accent_color

    fields = [
        {"name": "👤 Username", "value": f"`{username}`", "inline": True},
        {"name": "Display Name", "value": global_name, "inline": True},
        {"name": "🆔 User ID", "value": f"`{user_id}`", "inline": True},
        {"name": "📅 Account Creation Date", "value": f"`{creation_str}`", "inline": False},
        {"name": "🛡️ Current Clan (Guild Tag)", "value": clan_status, "inline": False},
        {"name": "✨ Avatar Decoration", "value": deco_status, "inline": False},
        {"name": "📝 Full Bio", "value": bio_text, "inline": False},
        {"name": "🖼️ Banner Link", "value": banner_status, "inline": False}
    ]

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": embed_color,
            "thumbnail": {"url": avatar_url},
            "image": {"url": banner_url} if banner_url else {},
            "fields": fields,
            "footer": {
                "text": "Advanced Discord Radar System",
                "icon_url": "https://cdn.discordapp.com/embed/avatars/4.png"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }

    requests.post(WEBHOOK_URL, json=payload)

# ============ مراقبة البروفايل (REST) ============
def start_radar():
    print("🔍 Initializing caches and starting monitoring for all accounts...")
    for uid in TARGET_USER_IDS:
        data = get_discord_user_data(uid)
        if data:
            cache = get_cache(uid)
            cache["username"] = data.get("username")
            cache["global_name"] = data.get("global_name")
            cache["bio"] = data.get("bio")
            cache["avatar"] = data.get("avatar")
            cache["banner"] = data.get("banner")
            cache["clan_tag"] = data.get("clan", {}).get("tag") if data.get("clan") else None
            cache["avatar_decoration"] = data.get("avatar_decoration_data", {}).get("asset") if data.get("avatar_decoration_data") else None
            send_to_webhook(data, uid)  # إشعار بدء المراقبة
        else:
            print(f"❌ Failed to initialize {uid}")

    print("🚀 Radar is running in the background... checking every minute.")
    while True:
        time.sleep(60)
        for uid in TARGET_USER_IDS:
            current_data = get_discord_user_data(uid)
            if not current_data:
                continue
            cache = get_cache(uid)
            changes = []

            current_username = current_data.get("username")
            if current_username != cache["username"]:
                changes.append(f"🔹 **Username:** `{cache['username']}` → `{current_username}`")
                cache["username"] = current_username

            current_global = current_data.get("global_name")
            if current_global != cache["global_name"]:
                changes.append(f"🔹 **Display Name:** `{cache['global_name']}` → `{current_global}`")
                cache["global_name"] = current_global

            current_bio = current_data.get("bio")
            if current_bio != cache["bio"]:
                changes.append("📝 **Bio has been modified.**")
                cache["bio"] = current_bio

            current_avatar = current_data.get("avatar")
            if current_avatar != cache["avatar"]:
                changes.append("🖼️ **Avatar changed!**")
                cache["avatar"] = current_avatar

            current_banner = current_data.get("banner")
            if current_banner != cache["banner"]:
                changes.append("🌌 **Banner image updated.**")
                cache["banner"] = current_banner

            current_clan_tag = current_data.get("clan", {}).get("tag") if current_data.get("clan") else None
            if current_clan_tag != cache["clan_tag"]:
                changes.append(f"🛡️ **Clan Tag:** `{cache['clan_tag']}` → `{current_clan_tag}`")
                cache["clan_tag"] = current_clan_tag

            current_deco = current_data.get("avatar_decoration_data", {}).get("asset") if current_data.get("avatar_decoration_data") else None
            if current_deco != cache["avatar_decoration"]:
                changes.append("✨ **Avatar Decoration changed.**")
                cache["avatar_decoration"] = current_deco

            if changes:
                changes_string = "\n".join(changes)
                print(f"🔥 Updates for {uid}: {changes_string}")
                send_to_webhook(current_data, uid, changes_made=changes_string, event_type="profile_update")

# ============ مراقبة الأونلاين/أوفلاين ============
@discord_bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    user_id = str(after.id)
    if user_id not in TARGET_USER_IDS:
        return  # الشخص مش ضمن قائمة المراقبة

    old_status = before.status
    new_status = after.status
    now_utc = datetime.now(timezone.utc)

    if user_id not in presence_tracker:
        presence_tracker[user_id] = {
            "last_online": now_utc if new_status == discord.Status.online else None,
            "last_offline": now_utc if new_status == discord.Status.offline else None,
            "offline_start": now_utc if new_status == discord.Status.offline else None
        }
        return

    tracker = presence_tracker[user_id]

    # الشخص دخل أونلاين
    if new_status == discord.Status.online and old_status != discord.Status.online:
        offline_duration = None
        if tracker.get("offline_start"):
            offline_duration = (now_utc - tracker["offline_start"]).total_seconds()
            tracker["offline_start"] = None

        if offline_duration is not None:
            if offline_duration > 600:  # أكثر من 10 دقايق
                msg = (
                    f"🟢 **User came back online** after being offline for {int(offline_duration//60)} min {int(offline_duration%60)} sec.\n"
                    f"⏱️ This indicates **Discord was fully closed**.\n"
                    f"🕒 Online at: {get_egypt_time(now_utc)}"
                )
            else:
                msg = (
                    f"🟢 **User came back online** after a brief offline period ({int(offline_duration)} sec).\n"
                    f"📌 This is probably the same session (connection hiccup).\n"
                    f"🕒 Online at: {get_egypt_time(now_utc)}"
                )
        else:
            msg = f"🟢 **User is now online**\n🕒 Online at: {get_egypt_time(now_utc)}"
        send_presence_webhook(after, msg)

    # الشخص دخل أوفلاين
    elif new_status == discord.Status.offline and old_status != discord.Status.offline:
        tracker["offline_start"] = now_utc
        msg = f"🔴 **User went offline**\n🕒 Offline at: {get_egypt_time(now_utc)}"
        send_presence_webhook(after, msg)

    # تحديث آخر أونلاين / أوفلاين
    if new_status == discord.Status.online:
        tracker["last_online"] = now_utc
    elif new_status == discord.Status.offline:
        tracker["last_offline"] = now_utc

def send_presence_webhook(member: discord.Member, message):
    """إرسال Webhook لتحديثات الحضور"""
    payload = {
        "embeds": [{
            "title": f"👀 Presence Update: @{member.name}",
            "description": message,
            "color": 0x7289DA,
            "footer": {
                "text": "Advanced Discord Radar System • Presence Tracking"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }
    requests.post(WEBHOOK_URL, json=payload)

# ============ أوامر البوت ============
@discord_bot.event
async def on_ready():
    print(f"\n{'='*70}")
    print(f"🤖 Discord Monitor Bot Ready as: {discord_bot.user.name}")
    print(f"{'='*70}\n")

@discord_bot.command(name="commands")
async def cmd_commands(ctx):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    embed = discord.Embed(title="📖 Discord Monitor Commands", color=0x7289DA)
    embed.add_field(
        name="👤 !profile [user_id]",
        value="Displays the current profile of a monitored user. If no ID is given, shows the first target.\n"
              "**Example:** `!profile 1249754394417696801`",
        inline=False
    )
    embed.add_field(
        name="🔔 Automatic Alerts",
        value="The system sends instant alerts when:\n"
              "📝 **Bio modified**\n"
              "🖼️ **Avatar changed**\n"
              "🌌 **Banner changed**\n"
              "👤 **Display name changed**\n"
              "🛡️ **Joined/Left a Clan**\n"
              "✨ **Avatar decoration changed**\n"
              "🟢🔴 **Online/Offline status changes** (requires shared server & presence intent)\n",
        inline=False
    )
    embed.set_footer(text="Radar checks profiles every minute • Presence tracking is real-time")
    await ctx.send(embed=embed)

@discord_bot.command(name="profile")
async def cmd_profile(ctx, user_id: str = None):
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return

    if not user_id:
        user_id = TARGET_USER_IDS[0]
    elif user_id not in TARGET_USER_IDS:
        await ctx.send("❌ This ID is not in the monitoring list.")
        return

    user_data = get_discord_user_data(user_id)
    if not user_data:
        await ctx.send("❌ Failed to fetch profile data!")
        return

    username = user_data.get("username", "Unknown")
    global_name = user_data.get("global_name") or "No display name"
    bio_text = user_data.get("bio") or "*This user has no bio.*"
    accent_color = user_data.get("accent_color") or 0x7289DA
    creation_str = "Unable to calculate"
    try:
        snowflake_id = int(user_id)
        timestamp = ((snowflake_id >> 22) + 1420070400000) / 1000
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        creation_str = get_egypt_time(creation_date)
    except:
        pass

    avatar_hash = user_data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{'gif' if avatar_hash.startswith('a_') else 'png'}?size=1024" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"

    banner_hash = user_data.get("banner")
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"
        banner_status = f"[Click to open banner]({banner_url})"
    else:
        banner_url = None
        banner_status = "*No banner set*"

    clan_data = user_data.get("clan")
    if clan_data:
        clan_tag = clan_data.get("tag", "No tag")
        clan_id = clan_data.get("identity_guild_id") or clan_data.get("guild_id") or "Unknown"
        clan_status = f"**₊ {clan_tag}**\n🆔 **ID:** `{clan_id}`"
    else:
        clan_status = "*Not in any Clan*"

    deco_data = user_data.get("avatar_decoration_data")
    if deco_data:
        asset_hash = deco_data.get("asset")
        deco_url = f"https://cdn.discordapp.com/avatar-decorations/{asset_hash}.png"
        deco_status = f"[Click to preview decoration]({deco_url})"
    else:
        deco_status = "*No avatar decoration*"

    embed = discord.Embed(
        title=f"👤 Profile: @{username}",
        description=f"Full profile details (retrieved at {get_egypt_time()})",
        color=accent_color,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=avatar_url)
    if banner_hash:
        embed.set_image(url=banner_url)

    embed.add_field(name="👤 Username", value=f"`{username}`", inline=True)
    embed.add_field(name="Display Name", value=global_name, inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
    embed.add_field(name="📅 Account Creation Date", value=f"`{creation_str}`", inline=False)
    embed.add_field(name="🛡️ Current Clan", value=clan_status, inline=False)
    embed.add_field(name="✨ Avatar Decoration", value=deco_status, inline=False)
    embed.add_field(name="📝 Bio", value=bio_text, inline=False)
    embed.add_field(name="🖼️ Banner", value=banner_status, inline=False)

    embed.set_footer(text="Advanced Discord Radar System • Instant fetch")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    print("🚀 Launching Advanced Discord Monitor...")
    radar_thread = threading.Thread(target=start_radar, daemon=True)
    radar_thread.start()
    discord_bot.run(BOT_TOKEN)
