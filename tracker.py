#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# ==================== الإعدادات والروابط المباشرة ====================
TARGET_USER_ID = 7620590660
ROBLOSECURITY = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzg3MDc0NjI1MjE0MTU4NjY0MTMoAw.lR4MHfm3X3EsX6l5GP_KSoP7J8ItNv3Y-M21bw3uw7EsTysoES0xiYjedO_l--XbWmFe2L7j7sV259vfgSB6DjwCm8rQBsRu-PRBvN56FQTLExPJEbw61_kh1w6P-HdVu6mmxfUzGh4ES4U4niEFLrsBQQyCPc9mmqkToyHQXFl9PakEGyMEuw-ywbGelm6Mmf0J5gEEEJsg45-TUcQoEbm2aa-bme-REDE7pM33dQBwNjDHipvkv4Dg5XWSfCYCgn3cpwl1JCR4BtHcrz-z1vZ_8pUy4pIEzlbQnBwrA6_BGveWXOwqEoyaBu-Jt_RsGpdTnZhpGDe6p5pR3SKGNU9nh5h0S5NXKs6ApPc9pup1rb1HB1cI7aUhfUuv1ap2rE5o6gCJB3vKlWh-8JMcbBqL4DSw3QivmRphFM2Cn2f5rI8ilrzMTXlvAouPFq00FJV9J71WyCx-69WEx6b-F2UfKiLdRFUM-Cu4CAwXRkqcz6HLs8BNGoP2ajEhb8QptKl5-faQy4szP4xSG8o8rp2ZhUfnHpHeMBP68wYf9XPRtvUIzkj_Jg2Dlwsfc7b5j9_fY8Ke-0_Rta8fwDLnITgP0zVim90_RzAZ7ejROXUA97pkxnM0bpYvsVzk_COZ7haU5MRZukF0oWVTsEMh8g89wNSczqGGFfvc082KrSCnRLHHozaRZbv6gXlsVvNUxQ3XxhNX6BQfbgyOjHXbC4Wp9U5OWtKAk9bNXkg-acTmySMNPjCqQRAvYXdeLmqz-C6CEUYWiV4IUen4pGOzUxDSVIZfvBIOp33gfO1QRbj8mDYjpJXCVJQObSom8uGRG0iMoSFDkFRl8Obek_poPejb7-VyH925rwmgWZcvFzmJ6KEaBqU1kQc9tb-BzwHKRYoadC14KKGpAPRiBUKMe9rnMDKq_bbKpRqSEQfdGtotDGjnxE5Hi_mJYVSFjC0YEztMzw"

BOT_TOKEN = "MTUwOTM3MDgyMzExNzUwODYyOA.Gcu40Y.GjypUteQXyVwe55l_Fgg0NCyD9P_eWQid4OzOY"
CMD_CHANNEL_ID = 1509431098117984327
ALERT_CHANNEL_ID = 1509345547197091940

# ==================== MongoDB Configuration ====================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://marwangamer056_db_user:NulNLKsdAz55Av50@cluster0.j35ail6.mongodb.net/?appName=Cluster0")
INTERVAL = 60
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

USER_NAME = "Unknown"
DISPLAY_NAME = "Unknown"

state = {
    "status": None,
    "game": None,
    "place_id": None,
    "game_id": None,
    "last_online_time": None,      
    "offline_since": None,         
    "offline_alert_sent": False,   
    "last_game_name": "مفيش مابات مسجلة",
    "last_game_time": None,
    "game_session_start": None,
    "session_recorded": False     # لمنع تسجيل الجلسة أكثر من مرة
}

headers = {
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}",
    "Content-Type": "application/json"
}

# ==================== MongoDB Connection ====================
try:
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    db = mongo_client.roblox_radar
    print("✅ اتصال MongoDB نجح!")
except ConnectionFailure as e:
    print(f"❌ فشل الاتصال بـ MongoDB: {e}")
    exit(1)

# Collections
friends_collection = db.friends
games_collection = db.games
state_collection = db.state

# ==================== Database Helper Functions ====================
def load_friends_data():
    """تحميل بيانات الأصدقاء من MongoDB"""
    doc = friends_collection.find_one({"_id": "friends_data"})
    if doc:
        return {
            "baseline_ids": doc.get("baseline_ids", []),
            "friends_details": doc.get("friends_details", {}),
            "detected_new_friends": doc.get("detected_new_friends", {})
        }
    return {"baseline_ids": [], "friends_details": {}, "detected_new_friends": {}}

def save_friends_data(data):
    """حفظ بيانات الأصدقاء في MongoDB"""
    friends_collection.replace_one(
        {"_id": "friends_data"},
        {
            "_id": "friends_data",
            "baseline_ids": data.get("baseline_ids", []),
            "friends_details": data.get("friends_details", {}),
            "detected_new_friends": data.get("detected_new_friends", {}),
            "last_updated": datetime.now()
        },
        upsert=True
    )

def load_games_stats():
    """تحميل إحصائيات الألعاب من MongoDB"""
    doc = games_collection.find_one({"_id": "games_stats"})
    if doc:
        stats = {}
        for key, value in doc.items():
            if key != "_id":
                stats[key] = value
        return stats
    return {}

def save_games_stats(data):
    """حفظ إحصائيات الألعاب في MongoDB"""
    doc = {"_id": "games_stats", "last_updated": datetime.now()}
    doc.update(data)
    games_collection.replace_one({"_id": "games_stats"}, doc, upsert=True)

def record_game_session(place_id, game_name, duration_seconds):
    """تسجيل جلسة لعب جديدة"""
    if not place_id or not game_name:
        return
    
    stats = load_games_stats()
    place_id_str = str(place_id)
    
    if place_id_str not in stats:
        stats[place_id_str] = {
            "name": game_name,
            "total_time": 0,
            "sessions": 0,
            "last_played": None
        }
    
    stats[place_id_str]["total_time"] += duration_seconds
    stats[place_id_str]["sessions"] += 1
    stats[place_id_str]["last_played"] = datetime.now().isoformat()
    
    save_games_stats(stats)

def get_relative_time_str(past_time):
    """عرض الوقت بصيغة نسبية (منذ كام وقت) بالعربية مع الثواني"""
    if not past_time:
        return "❌ مفيش بيانات مسجلة - لم يكن الشخص أونلاين بعد"
    
    diff = datetime.now() - past_time
    total_seconds = int(diff.total_seconds())
    
    # حساب الأيام والساعات والدقائق والثواني
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # بناء النتيجة بناءً على الفترة الزمنية
    if days > 0:
        return f"منذ {days} يوم و {hours} ساعة و {minutes} دقيقة"
    elif hours > 0:
        return f"منذ {hours} ساعة و {minutes} دقيقة و {seconds} ثانية"
    elif minutes > 0:
        return f"منذ {minutes} دقيقة و {seconds} ثانية"
    else:
        return f"منذ {seconds} ثانية فقط (أونلاين حالياً تقريباً)"

# --- جلب بيانات أي يوزر بالـ ID من روبلوكس ---
async def fetch_single_user_profile(session, user_id):
    try:
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("name"), data.get("displayName")
    except:
        pass
    return None, None

# --- جلب قائمة الأصدقاء كاملة ---
async def fetch_all_friends(session):
    all_friends = []
    cursor = ""
    while True:
        url = f"https://friends.roblox.com/v1/users/{TARGET_USER_ID}/friends?userSortLimit=50"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            async with session.get(url, timeout=10) as r:
                if r.status == 200:
                    res_data = await r.json()
                    page_data = res_data.get("data", [])
                    all_friends.extend(page_data)
                    cursor = res_data.get("nextPageCursor")
                    if not cursor:
                        break
                else:
                    break
        except Exception as e:
            print(f"Error fetching friends page: {e}")
            break
    return all_friends

async def fetch_roblox_profile():
    global USER_NAME, DISPLAY_NAME
    async with aiohttp.ClientSession() as session:
        u_name, d_name = await fetch_single_user_profile(session, TARGET_USER_ID)
        if u_name:
            USER_NAME = u_name
            DISPLAY_NAME = d_name
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Target Loaded Successfully: {DISPLAY_NAME} (@{USER_NAME})")

@bot.event
async def on_ready():
    print("\n" + "="*70)
    print(f"🤖 Bot is Online as: {bot.user.name} | MongoDB Radar System 🔥")
    print("="*70 + "\n")
    await fetch_roblox_profile()
    roblox_radar_loop.start()

@bot.check
async def check_channel(ctx):
    return ctx.channel.id == CMD_CHANNEL_ID

# --- الأوامر التفاعلية ---

@bot.command(name="commands")
async def cmd_commands(ctx):
    embed = discord.Embed(title="📖 قائمة الأوامر المتاحة (Commands Menu)", color=0x9b59b6)
    
    embed.add_field(name="📊 !lastseen", value="يعرض آخر وقت شُفت اللاعب فيه أونلاين\n**مثال:** `!lastseen`", inline=False)
    embed.add_field(name="🎮 !lastgame", value="يعرض آخر ماب دخلها اللاعب ومنذ كام وقت\n**مثال:** `!lastgame`", inline=False)
    embed.add_field(name="⏱️ !gametime", value="يعرض وقت اللعب الحالي في اللعبة المفتوحة الآن\n**مثال:** `!gametime`", inline=False)
    embed.add_field(name="🔗 !join", value="يبعتلك رابط الدخول المباشر (Join Link) الحالي للعبة\n**مثال:** `!join`", inline=False)
    embed.add_field(name="🗺️ !map", value="يعطيك رابط صفحة الماب الحالية على روبلوكس\n**مثال:** `!map`", inline=False)
    embed.add_field(name="🏆 !top [3/custom/all]", value="اختر عدد الألعاب: 3، أو رقم مخصص، أو كل الألعاب المسجلة\n**أمثلة:** `!top 3`, `!top 5`, `!top all`", inline=False)
    embed.add_field(name="📈 !totaltimeplayed", value="يعرض إجمالي ساعات اللعب لكل الألعاب مضافة\n**مثال:** `!totaltimeplayed`", inline=False)
    embed.add_field(name="📊 !gamesstats", value="إحصائيات تفصيلية عن كل لعبة مع عدد الجلسات\n**مثال:** `!gamesstats`", inline=False)
    embed.add_field(name="👤 !avatar", value="يعطيك صورة الأفاتار (الشخصية) في روبلوكس\n**مثال:** `!avatar`", inline=False)
    embed.add_field(name="📝 !about", value="يعرض البايو (الوصف) الحالي في بروفايل اللاعب\n**مثال:** `!about`", inline=False)
    embed.add_field(name="👥 !friendstest", value="يختبر ويعرض أول 10 أصدقاء من القائمة الكاملة\n**مثال:** `!friendstest`", inline=False)
    embed.add_field(name="➕ !newfriends", value="يعرض آخر 5 أصدقاء جدد تم اكتشافهم\n**مثال:** `!newfriends`", inline=False)
    embed.add_field(name="📜 !newhistoryfriends", value="يعرض السجل الكامل لجميع الأصدقاء الجدد المكتشفة من البداية\n**مثال:** `!newhistoryfriends`", inline=False)
    embed.add_field(name="📊 !status", value="عرض حالة نظام الرادار والإحصائيات\n**مثال:** `!status`", inline=False)
    embed.set_footer(text="اكتب الأمر في روم الأوامر المخصص ويرد عليك الرادار بسرعة ⚡")
    await ctx.send(embed=embed)

@bot.command(name="friendstest")
async def cmd_friends_test(ctx):
    await ctx.send("🔄 جاري فحص وجلب قائمة الأصدقاء من MongoDB...")
    async with aiohttp.ClientSession() as session:
        try:
            friends = await fetch_all_friends(session)
            if not friends:
                await ctx.send("👤 قائمة الأصدقاء مخفية، فارغة، أو تعذر جلبها حالياً.")
                return
            
            embed = discord.Embed(title=f"👥 اختبار قائمة الأصدقاء (عددها الكلي: {len(friends)})", color=0x3498db)
            for f in friends[:10]:
                fid = f.get('id')
                real_username, real_display = await fetch_single_user_profile(session, fid)
                if not real_username: real_username = f.get('name') or "Unknown"
                if not real_display: real_display = f.get('displayName') or real_username
                embed.add_field(name=real_display, value=f"@{real_username}\nID: `{fid}`", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ: {str(e)[:50]}")

@bot.command(name="lastseen")
async def cmd_last_seen(ctx):
    """عرض آخر وقت رُصد الشخص أونلاين"""
    if state["status"] in [1, 2, 3]:
        # إذا كان أونلاين الآن
        embed = discord.Embed(
            title="🟢 الشخص أونلاين الآن!",
            description="الهدف متصل بالإنترنت حالياً",
            color=0x2ecc71
        )
        embed.add_field(
            name="⏱️ آخر مرة تُسجل أونلاين",
            value="الآن",
            inline=False
        )
        embed.set_footer(text="تحديث فوري من الرادار")
        await ctx.send(embed=embed)
    else:
        # إذا كان أوفلاين
        time_str = get_relative_time_str(state["last_online_time"])
        
        if state["last_online_time"]:
            # عرض التاريخ والوقت بالتفصيل
            exact_time = state["last_online_time"].strftime("%Y-%m-%d %H:%M:%S")
            embed = discord.Embed(
                title="🔴 الشخص أوفلاين",
                description=f"آخر مرة تُرصد اتصال: {time_str}",
                color=0xff6b6b
            )
            embed.add_field(
                name="⏱️ الوقت الدقيق",
                value=f"`{exact_time}`",
                inline=False
            )
            embed.set_footer(text="البيانات من نظام الرادار المراقب")
        else:
            embed = discord.Embed(
                title="❓ لا توجد بيانات",
                description="لم يتم رصد الشخص أونلاين بعد منذ بدء الرادار",
                color=0x95a5a6
            )
        
        await ctx.send(embed=embed)

@bot.command(name="lastgame")
async def cmd_last_game(ctx):
    time_str = get_relative_time_str(state["last_game_time"])
    await ctx.send(f"🎮 **آخر ماب دخلها:** {state['last_game_name']} \n⏱️ **منذ:** `{time_str}`")

@bot.command(name="about")
async def cmd_about(ctx):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://users.roblox.com/v1/users/{TARGET_USER_ID}") as r:
                if r.status == 200:
                    desc = (await r.json()).get("description", "لا يوجد بايو مكتوب.")
                    if desc == "": desc = "البايو فارغ."
                    embed = discord.Embed(title=f"📝 البايو الحالي لـ {DISPLAY_NAME}", description=desc, color=0x9b59b6)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ تعذر جلب البايو.")
        except Exception as e:
            await ctx.send(f"❌ خطأ: {e}")

@bot.command(name="newfriends")
async def cmd_new_friends(ctx):
    data = load_friends_data()
    new_friends = data.get("detected_new_friends", {})
    if not new_friends:
        await ctx.send("🔍 لم يتم رصد أي أصدقاء جدد منذ تشغيل الرادار.")
        return
    
    embed = discord.Embed(title="➕ آخر 5 أصدقاء جدد تم رصدهم", color=0x2ecc71)
    items = list(new_friends.values())[-5:]
    items.reverse()
    for f in items:
        embed.add_field(name=f['display_name'], value=f"@{f['username']}\n📅 رُصد في: {f['detected_at']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="newhistoryfriends")
async def cmd_new_history_friends(ctx):
    data = load_friends_data()
    new_friends = data.get("detected_new_friends", {})
    if not new_friends:
        await ctx.send("🔍 السجل فارغ، مفيش أي إضافة جديدة متسجلة.")
        return
    
    embed = discord.Embed(title="📜 سجل جميع الإضافات الجديدة المكتشفة", color=0xe67e22)
    for fid, f in new_friends.items():
        embed.add_field(name=f['display_name'], value=f"@{f['username']}\n📅 التوقيت: {f['detected_at']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="join")
async def cmd_join(ctx):
    if not state.get("place_id") or not state.get("game_id"):
        await ctx.send("❌ اللاعب مش دخال أي لعبة دلوقتي، ما فيش رابط join متاح.")
        return
    
    join_link = f"roblox://experiences/start?placeId={state['place_id']}&gameId={state['game_id']}"
    embed = discord.Embed(title="🔗 رابط الدخول المباشر (JOIN LINK)", color=0x2ecc71)
    embed.add_field(name="Click to Join", value=f"[اضغط هنا للدخول وراه الآن 🔥]({join_link})", inline=False)
    embed.set_footer(text="الرابط يفتح لعبة الروبلوكس تلقائياً")
    await ctx.send(embed=embed)

@bot.command(name="map")
async def cmd_map(ctx):
    if not state.get("place_id"):
        await ctx.send("❌ اللاعب مش دخال أي لعبة دلوقتي، ما فيش ماب.")
        return
    
    map_page = f"https://www.roblox.com/games/{state['place_id']}"
    embed = discord.Embed(title="🎮 رابط صفحة الماب", description=state.get("game", "Unknown"), color=0x3498db)
    embed.add_field(name="اسم الماب", value=f"**{state['game']}**", inline=False)
    embed.add_field(name="رابط الصفحة", value=f"[اضغط هنا لفتح صفحة الماب]({map_page})", inline=False)
    embed.add_field(name="Place ID", value=f"`{state['place_id']}`", inline=False)
    await ctx.send(embed=embed)

async def fetch_avatar_urls(session):
    """جلب روابط صور الأفاتار الحالية من Roblox API"""
    try:
        avatar_full_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={TARGET_USER_ID}&size=720x720&format=Png&isCircular=false"
        
        async with session.get(avatar_full_url, timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                if data.get('data') and len(data['data']) > 0:
                    full_img_url = data['data'][0].get('imageUrl')
                    if full_img_url:
                        return full_img_url
        
        headshot_url = f"https://assetdelivery.roblox.com/v2/avatar-thumbnails?ids={TARGET_USER_ID}&size=720x720&format=Png"
        
        async with session.get(headshot_url, timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                if data.get('data') and len(data['data']) > 0:
                    img_url = data['data'][0].get('imageUrl')
                    return img_url
                    
    except Exception as e:
        print(f"Error fetching avatar URLs: {e}")
    
    return None

@bot.command(name="avatar")
async def cmd_avatar(ctx):
    """عرض صورة الأفاتار الكاملة والكبيرة والمحدّثة للشخصية"""
    async with aiohttp.ClientSession() as session:
        try:
            avatar_url = await fetch_avatar_urls(session)
            
            if avatar_url:
                embed = discord.Embed(title=f"👤 صورة الأفاتار - {DISPLAY_NAME}", description="صورة الشخصية الكاملة والكبيرة (محدّثة تلقائياً)", color=0x9b59b6)
                embed.set_image(url=avatar_url)
                embed.add_field(name="Username", value=f"@{USER_NAME}", inline=True)
                embed.add_field(name="User ID", value=f"`{TARGET_USER_ID}`", inline=True)
                embed.set_footer(text="الصورة محدّثة تلقائياً عند تغيير الأفاتار")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ لم يتمكن من جلب صورة الأفاتار.")
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name="top")
async def cmd_top(ctx, limit: str = "3"):
    stats = load_games_stats()
    if not stats:
        await ctx.send("📊 لا توجد بيانات إحصائيات ألعاب متسجلة حتى الآن.")
        return
    
    sorted_games = sorted(stats.items(), key=lambda x: x[1].get("total_time", 0) if isinstance(x[1], dict) else 0, reverse=True)
    
    # تحديد العدد المطلوب
    if limit.lower() == "all":
        limit_num = len(sorted_games)
        title = "🏆 جميع الألعاب المسجلة (الكاملة)"
    elif limit.isdigit():
        limit_num = int(limit)
        title = f"🏆 أعلى {limit_num} ألعاب"
    else:
        limit_num = 3
        title = "🏆 أعلى 3 ألعاب"
    
    embed = discord.Embed(title=title, color=0xf39c12)
    
    if not sorted_games:
        embed.description = "❌ لا توجد بيانات"
        await ctx.send(embed=embed)
        return
    
    total_hours_all = 0
    total_sessions_all = 0
    
    for idx, (place_id, data) in enumerate(sorted_games[:limit_num], 1):
        if not isinstance(data, dict):
            continue
        total_seconds = data.get("total_time", 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        sessions = data.get("sessions", 0)
        total_hours_all += hours
        total_sessions_all += sessions
        
        time_str = f"{hours}س {minutes}د" if hours > 0 else f"{minutes}د"
        
        embed.add_field(
            name=f"#{idx} - {data.get('name', 'Unknown')}",
            value=f"⏱️ الوقت الكلي: **{time_str}**\n📊 عدد الجلسات: **{sessions}**\n🆔 Place ID: `{place_id}`",
            inline=False
        )
    
    embed.set_footer(text=f"📊 الإجمالي: {total_hours_all} ساعة عبر {total_sessions_all} جلسة | يتم التحديث تلقائياً")
    await ctx.send(embed=embed)

@bot.command(name="gametime")
async def cmd_game_time(ctx):
    """عرض وقت اللعب الحالي"""
    if state["status"] != 2 or not state["game_session_start"]:
        await ctx.send("❌ اللاعب غير لاعب الآن، لا يوجد وقت لعب")
        return
    
    current_session_duration = int((datetime.now() - state["game_session_start"]).total_seconds())
    hours = current_session_duration // 3600
    minutes = (current_session_duration % 3600) // 60
    seconds = current_session_duration % 60
    
    time_str = ""
    if hours > 0:
        time_str = f"**{hours}س {minutes}د {seconds}ث**"
    elif minutes > 0:
        time_str = f"**{minutes}د {seconds}ث**"
    else:
        time_str = f"**{seconds}ث**"
    
    embed = discord.Embed(title=f"⏱️ وقت اللعب الحالي", description=f"اللعبة: **{state['game']}**", color=0x3498db)
    embed.add_field(name="⏳ المدة المقضية في هذه الجلسة", value=time_str, inline=False)
    embed.set_footer(text="يتم التحديث لحظة بلحظة")
    await ctx.send(embed=embed)

@bot.command(name="totaltimeplayed")
async def cmd_total_time(ctx):
    """إجمالي ساعات اللعب"""
    stats = load_games_stats()
    if not stats:
        await ctx.send("📊 لا توجد بيانات إحصائيات ألعاب متسجلة حتى الآن.")
        return
    
    total_seconds = sum(data.get("total_time", 0) for data in stats.values() if isinstance(data, dict))
    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60
    total_sessions = sum(data.get("sessions", 0) for data in stats.values() if isinstance(data, dict))
    
    time_str = f"{total_hours}س {total_minutes}د" if total_hours > 0 else f"{total_minutes}د"
    
    embed = discord.Embed(title="📈 إجمالي ساعات اللعب", color=0x2ecc71)
    embed.add_field(name="⏰ الوقت الكلي", value=f"**{time_str}**", inline=True)
    embed.add_field(name="🎮 إجمالي الجلسات", value=f"**{total_sessions}**", inline=True)
    embed.set_footer(text="محسوب من جميع الألعاب المسجلة")
    await ctx.send(embed=embed)

@bot.command(name="gamesstats")
async def cmd_games_stats(ctx):
    """إحصائيات تفصيلية عن الألعاب"""
    stats = load_games_stats()
    if not stats:
        await ctx.send("📊 لا توجد بيانات إحصائيات ألعاب متسجلة حتى الآن.")
        return
    
    sorted_games = sorted(stats.items(), key=lambda x: x[1].get("total_time", 0) if isinstance(x[1], dict) else 0, reverse=True)
    
    embed = discord.Embed(title="📊 إحصائيات الألعاب التفصيلية", color=0x9b59b6)
    
    for idx, (place_id, data) in enumerate(sorted_games, 1):
        if not isinstance(data, dict):
            continue
        total_seconds = data.get("total_time", 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        sessions = data.get("sessions", 0)
        avg_session = (total_seconds // sessions) if sessions > 0 else 0
        avg_minutes = avg_session // 60
        avg_seconds = avg_session % 60
        
        time_str = f"{hours}س {minutes}د" if hours > 0 else f"{minutes}د"
        avg_str = f"{avg_minutes}د {avg_seconds}ث" if avg_minutes > 0 else f"{avg_seconds}ث"
        
        embed.add_field(
            name=f"#{idx} - {data.get('name', 'Unknown')}",
            value=f"⏱️ الكلي: **{time_str}**\n📊 الجلسات: **{sessions}**\n📌 المتوسط: **{avg_str}**\n🆔 ID: `{place_id}`",
            inline=False
        )
    
    embed.set_footer(text="إحصائيات دقيقة وملخصة")
    await ctx.send(embed=embed)

@bot.command(name="status")
async def cmd_status(ctx):
    """التحقق من حالة نظام الرادار والأصدقاء"""
    data = load_friends_data()
    stats = load_games_stats()
    
    baseline_count = len(data.get("baseline_ids", []))
    new_friends_count = len(data.get("detected_new_friends", {}))
    total_friends = len(data.get("friends_details", {}))
    games_recorded = len([k for k in stats.keys() if k != "_id"])
    
    embed = discord.Embed(title="📊 حالة نظام الرادار (MongoDB)", color=0x00ff00)
    
    embed.add_field(name="👤 الهدف", value=f"**{DISPLAY_NAME}** (@{USER_NAME})\nID: `{TARGET_USER_ID}`", inline=False)
    
    status_text = "🟢 أونلاين" if state["status"] in [1, 2, 3] else "🔴 أوفلاين"
    embed.add_field(name="🔌 حالة الاتصال", value=status_text, inline=False)
    
    if state["status"] == 2:
        embed.add_field(name="🎮 اللعبة الحالية", value=f"**{state['game']}**", inline=False)
    
    embed.add_field(name="👥 إحصائيات الأصدقاء", value=f"✅ أساسيين: `{baseline_count}`\n➕ جدد: `{new_friends_count}`\n📊 الكل: `{total_friends}`", inline=False)
    embed.add_field(name="🎮 إحصائيات الألعاب", value=f"📈 ألعاب مسجلة: `{games_recorded}`", inline=False)
    embed.add_field(name="☁️ قاعدة البيانات", value="✅ MongoDB Atlas متصل", inline=False)
    
    embed.set_footer(text="يتم تحديث البيانات تلقائياً كل دقيقة")
    await ctx.send(embed=embed)

# --- رادار الفحص الدوري التلقائي ---

@tasks.loop(seconds=INTERVAL)
async def roblox_radar_loop():
    global state
    alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not alert_channel: return

    async with aiohttp.ClientSession() as session:
        try:
            # 1. فحص الحالة والنشاط والمابات
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [TARGET_USER_ID]}, headers=headers) as r:
                if r.status == 200:
                    presence_data = await r.json()
                    presence = presence_data["userPresences"][0]
                    status = presence["userPresenceType"]
                    game = presence.get("lastLocation", "Unknown")
                    place_id = presence.get("placeId")
                    game_id = presence.get("gameId")
                    now = datetime.now()

                    if status in [1, 2, 3] and state["status"] == 0:
                        away_text = ""
                        if state["last_online_time"]:
                            away_diff = now - state["last_online_time"]
                            if away_diff > timedelta(minutes=30):
                                total_secs = int(away_diff.total_seconds())
                                hours = total_secs // 3600
                                mins = (total_secs % 3600) // 60
                                away_text = f"\n⚠️ **مكانتش فاتحة بقالها:** {hours} ساعة و {mins} دقيقة"
                        
                        embed = discord.Embed(title="🔵 [الهدف أونلاين الآن]", description=f"اللاعب متواجد حالياً في الموقع أو القائمة الرئيسية.{away_text}", color=0x3498db)
                        await alert_channel.send(embed=embed)
                        state["offline_alert_sent"] = False
                        state["offline_since"] = None

                    if status in [1, 2, 3]:
                        state["last_online_time"] = now

                    if status == 2 and state["status"] != 2:
                        state["last_game_name"] = game
                        state["last_game_time"] = now
                        state["place_id"] = place_id
                        state["game_id"] = game_id
                        state["game_session_start"] = now
                        state["session_recorded"] = False  # إعادة تعيين عند بدء جلسة جديدة
                        page_link = f"https://www.roblox.com/games/{place_id}"
                        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}" if game_id else page_link

                        embed = discord.Embed(title="🎮 [بدأ يلعب ماب جديدة الآن]", description=f"الهدف دخل سيرفر ماب جديد يعيش!", color=0x2ecc71)
                        embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
                        embed.add_field(name="رابط صفحة الماب (Roblox Page)", value=f"[اضغط هنا لفتح الصفحة]({page_link})", inline=False)
                        embed.add_field(name="رابط الدخول المباشر وراه (JOIN LINK) 🔥", value=f"[اضغط هنا للدخول وراه السيرفر فوراً]({join_link})", inline=False)
                        await alert_channel.send(embed=embed)
                    
                    # تسجيل الجلسة مرة واحدة فقط عند الخروج من اللعبة
                    if status != 2 and state["status"] == 2:
                        if state["game_session_start"] and state["last_game_name"] != "مفيش مابات مسجلة" and not state["session_recorded"]:
                            session_duration = int((now - state["game_session_start"]).total_seconds())
                            record_game_session(state["place_id"], state["last_game_name"], session_duration)
                            state["session_recorded"] = True  # وضع علامة بأن الجلسة تم تسجيلها
                            
                            # إرسال رسالة تفصيلية عند الخروج من اللعب
                            hours = session_duration // 3600
                            minutes = (session_duration % 3600) // 60
                            seconds = session_duration % 60
                            time_str = f"{hours}س {minutes}د {seconds}ث" if hours > 0 else f"{minutes}د {seconds}ث"
                            
                            online_duration = int((now - state["last_online_time"]).total_seconds()) if state["last_online_time"] else 0
                            online_hours = online_duration // 3600
                            online_minutes = (online_duration % 3600) // 60
                            online_str = f"{online_hours}س {online_minutes}د" if online_hours > 0 else f"{online_minutes}د"
                            
                            # جلب البيانات الإحصائية للعبة من MongoDB
                            stats = load_games_stats()
                            game_stats = stats.get(str(state["place_id"]), {})
                            total_game_time = game_stats.get("total_time", 0)
                            total_sessions = game_stats.get("sessions", 0)
                            last_played = game_stats.get("last_played")
                            
                            total_game_hours = total_game_time // 3600
                            total_game_minutes = (total_game_time % 3600) // 60
                            total_game_str = f"{total_game_hours}س {total_game_minutes}د" if total_game_hours > 0 else f"{total_game_minutes}د"
                            
                            embed_end = discord.Embed(
                                title="⏹️ [انتهت جلسة اللعب]", 
                                description=f"الهدف خرج من اللعبة وتم تسجيل الجلسة", 
                                color=0xff6b6b
                            )
                            
                            embed_end.add_field(name="🎮 اسم اللعبة", value=f"**{state['last_game_name']}**", inline=False)
                            embed_end.add_field(name="⏱️ مدة هذه الجلسة", value=f"**{time_str}**", inline=True)
                            embed_end.add_field(name="🟢 مدة الاتصال الكلية", value=f"**{online_str}**", inline=True)
                            embed_end.add_field(name="📊 إجمالي الوقت بهذه اللعبة", value=f"**{total_game_str}**", inline=True)
                            embed_end.add_field(name="📍 عدد مرات اللعب", value=f"**{total_sessions} جلسة**", inline=True)
                            
                            if last_played:
                                embed_end.add_field(name="📅 آخر مرة تم تسجيلها", value=f"`{last_played}`", inline=False)
                            
                            embed_end.add_field(name="🆔 Place ID", value=f"`{state['place_id']}`", inline=False)
                            embed_end.set_footer(text="✅ تم تسجيل الجلسة بنجاح في قاعدة البيانات MongoDB")
                            await alert_channel.send(embed=embed_end)

                    if status == 0 and state["status"] != 0:
                        state["offline_since"] = now
                        state["offline_alert_sent"] = False

                    if status == 0 and state["offline_since"] and not state["offline_alert_sent"]:
                        if now - state["offline_since"] >= timedelta(minutes=10):
                            embed = discord.Embed(title="🔴 [الهدف أوفلاين الآن]", description="اللاعب قفل الحساب تماماً ومبقاش متصل (عدى أكتر من 10 دقائق أوفلاين).", color=0x7f8c8d)
                            await alert_channel.send(embed=embed)
                            state["offline_alert_sent"] = True

                    if status != state["status"]: state["status"] = status
                    if status == 2: state["game"] = game

            # 2. رادار الأصدقاء المتقدم مع MongoDB
            curr_friends = await fetch_all_friends(session)
            if curr_friends:
                current_ids = [f["id"] for f in curr_friends]
                friends_data = load_friends_data()
                
                if not friends_data["baseline_ids"]:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] First run! Storing ALL baseline to MongoDB silently...")
                    friends_data["baseline_ids"] = current_ids
                    for f in curr_friends:
                        fid = str(f["id"])
                        friends_data["friends_details"][fid] = {
                            "username": f.get("name") or "Unknown",
                            "display_name": f.get("displayName") or f.get("name") or "Unknown",
                            "added_at": "Baseline"
                        }
                    save_friends_data(friends_data)
                    print(f"✅ Full baseline saved to MongoDB with {len(current_ids)} friends.")
                
                else:
                    baseline_set = set(friends_data["baseline_ids"])
                    for f in curr_friends:
                        fid = f["id"]
                        fid_str = str(fid)
                        
                        if fid not in baseline_set:
                            real_username, real_display = await fetch_single_user_profile(session, fid)
                            if not real_username: real_username = f.get("name") or "Unknown"
                            if not real_display: real_display = f.get("displayName") or real_username
                            
                            now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                            
                            friends_data["detected_new_friends"][fid_str] = {
                                "username": real_username,
                                "display_name": real_display,
                                "detected_at": now_str
                            }
                            friends_data["friends_details"][fid_str] = {
                                "username": real_username,
                                "display_name": real_display,
                                "added_at": now_str
                            }
                            friends_data["baseline_ids"].append(fid)
                            save_friends_data(friends_data)
                            
                            embed_f = discord.Embed(title="➕ [إشعار أمني: إضافة صديق جديد حقيقي]", description="الرادار لقط فرند جديد تماماً ومختلف عن MongoDB!", color=0x2ecc71)
                            embed_f.add_field(name="Display Name", value=real_display, inline=True)
                            embed_f.add_field(name="Username", value=f"@{real_username}", inline=True)
                            embed_f.add_field(name="رقم الأيدي (User ID)", value=f"`{fid}`", inline=False)
                            embed_f.add_field(name="تاريخ الرصد المباشر", value=f"`{now_str}`", inline=False)
                            await alert_channel.send(embed=embed_f)
                    
                    friends_data["baseline_ids"] = current_ids
                    save_friends_data(friends_data)

        except Exception as e:
            print(f"Error in main background radar: {e}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

