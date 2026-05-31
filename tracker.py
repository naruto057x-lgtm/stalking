#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import sys
from datetime import datetime, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# ==================== Timezone Helper ====================
def _make_aware(dt):
    """تحويل naive datetimes من MongoDB إلى aware datetimes في timezone Europe/Lisbon"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Lisbon"))
    return dt

# ==================== الإعدادات والروابط المباشرة ====================
TARGET_USER_ID = 7620590660
ROBLOSECURITY = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzg3MDc0NjI1MjE0MTU4NjY0MTMoAw.lR4MHfm3X3EsX6l5GP_KSoP7J8ItNv3Y-M21bw3uw7EsTysoES0xiYjedO_l--XbWmFe2L7j7sV259vfgSB6DjwCm8rQBsRu-PRBvN56FQTLExPJEbw61_kh1w6P-HdVu6mmxfUzGh4ES4U4niEFLrsBQQyCPc9mmqkToyHQXFl9PakEGyMEuw-ywbGelm6Mmf0J5gEEEJsg45-TUcQoEbm2aa-bme-REDE7pM33dQBwNjDHipvkv4Dg5XWSfCYCgn3cpwl1JCR4BtHcrz-z1vZ_8pUy4pIEzlbQnBwrA6_BGveWXOwqEoyaBu-Jt_RsGpdTnZhpGDe6p5pR3SKGNU9nh5h0S5NXKs6ApPc9pup1rb1HB1cI7aUhfUuv1ap2rE5o6gCJB3vKlWh-8JMcbBqL4DSw3QivmRphFM2Cn2f5rI8ilrzMTXlvAouPFq00FJV9J71WyCx-69WEx6b-F2UfKiLdRFUM-Cu4CAwXRkqcz6HLs8BNGoP2ajEhb8QptKl5-faQy4szP4xSG8o8rp2ZhUfnHpHeMBP68wYf9XPRtvUIzkj_Jg2Dlwsfc7b5j9_fY8Ke-0_Rta8fwDLnITgP0zVim90_RzAZ7ejROXUA97pkxnM0bpYvsVzk_COZ7haU5MRZukF0oWVTsEMh8g89wNSczqGGFfvc082KrSCnRLHHozaRZbv6gXlsVvNUxQ3XxhNX6BQfbgyOjHXbC4Wp9U5OWtKAk9bNXkg-acTmySMNPjCqQRAvYXdeLmqz-C6CEUYWiV4IUen4pGOzUxDSVIZfvBIOp33gfO1QRbj8mDYjpJXCVJQObSom8uGRG0iMoSFDkFRl8Obek_poPejb7-VyH925rwmgWZcvFzmJ6KEaBqU1kQc9tb-BzwHKRYoadC14KKGpAPRiBUKMe9rnMDKq_bbKpRqSEQfdGtotDGjnxE5Hi_mJYVSFjC0YEztMzw"

BOT_TOKEN = "MTUwOTM3MDgyMzExNzUwODYyOA.Gcu40Y.GjypUteQXyVwe55l_Fgg0NCyD9P_eWQid4OzOY"
CMD_CHANNEL_ID = 1509431098117984327
ALERT_CHANNEL_ID = 1509345547197091940
DAILY_SUMMARY_CHANNEL_ID = 1510270977513099296
WEEKLY_SUMMARY_CHANNEL_ID = 1510275621316595802
DETAIL_CHANNEL_ID = 1510541538445230080

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
    "session_recorded": False,
    "online_session_start": None,
    "pending_resume": False,
    "pending_resume_place_id": None,
    "pending_resume_game_name": None,
    "pending_resume_leave_time": None,
    "last_avatar_url": None,
    "privacy_alert_sent": False,
    "last_activity_time": None,
    "session_day_start": None,
    "offline_notification_sent": False,
    "logical_day_key": None
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
daily_stats_collection = db.daily_stats
session_logs = db.session_logs

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
            "last_updated": datetime.now(ZoneInfo("Europe/Lisbon"))
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
    doc = {"_id": "games_stats", "last_updated": datetime.now(ZoneInfo("Europe/Lisbon"))}
    doc.update(data)
    games_collection.replace_one({"_id": "games_stats"}, doc, upsert=True)


def load_state_data():
    """تحميل حالة الروبوت من MongoDB"""
    doc = state_collection.find_one({"_id": "state_data"})
    if doc:
        return {
            "status": doc.get("status"),
            "last_online_time": _make_aware(doc.get("last_online_time")),
            "online_session_start": _make_aware(doc.get("online_session_start")),
            "offline_since": _make_aware(doc.get("offline_since")),
            "offline_alert_sent": doc.get("offline_alert_sent", False),
            "pending_resume": doc.get("pending_resume", False),
            "pending_resume_place_id": doc.get("pending_resume_place_id"),
            "pending_resume_game_name": doc.get("pending_resume_game_name"),
            "pending_resume_leave_time": _make_aware(doc.get("pending_resume_leave_time")),
            "last_avatar_url": doc.get("last_avatar_url"),
            "privacy_alert_sent": doc.get("privacy_alert_sent", False),
            "last_activity_time": _make_aware(doc.get("last_activity_time")),
            "session_day_start": doc.get("session_day_start"),
            "offline_notification_sent": doc.get("offline_notification_sent", False),
            "logical_day_key": doc.get("logical_day_key")
        }
    return {
        "status": None,
        "last_online_time": None,
        "online_session_start": None,
        "offline_since": None,
        "offline_alert_sent": False,
        "pending_resume": False,
        "pending_resume_place_id": None,
        "pending_resume_game_name": None,
        "pending_resume_leave_time": None,
        "last_avatar_url": None,
        "privacy_alert_sent": False,
        "last_activity_time": None,
        "session_day_start": None,
        "offline_notification_sent": False,
        "logical_day_key": None
    }


def save_state_data():
    """حفظ حالة الروبوت المهمة في MongoDB"""
    state_collection.replace_one(
        {"_id": "state_data"},
        {
            "_id": "state_data",
            "status": state.get("status"),
            "last_online_time": state.get("last_online_time"),
            "online_session_start": state.get("online_session_start"),
            "offline_since": state.get("offline_since"),
            "offline_alert_sent": state.get("offline_alert_sent", False),
            "pending_resume": state.get("pending_resume", False),
            "pending_resume_place_id": state.get("pending_resume_place_id"),
            "pending_resume_game_name": state.get("pending_resume_game_name"),
            "pending_resume_leave_time": state.get("pending_resume_leave_time"),
            "last_avatar_url": state.get("last_avatar_url"),
            "privacy_alert_sent": state.get("privacy_alert_sent", False),
            "last_activity_time": state.get("last_activity_time"),
            "session_day_start": state.get("session_day_start"),
            "offline_notification_sent": state.get("offline_notification_sent", False),
            "logical_day_key": state.get("logical_day_key"),
            "last_updated": datetime.now(ZoneInfo("Europe/Lisbon"))
        },
        upsert=True
    )


def get_date_str(dt):
    return dt.strftime("%Y-%m-%d")


def sanitize_game_key(game_name):
    if game_name is None:
        return None
    return str(game_name).replace('.', '_').replace('$', '_')


def log_session_entry(game_name, place_id, start_time, end_time, date_key=None):
    if not game_name or not place_id or not start_time or not end_time or end_time <= start_time:
        return
    session_logs.insert_one(
        {
            "game_name": game_name,
            "place_id": str(place_id),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": int((end_time - start_time).total_seconds()),
            "date_key": date_key or start_time.strftime("%Y-%m-%d")
        }
    )


def split_duration_by_date(start_dt, end_dt):
    result = {}
    current = start_dt
    while current.date() < end_dt.date():
        next_midnight = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), tzinfo=ZoneInfo("Europe/Lisbon"))
        result[get_date_str(current)] = int((next_midnight - current).total_seconds())
        current = next_midnight
    result[get_date_str(current)] = int((end_dt - current).total_seconds())
    return result


def get_active_report_date():
    if state.get("logical_day_key"):
        return state["logical_day_key"]
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    if state.get("last_activity_time"):
        last_activity = _make_aware(state.get("last_activity_time"))
        if last_activity:
            return get_date_str(last_activity)
    return get_date_str(now)


def get_logical_day_close_deadline(now=None):
    if not state.get("logical_day_key"):
        return None
    now = now or datetime.now(ZoneInfo("Europe/Lisbon"))
    try:
        active_day = datetime.strptime(state["logical_day_key"], "%Y-%m-%d").date()
    except Exception:
        return None

    if now.date() <= active_day:
        return None

    midnight = datetime.combine(now.date(), dt_time.min, tzinfo=ZoneInfo("Europe/Lisbon"))
    last_activity = state.get("last_activity_time")
    if last_activity:
        last_activity = _make_aware(last_activity)
        if last_activity >= midnight:
            return last_activity + timedelta(hours=2)
    return midnight + timedelta(hours=2)


def update_daily_online(start_dt, end_dt, date_key=None):
    if not start_dt or not end_dt or end_dt <= start_dt:
        return
    if date_key:
        seconds = int((end_dt - start_dt).total_seconds())
        daily_stats_collection.update_one(
            {"_id": date_key},
            {
                "$inc": {"online_seconds": seconds, "total_game_seconds": 0},
                "$setOnInsert": {"games": {}, "last_updated": datetime.now(ZoneInfo("Europe/Lisbon"))}
            },
            upsert=True
        )
        return

    parts = split_duration_by_date(start_dt, end_dt)
    for date_key, seconds in parts.items():
        daily_stats_collection.update_one(
            {"_id": date_key},
            {
                "$inc": {"online_seconds": seconds, "total_game_seconds": 0},
                "$setOnInsert": {"games": {}, "last_updated": datetime.now(ZoneInfo("Europe/Lisbon"))}
            },
            upsert=True
        )


def update_daily_game(place_id, game_name, seconds, date_key=None):
    if not place_id or not game_name or seconds <= 0:
        return
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    game_key = sanitize_game_key(game_name)
    date_key = date_key or get_date_str(now)
    daily_stats_collection.update_one(
        {"_id": date_key},
        {
            "$inc": {f"games.{game_key}.total_time": seconds, f"games.{game_key}.sessions": 1, "total_game_seconds": seconds},
            "$set": {f"games.{game_key}.name": game_name, f"games.{game_key}.place_id": str(place_id), "last_updated": now}
        },
        upsert=True
    )


def get_daily_range(period, date_str=None):
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()
    if period in [None, "today"]:
        return today, today
    if period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if period in ["week", "weekly"]:
        start = today - timedelta(days=today.weekday())
        return start, today
    if period in ["month", "monthly"]:
        start = today.replace(day=1)
        return start, today
    try:
        parsed = datetime.strptime(date_str or period, "%Y-%m-%d").date()
        return parsed, parsed
    except Exception:
        return None, None


def format_seconds(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours:
        parts.append(f"{hours}س")
    if minutes:
        parts.append(f"{minutes}د")
    if secs or not parts:
        parts.append(f"{secs}ث")
    return " ".join(parts)


def get_relative_time_str(past_time):
    """عرض الوقت بصيغة نسبية (منذ كام وقت) بالعربية"""
    if not past_time:
        return "❌ مفيش بيانات مسجلة - لم يكن الشخص أونلاين بعد"
    
    past_time = _make_aware(past_time)
    if not past_time:
        return "❌ مفيش بيانات مسجلة - لم يكن الشخص أونلاين بعد"
    
    diff = datetime.now(ZoneInfo("Europe/Lisbon")) - past_time
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


def load_stats_for_period(start_date, end_date):
    query = {"_id": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}}
    docs = daily_stats_collection.find(query)
    total_online = 0
    game_totals = {}
    for doc in docs:
        total_online += doc.get("online_seconds", 0)
        for game_key, game in doc.get("games", {}).items():
            entry = game_totals.setdefault(game_key, {"name": game.get("name"), "total_time": 0, "sessions": 0})
            entry["total_time"] += game.get("total_time", 0)
            entry["sessions"] += game.get("sessions", 0)
    return total_online, game_totals


def get_top_games(start_date, end_date, limit=5):
    _, game_totals = load_stats_for_period(start_date, end_date)
    sorted_games = sorted(game_totals.items(), key=lambda x: x[1]["total_time"], reverse=True)
    return sorted_games[:limit]


def get_new_friends_count(date_key):
    friends = load_friends_data().get("detected_new_friends", {})
    count = 0
    names = []
    for f in friends.values():
        detected_at = f.get("detected_at", "")
        try:
            dt = datetime.strptime(detected_at, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            try:
                dt = datetime.strptime(detected_at[:10], "%Y-%m-%d")
            except Exception:
                continue
        if dt.strftime("%Y-%m-%d") == date_key:
            count += 1
            names.append(f.get("display_name", f.get("username", "Unknown")))
    return count, names


def build_daily_summary_embed(date_key):
    doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    total_online = doc.get("online_seconds", 0)
    games = doc.get("games", {})
    total_maps = len(games)
    total_sessions = sum(game.get("sessions", 0) for game in games.values())
    total_game_seconds = sum(game.get("total_time", 0) for game in games.values())
    # split online time into inside/outside maps
    online_inside_maps = total_game_seconds
    online_outside_maps = max(total_online - total_game_seconds, 0)
    most_played = None
    if games:
        most_played = max(games.items(), key=lambda x: x[1].get("total_time", 0))

    new_friends_count, new_friends_names = get_new_friends_count(date_key)
    date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%d/%m/%Y")
    title = f"📅 ملخص اليوم لليوم {date_display}"
    embed = discord.Embed(title=title, color=0x1abc9c)
    embed.add_field(name="🕒 الوقت الكلي أونلاين", value=f"**{format_seconds(total_online)}**", inline=False)
    embed.add_field(name="🎮 الوقت داخل المابات", value=f"**{format_seconds(online_inside_maps)}**", inline=False)
    embed.add_field(name="🌐 الوقت خارج المابات", value=f"**{format_seconds(online_outside_maps)}**", inline=False)
    embed.add_field(name="🗺️ عدد المابات اللي لعبها", value=f"**{total_maps}** ماب", inline=True)
    embed.add_field(name="📊 عدد الجلسات", value=f"**{total_sessions}** جلسة", inline=True)

    if most_played:
        game_key, game_data = most_played
        embed.add_field(
            name="🏆 أعلى ماب لعبها",
            value=f"**{game_data.get('name', 'Unknown')}**\n⏱️ وقت اللعب: **{format_seconds(game_data.get('total_time', 0))}**\n📊 الجلسات: **{game_data.get('sessions', 0)}**\n🆔 `{game_key}`",
            inline=False
        )
    else:
        embed.add_field(name="🏆 أعلى ماب لعبها", value="لا توجد بيانات مابات لهذا اليوم.", inline=False)

    if new_friends_count > 0:
        preview = "، ".join(new_friends_names[:5])
        if len(new_friends_names) > 5:
            preview += "، ..."
        embed.add_field(name="➕ أصدقاء جدد", value=f"**{new_friends_count}** جديدين\n{preview}", inline=False)
    else:
        embed.add_field(name="➕ أصدقاء جدد", value="لم يتم إضافة أصدقاء جدد اليوم.", inline=False)

    # Avatar changes count
    avatar_changes = doc.get("avatar_changes", 0)
    if avatar_changes > 0:
        embed.add_field(name="🎭 تغييرات الأفاتار", value=f"**{avatar_changes} مرة**", inline=False)
    else:
        embed.add_field(name="🎭 تغييرات الأفاتار", value="لم يتغير الأفاتار اليوم", inline=False)

    if games:
        top_games = sorted(games.items(), key=lambda x: x[1].get("total_time", 0), reverse=True)[:5]
        details = []
        for idx, (game_key, info) in enumerate(top_games, 1):
            details.append(f"**{idx}. {info.get('name', 'Unknown')}** — {format_seconds(info.get('total_time', 0))} في {info.get('sessions', 0)} جلسات")
        embed.add_field(name="📌 أهم 5 مابات", value="\n".join(details), inline=False)
    else:
        embed.add_field(name="📌 أهم 5 مابات", value="لا توجد مابات مسجلة لهذا اليوم.", inline=False)

    embed.set_footer(text="ملخص يومي مرتب وشامل لكل أحداث اليوم")
    return embed


def build_weekly_summary_embed():
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_date, end_date = start_of_week.date(), end_of_week.date()
    total_online, game_totals = load_stats_for_period(start_date, end_date)
    
    total_sessions = sum(g.get("sessions", 0) for g in game_totals.values())
    total_game_seconds = sum(g.get("total_time", 0) for g in game_totals.values())
    
    sorted_games = sorted(game_totals.items(), key=lambda x: x[1]["total_time"], reverse=True)[:10]
    
    week_start_str = start_date.strftime("%d/%m/%Y")
    week_end_str = end_date.strftime("%d/%m/%Y")
    
    embed = discord.Embed(
        title=f"📊 ملخص الأسبوع ({week_start_str} - {week_end_str})",
        description="📈 إحصائيات شاملة لكامل الأسبوع",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="⏰ إجمالي وقت الأونلاين",
        value=f"**{format_seconds(total_online)}**",
        inline=False
    )
    embed.add_field(
        name="🎮 إجمالي وقت اللعب",
        value=f"**{format_seconds(total_game_seconds)}**",
        inline=False
    )
    embed.add_field(
        name="📍 عدد المابات المختلفة",
        value=f"**{len(game_totals)}** ماب",
        inline=True
    )
    embed.add_field(
        name="📊 إجمالي الجلسات",
        value=f"**{total_sessions}** جلسة",
        inline=True
    )
    
    if sorted_games:
        details = []
        for idx, (game_key, info) in enumerate(sorted_games[:5], 1):
            details.append(
                f"**{idx}. {info.get('name', 'Unknown')}**\n"
                f"  ⏱️ {format_seconds(info.get('total_time', 0))} | "
                f"📊 {info.get('sessions', 0)} جلسات"
            )
        embed.add_field(
            name="🏆 أفضل 5 مابات هذا الأسبوع",
            value="\n".join(details),
            inline=False
        )
    
    new_friends_week = 0
    friends_data = load_friends_data()
    for f in friends_data.get("detected_new_friends", {}).values():
        detected_at = f.get("detected_at", "")
        dt = None
        try:
            dt = datetime.strptime(detected_at, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            try:
                dt = datetime.strptime(detected_at[:10], "%Y-%m-%d")
            except Exception as e:
                print(f"Warning: couldn't parse detected_at '{detected_at}': {e}")
                continue
        if start_date <= dt.date() <= end_date:
            new_friends_week += 1
    
    embed.add_field(
        name="👥 أصدقاء جدد هذا الأسبوع",
        value=f"**{new_friends_week}** صديق جديد",
        inline=False
    )
    
    avg_session = total_game_seconds // total_sessions if total_sessions > 0 else 0
    embed.add_field(
        name="📌 متوسط طول الجلسة",
        value=f"**{format_seconds(avg_session)}**",
        inline=True
    )
    
    avg_online_day = total_online // 7
    embed.add_field(
        name="🕐 متوسط وقت الأونلاين يومياً",
        value=f"**{format_seconds(avg_online_day)}**",
        inline=True
    )
    
    embed.set_footer(text="ملخص أسبوعي شامل بتفاصيل كاملة")
    return embed


def build_detail_embeds(date_key):
    """بناء قائمة embeds بتفاصيل الجلسات ليوم محدد"""
    # Query session_logs
    sessions = list(session_logs.find({"date_key": date_key}).sort("start_time", 1))
    
    # Query avatar changes first (needed for both cases)
    daily_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    avatar_changes = daily_doc.get("avatar_changes", 0)
    
    if not sessions:
        # No sessions - return single embed with avatar_changes field
        date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%d/%m/%Y")
        embed = discord.Embed(
            title=f"📋 تفاصيل يوم {date_display}",
            description="لا توجد جلسات مسجلة لهذا اليوم",
            color=0x3498db
        )
        if avatar_changes > 0:
            embed.add_field(
                name="🎭 تغييرات الأفاتار",
                value=f"**{avatar_changes} مرة**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 تغييرات الأفاتار",
                value="لم يتغير الأفاتار اليوم",
                inline=False
            )
        embed.set_footer(text="تقرير تفصيلي كامل لكل جلسات اليوم")
        return [embed]
    
    # Build embeds with max 20 session fields per embed
    embeds = []
    date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%d/%m/%Y")
    fields_added = 0
    current_embed = discord.Embed(
        title=f"📋 تفاصيل يوم {date_display}",
        color=0x3498db
    )
    
    total_sessions = len(sessions)
    for idx, session in enumerate(sessions, start=1):
        game_name = session.get("game_name", "Unknown")
        start_time = session.get("start_time")
        end_time = session.get("end_time")
        duration_seconds = session.get("duration_seconds", 0)
        
        if start_time and end_time:
            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")
        else:
            start_str = "Unknown"
            end_str = "Unknown"
        
        field_name = f"🎮 {game_name}"
        field_value = f"🕒 من {start_str} لحد {end_str}\n⏱️ مدة: {format_seconds(duration_seconds)}"
        current_embed.add_field(name=field_name, value=field_value, inline=False)
        fields_added += 1
        
        # If we've added 20 fields and there are more sessions to add, create a new embed
        if fields_added >= 20 and idx != total_sessions:
            embeds.append(current_embed)
            current_embed = discord.Embed(
                title=f"📋 تفاصيل يوم {date_display} (متابعة)",
                color=0x3498db
            )
            fields_added = 0
    
    # Add avatar changes field to the last embed
    if avatar_changes > 0:
        current_embed.add_field(
            name="🎭 تغييرات الأفاتار",
            value=f"**{avatar_changes} مرة**",
            inline=False
        )
    else:
        current_embed.add_field(
            name="🎭 تغييرات الأفاتار",
            value="لم يتغير الأفاتار اليوم",
            inline=False
        )
    
    current_embed.set_footer(text="تقرير تفصيلي كامل لكل جلسات اليوم")
    embeds.append(current_embed)
    
    return embeds


def record_game_session(place_id, game_name, duration_seconds, start_time=None, force_date=None):
    """تسجيل جلسة لعب جديدة"""
    if not place_id or not game_name or duration_seconds <= 0:
        return
    
    stats = load_games_stats()
    game_key = sanitize_game_key(game_name)
    place_id_str = str(place_id)
    
    if game_key not in stats:
        stats[game_key] = {
            "name": game_name,
            "place_id": place_id_str,
            "total_time": 0,
            "sessions": 0,
            "last_played": None
        }
    
    stats[game_key]["total_time"] += duration_seconds
    stats[game_key]["sessions"] += 1
    stats[game_key]["place_id"] = place_id_str
    stats[game_key]["last_played"] = datetime.now(ZoneInfo("Europe/Lisbon")).isoformat()
    
    save_games_stats(stats)

    report_date_key = force_date or state.get("logical_day_key")
    if not report_date_key and start_time:
        report_date_key = start_time.strftime("%Y-%m-%d")

    if start_time:
        end_time = start_time + timedelta(seconds=duration_seconds)
        log_session_entry(game_name, place_id, start_time, end_time, date_key=report_date_key)
        if report_date_key:
            update_daily_game(place_id, game_name, duration_seconds, date_key=report_date_key)
        else:
            parts = split_duration_by_date(start_time, end_time)
            for date_key, seconds in parts.items():
                update_daily_game(place_id, game_name, seconds, date_key=date_key)
    else:
        update_daily_game(place_id, game_name, duration_seconds, date_key=report_date_key)
# --- جلب بيانات أي يوزر بالـ ID من روبلوكس ---
async def fetch_single_user_profile(session, user_id):
    try:
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("name"), data.get("displayName")
    except Exception as e:
        print(f"Error fetching user profile {user_id}: {e}")
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
            print(f"[{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M:%S')}] Target Loaded Successfully: {DISPLAY_NAME} (@{USER_NAME})")

@bot.event
async def on_ready():
    print("\n" + "="*70)
    print(f"🤖 Bot is Online as: {bot.user.name} | MongoDB Radar System 🔥")
    print("="*70 + "\n")
    await fetch_roblox_profile()
    saved_state = load_state_data()
    state["status"] = saved_state.get("status")
    state["last_online_time"] = saved_state.get("last_online_time")
    state["online_session_start"] = saved_state.get("online_session_start")
    state["offline_since"] = saved_state.get("offline_since")
    state["offline_alert_sent"] = saved_state.get("offline_alert_sent", False)
    state["pending_resume"] = saved_state.get("pending_resume", False)
    state["pending_resume_place_id"] = saved_state.get("pending_resume_place_id")
    state["pending_resume_game_name"] = saved_state.get("pending_resume_game_name")
    state["pending_resume_leave_time"] = saved_state.get("pending_resume_leave_time")
    state["last_avatar_url"] = saved_state.get("last_avatar_url")
    state["privacy_alert_sent"] = saved_state.get("privacy_alert_sent", False)
    state["last_activity_time"] = saved_state.get("last_activity_time")
    state["session_day_start"] = saved_state.get("session_day_start")
    state["offline_notification_sent"] = saved_state.get("offline_notification_sent", False)
    state["logical_day_key"] = saved_state.get("logical_day_key")

    if state["logical_day_key"] is None:
        now = datetime.now(ZoneInfo("Europe/Lisbon"))
        if state["last_activity_time"] and state["last_activity_time"].date() < now.date():
            state["logical_day_key"] = state["last_activity_time"].strftime("%Y-%m-%d")
        else:
            state["logical_day_key"] = get_date_str(now)
    state["session_day_start"] = state["logical_day_key"]
    roblox_radar_loop.start()
    daily_summary_task.start()
    weekly_summary_task.start()

@bot.check
async def check_channel(ctx):
    if ctx.command and ctx.command.name == "detail":
        return ctx.channel.id in [CMD_CHANNEL_ID, DETAIL_CHANNEL_ID]
    return ctx.channel.id == CMD_CHANNEL_ID

# --- الأوامر التفاعلية ---

@bot.command(name="avatarc")
async def cmd_avatarc(ctx):
    """عدد تغييرات الأفاتار اليوم"""
    report_date = get_active_report_date()
    doc = daily_stats_collection.find_one({"_id": report_date}) or {}
    count = doc.get("avatar_changes", 0)
    embed = discord.Embed(title="📊 [عداد الأفاتار - اليوم]", color=0x3498db)
    if count > 0:
        embed.add_field(name="🎭 تغييرات الأفاتار اليوم", value=f"**{count} مرة**", inline=False)
    else:
        embed.add_field(name="🎭 تغييرات الأفاتار اليوم", value="لم يتغير الأفاتار اليوم", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="avatarw")
async def cmd_avatarw(ctx):
    """عدد تغييرات الأفاتار للأسبوع الحالي (آخر 7 أيام)"""
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()
    start = today - timedelta(days=6)
    query = {"_id": {"$gte": start.strftime("%Y-%m-%d"), "$lte": today.strftime("%Y-%m-%d")}}
    docs = daily_stats_collection.find(query)
    total = 0
    for d in docs:
        total += d.get("avatar_changes", 0)
    embed = discord.Embed(title="📅 [عداد الأفاتار - الأسبوع الحالي]", color=0x9b59b6)
    if total > 0:
        embed.add_field(name="📆 إجمالي تغييرات الأفاتار خلال آخر 7 أيام", value=f"**{total} مرة**", inline=False)
    else:
        embed.add_field(name="📆 إجمالي تغييرات الأفاتار خلال آخر 7 أيام", value="لم يتغير الأفاتار خلال الأسبوع الحالي", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="avatara")
async def cmd_avatara(ctx):
    """إجمالي تغييرات الأفاتار عبر التاريخ"""
    docs = daily_stats_collection.find({}, {"avatar_changes": 1})
    total = 0
    for d in docs:
        total += d.get("avatar_changes", 0)
    embed = discord.Embed(title="👑 [عداد الأفاتار - التاريخ الكلي]", color=0xf1c40f)
    if total > 0:
        embed.add_field(name="📜 إجمالي تغييرات الأفاتار (الكل)", value=f"**{total} مرة**", inline=False)
    else:
        embed.add_field(name="📜 إجمالي تغييرات الأفاتار (الكل)", value="لم يتم تسجيل أي تغيير بالأفاتار حتى الآن", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="detail")
async def cmd_detail(ctx, date_arg: str = None):
    """عرض تفاصيل الجلسات ليوم محدد"""
    # Allow command in both CMD_CHANNEL_ID and DETAIL_CHANNEL_ID
    if ctx.channel.id not in [CMD_CHANNEL_ID, DETAIL_CHANNEL_ID]:
        return
    
    if date_arg is None:
        # Default to yesterday
        now = datetime.now(ZoneInfo("Europe/Lisbon"))
        yesterday = now.date() - timedelta(days=1)
        date_key = yesterday.strftime("%Y-%m-%d")
    else:
        # Validate format YYYY-MM-DD
        try:
            datetime.strptime(date_arg, "%Y-%m-%d")
            date_key = date_arg
        except ValueError:
            await ctx.send("❌ تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD")
            return
    
    embeds = build_detail_embeds(date_key)
    try:
        for embed in embeds:
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ خطأ في إرسال التفاصيل: {str(e)}")


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
    
    total_seconds_all = 0
    total_sessions_all = 0
    
    for idx, (game_key, data) in enumerate(sorted_games[:limit_num], 1):
        if not isinstance(data, dict):
            continue
        total_seconds = data.get("total_time", 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        sessions = data.get("sessions", 0)
        total_seconds_all += total_seconds
        total_sessions_all += sessions

        time_str = f"{hours}س {minutes}د {seconds}ث" if hours > 0 else (f"{minutes}د {seconds}ث" if minutes > 0 else f"{seconds}ث")
        
        embed.add_field(
            name=f"#{idx} - {data.get('name', 'Unknown')}",
            value=f"⏱️ الوقت الكلي: **{time_str}**\n📊 عدد الجلسات: **{sessions}**\n🆔 Game Key: `{game_key}`",
            inline=False
        )
    
    embed.set_footer(text=f"📊 الإجمالي: {format_seconds(total_seconds_all)} عبر {total_sessions_all} جلسة | يتم التحديث تلقائياً")
    await ctx.send(embed=embed)

@bot.command(name="gametime")
async def cmd_game_time(ctx):
    """عرض وقت اللعب الحالي"""
    if state["status"] != 2 or not state["game_session_start"]:
        await ctx.send("❌ اللاعب غير لاعب الآن، لا يوجد وقت لعب")
        return
    
    current_session_duration = int((datetime.now(ZoneInfo("Europe/Lisbon")) - state["game_session_start"]).total_seconds())
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
    
    for idx, (game_key, data) in enumerate(sorted_games, 1):
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
            value=f"⏱️ الكلي: **{time_str}**\n📊 الجلسات: **{sessions}**\n📌 المتوسط: **{avg_str}**\n🆔 Game Key: `{game_key}`",
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
    games_recorded = len([k for k, v in stats.items() if isinstance(v, dict)])
    
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

async def send_daily_summary(date_key):
    channel = bot.get_channel(DAILY_SUMMARY_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DAILY_SUMMARY_CHANNEL_ID)
        except Exception as e:
            print(f"Error fetching daily summary channel: {e}")
            return

    embed = build_daily_summary_embed(date_key)
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending daily summary: {e}")


async def send_daily_detail(date_key):
    """إرسال التقرير التفصيلي ليوم محدد إلى قناة التفاصيل"""
    channel = bot.get_channel(DETAIL_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DETAIL_CHANNEL_ID)
        except Exception as e:
            print(f"Error fetching detail channel: {e}")
            return
    
    embeds = build_detail_embeds(date_key)
    try:
        for embed in embeds:
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending detail embeds: {e}")


async def maybe_close_logical_day(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Lisbon"))
    if state["status"] != 0 or not state.get("logical_day_key"):
        return

    deadline = get_logical_day_close_deadline(now)
    if not deadline or now < deadline:
        return

    closed_day_key = state["logical_day_key"]
    if state.get("online_session_start"):
        update_daily_online(state["online_session_start"], now, date_key=closed_day_key)
        state["online_session_start"] = None

    embed = discord.Embed(
        title="🔴 [الهدف أوفلاين الآن - اليوم انتهى]",
        description=(
            f"اللاعب بقي أوفلاين لمدة ساعتين بعد آخر نشاط بعد منتصف الليل.\n"
            f"آخر نشاط: {state['last_activity_time'].strftime('%H:%M:%S') if state.get('last_activity_time') else 'Unknown'}\n\n"
            "✅ اليوم السابق اتسجل وانتهى!"
        ),
        color=0x7f8c8d
    )

    alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
    if alert_channel is None:
        try:
            alert_channel = await bot.fetch_channel(ALERT_CHANNEL_ID)
        except Exception as e:
            print(f"Error fetching alert channel for logical day close: {e}")
            alert_channel = None

    if alert_channel:
        try:
            await alert_channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending logical day close embed: {e}")

    await send_daily_summary(closed_day_key)
    await send_daily_detail(closed_day_key)

    state["logical_day_key"] = get_date_str(now)
    state["session_day_start"] = state["logical_day_key"]
    state["offline_notification_sent"] = True
    state["offline_since"] = None
    state["offline_alert_sent"] = False
    state["last_activity_time"] = None


@tasks.loop(time=dt_time(0, 0, 0, tzinfo=ZoneInfo("Europe/Lisbon")))
async def daily_summary_task():
    await maybe_close_logical_day(datetime.now(ZoneInfo("Europe/Lisbon")))

@tasks.loop(time=dt_time(1, 0, 0, tzinfo=ZoneInfo("Europe/Lisbon")))
async def weekly_summary_task():
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    if now.weekday() == 6:  # الأحد
        channel = bot.get_channel(WEEKLY_SUMMARY_CHANNEL_ID)
        if channel is None:
            try:
                channel = await bot.fetch_channel(WEEKLY_SUMMARY_CHANNEL_ID)
            except Exception as e:
                print(f"Error fetching weekly summary channel: {e}")
                return
        
        embed = build_weekly_summary_embed()
        try:
            await channel.send(embed=embed)
            print(f"✅ Weekly summary sent successfully")
        except Exception as e:
            print(f"Error sending weekly summary: {e}")

@bot.command(name="online", aliases=["onlinetime", "timeonline"])
async def cmd_online(ctx, period: str = "today", date_arg: str = None):
    query = period.lower() if period else "today"
    if date_arg:
        if query in ["date", "day"]:
            query = date_arg
        else:
            return await ctx.send("❌ استخدم: `!online today`, `!online week`, `!online month`, أو `!online YYYY-MM-DD`")
    # For 'today' use logical day key instead of calendar date
    if query == "today":
        date_key = get_active_report_date()
        try:
            parsed = datetime.strptime(date_key, "%Y-%m-%d").date()
            start_date, end_date = parsed, parsed
        except Exception:
            start_date, end_date = get_daily_range(query, date_str=query)
    else:
        start_date, end_date = get_daily_range(query, date_str=query)

    if not start_date or not end_date:
        return await ctx.send("❌ التنسيق غير صحيح. استخدم YYYY-MM-DD أو one of today/yesterday/week/month.")

    total_online, game_totals = load_stats_for_period(start_date, end_date)
    period_text = f"منذ {start_date.strftime('%Y-%m-%d')}" if start_date != end_date else f"في {start_date.strftime('%Y-%m-%d')}"
    if query == "today":
        title = "⏱️ وقت الأونلاين اليوم"
    elif query == "yesterday":
        title = "⏱️ وقت الأونلاين امبارح"
    elif query in ["week", "weekly"]:
        title = "⏱️ وقت الأونلاين هذا الأسبوع"
        period_text = f"من {start_date.strftime('%Y-%m-%d')} حتى {end_date.strftime('%Y-%m-%d')}"
    elif query in ["month", "monthly"]:
        title = "⏱️ وقت الأونلاين هذا الشهر"
        period_text = f"من {start_date.strftime('%Y-%m-%d')} حتى {end_date.strftime('%Y-%m-%d')}"
    else:
        title = f"⏱️ وقت الأونلاين ليوم {start_date.strftime('%Y-%m-%d')}"

    embed = discord.Embed(title=title, description=period_text, color=0x1abc9c)
    embed.add_field(name="⏰ الوقت الكلي", value=f"**{format_seconds(total_online)}**", inline=False)
    embed.set_footer(text="مبني على بيانات الأونلاين اليومية المسجلة")
    await ctx.send(embed=embed)

@bot.command(name="topmap", aliases=["maptop", "mapstats"])
async def cmd_top_map(ctx, period: str = "yesterday", date_arg: str = None):
    query = period.lower() if period else "yesterday"
    if date_arg:
        if query in ["date", "day"]:
            query = date_arg
        else:
            return await ctx.send("❌ استخدم: `!topmap yesterday`, `!topmap week`, `!topmap month`, أو `!topmap YYYY-MM-DD`")

    # For 'today' use logical day if available
    if query == "today":
        date_key = get_active_report_date()
        try:
            parsed = datetime.strptime(date_key, "%Y-%m-%d").date()
            start_date, end_date = parsed, parsed
        except Exception:
            start_date, end_date = get_daily_range(query, date_str=query)
    else:
        start_date, end_date = get_daily_range(query, date_str=query)

    if not start_date or not end_date:
        return await ctx.send("❌ التنسيق غير صحيح. استخدم YYYY-MM-DD أو one of yesterday/week/month.")

    top_games = get_top_games(start_date, end_date, limit=5)
    if not top_games:
        return await ctx.send("📊 لا توجد بيانات مابات لهذا النطاق.")

    if query == "yesterday":
        title = "🗺️ أكثر المابات لعباً امبارح"
        description = f"من: {start_date.strftime('%Y-%m-%d')}"
    elif query in ["week", "weekly"]:
        title = "🗺️ أكثر المابات لعباً هذا الأسبوع"
        description = f"من {start_date.strftime('%Y-%m-%d')} حتى {end_date.strftime('%Y-%m-%d')}"
    elif query in ["month", "monthly"]:
        title = "🗺️ أكثر المابات لعباً هذا الشهر"
        description = f"من {start_date.strftime('%Y-%m-%d')} حتى {end_date.strftime('%Y-%m-%d')}"
    elif query == "today":
        title = "🗺️ أكثر المابات لعباً اليوم"
        description = f"في {start_date.strftime('%Y-%m-%d')}"
    else:
        title = f"🗺️ أكثر المابات لعباً في {start_date.strftime('%Y-%m-%d')}"
        description = f"في {start_date.strftime('%Y-%m-%d')}"

    embed = discord.Embed(title=title, description=description, color=0x9b59b6)
    for idx, (game_key, data) in enumerate(top_games, 1):
        time_str = format_seconds(data.get("total_time", 0))
        sessions = data.get("sessions", 0)
        embed.add_field(
            name=f"#{idx} - {data.get('name', 'Unknown')}",
            value=f"⏱️ وقت اللعب: **{time_str}**\n📊 عدد الجلسات: **{sessions}**\n🆔 Game Key: `{game_key}`",
            inline=False
        )
    embed.set_footer(text="يعتمد على سجل المابات اليومية والبيانات المجمعة")
    await ctx.send(embed=embed)

# --- رادار الفحص الدوري التلقائي ---

@tasks.loop(seconds=INTERVAL)
async def roblox_radar_loop():
    global state
    alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not alert_channel: return

    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    await maybe_close_logical_day(now)

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

                    previous_status = state["status"]
                    current_avatar_url = await fetch_avatar_urls(session)
                    if current_avatar_url:
                        if state["last_avatar_url"] is None:
                            state["last_avatar_url"] = current_avatar_url
                        elif status == 0 and state["last_avatar_url"] != current_avatar_url and not state["privacy_alert_sent"]:
                            embed_privacy = discord.Embed(
                                title="⚠️ [تحذير: تغيير الأفاتار أثناء الأوفلاين]",
                                description="يبدو أن الهدف غيّر الأفاتار وهو في وضع عدم الظهور، قد يكون مخفي أونلاين رغم ظهوره كأوفلاين.",
                                color=0xe74c3c
                            )
                            embed_privacy.add_field(name="⛔ الحالة الحالية", value="أوفلاين رسميًا لكن الأفاتار تغير", inline=False)
                            embed_privacy.add_field(name="🧠 معنى ذلك", value="ممكن يكون المستخدم مستخدم الوضع الخاص لإخفاء ظهور الأونلاين.", inline=False)
                            embed_privacy.add_field(name="🌐 رابط الأفاتار الجديد", value=current_avatar_url, inline=False)
                            await alert_channel.send(embed=embed_privacy)
                            state["privacy_alert_sent"] = True
                            # Log avatar change in daily stats using logical day key
                            try:
                                daily_stats_collection.update_one(
                                    {"_id": get_active_report_date()},
                                    {"$inc": {"avatar_changes": 1}},
                                    upsert=True
                                )
                            except Exception:
                                pass
                            state["last_avatar_url"] = current_avatar_url
                        elif status != 0:
                            state["privacy_alert_sent"] = False
                            state["last_avatar_url"] = current_avatar_url

                    if state["pending_resume"] and state["pending_resume_leave_time"] and status != 2:
                        if now - state["pending_resume_leave_time"] > timedelta(minutes=10) and not state["session_recorded"]:
                            leave_duration = int((state["pending_resume_leave_time"] - state["game_session_start"]).total_seconds()) if state["game_session_start"] else 0
                            record_game_session(state["pending_resume_place_id"], state["pending_resume_game_name"], leave_duration, start_time=state["game_session_start"])

                            start_time_str = state["game_session_start"].strftime("%H:%M:%S") if state["game_session_start"] else "Unknown"
                            end_time_str = state["pending_resume_leave_time"].strftime("%H:%M:%S") if state["pending_resume_leave_time"] else "Unknown"
                            embed_recorded = discord.Embed(
                                title="✅ [جلسة تم تسجيلها]",
                                color=0x2ecc71
                            )
                            embed_recorded.add_field(name="🎮 الماب", value=f"**{state['pending_resume_game_name']}**", inline=False)
                            embed_recorded.add_field(name="⏱️ المدة الكلية", value=f"**{format_seconds(leave_duration)}**", inline=False)
                            embed_recorded.add_field(name="🕐 بدأت", value=f"`{start_time_str}`", inline=True)
                            embed_recorded.add_field(name="🕑 انتهت", value=f"`{end_time_str}`", inline=True)
                            await alert_channel.send(embed=embed_recorded)

                            state["session_recorded"] = True
                            state["pending_resume"] = False
                            state["game_session_start"] = None

                    if status in [1, 2, 3]:
                        if previous_status not in [1, 2, 3]:
                            if not state["online_session_start"]:
                                state["online_session_start"] = now
                                if not state["session_day_start"]:
                                    state["session_day_start"] = now.date()
                        state["last_activity_time"] = now
                        state["last_online_time"] = now
                        state["offline_since"] = None
                        state["offline_notification_sent"] = False
                    elif previous_status in [1, 2, 3]:
                        pass

                    if status in [1, 2, 3] and previous_status == 0:
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
                        state["offline_notification_sent"] = False

                    if status == 2 and previous_status == 2 and place_id != state["place_id"]:
                        # اللاعب غير اللعبة خلال حالة متصلة 2، اعتبر ذلك جلسة جديدة للماب الجديدة
                        if state["game_session_start"] and not state["session_recorded"]:
                            old_duration = int((now - state["game_session_start"]).total_seconds())
                            record_game_session(state["place_id"], state["last_game_name"], old_duration, start_time=state["game_session_start"])
                        state["pending_resume"] = False
                        state["pending_resume_leave_time"] = None
                        state["last_game_name"] = game
                        state["last_game_time"] = now
                        state["place_id"] = place_id
                        state["game_id"] = game_id
                        state["game_session_start"] = now
                        state["session_recorded"] = False
                        page_link = f"https://www.roblox.com/games/{place_id}"
                        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}" if game_id else page_link
                        embed = discord.Embed(title="🎮 [الهدف انتقل لماب جديدة]", description="اللاعب دخل ماب جديدة في نفس الجلسة الحالية.", color=0x2ecc71)
                        embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
                        embed.add_field(name="رابط صفحة الماب (Roblox Page)", value=f"[اضغط هنا لفتح الصفحة]({page_link})", inline=False)
                        embed.add_field(name="رابط الدخول المباشر وراه (JOIN LINK) 🔥", value=f"[اضغط هنا للدخول وراه السيرفر فوراً]({join_link})", inline=False)
                        await alert_channel.send(embed=embed)

                    elif status == 2 and state["status"] != 2:
                        resumed_same_session = False
                        if state["pending_resume"] and place_id == state["pending_resume_place_id"] and game == state["pending_resume_game_name"]:
                            time_since_leave = now - state["pending_resume_leave_time"]
                            if time_since_leave <= timedelta(minutes=10):
                                resumed_same_session = True
                                embed_resume = discord.Embed(
                                    title="🔄 [رجع نفس الماب خلال 10 دقائق]",
                                    description="اللاعب رجع نفس الماب خلال 10 دقائق، هتتحسب كجلسة واحدة فقط.",
                                    color=0x3498db
                                )
                                embed_resume.add_field(name="اسم الماب", value=f"**{game}**", inline=False)
                                embed_resume.add_field(name="مدة الخروج", value=f"**{format_seconds(int(time_since_leave.total_seconds()))}**", inline=False)
                                embed_resume.set_footer(text="الجلسة استمرت في نفس الماب، والسجل هيفضل نفس الجلسة.")
                                await alert_channel.send(embed=embed_resume)
                                state["pending_resume"] = False
                                state["pending_resume_leave_time"] = None
                                state["last_game_time"] = now
                                state["place_id"] = place_id
                                state["game_id"] = game_id
                        if not resumed_same_session:
                            if state["pending_resume"] and not state["session_recorded"]:
                                leave_duration = int((state["pending_resume_leave_time"] - state["game_session_start"]).total_seconds()) if state["game_session_start"] else 0
                                record_game_session(state["pending_resume_place_id"], state["pending_resume_game_name"], leave_duration, start_time=state["game_session_start"])
                                state["pending_resume"] = False
                                state["pending_resume_leave_time"] = None
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

                    if status != 2 and state["status"] == 2:
                        if state["game_session_start"] and state["last_game_name"] != "مفيش مابات مسجلة" and not state["pending_resume"]:
                            state["pending_resume"] = True
                            state["pending_resume_place_id"] = state["place_id"]
                            state["pending_resume_game_name"] = state["last_game_name"]
                            state["pending_resume_leave_time"] = now
                            state["session_recorded"] = False

                            embed_leave = discord.Embed(
                                title="⏹️ [خرج من الماب مؤقتًا]",
                                description="اللاعب خرج من الماب. إذا رجع لنفس الماب خلال 10 دقائق، هتتحسب كجلسة واحدة.",
                                color=0xe67e22
                            )
                            embed_leave.add_field(name="اسم الماب", value=f"**{state['last_game_name']}**", inline=False)
                            embed_leave.add_field(name="وقت الخروج", value=f"`{now.strftime('%Y-%m-%d %H:%M:%S')}`", inline=False)
                            embed_leave.add_field(name="ملاحظة", value="لو رجع نفس الماب خلال 10 دقائق، الجلسة ستحسب كجلسة واحدة.", inline=False)
                            await alert_channel.send(embed=embed_leave)

                    if status == 0 and state["status"] != 0:
                        state["offline_since"] = now
                        state["offline_alert_sent"] = False

                    # إشعار 10 دقائق - إخباري فقط (لا يؤثر على الجلسة)
                    if status == 0 and state["offline_since"] and not state["offline_alert_sent"]:
                        if now - state["offline_since"] >= timedelta(minutes=10):
                            embed = discord.Embed(
                                title="⏰ [تنبيه: 10 دقائق أوفلاين]",
                                description="اللاعب بقي أوفلاين لمدة 10 دقائق.",
                                color=0xe67e22
                            )
                            await alert_channel.send(embed=embed)
                            state["offline_alert_sent"] = True

                    # النظام الذكي: انتظر ساعتين من آخر نشاط قبل إنهاء اليوم
                    if status == 0 and state["last_activity_time"] and not state["offline_notification_sent"]:
                        deadline = get_logical_day_close_deadline(now)
                        if deadline and now >= deadline:
                            # حفظ الجلسة الحالية ضمن اليوم المنطقي القديم
                            if state["online_session_start"]:
                                update_daily_online(state["online_session_start"], now, date_key=state.get("logical_day_key"))
                                state["online_session_start"] = None
                            
                            embed = discord.Embed(
                                title="🔴 [الهدف أوفلاين الآن - اليوم انتهى]",
                                description=(
                                    f"اللاعب بقي أوفلاين لمدة ساعتين بعد آخر نشاط بعد منتصف الليل.\\n"
                                    f"آخر نشاط: {state['last_activity_time'].strftime('%H:%M:%S') if state.get('last_activity_time') else 'Unknown'}\\n\\n"
                                    "✅ اليوم السابق اتسجل وانتهى!"
                                ),
                                color=0x7f8c8d
                            )
                            await alert_channel.send(embed=embed)
                            await send_daily_summary(state.get("logical_day_key"))
                            await send_daily_detail(state.get("logical_day_key"))
                            state["logical_day_key"] = get_date_str(now)
                            state["session_day_start"] = state["logical_day_key"]
                            state["offline_notification_sent"] = True
                            state["offline_since"] = None
                            state["offline_alert_sent"] = False
                            state["last_activity_time"] = None

                    if status != state["status"]: state["status"] = status
                    if status == 2: state["game"] = game

            # 2. رادار الأصدقاء المتقدم مع MongoDB
            curr_friends = await fetch_all_friends(session)
            if curr_friends:
                current_ids = [f["id"] for f in curr_friends]
                friends_data = load_friends_data()
                
                if not friends_data["baseline_ids"]:
                    print(f"[{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M:%S')}] First run! Storing ALL baseline to MongoDB silently...")
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
                            
                            now_str = datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %I:%M:%S %p")
                            
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

            save_state_data()

        except Exception as e:
            print(f"Error in main background radar: {e}")
        finally:
            try:
                save_state_data()
            except Exception as err:
                print(f"Error saving state after loop: {err}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

