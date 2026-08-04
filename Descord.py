import requests
import time
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone

# ==================== الإعدادات الأساسية ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables!")

TARGET_USER_ID = "1249754394417696801"    
WEBHOOK_URL = "https://discord.com/api/webhooks/1509353177663803522/OMdWhlsdCCU0rlTrVs-pWGt0Vhqnb81PYrJ9Q0IEOlhjs0ackASANAB59YOwfEuU-Bg7"
COMMANDS_CHANNEL_ID = 1509464730509643846
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix="!", intents=intents)

headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

# كاش لحفظ الحالة القديمة ومقارنتها بالتحديثات الجديدة
profile_cache = {
    "username": None,
    "global_name": None,
    "bio": None,
    "avatar": None,
    "banner": None,
    "clan_tag": None,
    "avatar_decoration": None
}

def get_discord_user_data(user_id):
    url = f"https://discord.com/api/v10/users/{user_id}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        else:
            print(f"❌ فشل في جلب البيانات من ديسكورد. كود الخطأ: {res.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال بالسيرفر: {e}")
    return None

def send_to_webhook(user_data, user_id, changes_made=None):
    username = user_data.get("username", "Unknown")
    global_name = user_data.get("global_name") or "لا يوجد اسم مستعار"
    bio_text = user_data.get("bio") or "*هذا الشخص مش كاتب بايو في بروفايله*"
    accent_color = user_data.get("accent_color") or 0x7289DA
    
    # 1. حساب تاريخ إنشاء الحساب
    try:
        snowflake_id = int(user_id)
        timestamp = ((snowflake_id >> 22) + 1420070400000) / 1000
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p UTC')
    except:
        creation_date = "غير قادر على الحساب"

    # 2. روابط البروفايل والبانر
    avatar_hash = user_data.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=1024"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    banner_hash = user_data.get("banner")
    banner_url = "https://images.jpg"
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"
        banner_status = f"[اضغط هنا لفتح البانر]({banner_url})"
    else:
        banner_status = "*الشخص مش حاطط صورة بانر*"

    # 3. بيانات الـ Clan
    clan_data = user_data.get("clan")
    if clan_data:
        clan_tag = clan_data.get("tag", "بدون تاغ")
        clan_id = clan_data.get("identity_guild_id") or clan_data.get("guild_id") or "غير معروف"
        clan_status = f"**₊ {clan_tag}**\n🆔 **ID:** `{clan_id}`"
    else:
        clan_status = "*الشخص ده مش مشترك في أي Clan حالياً*"

    # 4. بيانات الديكوريشن
    deco_data = user_data.get("avatar_decoration_data")
    if deco_data:
        asset_hash = deco_data.get("asset")
        deco_url = f"https://cdn.discordapp.com/avatar-decorations/{asset_hash}.png"
        deco_status = f"[اضغط هنا لمعاينة الديكوريشن]({deco_url})"
    else:
        deco_status = "*الشخص مش حاطط أي ديكوريشن على الأفاتار*"

    fields = [
        {"name": "👤 Username:", "value": f"`{username}`", "inline": True},
        {"name": "Name (Global Name):", "value": global_name, "inline": True},
        {"name": "🆔 User ID:", "value": f"`{user_id}`", "inline": True},
        {"name": "📅 تاريخ إنشاء الحساب:", "value": f"`{creation_date}`", "inline": False},
        {"name": "🛡️ الـ Clan الحالي (Guild Tag):", "value": clan_status, "inline": False},
        {"name": "✨ زينة الأفاتار (Decoration):", "value": deco_status, "inline": False},
        {"name": "📝 البايو (Bio) بالكامل:", "value": bio_text, "inline": False},
        {"name": "🖼️ رابط صورة البانر:", "value": banner_status, "inline": False}
    ]

    # لو مفيش تغييرات يبقا ده الإشعار المبدئي للتشغيل
    title = f"⚙️ تم بدء مراقبة الحساب بنجاح: @{username}"
    description = "الرادار شغال الآن 24 ساعة وهيتم فحص أي تغيير كل دقيقة تلقائياً."
    embed_color = accent_color

    # لو فيه لستة تغييرات واصلة للـ دالة
    if changes_made:
        title = f"🔥 قفشة! تم رصد تغيير جديد في بروفايل: @{username}"
        description = f"**التحديثات التي تم رصدها فوراً:**\n{changes_made}"
        embed_color = 0xFF0000  # قلب اللون أحمر عشان الإشعار يبان خطر وجامد في السيرفر

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": embed_color,
            "thumbnail": {"url": avatar_url},
            "image": {"url": banner_url if banner_hash else None},
            "fields": fields,
            "footer": {
                "text": "نظام الرادار الذكي المستمر • ديسكورد",
                "icon_url": "https://cdn.discordapp.com/embed/avatars/4.png"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }

    requests.post(WEBHOOK_URL, json=payload)

def start_radar():
    print("🔍 جاري الاتصال المبدئي لتهيئة الكاش وسحب البيانات الحالية...")
    initial_data = get_discord_user_data(TARGET_USER_ID)
    
    if not initial_data:
        print("❌ فشل تشغيل الرادار. تأكد من صلاحية التوكن والـ ID الحساب.")
        return

    # حفظ الداتا الحالية في الكاش لأول مرة
    profile_cache["username"] = initial_data.get("username")
    profile_cache["global_name"] = initial_data.get("global_name")
    profile_cache["bio"] = initial_data.get("bio")
    profile_cache["avatar"] = initial_data.get("avatar")
    profile_cache["banner"] = initial_data.get("banner")
    profile_cache["clan_tag"] = initial_data.get("clan", {}).get("tag") if initial_data.get("clan") else None
    profile_cache["avatar_decoration"] = initial_data.get("avatar_decoration_data", {}).get("asset") if initial_data.get("avatar_decoration_data") else None

    # إرسال كارت البروفايل الحالي فوراً للإعلان عن بدء الرادار
    send_to_webhook(initial_data, TARGET_USER_ID)
    print("🚀 الرادار مستقر وشغال في الخلفية الآن.. الفحص مستمر كل دقيقة!")

    while True:
        time.sleep(60)  # الفحص دقيقة بدقيقة
        current_data = get_discord_user_data(TARGET_USER_ID)
        if not current_data:
            continue

        detected_changes = []

        # 1. قنص تغيير اليوزرنيم
        current_username = current_data.get("username")
        print(f"[DEBUG] Username: {current_username} vs {profile_cache['username']}")
        if current_username != profile_cache["username"]:
            detected_changes.append(f"🔹 **تغيير اليوزرنيم:** من `{profile_cache['username']}` إلى `{current_username}`")
            print(f"✅ تم رصد تغيير في Username")
            profile_cache["username"] = current_username

        # 2. قنص تغيير الـ Global Name
        current_global_name = current_data.get("global_name")
        print(f"[DEBUG] Global Name: {current_global_name} vs {profile_cache['global_name']}")
        if current_global_name != profile_cache["global_name"]:
            detected_changes.append(f"🔹 **تغيير الاسم المستعار:** من `{profile_cache['global_name']}` إلى `{current_global_name}`")
            print(f"✅ تم رصد تغيير في Global Name")
            profile_cache["global_name"] = current_global_name

        # 3. قنص تغيير البايو كاملاً
        current_bio = current_data.get("bio")
        print(f"[DEBUG] Bio: {current_bio} vs {profile_cache['bio']}")
        if current_bio != profile_cache["bio"]:
            detected_changes.append("📝 **قام بتعديل البايو (Bio) الخاص ببروفايله الحساب!**")
            print(f"✅ تم رصد تغيير في Bio")
            profile_cache["bio"] = current_bio

        # 4. قنص قفشة تغيير صورة البروفايل (الأفاتار)
        current_avatar = current_data.get("avatar")
        print(f"[DEBUG] Avatar: {current_avatar} vs {profile_cache['avatar']}")
        if current_avatar != profile_cache["avatar"]:
            detected_changes.append("🖼️ **قفشة! الشخص قام بتغيير صورة البروفايل (Avatar) الحالية!**")
            print(f"✅ تم رصد تغيير في Avatar")
            profile_cache["avatar"] = current_avatar

        # 5. قنص تغيير البانر
        current_banner = current_data.get("banner")
        print(f"[DEBUG] Banner: {current_banner} vs {profile_cache['banner']}")
        if current_banner != profile_cache["banner"]:
            detected_changes.append("🌌 **تم رصد تغيير في صورة البانر (Banner) الخلفية!**")
            print(f"✅ تم رصد تغيير في Banner")
            profile_cache["banner"] = current_banner

        # 6. قنص خروج أو دخول كلان (Guild Tag)
        current_clan_tag = current_data.get("clan", {}).get("tag") if current_data.get("clan") else None
        print(f"[DEBUG] Clan Tag: {current_clan_tag} vs {profile_cache['clan_tag']}")
        if current_clan_tag != profile_cache["clan_tag"]:
            detected_changes.append(f"🛡️ **تعديل الـ Clan Tag:** من `{profile_cache['clan_tag']}` إلى `{current_clan_tag}`")
            print(f"✅ تم رصد تغيير في Clan Tag")
            profile_cache["clan_tag"] = current_clan_tag

        # 7. قنص تغيير زينة الأفاتار (Decoration)
        current_deco = current_data.get("avatar_decoration_data", {}).get("asset") if current_data.get("avatar_decoration_data") else None
        print(f"[DEBUG] Decoration: {current_deco} vs {profile_cache['avatar_decoration']}")
        if current_deco != profile_cache["avatar_decoration"]:
            detected_changes.append("✨ **قام بتغيير أو تحديث زينة الأفاتار (Avatar Decoration)!**")
            print(f"✅ تم رصد تغيير في Decoration")
            profile_cache["avatar_decoration"] = current_deco

        # إذا لستة التغييرات فيها داتا، ابعت التنبيه فوراً
        if detected_changes:
            changes_string = "\n".join(detected_changes)
            print("🔥 تم رصد تحديثات جديدة! جاري إرسال التنبيه الفوري...")
            send_to_webhook(current_data, TARGET_USER_ID, changes_made=changes_string)

@discord_bot.event
async def on_ready():
    print(f"\n{'='*70}")
    print(f"🤖 Discord Monitor Bot Ready as: {discord_bot.user.name}")
    print(f"{'='*70}\n")
    radar_monitor_loop.start()

@discord_bot.command(name="commands")
async def cmd_commands(ctx):
    """عرض جميع أوامر رادار ديسكورد"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    embed = discord.Embed(title="📖 قائمة أوامر رادار ديسكورد (Discord Monitor Commands)", color=0x7289DA)
    
    embed.add_field(
        name="👤 !profile",
        value="عرض بيانات البروفايل الحالية للحساب المراقب\n**مثال:** `!profile`",
        inline=False
    )
    
    embed.add_field(
        name="🔔 التنبيهات التلقائية",
        value="**النظام يرسل إشعارات تلقائية متى:**\n"
              "📝 **تعديل البايو** - إشعار فوري\n"
              "🖼️ **تغيير صورة البروفايل** - إشعار فوري مع الصورة الجديدة\n"
              "🌌 **تغيير صورة البانر** - إشعار فوري\n"
              "👤 **تغيير الاسم المستعار** - إشعار فوري\n"
              "🛡️ **الدخول/الخروج من Clan** - إشعار فوري\n"
              "✨ **تغيير زينة الأفاتار** - إشعار فوري",
        inline=False
    )
    
    embed.set_footer(text="الرادار يفحص البروفايل كل دقيقة تلقائياً 🔍")
    await ctx.send(embed=embed)

@discord_bot.command(name="profile")
async def cmd_profile(ctx):
    """عرض بيانات البروفايل الحالية"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    user_data = get_discord_user_data(TARGET_USER_ID)
    if not user_data:
        await ctx.send("❌ تعذر جلب بيانات البروفايل!")
        return
    
    # إنشاء نفس البيانات والـ embed مباشرة في هذه الروم دون الاعتماد على webhook
    username = user_data.get("username", "Unknown")
    global_name = user_data.get("global_name") or "لا يوجد اسم مستعار"
    bio_text = user_data.get("bio") or "*هذا الشخص مش كاتب بايو في بروفايله*"
    accent_color = user_data.get("accent_color") or 0x7289DA
    
    # حساب تاريخ إنشاء الحساب
    try:
        snowflake_id = int(TARGET_USER_ID)
        timestamp = ((snowflake_id >> 22) + 1420070400000) / 1000
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p UTC')
    except:
        creation_date = "غير قادر على الحساب"

    # روابط البروفايل والبانر
    avatar_hash = user_data.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{TARGET_USER_ID}/{avatar_hash}.{ext}?size=1024"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    banner_hash = user_data.get("banner")
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{TARGET_USER_ID}/{banner_hash}.{ext}?size=1024"
        banner_status = f"[اضغط هنا لفتح البانر]({banner_url})"
    else:
        banner_status = "*الشخص مش حاطط صورة بانر*"

    # بيانات الـ Clan
    clan_data = user_data.get("clan")
    if clan_data:
        clan_tag = clan_data.get("tag", "بدون تاغ")
        clan_id = clan_data.get("identity_guild_id") or clan_data.get("guild_id") or "غير معروف"
        clan_status = f"**₊ {clan_tag}**\n🆔 **ID:** `{clan_id}`"
    else:
        clan_status = "*الشخص ده مش مشترك في أي Clan حالياً*"

    # بيانات الديكوريشن
    deco_data = user_data.get("avatar_decoration_data")
    if deco_data:
        asset_hash = deco_data.get("asset")
        deco_url = f"https://cdn.discordapp.com/avatar-decorations/{asset_hash}.png"
        deco_status = f"[اضغط هنا لمعاينة الديكوريشن]({deco_url})"
    else:
        deco_status = "*الشخص مش حاطط أي ديكوريشن على الأفاتار*"

    # إنشاء الـ Embed مباشرة في الروم
    embed = discord.Embed(
        title=f"👤 بيانات البروفايل الحالية: @{username}",
        description="تفاصيل شاملة عن حساب الهدف",
        color=accent_color,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=avatar_url)
    if banner_hash:
        embed.set_image(url=banner_url)
    
    embed.add_field(name="👤 Username", value=f"`{username}`", inline=True)
    embed.add_field(name="Name (Global Name)", value=global_name, inline=True)
    embed.add_field(name="🆔 User ID", value=f"`{TARGET_USER_ID}`", inline=True)
    embed.add_field(name="📅 تاريخ إنشاء الحساب", value=f"`{creation_date}`", inline=False)
    embed.add_field(name="🛡️ الـ Clan الحالي (Guild Tag)", value=clan_status, inline=False)
    embed.add_field(name="✨ زينة الأفاتار (Decoration)", value=deco_status, inline=False)
    embed.add_field(name="📝 البايو (Bio) بالكامل", value=bio_text, inline=False)
    embed.add_field(name="🖼️ رابط صورة البانر", value=banner_status, inline=False)
    
    embed.set_footer(text="نظام الرادار الذكي المستمر • ديسكورد | تم الجلب الآن")
    
    await ctx.send(embed=embed)

async def radar_monitor_loop_task():
    """حلقة المراقبة المستمرة في الخلفية"""
    await discord_bot.wait_until_ready()
    start_radar()

def main():
    """تشغيل البوت"""
    import asyncio
    # تشغيل حلقة المراقبة في الخلفية
    asyncio.create_task(radar_monitor_loop_task())
    discord_bot.run(BOT_TOKEN)

@tasks.loop(minutes=1)
async def radar_monitor_loop():
    """مراقبة محدثة كل دقيقة"""
    pass

if __name__ == "__main__":
    print("🚀 إطلاق نظام مراقبة ديسكورد المتقدم...")
    
    # تشغيل البوت والرادار معاً
    import asyncio
    import threading
    
    # تشغيل الرادار في خيط منفصل
    radar_thread = threading.Thread(target=start_radar, daemon=True)
    radar_thread.start()
    
    # تشغيل البوت الرئيسي
    discord_bot.run(BOT_TOKEN)
