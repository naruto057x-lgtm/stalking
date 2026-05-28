#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import Descord
import instagram
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
    "game_session_start": None
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
    if not past_time: return "مفيش بيانات مسجلة"
    diff = datetime.now() - past_time
    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours} hours ago"
    else:
        return f"{minutes} minutes ago"

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
    embed.add_field(name="🔗 !join", value="يبعتلك رابط الدخول المباشر (Join Link) الحالي للعبة\n**مثال:** `!join`", inline=False)
    embed.add_field(name="🗺️ !map", value="يعطيك رابط صفحة الماب الحالية على روبلوكس\n**مثال:** `!map`", inline=False)
    embed.add_field(name="🏆 !top", value="يعرض أعلى 10 ألعاب مشغولة مع إجمالي الوقت المقضي\n**مثال:** `!top`", inline=False)
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
    if state["status"] in [1, 2, 3]:
        await ctx.send(f"🟢 اللاعب متواجد أونلاين الآن حالياً!")
    else:
        time_str = get_relative_time_str(state["last_online_time"])
        await ctx.send(f"⏱️ **Last seen:** `{time_str}`")

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
async def cmd_top(ctx):
    stats = load_games_stats()
    if not stats:
        await ctx.send("📊 لا توجد بيانات إحصائيات ألعاب متسجلة حتى الآن.")
        return
    
    sorted_games = sorted(stats.items(), key=lambda x: x[1].get("total_time", 0) if isinstance(x[1], dict) else 0, reverse=True)
    
    embed = discord.Embed(title="🏆 إحصائيات الألعاب المفضلة (الأكثر لعباً)", color=0xf39c12)
    
    for idx, (place_id, data) in enumerate(sorted_games[:10], 1):
        if not isinstance(data, dict):
            continue
        total_seconds = data.get("total_time", 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        sessions = data.get("sessions", 0)
        
        time_str = f"{hours}س {minutes}د" if hours > 0 else f"{minutes}د"
        
        embed.add_field(
            name=f"#{idx} - {data.get('name', 'Unknown')}",
            value=f"⏱️ الوقت الكلي: **{time_str}**\n📊 عدد الجلسات: **{sessions}**\n🆔 Place ID: `{place_id}`",
            inline=False
        )
    
    embed.set_footer(text="يتم تحديث الإحصائيات تلقائياً via MongoDB")
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
                        page_link = f"https://www.roblox.com/games/{place_id}"
                        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}" if game_id else page_link

                        embed = discord.Embed(title="🎮 [بدأ يلعب ماب جديدة الآن]", description=f"الهدف دخل سيرفر ماب جديد يعيش!", color=0x2ecc71)
                        embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
                        embed.add_field(name="رابط صفحة الماب (Roblox Page)", value=f"[اضغط هنا لفتح الصفحة]({page_link})", inline=False)
                        embed.add_field(name="رابط الدخول المباشر وراه (JOIN LINK) 🔥", value=f"[اضغط هنا للدخول وراه السيرفر فوراً]({join_link})", inline=False)
                        await alert_channel.send(embed=embed)
                    
                    if (status == 2 and state["status"] == 2) or (status != 2 and state["status"] == 2):
                        if state["game_session_start"] and state["last_game_name"] != "مفيش مابات مسجلة":
                            session_duration = int((now - state["game_session_start"]).total_seconds())
                            record_game_session(state["place_id"], state["last_game_name"], session_duration)

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

# ==================== الإعدادات والروابط المباشرة ====================
TARGET_USER_ID = 7620590660
ROBLOSECURITY = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzg3MDc0NjI1MjE0MTU4NjY0MTMoAw.lR4MHfm3X3EsX6l5GP_KSoP7J8ItNv3Y-M21bw3uw7EsTysoES0xiYjedO_l--XbWmFe2L7j7sV259vfgSB6DjwCm8rQBsRu-PRBvN56FQTLExPJEbw61_kh1w6P-HdVu6mmxfUzGh4ES4U4niEFLrsBQQyCPc9mmqkToyHQXFl9PakEGyMEuw-ywbGelm6Mmf0J5gEEEJsg45-TUcQoEbm2aa-bme-REDE7pM33dQBwNjDHipvkv4Dg5XWSfCYCgn3cpwl1JCR4BtHcrz-z1vZ_8pUy4pIEzlbQnBwrA6_BGveWXOwqEoyaBu-Jt_RsGpdTnZhpGDe6p5pR3SKGNU9nh5h0S5NXKs6ApPc9pup1rb1HB1cI7aUhfUuv1ap2rE5o6gCJB3vKlWh-8JMcbBqL4DSw3QivmRphFM2Cn2f5rI8ilrzMTXlvAouPFq00FJV9J71WyCx-69WEx6b-F2UfKiLdRFUM-Cu4CAwXRkqcz6HLs8BNGoP2ajEhb8QptKl5-faQy4szP4xSG8o8rp2ZhUfnHpHeMBP68wYf9XPRtvUIzkj_Jg2Dlwsfc7b5j9_fY8Ke-0_Rta8fwDLnITgP0zVim90_RzAZ7ejROXUA97pkxnM0bpYvsVzk_COZ7haU5MRZukF0oWVTsEMh8g89wNSczqGGFfvc082KrSCnRLHHozaRZbv6gXlsVvNUxQ3XxhNX6BQfbgyOjHXbC4Wp9U5OWtKAk9bNXkg-acTmySMNPjCqQRAvYXdeLmqz-C6CEUYWiV4IUen4pGOzUxDSVIZfvBIOp33gfO1QRbj8mDYjpJXCVJQObSom8uGRG0iMoSFDkFRl8Obek_poPejb7-VyH925rwmgWZcvFzmJ6KEaBqU1kQc9tb-BzwHKRYoadC14KKGpAPRiBUKMe9rnMDKq_bbKpRqSEQfdGtotDGjnxE5Hi_mJYVSFjC0YEztMzw"  # حط الكوكي بتاعك هنا يصحبي دايماً عشان يشتغل صح

BOT_TOKEN = "MTUwOTM3MDgyMzExNzUwODYyOA.Gnnk5d.ja7miRoobZd-39AgB9dJ3Ad5-_app0Me_NB0q0"
CMD_CHANNEL_ID = 1509431098117984327      # روم الأوامر والتفاعل (تستقبل وترد)
ALERT_CHANNEL_ID = 1509345547197091940    # روم الإشعارات الدورية التلقائية

STATS_FILE = "gameplay_stats.json"
FRIENDS_FILE = "friends_data.json"
NEW_FRIENDS_DIR = "new_friends"           # الفولدر الجديد المخصص للأصدقاء الجدد
GAMES_STATS_FILE = "games_history.json"  # ملف تتبع إحصائيات الألعاب
INTERVAL = 60  # الفحص كل دقيقة بالظبط لضمان الاستقرار
# ============================================================

# إنشاء الفولدر المخصص للأصدقاء الجدد لو مش موجود
if not os.path.exists(NEW_FRIENDS_DIR):
    os.makedirs(NEW_FRIENDS_DIR)

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
    "game_session_start": None     # لتتبع بداية جلسة اللعب
}

headers = {
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}",
    "Content-Type": "application/json"
}

# --- دالات إدارة ملفات الـ JSON ---
def load_json(filename, default_factory):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "baseline_ids" not in data: data["baseline_ids"] = []
                if "friends_details" not in data: data["friends_details"] = {}
                if "detected_new_friends" not in data: data["detected_new_friends"] = {}
                return data
        except:
            return default_factory()
    return default_factory()

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

def load_games_stats():
    if os.path.exists(GAMES_STATS_FILE):
        try:
            with open(GAMES_STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_games_stats(data):
    try:
        with open(GAMES_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

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
    if not past_time: return "مفيش بيانات مسجلة"
    diff = datetime.now() - past_time
    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours} hours ago"
    else:
        return f"{minutes} minutes ago"

# --- جلب بيانات أي يوزر بالـ ID من روبلوكس لمنع الـ Unknown ---
async def fetch_single_user_profile(session, user_id):
    try:
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("name"), data.get("displayName")
    except:
        pass
    return None, None

# --- جلب قائمة الأصدقاء كاملة بجميع الصفحات (حل مشكلة السبام) ---
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
    print(f"🤖 Bot is Online as: {bot.user.name} | Radar System Fixed 🔥")
    print("="*70 + "\n")
    await fetch_roblox_profile()
    roblox_radar_loop.start()

@bot.check
async def check_channel(ctx):
    return ctx.channel.id == CMD_CHANNEL_ID

# --- الأوامر التفاعلية المنظمة بالكامل ---

@bot.command(name="commands")
async def cmd_commands(ctx):
    embed = discord.Embed(title="📖 قائمة الأوامر المتاحة (Commands Menu)", color=0x9b59b6)
    
    embed.add_field(
        name="📊 !lastseen",
        value="يعرض آخر وقت شُفت اللاعب فيه أونلاين\n**مثال:** `!lastseen`",
        inline=False
    )
    
    embed.add_field(
        name="🎮 !lastgame",
        value="يعرض آخر ماب دخلها اللاعب ومنذ كام وقت\n**مثال:** `!lastgame`",
        inline=False
    )
    
    embed.add_field(
        name="� !join",
        value="يبعتلك رابط الدخول المباشر (Join Link) الحالي للعبة\n**مثال:** `!join`",
        inline=False
    )
    
    embed.add_field(
        name="🗺️ !map",
        value="يعطيك رابط صفحة الماب الحالية على روبلوكس\n**مثال:** `!map`",
        inline=False
    )
    
    embed.add_field(
        name="🏆 !top",
        value="يعرض أعلى 10 ألعاب مشغولة مع إجمالي الوقت المقضي\n**مثال:** `!top`",
        inline=False
    )
    
    embed.add_field(
        name="👤 !avatar",
        value="يعطيك صورة الأفاتار (الشخصية) في روبلوكس\n**مثال:** `!avatar`",
        inline=False
    )
    
    embed.add_field(
        name="�📝 !about",
        value="يعرض البايو (الوصف) الحالي في بروفايل اللاعب\n**مثال:** `!about`",
        inline=False
    )
    
    embed.add_field(
        name="👥 !friendstest",
        value="يختبر ويعرض أول 10 أصدقاء من القائمة الكاملة\n**مثال:** `!friendstest`",
        inline=False
    )
    
    embed.add_field(
        name="➕ !newfriends",
        value="يعرض آخر 5 أصدقاء جدد تم اكتشافهم\n**مثال:** `!newfriends`",
        inline=False
    )
    
    embed.add_field(
        name="📜 !newhistoryfriends",
        value="يعرض السجل الكامل لجميع الأصدقاء الجدد المكتشفة من البداية\n**مثال:** `!newhistoryfriends`",
        inline=False
    )
    
    embed.add_field(
        name="🔔 التنبيهات التلقائية",
        value="**النظام يرسل إشعارات تلقائية متى:**\n"
              "🔵 **اللاعب يكون أونلاين** - إشعار فوري\n"
              "🔴 **اللاعب يروح أوفلاين** - بعد 10 دقائق\n"
              "🎮 **يدخل لعبة/ماب** - مع رابط الماب واسمها و Join Link مباشر 🔥\n"
              "➕ **يضيف صديق جديد** - إشعار فوري مع البيانات",
        inline=False
    )
    
    embed.set_footer(text="اكتب الأمر في روم الأوامر المخصص ويرد عليك الرادار بسرعة ⚡")
    await ctx.send(embed=embed)

@bot.command(name="friendstest")
async def cmd_friends_test(ctx):
    await ctx.send("🔄 جاري فحص وجلب قائمة الأصدقاء الحقيقية كاملة الآن بدون نقص...")
    async with aiohttp.ClientSession() as session:
        try:
            friends = await fetch_all_friends(session)
            if not friends:
                await ctx.send("👤 قائمة الأصدقاء مخفية، فارغة، أو تعذر جلبها حالياً.")
                return
            
            embed = discord.Embed(title=f"👥 اختبار قائمة الأصدقاء (عددها الكلي المسجل: {len(friends)})", color=0x3498db)
            # عرض آخر 10 أصدقاء تم جلبهم
            for f in friends[:10]:
                fid = f.get('id')
                real_username, real_display = await fetch_single_user_profile(session, fid)
                if not real_username: real_username = f.get('name') or "Unknown"
                if not real_display: real_display = f.get('displayName') or real_username
                
                embed.add_field(name=real_display, value=f"@{real_username}\nID: `{fid}`", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ أثناء تشغيل الاختبار: {str(e)[:50]}")

@bot.command(name="lastseen")
async def cmd_last_seen(ctx):
    if state["status"] in [1, 2, 3]:
        await ctx.send(f"🟢 اللاعب متواجد أونلاين الآن حالياً!")
    else:
        time_str = get_relative_time_str(state["last_online_time"])
        await ctx.send(f"⏱️ **Last seen:** `{time_str}`")

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
    data = load_json(FRIENDS_FILE, lambda: {"baseline_ids": [], "friends_details": {}, "detected_new_friends": {}})
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
    data = load_json(FRIENDS_FILE, lambda: {"baseline_ids": [], "friends_details": {}, "detected_new_friends": {}})
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
        # محاولة استخدام Thumbnails API - جلب الصورة الكبيرة
        avatar_full_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={TARGET_USER_ID}&size=720x720&format=Png&isCircular=false"
        
        async with session.get(avatar_full_url, timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                if data.get('data') and len(data['data']) > 0:
                    full_img_url = data['data'][0].get('imageUrl')
                    if full_img_url:
                        return full_img_url  # رجع الصورة الكبيرة
        
        # إذا فشلت المحاولة الأولى، جرب الطريقة البديلة
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
                await ctx.send(f"❌ لم يتمكن من جلب صورة الأفاتار. قد تكون البروفايل مخفية أو هناك مشكلة في الاتصال.")
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name="testimg")
async def cmd_test_img(ctx):
    """أمر اختبار لفحص جميع روابط الصور"""
    await ctx.send("🧪 جاري اختبار جميع الروابط المتاحة...")
    
    async with aiohttp.ClientSession() as session:
        urls_to_test = [
            ("Thumbnails Headshot API", f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={TARGET_USER_ID}&size=420x420&format=Png&isCircular=false"),
            ("Thumbnails Avatar API", f"https://thumbnails.roblox.com/v1/users/avatar?userIds={TARGET_USER_ID}&size=720x720&format=Png&isCircular=false"),
            ("Asset Delivery v2", f"https://assetdelivery.roblox.com/v2/avatar-thumbnails?ids={TARGET_USER_ID}&size=420x420&format=Png"),
            ("RBXcdn Direct", f"https://tr.rbxcdn.com/default-avatar-60x60.png"),
        ]
        
        results = []
        for name, url in urls_to_test:
            try:
                async with session.get(url, timeout=5) as r:
                    status = "✅ يعمل" if r.status == 200 else f"❌ Status {r.status}"
                    results.append(f"{name}: {status}")
                    if r.status == 200 and name == "Thumbnails Headshot API":
                        # عرض الصورة إذا نجحت
                        embed = discord.Embed(title=f"✅ {name}" , color=0x2ecc71)
                        data = await r.json()
                        if data.get('data') and len(data['data']) > 0:
                            img_url = data['data'][0].get('imageUrl')
                            embed.set_image(url=img_url)
                            embed.description = f"الرابط: `{img_url}`"
                        await ctx.send(embed=embed)
            except Exception as e:
                results.append(f"{name}: ❌ خطأ - {str(e)[:30]}")
        
        # إرسال النتائج
        embed = discord.Embed(title="📊 نتائج الاختبار", color=0x3498db)
        for result in results:
            embed.add_field(name="", value=result, inline=False)
        await ctx.send(embed=embed)

@bot.command(name="top")
async def cmd_top(ctx):
    stats = load_games_stats()
    if not stats:
        await ctx.send("📊 لا توجد بيانات إحصائيات ألعاب متسجلة حتى الآن.")
        return
    
    # ترتيب الألعاب حسب الوقت المقضي (من الأكثر للأقل)
    sorted_games = sorted(stats.items(), key=lambda x: x[1]["total_time"], reverse=True)
    
    embed = discord.Embed(title="🏆 إحصائيات الألعاب المفضلة (الأكثر لعباً)", color=0xf39c12)
    
    for idx, (place_id, data) in enumerate(sorted_games[:10], 1):  # أعلى 10 ألعاب
        total_seconds = data["total_time"]
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        sessions = data["sessions"]
        
        time_str = f"{hours}س {minutes}د" if hours > 0 else f"{minutes}د"
        
        embed.add_field(
            name=f"#{idx} - {data['name']}",
            value=f"⏱️ الوقت الكلي: **{time_str}**\n📊 عدد الجلسات: **{sessions}**\n🆔 Place ID: `{place_id}`",
            inline=False
        )
    
    embed.set_footer(text="يتم تحديث الإحصائيات تلقائياً مع كل جلسة لعب جديدة")
    await ctx.send(embed=embed)

@bot.command(name="status")
async def cmd_status(ctx):
    """التحقق من حالة نظام الرادار والأصدقاء"""
    data = load_json(FRIENDS_FILE, lambda: {"baseline_ids": [], "friends_details": {}, "detected_new_friends": {}})
    stats = load_games_stats()
    
    baseline_count = len(data.get("baseline_ids", []))
    new_friends_count = len(data.get("detected_new_friends", {}))
    total_friends = len(data.get("friends_details", {}))
    games_recorded = len(stats)
    
    embed = discord.Embed(title="📊 حالة نظام الرادار", color=0x00ff00)
    
    # معلومات الشخص المرصود
    embed.add_field(name="👤 الهدف", value=f"**{DISPLAY_NAME}** (@{USER_NAME})\nID: `{TARGET_USER_ID}`", inline=False)
    
    # حالة النظام
    status_text = "🟢 أونلاين" if state["status"] in [1, 2, 3] else "🔴 أوفلاين"
    embed.add_field(name="🔌 حالة الاتصال", value=status_text, inline=False)
    
    # اللعبة الحالية
    if state["status"] == 2:
        embed.add_field(name="🎮 اللعبة الحالية", value=f"**{state['game']}**", inline=False)
    
    # إحصائيات الأصدقاء
    embed.add_field(name="👥 إحصائيات الأصدقاء", value=f"✅ أساسيين: `{baseline_count}`\n➕ جدد: `{new_friends_count}`\n📊 الكل: `{total_friends}`", inline=False)
    
    # إحصائيات الألعاب
    embed.add_field(name="🎮 إحصائيات الألعاب", value=f"📈 ألعاب مسجلة: `{games_recorded}`", inline=False)
    
    # حالة الملفات
    friends_file_exists = "✅ موجود" if os.path.exists(FRIENDS_FILE) else "❌ غير موجود"
    games_file_exists = "✅ موجود" if os.path.exists(GAMES_STATS_FILE) else "❌ غير موجود"
    new_friends_dir_exists = "✅ موجود" if os.path.exists(NEW_FRIENDS_DIR) else "❌ غير موجود"
    
    embed.add_field(name=" حالة الملفات", value=f"Friends: {friends_file_exists}\nGames: {games_file_exists}\nNew Friends Dir: {new_friends_dir_exists}", inline=False)
    
    embed.set_footer(text="يتم تحديث البيانات تلقائياً كل دقيقة")
    await ctx.send(embed=embed)


# --- رادار الفحص الدوري التلقائي (كل دقيقة) ---

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
                        state["game_session_start"] = now  # بداية جلسة جديدة
                        page_link = f"https://www.roblox.com/games/{place_id}"
                        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}" if game_id else page_link

                        embed = discord.Embed(title="🎮 [بدأ يلعب ماب جديدة الآن]", description=f"الهدف دخل سيرفر ماب جديد يعيش!", color=0x2ecc71)
                        embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
                        embed.add_field(name="رابط صفحة الماب (Roblox Page)", value=f"[اضغط هنا لفتح الصفحة]({page_link})", inline=False)
                        embed.add_field(name="رابط الدخول المباشر وراه (JOIN LINK) 🔥", value=f"[اضغط هنا للدخول وراه السيرفر فوراً]({join_link})", inline=False)
                        await alert_channel.send(embed=embed)
                    
                    # إذا دخل لعبة جديدة أو خرج من اللعبة القديمة، سجل الإحصائيات
                    if (status == 2 and state["status"] == 2) or (status != 2 and state["status"] == 2):
                        if state["game_session_start"] and state["last_game_name"] != "مفيش مابات مسجلة":
                            session_duration = int((now - state["game_session_start"]).total_seconds())
                            record_game_session(state["place_id"], state["last_game_name"], session_duration)

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

            # 2. رادار الأصدقاء المطور (قناص الصفحات بالكامل + إنشاء ملفات منفصلة للتثبيت)
            curr_friends = await fetch_all_friends(session)
            if curr_friends:
                current_ids = [f["id"] for f in curr_friends]
                friends_data = load_json(FRIENDS_FILE, lambda: {"baseline_ids": [], "friends_details": {}, "detected_new_friends": {}})
                
                # --- [حالة التشغيل لأول مرة: صمت تام وحفظ كل الموجود بدون سبام] ---
                if not friends_data["baseline_ids"]:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] First run! Storing ALL baseline pages silently...")
                    friends_data["baseline_ids"] = current_ids
                    for f in curr_friends:
                        fid = str(f["id"])
                        friends_data["friends_details"][fid] = {
                            "username": f.get("name") or "Unknown",
                            "display_name": f.get("displayName") or f.get("name") or "Unknown",
                            "added_at": "Baseline"
                        }
                    save_json(FRIENDS_FILE, friends_data)
                    print(f"✅ Full baseline saved with {len(current_ids)} friends. Zero spam sent.")
                
                # --- [الحالة العادية: قنص الفرندز الجدد الحقيقيين والمختلفين عن الداتا] ---
                else:
                    baseline_set = set(friends_data["baseline_ids"])
                    for f in curr_friends:
                        fid = f["id"]
                        fid_str = str(fid)
                        
                        if fid not in baseline_set:
                            # تأكيد البيانات بالكامل بالـ API الفردي عشان نضمن الاسم 100%
                            real_username, real_display = await fetch_single_user_profile(session, fid)
                            if not real_username: real_username = f.get("name") or "Unknown"
                            if not real_display: real_display = f.get("displayName") or real_username
                            
                            now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                            
                            # 1. حفظ البيانات في ملف الـ JSON الأساسي للـ Commands
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
                            save_json(FRIENDS_FILE, friends_data)
                            
                            # 2. الخصيصة الجديدة: إنشاء ملف نصي منفصل لكل فرند جديد داخل فولدر new_friends
                            file_path = os.path.join(NEW_FRIENDS_DIR, f"{real_username}.txt")
                            try:
                                with open(file_path, "w", encoding="utf-8") as nf_file:
                                    nf_file.write(f"Display Name: {real_display}\n")
                                    nf_file.write(f"Username: @{real_username}\n")
                                    nf_file.write(f"User ID: {fid}\n")
                                    nf_file.write(f"Friend Since: {now_str}\n")
                            except Exception as file_err:
                                print(f"Error creating individual text file: {file_err}")
                            
                            # 3. إرسال الإشعار المنظم الحقيقي لديسكورد
                            embed_f = discord.Embed(title="➕ [إشعار أمني: إضافة صديق جديد حقيقي]", description="الرادار لقط فرند جديد تماماً ومختلف عن داتا السستم!", color=0x2ecc71)
                            embed_f.add_field(name="Display Name", value=real_display, inline=True)
                            embed_f.add_field(name="Username", value=f"@{real_username}", inline=True)
                            embed_f.add_field(name="رقم الأيدي (User ID)", value=f"`{fid}`", inline=False)
                            embed_f.add_field(name="تاريخ الرصد المباشر", value=f"`{now_str}`", inline=False)
                            await alert_channel.send(embed=embed_f)
                    
                    # تحديث ومزامنة خط الأساس بالكامل لمنع أي تكرار
                    friends_data["baseline_ids"] = current_ids
                    save_json(FRIENDS_FILE, friends_data)

        except Exception as e:
            print(f"Error in main background radar: {e}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
