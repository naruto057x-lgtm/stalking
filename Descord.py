import requests
import time
from datetime import datetime, timezone

# ==================== الإعدادات الأساسية ====================
BOT_TOKEN = "MTUwOTM3MDgyMzExNzUwODYyOA.Gcu40Y.GjypUteQXyVwe55l_Fgg0NCyD9P_eWQid4OzOY"  
TARGET_USER_ID = "1332799976077656105"    
WEBHOOK_URL = "https://discord.com/api/webhooks/1509353177663803522/OMdWhlsdCCU0rlTrVs-pWGt0Vhqnb81PYrJ9Q0IEOlhjs0ackASANAB59YOwfEuU-Bg7"
# ============================================================

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
        if current_data.get("username") != profile_cache["username"]:
            detected_changes.append(f"🔹 **تغيير اليوزرنيم:** من `{profile_cache['username']}` إلى `{current_data.get('username')}`")
            profile_cache["username"] = current_data.get("username")

        # 2. قنص تغيير الـ Global Name
        if current_data.get("global_name") != profile_cache["global_name"]:
            detected_changes.append(f"🔹 **تغيير الاسم المستعار:** من `{profile_cache['global_name']}` إلى `{current_data.get('global_name')}`")
            profile_cache["global_name"] = current_data.get("global_name")

        # 3. قنص تغيير البايو كاملاً
        if current_data.get("bio") != profile_cache["bio"]:
            detected_changes.append("📝 **قام بتعديل البايو (Bio) الخاص ببروفايله الحساب!**")
            profile_cache["bio"] = current_data.get("bio")

        # 4. قنص قفشة تغيير صورة البروفايل (الأفاتار)
        if current_data.get("avatar") != profile_cache["avatar"]:
            detected_changes.append("🖼️ **قفشة! الشخص قام بتغيير صورة البروفايل (Avatar) الحالية!**")
            profile_cache["avatar"] = current_data.get("avatar")

        # 5. قنص تغيير البانر
        if current_data.get("banner") != profile_cache["banner"]:
            detected_changes.append("🌌 **تم رصد تغيير في صورة البانر (Banner) الخلفية!**")
            profile_cache["banner"] = current_data.get("banner")

        # 6. قنص خروج أو دخول كلان (Guild Tag)
        current_clan_tag = current_data.get("clan", {}).get("tag") if current_data.get("clan") else None
        if current_clan_tag != profile_cache["clan_tag"]:
            detected_changes.append(f"🛡️ **تعديل الـ Clan Tag:** من `{profile_cache['clan_tag']}` إلى `{current_clan_tag}`")
            profile_cache["clan_tag"] = current_clan_tag

        # 7. قنص تغيير زينة الأفاتار (Decoration)
        current_deco = current_data.get("avatar_decoration_data", {}).get("asset") if current_data.get("avatar_decoration_data") else None
        if current_deco != profile_cache["avatar_decoration"]:
            detected_changes.append("✨ **قام بتغيير أو تحديث زينة الأفاتار (Avatar Decoration)!**")
            profile_cache["avatar_decoration"] = current_deco

        # إذا لستة التغييرات فيها داتا، ابعت التنبيه فوراً
        if detected_changes:
            changes_string = "\n".join(detected_changes)
            print("🔥 تم رصد تحديثات جديدة! جاري إرسال التنبيه الفوري...")
            send_to_webhook(current_data, TARGET_USER_ID, changes_made=changes_string)

if __name__ == "__main__":
    start_radar()
