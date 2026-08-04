#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import sys
import hashlib
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
ROBLOSECURITY = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEQAhoEEAQYASIcCgRkdWlkEhQxMTEzMzUzNjIwMjU1NjgxNjg1MCITCgV1bmFtZRIKQm9ydUdvYXQzMyIRCgN1aWQSCjcyMTQ1MTExOTEoAw.AQ2h8jVPK02spj6G979D5Z2S8ZItYw8KyzUFac9KpD9Jnmcb3O-f7Ci96ZdF6M_9nz8EdT3FMOTh5-O-gTA69CYQvnEb_RLSIO11fhijc2Ui0hlETRCOzX9INNJqmf10X-A8DRctRh9FAqgPUgqopn1gs4QODPpfKPB4uXlcS516_m0K-0aXC3q5hljmnxP4sRe6r4Fu211IqvFE4G9Uxn1gUVTMzgrnLvcQMEzpAWe9EQ8xa07G1JGkv9Srfs1x5X_jUXWMabvHUzkYVLeHk7PD0aQN3-Dw87XXLPpmGkA6k9M-a6RyLZqNNiSYiPq8RgYZYR2k54Mht3zb5CZQeBdKTwg5Jrv_1qJzhhG1Gu_kHn0Cb78OkoBDCswtxZpyRetUCLrjAaXpumg8IL0s0Oh0dqp7neLBghAT49Zm2JU1HJZnU6WfbDlz3hKuZO89ebV0EWVRi4fU9hH1ooRvF641mfjNez3VtZCg9muxLLBh_cR703lRxH7ji4o7TGck4UZoN1-KtAjppiZT8IFKqxiXad5SHkKKmJELkde9tlDD54v4kL3tzII32hdoO8DkSUgam3sPTlYfLuQHtXdpyRDCs5xgJaf_JMhe39SHsTKLEYcs6eLkxNmY8oZlYyRckiLwzuG_nK3xjCnyytxGL3bfd7h6S_Fgg_f4TBuuUCmzJfwjlVjvMK0Vyvb7Liqy62Oo4KJjPBmjIrVSDqLWblOnnceiif7ZaZMxgR5MKKF2AyCdLniTj89LizL6GPa-Z40GpK7CJuvY0uEnjgCqYuRY2J14cHf8ZqBx6gv_FGJJ94_JybLruHQ2DRpNNt-KfSNqBdeG1JxPSUx_WqEhaeKskBeAkgR9jVYzRWXmP6geT42-SP1loOWx6chNepxVDvG-XaAECcnkwg7SLWbSiq_vo8WdSeBwmGDK_OczxqM.qExrLrcVcXgd-AJcYhEPMKEu2Bc"

BOT_TOKEN = "MTM0MTE4NTI0MTgwMDI0NTI5MQ.G4sqeg.IBMKpnb9RBH0ito-aIkkOOd1kofZ679wtNvPso"
CMD_CHANNEL_ID = 1509431098117984327
ALERT_CHANNEL_ID = 1509345547197091940
DAILY_SUMMARY_CHANNEL_ID = 1510270977513099296
WEEKLY_SUMMARY_CHANNEL_ID = 1510275621316595802
DETAIL_CHANNEL_ID = 1510541538445230080
AVATAR_CHANGE_CHANNEL_ID = 1510752801196871850
TIMELINE_CHANNEL_ID = 1510754643414876301
PRECISE_STATS_CHANNEL_ID = 1510936751252832288

# ==================== MongoDB Configuration ====================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://marwangamer056_db_user:NulNLKsdAz55Av50@cluster0.j35ail6.mongodb.net/?appName=Cluster0")
INTERVAL = 20 # فترة التحقق بالثواني (20 ثانية) 
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
    "last_avatar_hash": None,
    "timeline_current_session_start": None,
    "timeline_last_offline_time": None,
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
daily_timeline_collection = db.daily_timeline

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
            "last_avatar_hash": doc.get("last_avatar_hash"),
            "timeline_current_session_start": _make_aware(doc.get("timeline_current_session_start")),
            "timeline_last_offline_time": _make_aware(doc.get("timeline_last_offline_time")),
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
        "last_avatar_hash": None,
        "timeline_current_session_start": None,
        "timeline_last_offline_time": None,
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
            "last_avatar_hash": state.get("last_avatar_hash"),
            "timeline_current_session_start": state.get("timeline_current_session_start"),
            "timeline_last_offline_time": state.get("timeline_last_offline_time"),
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
    # allow missing place_id (store None) so we don't drop session logs
    if not game_name or not start_time or not end_time or end_time <= start_time:
        return
    place_id_str = str(place_id) if place_id else None
    session_logs.insert_one(
        {
            "game_name": game_name,
            "place_id": place_id_str,
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
    # If there was activity after midnight, use 2-hour grace after last activity.
    # If there was NO activity after midnight (player was already offline at midnight),
    # use a 4-hour midnight waiting window (00:00 - 04:00) before closing the logical day.
    if last_activity:
        last_activity = _make_aware(last_activity)
        if last_activity >= midnight:
            return last_activity + timedelta(hours=2)
        else:
            return midnight + timedelta(hours=4)
    # No last_activity recorded — fall back to 4-hour midnight window
    return midnight + timedelta(hours=4)


def update_daily_online(start_dt, end_dt, date_key=None):
    # If a date_key is provided, compute online_seconds from the authoritative
    # timeline documents (daily_timeline_collection) clipped to the logical-day
    # interval (and optional end time). This avoids counting waiting/grace windows
    # or long offline gaps when `online_session_start` spans multiple online/offline segments.
    if date_key:
        try:
            tz = ZoneInfo("Europe/Lisbon")
            # Determine clipping end: prefer end_dt if provided and valid, else
            # use any stored logical_close_at in daily_stats, else calendar day end
            clip_end = None
            if end_dt:
                clip_end = end_dt
            else:
                doc = daily_stats_collection.find_one({"_id": date_key}) or {}
                lc = doc.get("logical_close_at")
                if lc:
                    clip_end = _make_aware(lc)

            # compute day start and default day end if clip_end not set
            day = datetime.strptime(date_key, "%Y-%m-%d").date()
            day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
            day_end_default = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)
            day_end = clip_end if clip_end else day_end_default

            # Aggregate from timeline docs for the date.
            # Include the next-day calendar document if the logical day is still active,
            # or if the closed logical day extended past midnight into the next calendar date.
            active_day = state.get("logical_day_key") == date_key
            doc_keys = [date_key]
            if active_day or (clip_end and clip_end.date() > day):
                doc_keys.append((day + timedelta(days=1)).strftime("%Y-%m-%d"))

            total = 0
            for d_key in doc_keys:
                doc = daily_timeline_collection.find_one({"_id": d_key}) or {}
                for s in doc.get("sessions", []):
                    try:
                        st = _make_aware(s.get("start_time"))
                        ed_raw = s.get("end_time")
                        ed = _make_aware(ed_raw) if ed_raw else None
                        seg_start = st if st and st >= day_start else day_start
                        seg_end = ed if ed and ed <= day_end else day_end
                        if seg_end and seg_start and seg_end > seg_start:
                            total += int((seg_end - seg_start).total_seconds())
                    except Exception:
                        continue

            now_ts = datetime.now(ZoneInfo("Europe/Lisbon"))
            daily_stats_collection.update_one(
                {"_id": date_key},
                {
                    "$set": {"online_seconds": int(total), "last_updated": now_ts},
                    "$setOnInsert": {"games": {}, "created_at": now_ts}
                },
                upsert=True
            )
        except Exception as e:
            print(f"Error computing online from timeline for {date_key}: {e}")
        return

    # Backward-compatible: if no date_key (rare), fall back to splitting by calendar dates
    if not start_dt or not end_dt or end_dt <= start_dt:
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


def compute_logical_day_timeline_total(date_key):
    tz = ZoneInfo("Europe/Lisbon")
    try:
        day = datetime.strptime(date_key, "%Y-%m-%d").date()
    except Exception:
        return 0

    day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
    stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    logical_close_at = stats_doc.get("logical_close_at")
    is_active = state.get("logical_day_key") == date_key
    now = datetime.now(tz)
    if is_active:
        day_end = now
    elif logical_close_at:
        day_end = _make_aware(logical_close_at)
    else:
        day_end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)

    doc_keys = [date_key]
    if is_active or (logical_close_at and logical_close_at.date() > day):
        doc_keys.append((day + timedelta(days=1)).strftime("%Y-%m-%d"))

    total = 0
    for d_key in doc_keys:
        doc = daily_timeline_collection.find_one({"_id": d_key}) or {}
        for s in doc.get("sessions", []):
            try:
                st = _make_aware(s.get("start_time"))
                ed_raw = s.get("end_time")
                ed = _make_aware(ed_raw) if ed_raw else None
                if ed is None:
                    if is_active:
                        ed = now
                    else:
                        continue
                seg_start = st if st and st >= day_start else day_start
                seg_end = ed if ed and ed <= day_end else day_end
                if seg_end and seg_start and seg_end > seg_start:
                    total += int((seg_end - seg_start).total_seconds())
            except Exception:
                continue
    return total


def merge_segments(segments):
    merged = []
    for start, end in sorted(segments, key=lambda x: x[0]):
        if not merged:
            merged.append([start, end])
            continue
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def get_logical_day_timeline_segments(date_key):
    tz = ZoneInfo("Europe/Lisbon")
    try:
        day = datetime.strptime(date_key, "%Y-%m-%d").date()
    except Exception:
        return []

    day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
    stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    logical_close_at = stats_doc.get("logical_close_at")
    is_active = state.get("logical_day_key") == date_key
    now = datetime.now(tz)
    if is_active:
        day_end = now
    elif logical_close_at:
        day_end = _make_aware(logical_close_at)
    else:
        day_end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)

    doc_keys = [date_key]
    if is_active or (logical_close_at and logical_close_at.date() > day):
        doc_keys.append((day + timedelta(days=1)).strftime("%Y-%m-%d"))

    segments = []
    for d_key in doc_keys:
        doc = daily_timeline_collection.find_one({"_id": d_key}) or {}
        for s in doc.get("sessions", []):
            st = _make_aware(s.get("start_time"))
            ed_raw = s.get("end_time")
            ed = _make_aware(ed_raw) if ed_raw else None
            if ed is None:
                if is_active:
                    ed = now
                else:
                    continue
            seg_start = st if st and st >= day_start else day_start
            seg_end = ed if ed and ed <= day_end else day_end
            if seg_start and seg_end and seg_end > seg_start:
                segments.append((seg_start, seg_end))

    if is_active and state.get("timeline_current_session_start"):
        try:
            start = _make_aware(state.get("timeline_current_session_start"))
            if start:
                seg_start = start if start >= day_start else day_start
                loff = state.get("timeline_last_offline_time")
                include_now = False
                if state.get("status") in [1, 2, 3]:
                    include_now = True
                elif loff:
                    loff_a = _make_aware(loff)
                    if loff_a and (now - loff_a) < timedelta(minutes=30):
                        include_now = True

                if include_now and seg_start < day_end:
                    last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
                    if state.get("status") in [1, 2, 3]:
                        seg_end = min(now, day_end)
                    else:
                        seg_end = last_online if last_online and last_online <= day_end else None
                    if seg_end and seg_end > seg_start:
                        segments.append((seg_start, seg_end))
        except Exception:
            pass

    return merge_segments(segments)


def get_logical_day_inside_segments(date_key):
    tz = ZoneInfo("Europe/Lisbon")
    try:
        day = datetime.strptime(date_key, "%Y-%m-%d").date()
    except Exception:
        return []

    day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
    stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    logical_close_at = stats_doc.get("logical_close_at")
    is_active = state.get("logical_day_key") == date_key
    now = datetime.now(tz)
    if is_active:
        day_end = now
    elif logical_close_at:
        day_end = _make_aware(logical_close_at)
    else:
        day_end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)

    segments = []
    try:
        cursor = session_logs.find({"start_time": {"$lt": day_end}, "end_time": {"$gt": day_start}})
        for s in cursor:
            st = _make_aware(s.get("start_time"))
            ed = _make_aware(s.get("end_time"))
            if not st or not ed:
                continue
            seg_start = st if st >= day_start else day_start
            seg_end = ed if ed <= day_end else day_end
            if seg_start and seg_end and seg_end > seg_start:
                segments.append((seg_start, seg_end))
    except Exception:
        pass

    try:
        if state.get("game_session_start"):
            gst = _make_aware(state.get("game_session_start"))
            if gst:
                seg_start = gst if gst >= day_start else day_start
                last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
                if state.get("logical_day_key") == date_key:
                    if state.get("status") in [1, 2, 3]:
                        seg_end = min(now, day_end)
                    else:
                        seg_end = last_online if last_online and last_online <= day_end else None
                else:
                    seg_end = day_end
                if seg_end and seg_end > seg_start:
                    segments.append((seg_start, seg_end))
    except Exception:
        pass

    return merge_segments(segments)


def compute_segment_overlap(segments_a, segments_b):
    a = merge_segments(segments_a)
    b = merge_segments(segments_b)
    i = j = 0
    overlap = 0
    while i < len(a) and j < len(b):
        a_start, a_end = a[i]
        b_start, b_end = b[j]
        start = max(a_start, b_start)
        end = min(a_end, b_end)
        if start < end:
            overlap += int((end - start).total_seconds())
        if a_end <= b_end:
            i += 1
        else:
            j += 1
    return overlap


def update_daily_game(place_id, game_name, seconds, date_key=None):
    # allow missing place_id (store None) to avoid dropping game stats
    if not game_name or seconds <= 0:
        return
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    game_key = sanitize_game_key(game_name)
    date_key = date_key or get_date_str(now)
    place_id_str = str(place_id) if place_id else None
    # Build update dict; set place_id (possibly None) if provided
    set_fields = {f"games.{game_key}.name": game_name, "last_updated": now}
    set_fields[f"games.{game_key}.place_id"] = place_id_str
    daily_stats_collection.update_one(
        {"_id": date_key},
        {
            "$inc": {f"games.{game_key}.total_time": seconds, f"games.{game_key}.sessions": 1, "total_game_seconds": seconds},
            "$set": set_fields
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
    total_online = compute_logical_day_timeline_total(date_key)
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
    raw_sessions = list(session_logs.find({"date_key": date_key}).sort("start_time", 1))

    # Query avatar changes first (needed for both cases)
    daily_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
    avatar_changes = daily_doc.get("avatar_changes", 0)

    date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%d/%m/%Y")

    # If no sessions, return a simple embed
    if not raw_sessions:
        embed = discord.Embed(
            title=f"📋 تفاصيل يوم {date_display}",
            description="لا توجد جلسات مسجلة لهذا اليوم",
            color=0x3498db
        )
        if avatar_changes > 0:
            embed.add_field(name="🎭 تغييرات الأفاتار", value=f"**{avatar_changes} مرة**", inline=False)
        else:
            embed.add_field(name="🎭 تغييرات الأفاتار", value="لم يتغير الأفاتار اليوم", inline=False)
        embed.set_footer(text="تقرير تفصيلي كامل لكل جلسات اليوم")
        return [embed]

    # Normalize sessions (ensure aware datetimes) and prepare for merging
    processed = []
    for s in raw_sessions:
        st_raw = s.get("start_time")
        ed_raw = s.get("end_time")
        try:
            st = _make_aware(st_raw) if st_raw else None
        except Exception:
            st = None
        try:
            ed = _make_aware(ed_raw) if ed_raw else None
        except Exception:
            ed = None

        duration = s.get("duration_seconds")
        if (not duration or duration <= 0) and st and ed:
            duration = int((ed - st).total_seconds())

        processed.append({
            "game_name": s.get("game_name", "Unknown"),
            "place_id": s.get("place_id"),
            "start_time": st,
            "end_time": ed,
            "duration_seconds": duration or 0
        })

    # Merge short gaps (<5 minutes) for the SAME map/place_id only (display-only)
    display_sessions = []
    for s in processed:
        if not display_sessions:
            display_sessions.append(s.copy())
            continue

        last = display_sessions[-1]
        try:
            # Use normalized game name as primary key for display merging
            g1 = sanitize_game_key(s.get("game_name") or "")
            g2 = sanitize_game_key(last.get("game_name") or "")
            same_map = (g1 and g2 and g1 == g2)
        except Exception:
            same_map = False

        if same_map and last.get("end_time") and s.get("start_time"):
            gap = s.get("start_time") - last.get("end_time")
            if gap <= timedelta(minutes=5):
                # Merge into last
                new_end = s.get("end_time") or last.get("end_time")
                if new_end and last.get("start_time"):
                    last["end_time"] = new_end
                    last["duration_seconds"] = int((new_end - last.get("start_time")).total_seconds())
                else:
                    # Fallback: extend duration by sum
                    last["duration_seconds"] = (last.get("duration_seconds", 0) + s.get("duration_seconds", 0))
                continue

        # Otherwise, append as separate display session
        display_sessions.append(s.copy())

    # Build embeds with max 20 session fields per embed, formatting times in 12-hour format
    embeds = []
    fields_added = 0
    current_embed = discord.Embed(title=f"📋 تفاصيل يوم {date_display}", color=0x3498db)

    total_sessions = len(display_sessions)
    for idx, session in enumerate(display_sessions, start=1):
        game_name = session.get("game_name", "Unknown")
        start_time = session.get("start_time")
        end_time = session.get("end_time")
        duration_seconds = session.get("duration_seconds", 0)

        if start_time and end_time:
            try:
                start_str = start_time.strftime("%I:%M %p")
                end_str = end_time.strftime("%I:%M %p")
            except Exception:
                start_str = str(start_time)
                end_str = str(end_time)
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
            current_embed = discord.Embed(title=f"📋 تفاصيل يوم {date_display} (متابعة)", color=0x3498db)
            fields_added = 0

    # Add avatar changes field to the last embed
    if avatar_changes > 0:
        current_embed.add_field(name="🎭 تغييرات الأفاتار", value=f"**{avatar_changes} مرة**", inline=False)
    else:
        current_embed.add_field(name="🎭 تغييرات الأفاتار", value="لم يتغير الأفاتار اليوم", inline=False)

    current_embed.set_footer(text="تقرير تفصيلي كامل لكل جلسات اليوم")
    embeds.append(current_embed)

    return embeds


def record_game_session(place_id, game_name, duration_seconds, start_time=None, force_date=None):
    """تسجيل جلسة لعب جديدة"""
    # allow missing place_id (store None) to avoid missing sessions when presence lacks placeId
    if not game_name or duration_seconds <= 0:
        return

    stats = load_games_stats()
    game_key = sanitize_game_key(game_name)
    place_id_str = str(place_id) if place_id else None
    
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
    state["last_avatar_hash"] = saved_state.get("last_avatar_hash")
    state["timeline_current_session_start"] = saved_state.get("timeline_current_session_start")
    state["timeline_last_offline_time"] = saved_state.get("timeline_last_offline_time")

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
    daily_timeline_task.start()

@bot.check
async def check_channel(ctx):
    # Allow `detail` in both CMD and DETAIL channels, `timeline` only in TIMELINE channel
    if ctx.command:
        if ctx.command.name == "detail":
            return ctx.channel.id in [CMD_CHANNEL_ID, DETAIL_CHANNEL_ID]
        if ctx.command.name == "timeline":
            return ctx.channel.id == TIMELINE_CHANNEL_ID
    return ctx.channel.id == CMD_CHANNEL_ID


@bot.event
async def on_command_error(ctx, error):
    # Provide clear feedback when a command is blocked by the channel check
    if isinstance(error, commands.CheckFailure):
        if ctx.command:
            if ctx.command.name == "timeline":
                await ctx.send("❌ هذا الأمر مسموح فقط في قناة سجل الأونلاين اليومية.")
                return
            if ctx.command.name == "precisestats":
                await ctx.send("❌ هذا الأمر مسموح فقط في قناة إحصائيات الدقة.")
                return
            if ctx.command.name == "detail":
                await ctx.send("❌ هذا الأمر مسموح فقط في قنوات الأوامر أو التفاصيل.")
                return
        await ctx.send("❌ لا تملك صلاحية استخدام هذا الأمر في هذه القناة.")
        return
    # For other errors, fall back to printing to console and allow default handling
    print(f"Command error: {error}")

# --- الأوامر التفاعلية ---

@bot.command(name="avatarc")
async def cmd_avatarc(ctx):
    """عدد تغييرات الأفاتار اليوم (اليوم المنطقي)"""
    # Use logical day key, not calendar date
    report_date = state.get("logical_day_key") or get_active_report_date()
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
            exact_time = state["last_online_time"].strftime("%Y-%m-%d %I:%M:%S %p")
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

def build_direct_join_link(place_id, game_id=None):
    if not place_id:
        return None
    if game_id:
        return f"https://www.roblox.com/games/start?placeId={place_id}&gameId={game_id}"
    return f"https://www.roblox.com/games/{place_id}"


@bot.command(name="join")
async def cmd_join(ctx):
    if not state.get("place_id") or not state.get("game_id"):
        await ctx.send("❌ اللاعب مش دخال أي لعبة دلوقتي، ما فيش رابط join متاح.")
        return
    
    join_link = build_direct_join_link(state["place_id"], state["game_id"])
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


async def fetch_image_hash(session, image_url):
    """Download image bytes and return sha256 hexdigest, or None on failure."""
    if not image_url:
        return None
    try:
        async with session.get(image_url, timeout=10) as r:
            if r.status == 200:
                data = await r.read()
                return hashlib.sha256(data).hexdigest()
    except Exception as e:
        print(f"Error fetching avatar image for hash: {e}")
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


@bot.command(name="what")
async def cmd_what(ctx):
    """عرض الوقت والتاريخ الحالي بتوقيت Europe/Lisbon"""
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M:%S %p")
    tz_info = "Europe/Lisbon"
    logical_day = get_active_report_date()
    logical_state = state.get("logical_day_key")
    last_act = state.get("last_activity_time")
    if last_act:
        last_act = _make_aware(last_act)
        last_act_str = last_act.strftime("%Y-%m-%d %I:%M:%S %p")
    else:
        last_act_str = "لا توجد بيانات"

    embed = discord.Embed(title="🕒 الوقت والتاريخ الحالي (كما يراه السكربت)", color=0x3498db)
    embed.add_field(name="التاريخ الآن (Lisbon)", value=f"`{date_str}`", inline=True)
    embed.add_field(name="الوقت الآن (Lisbon)", value=f"`{time_str}`", inline=True)
    embed.add_field(name="اليوم المنطقي (get_active_report_date)", value=f"`{logical_day}`", inline=False)
    embed.add_field(name="قيمة state['logical_day_key']", value=f"`{logical_state}`", inline=False)
    embed.add_field(name="آخر نشاط مسجل (last_activity_time)", value=f"`{last_act_str}`", inline=False)
    embed.set_footer(text=f"التوقيت المرجعي: {tz_info}")
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


def split_intervals_by_date(start_dt, end_dt):
    """Split an interval into (date_key, seg_start, seg_end, seconds) for each calendar date.
    Both start_dt and end_dt must be timezone-aware in Europe/Lisbon."""
    parts = []
    if not start_dt or not end_dt or end_dt <= start_dt:
        return parts
    current = start_dt
    tz = ZoneInfo("Europe/Lisbon")
    while current < end_dt:
        next_midnight = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), tzinfo=tz)
        seg_end = min(end_dt, next_midnight)
        date_key = get_date_str(current)
        seconds = int((seg_end - current).total_seconds())
        parts.append((date_key, current, seg_end, seconds))
        current = seg_end
    return parts


def record_timeline_session(start_dt, end_dt):
    """Record online timeline session, splitting across calendar dates into daily_timeline_collection."""
    if not start_dt or not end_dt or end_dt <= start_dt:
        return
    try:
        segments = split_intervals_by_date(start_dt, end_dt)
        now = datetime.now(ZoneInfo("Europe/Lisbon"))
        for date_key, seg_start, seg_end, seconds in segments:
            try:
                # Read existing sessions for the date
                doc = daily_timeline_collection.find_one({"_id": date_key}) or {}
                existing = doc.get("sessions", [])

                # Build list of intervals in seconds for merging
                intervals = []
                for s in existing:
                    try:
                        sst = s.get("start_time")
                        sed = s.get("end_time")
                        if sst and sed:
                            intervals.append((int(sst.timestamp()), int(sed.timestamp())))
                    except Exception:
                        continue

                # Append new segment
                intervals.append((int(seg_start.timestamp()), int(seg_end.timestamp())))

                # Merge intervals
                intervals.sort(key=lambda x: x[0])
                merged = []
                for iv in intervals:
                    if not merged:
                        merged.append(list(iv))
                    else:
                        last = merged[-1]
                        if iv[0] <= last[1]:
                            # overlap or adjacent -> merge
                            last[1] = max(last[1], iv[1])
                        else:
                            merged.append([iv[0], iv[1]])

                # Reconstruct sessions list and total seconds
                new_sessions = []
                total_seconds = 0
                for a, b in merged:
                    st_dt = datetime.fromtimestamp(a, tz=ZoneInfo("Europe/Lisbon"))
                    ed_dt = datetime.fromtimestamp(b, tz=ZoneInfo("Europe/Lisbon"))
                    dur = int(b - a)
                    total_seconds += dur
                    new_sessions.append({"start_time": st_dt, "end_time": ed_dt, "duration_seconds": dur})

                # Update document atomically (replace sessions + total_online_seconds)
                daily_timeline_collection.update_one(
                    {"_id": date_key},
                    {
                        "$set": {"sessions": new_sessions, "total_online_seconds": total_seconds},
                        "$setOnInsert": {"created_at": now}
                    },
                    upsert=True
                )
            except Exception as e:
                print(f"Error recording timeline segment for {date_key}: {e}")
    except Exception as e:
        print(f"Error recording timeline session: {e}")


def build_daily_timeline_embeds(date_key, include_open_session=False):
    """Build embeds for a given logical date_key (YYYY-MM-DD).
    This will aggregate sessions from the calendar date document and the next calendar date,
    then clip/merge them to the logical-day interval for `date_key`.
    If include_open_session=True, include any current open session portion up to Now.
    The date_key passed is authoritative — do NOT override with calendar date.
    """
    tz = ZoneInfo("Europe/Lisbon")
    try:
        day = datetime.strptime(date_key, "%Y-%m-%d").date()
    except Exception:
        # If invalid date_key is passed, log error but use provided key as-is
        print(f"Invalid date_key format: {date_key}")
        raise

    day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
    now = datetime.now(tz)
    # Determine logical-day end: if active day, use now; otherwise check stored logical_close_at
    if state.get("logical_day_key") == date_key:
        day_end = now
    else:
        # If this logical day was previously closed, use persisted close timestamp
        stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
        lc = stats_doc.get("logical_close_at")
        if lc:
            day_end = _make_aware(lc)
        else:
            day_end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)

    date_display = day.strftime("%d/%m/%Y")

    sessions = []
    total_online = 0

    def process_doc(doc):
        nonlocal sessions, total_online
        for s in doc.get("sessions", []):
            try:
                st = _make_aware(s.get("start_time"))
                ed_raw = s.get("end_time")
                ed = _make_aware(ed_raw) if ed_raw else None

                # Clip to logical-day interval
                seg_start = st if st and st >= day_start else day_start
                seg_end = ed if ed and ed <= day_end else (day_end if ed else (now if state.get("logical_day_key") == date_key else None))
                if seg_end is None:
                    # no valid end for historical closed day -> skip
                    continue
                if seg_end <= seg_start:
                    continue
                dur = int((seg_end - seg_start).total_seconds())
                total_online += dur
                # Mark as open if original had no end and we're including up-to-now
                is_open = (ed_raw is None) and (state.get("logical_day_key") == date_key)
                sessions.append({"start_time": seg_start, "end_time": (None if is_open else seg_end), "duration_seconds": dur})
            except Exception:
                continue

    # Load calendar docs for the day and the next calendar day (to capture early-morning segments)
    # For logical day boundaries, we need both the start calendar day and next calendar day
    # to handle sessions that cross midnight.
    doc1 = daily_timeline_collection.find_one({"_id": date_key}) or {}
    include_next_day = state.get("logical_day_key") == date_key
    if not include_next_day:
        stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
        lc = stats_doc.get("logical_close_at")
        if lc and _make_aware(lc).date() > day:
            include_next_day = True

    if include_next_day:
        doc2 = daily_timeline_collection.find_one({"_id": (day + timedelta(days=1)).strftime("%Y-%m-%d")}) or {}
        process_doc(doc1)
        process_doc(doc2)
    else:
        process_doc(doc1)

    # Optionally include any current open session portion overlapping this logical day
    if include_open_session and state.get("timeline_current_session_start"):
        try:
            start = _make_aware(state.get("timeline_current_session_start"))
            seg_start = start if start >= day_start else day_start

            include_now = False
            if state.get("status") in [1, 2, 3]:
                include_now = True
            else:
                loff = state.get("timeline_last_offline_time")
                if loff:
                    loff_a = _make_aware(loff)
                    if (now - loff_a) < timedelta(minutes=30):
                        include_now = True

            if include_now and seg_start < day_end:
                # Determine seg_end carefully: if user is currently online, include up-to-now.
                # If user is offline, do NOT include any time past the last known online instant
                # (this prevents counting 2h/4h grace or waiting windows).
                last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
                if state.get("status") in [1, 2, 3]:
                    seg_end = now if state.get("logical_day_key") == date_key else min(now, day_end)
                    is_open = True
                else:
                    # offline: clip to last_online if available, otherwise skip including
                    if last_online:
                        seg_end = last_online if last_online <= day_end else day_end
                    else:
                        seg_end = None
                    is_open = False

                if seg_end and seg_end > seg_start:
                    dur = int((seg_end - seg_start).total_seconds())
                    total_online += dur
                    sessions.append({"start_time": seg_start, "end_time": (None if is_open else seg_end), "duration_seconds": dur, "_open": is_open})
        except Exception:
            pass

    # Sort sessions by start_time
    sessions_sorted = sorted(sessions, key=lambda x: x.get("start_time") or datetime.min)

    if not sessions_sorted:
        embed = discord.Embed(title=f"📅 Daily Online Timeline — {date_display}", description="No sessions recorded for this day.", color=0x3498db)
        embed.add_field(name="⏰ Total Online", value=f"**{format_seconds(total_online)}**", inline=False)
        embed.add_field(name="📊 Sessions Count", value="0", inline=False)
        return [embed]

    embeds = []
    current_embed = discord.Embed(title=f"📅 Daily Online Timeline — {date_display}", color=0x3498db)
    current_embed.add_field(name="⏰ Total Online", value=f"**{format_seconds(total_online)}**", inline=False)

    fields_added = 0
    session_count = 0
    for s in sessions_sorted:
        session_count += 1
        st = s.get("start_time")
        ed = s.get("end_time")
        dur = s.get("duration_seconds", 0)
        try:
            st_str = st.strftime("%I:%M %p") if st else "Unknown"
            if ed:
                ed_str = ed.strftime("%I:%M %p")
            else:
                ed_str = "Now"
        except Exception:
            st_str = str(st)
            ed_str = str(ed) if ed else "Now"

        current_embed.add_field(name=f"Session #{session_count}", value=f"{st_str} → {ed_str}\nDuration: {format_seconds(dur)}", inline=False)
        fields_added += 1
        if fields_added >= 10:
            embeds.append(current_embed)
            current_embed = discord.Embed(title=f"📅 Daily Online Timeline — {date_display} (continued)", color=0x3498db)
            fields_added = 0

    # Footer info
    current_embed.add_field(name="Total Online", value=f"**{format_seconds(total_online)}**", inline=True)
    current_embed.add_field(name="Sessions Count", value=f"{session_count}", inline=True)
    embeds.append(current_embed)
    return embeds


async def send_daily_timeline(date_key):
    channel = bot.get_channel(TIMELINE_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(TIMELINE_CHANNEL_ID)
        except Exception as e:
            print(f"Error fetching timeline channel: {e}")
            return
    embeds = build_daily_timeline_embeds(date_key)
    try:
        for e in embeds:
            await channel.send(embed=e)
    except Exception as e:
        print(f"Error sending timeline embeds: {e}")


def build_precise_stats_embed(date_key=None):
    """Build precise real-time stats embed for a logical date_key.
    Excludes any grace/wait windows; computes actual online time from timeline docs
    and map sessions directly from `session_logs` (clipped to the logical-day interval).
    Always uses the logical day key, never auto-switches to calendar date.
    """
    tz = ZoneInfo("Europe/Lisbon")
    # Use logical day key for stats, not calendar date
    date_key = date_key or state.get("logical_day_key") or get_active_report_date()
    try:
        day = datetime.strptime(date_key, "%Y-%m-%d").date()
    except Exception:
        print(f"Invalid date_key format: {date_key}")
        day = datetime.now(tz).date()

    day_start = datetime.combine(day, dt_time.min, tzinfo=tz)
    # Determine logical-day end: if active day, use now; otherwise check persisted close
    now = datetime.now(tz)
    if state.get("logical_day_key") == date_key:
        day_end = now
    else:
        stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
        lc = stats_doc.get("logical_close_at")
        if lc:
            day_end = _make_aware(lc)
        else:
            day_end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz)

    timeline_segments = get_logical_day_timeline_segments(date_key)
    total_online = sum(int((end - start).total_seconds()) for start, end in timeline_segments)

    inside_segments = get_logical_day_inside_segments(date_key)
    inside_seconds = compute_segment_overlap(timeline_segments, inside_segments)
    outside_seconds = total_online - inside_seconds
    if outside_seconds < 0:
        outside_seconds = 0

    date_display = day.strftime("%d/%m/%Y")
    embed = discord.Embed(title=f"📈 Precise Stats — {date_display}", color=0x1abc9c)
    embed.add_field(name="⛳ Inside Maps (real)", value=f"**{format_seconds(inside_seconds)}**", inline=False)
    embed.add_field(name="🌐 Outside Maps (real)", value=f"**{format_seconds(outside_seconds)}**", inline=False)
    embed.add_field(name="🕒 Total Online (real)", value=f"**{format_seconds(total_online)}**", inline=False)
    embed.set_footer(text="Real-time metrics — excludes grace/wait windows")
    return embed


async def send_precise_stats(date_key=None):
    channel = bot.get_channel(PRECISE_STATS_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(PRECISE_STATS_CHANNEL_ID)
        except Exception as e:
            print(f"Error fetching precise stats channel: {e}")
            return
    embed = build_precise_stats_embed(date_key)
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending precise stats embed: {e}")


def normalize_timeline_session_start_for_current_day(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Lisbon"))
    if not state.get("timeline_current_session_start"):
        return
    start = _make_aware(state.get("timeline_current_session_start"))
    if not start:
        return
    midnight = datetime.combine(now.date(), dt_time.min, tzinfo=ZoneInfo("Europe/Lisbon"))
    if start >= midnight:
        return

    last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
    loff = _make_aware(state.get("timeline_last_offline_time")) if state.get("timeline_last_offline_time") else None
    record_end = midnight
    if state.get("status") not in [1, 2, 3]:
        # If offline now, prefer the last known valid online instant for closing the old session.
        if last_online and last_online >= start and last_online <= midnight:
            record_end = last_online
        elif loff and loff > start and loff <= midnight:
            record_end = loff

    if record_end and record_end > start:
        record_timeline_session(start, record_end)

    if state.get("status") in [1, 2, 3]:
        state["timeline_current_session_start"] = midnight
        if loff and loff < midnight:
            state["timeline_last_offline_time"] = None
    else:
        state["timeline_current_session_start"] = None
        state["timeline_last_offline_time"] = None
    save_state_data()

@tasks.loop(time=dt_time(0, 0, 0, tzinfo=ZoneInfo("Europe/Lisbon")))
async def daily_timeline_task():
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    # Close any crossing session at midnight: record portion up to midnight for yesterday
    midnight = datetime.combine(now.date(), dt_time.min, tzinfo=ZoneInfo("Europe/Lisbon"))
    yesterday = midnight - timedelta(days=1)
    # If there's an open timeline session that started before midnight, record its part until midnight
    try:
        if state.get("timeline_current_session_start"):
            start = _make_aware(state.get("timeline_current_session_start"))
            if start and start < midnight:
                # If the user is offline at midnight, do not count the offline gap as online time.
                # Close yesterday's segment at the last known online instant or the offline marker.
                record_end = midnight
                if state.get("status") not in [1, 2, 3]:
                    last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
                    loff = _make_aware(state.get("timeline_last_offline_time")) if state.get("timeline_last_offline_time") else None
                    if last_online and last_online > start and last_online <= midnight:
                        record_end = last_online
                    elif loff and loff > start and loff <= midnight:
                        record_end = loff

                if record_end and record_end > start:
                    record_timeline_session(start, record_end)

                if state.get("status") in [1, 2, 3]:
                    state["timeline_current_session_start"] = midnight
                else:
                    state["timeline_current_session_start"] = None
                    # Preserve the offline marker for the merge window if the user resumes shortly after midnight.
                    # Do not reset timeline_last_offline_time here; let the resume logic decide when to continue the session.
                save_state_data()
    except Exception as e:
        print(f"Error handling open timeline session at midnight: {e}")

    # Send timeline for the logical report date (align with daily summary / logical day)
    # Use the actual logical day key, NOT the calendar date (which may have changed at midnight)
    date_key = state.get("logical_day_key") or get_active_report_date()
    await send_daily_timeline(date_key)


async def maybe_close_logical_day(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Lisbon"))
    if state["status"] != 0 or not state.get("logical_day_key"):
        return

    deadline = get_logical_day_close_deadline(now)
    if not deadline or now < deadline:
        return

    closed_day_key = state["logical_day_key"]
    # Use only the last known online timestamp as the end boundary.
    # Do NOT use `now` as a fallback — that would include grace/wait windows.
    end_time = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None

    # Prefer recording timeline using timeline_current_session_start; fallback to
    # online_session_start if timeline marker is missing. Only record if we have
    # a valid end_time (last known online instant).
    try:
        t_start_raw = state.get("timeline_current_session_start") or state.get("online_session_start")
        if t_start_raw and end_time:
            tstart = _make_aware(t_start_raw)
            tend = end_time
            if tstart and tend and tend > tstart:
                record_timeline_session(tstart, tend)
        # Clear timeline markers (we've persisted the final piece)
        state["timeline_current_session_start"] = None
        state["timeline_last_offline_time"] = None
        save_state_data()
    except Exception as e:
        print(f"Error recording final timeline segment at close: {e}")

    # If we have an end_time, rebuild the authoritative online_seconds for the closed
    # logical day from the stored timeline (this ensures grace/wait windows never count).
    if end_time and state.get("online_session_start"):
        try:
            # Recompute online seconds from timeline and persist into daily_stats
            update_daily_online(state["online_session_start"], end_time, date_key=closed_day_key)
            # Persist logical close time so historical timeline queries can clip properly
            daily_stats_collection.update_one({"_id": closed_day_key}, {"$set": {"logical_close_at": end_time}}, upsert=True)
        except Exception as e:
            print(f"Error updating daily online from timeline at close: {e}")
        finally:
            state["online_session_start"] = None

    # Determine whether this was a 2-hour grace (activity after midnight)
    # or a 4-hour midnight waiting window (no activity after midnight)
    midnight = datetime.combine(now.date(), dt_time.min, tzinfo=ZoneInfo("Europe/Lisbon"))
    last_activity = state.get("last_activity_time")
    grace_hours = 2
    if last_activity:
        la = _make_aware(last_activity)
        if la < midnight:
            grace_hours = 4
    else:
        grace_hours = 4

    if grace_hours == 2:
        desc_line = f"اللاعب بقي أوفلاين لمدة ساعتين بعد آخر نشاط بعد منتصف الليل.\n"
    else:
        desc_line = f"اللاعب لم يعد خلال نافذة الانتظار لمدة 4 ساعات بعد منتصف الليل.\n"

    embed = discord.Embed(
        title="🔴 [الهدف أوفلاين الآن - اليوم انتهى]",
        description=(
            desc_line +
            f"آخر نشاط: {state['last_activity_time'].strftime('%I:%M:%S %p') if state.get('last_activity_time') else 'Unknown'}\n\n"
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
    # Send precise, real-time-only stats to the dedicated channel
    try:
        await send_precise_stats(closed_day_key)
    except Exception as e:
        print(f"Error sending precise stats: {e}")

    # Notify avatar change count for the closed logical day in the avatar channel
    try:
        avatar_doc = daily_stats_collection.find_one({"_id": closed_day_key}) or {}
        avatar_changes_count = avatar_doc.get("avatar_changes", 0)
        avatar_channel = bot.get_channel(AVATAR_CHANGE_CHANNEL_ID)
        if avatar_channel is None:
            try:
                avatar_channel = await bot.fetch_channel(AVATAR_CHANGE_CHANNEL_ID)
            except Exception as e:
                avatar_channel = None
                print(f"Error fetching avatar channel for day close: {e}")

        if avatar_channel:
            try:
                date_display = datetime.strptime(closed_day_key, "%Y-%m-%d").strftime("%d/%m/%Y")
                embed_avatar_summary = discord.Embed(
                    title=f"📸 تغييرات الأفاتار ليوم {date_display}",
                    description=f"عدد تغييرات الأفاتار المسجلة خلال اليوم: **{avatar_changes_count}**",
                    color=0x3498db
                )
                embed_avatar_summary.set_footer(text="تم الإرسال عند نهاية اليوم المنطقي")
                await avatar_channel.send(embed=embed_avatar_summary)
            except Exception as e:
                print(f"Error sending avatar day summary: {e}")
    except Exception as e:
        print(f"Error preparing avatar day summary: {e}")

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
        date_key = state.get("logical_day_key") or get_active_report_date()
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


@bot.command(name="timeline")
async def cmd_timeline(ctx):
    """عرض الـ Daily Online Timeline لليوم الميلادي الحالي (فقط في قناة الـ Timeline)."""
    if ctx.channel.id != TIMELINE_CHANNEL_ID:
        await ctx.send("❌ هذا الأمر مسموح فقط في قناة سجل الأونلاين اليومية.")
        return

    # Use logical day (same as daily summary / online today)
    # Always use the logical day key, never auto-switch to calendar date
    date_key = state.get("logical_day_key") or get_active_report_date()
    embeds = build_daily_timeline_embeds(date_key, include_open_session=True)
    try:
        for e in embeds:
            await ctx.send(embed=e)
    except Exception as e:
        await ctx.send(f"❌ خطأ أثناء إرسال التقرير: {e}")


@bot.command(name="debugonline")
async def cmd_debug_online(ctx, date_arg: str = None):
    """Diagnostic debug report for logical-day timeline/session totals."""
    if date_arg is None:
        await ctx.send("❌ استخدم: `!debugonline YYYY-MM-DD`")
        return

    try:
        report_date = datetime.strptime(date_arg, "%Y-%m-%d").date()
    except Exception:
        await ctx.send("❌ تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD")
        return

    tz = ZoneInfo("Europe/Lisbon")
    day_start = datetime.combine(report_date, dt_time.min, tzinfo=tz)
    now = datetime.now(tz)
    is_active_logical_day = state.get("logical_day_key") == date_arg

    stats_doc = daily_stats_collection.find_one({"_id": date_arg}) or {}
    logical_close_at = stats_doc.get("logical_close_at")
    if is_active_logical_day:
        day_end = now
    elif logical_close_at:
        day_end = _make_aware(logical_close_at)
    else:
        day_end = datetime.combine(report_date + timedelta(days=1), dt_time.min, tzinfo=tz)

    # Load relevant timeline docs
    docs = []
    doc1 = daily_timeline_collection.find_one({"_id": date_arg})
    if doc1:
        docs.append(doc1)
    if is_active_logical_day:
        next_doc = daily_timeline_collection.find_one({"_id": (report_date + timedelta(days=1)).strftime("%Y-%m-%d")})
        if next_doc:
            docs.append(next_doc)

    timeline_sessions = []
    timeline_total = 0
    timeline_warnings = []

    def to_str(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "None"

    for doc in docs:
        for s in doc.get("sessions", []):
            st = _make_aware(s.get("start_time"))
            ed_raw = s.get("end_time")
            ed = _make_aware(ed_raw) if ed_raw else None
            if ed is None:
                if is_active_logical_day:
                    ed = now
                else:
                    continue

            seg_start = st if st and st >= day_start else day_start
            seg_end = ed if ed and ed <= day_end else day_end
            if not seg_start or not seg_end or seg_end <= seg_start:
                timeline_warnings.append(f"Impossible timeline segment: start={to_str(st)} end={to_str(ed)}")
                continue

            duration = int((seg_end - seg_start).total_seconds())
            if duration < 0 or duration > 86400:
                timeline_warnings.append(f"Suspicious timeline duration {duration}s for {to_str(seg_start)} -> {to_str(seg_end)}")

            timeline_sessions.append({
                "start": seg_start,
                "end": seg_end,
                "duration": duration,
                "source_doc": doc.get("_id")
            })
            timeline_total += duration

    # Current open timeline portion if active day and applicable
    open_session = None
    if is_active_logical_day and state.get("timeline_current_session_start"):
        tstart = _make_aware(state.get("timeline_current_session_start"))
        loff = state.get("timeline_last_offline_time")
        include_now = False
        if state.get("status") in [1, 2, 3]:
            include_now = True
        elif loff:
            loff_a = _make_aware(loff)
            if (now - loff_a) < timedelta(minutes=30):
                include_now = True

        if include_now:
            seg_start = tstart if tstart and tstart >= day_start else day_start
            last_online = _make_aware(state.get("last_online_time")) if state.get("last_online_time") else None
            if state.get("status") in [1, 2, 3]:
                seg_end = now
            else:
                seg_end = last_online if last_online and last_online <= day_end else day_end if last_online else None

            if seg_end and seg_end > seg_start:
                open_session = {
                    "start": seg_start,
                    "end": seg_end,
                    "duration": int((seg_end - seg_start).total_seconds())
                }

    precise_total = timeline_total + (open_session["duration"] if open_session else 0)

    # Load session logs overlapping the logical day interval
    log_cursor = session_logs.find({"start_time": {"$lt": day_end}, "end_time": {"$gt": day_start}})
    session_log_records = []
    session_logs_total = 0
    session_logs_inside = 0
    log_warnings = []

    for s in log_cursor:
        st = _make_aware(s.get("start_time"))
        ed = _make_aware(s.get("end_time"))
        if not st or not ed:
            log_warnings.append(f"Invalid session log times: {s}")
            continue

        raw_duration = int((ed - st).total_seconds())
        seg_start = st if st >= day_start else day_start
        seg_end = ed if ed <= day_end else day_end
        if seg_end <= seg_start:
            log_warnings.append(f"Session log does not overlap day: {s.get('game_name')} {to_str(st)} -> {to_str(ed)}")
            continue

        clipped_duration = int((seg_end - seg_start).total_seconds())
        session_logs_total += clipped_duration
        if s.get("place_id") is not None:
            session_logs_inside += clipped_duration

        session_log_records.append({
            "game_name": s.get("game_name"),
            "place_id": s.get("place_id"),
            "start": st,
            "end": ed,
            "raw_duration": raw_duration,
            "clipped_duration": clipped_duration
        })

    session_logs_outside = precise_total - session_logs_inside
    if session_logs_outside < 0:
        session_logs_outside = 0

    # Validate timeline sessions for overlaps/duplicates
    timeline_sessions_sorted = sorted(timeline_sessions, key=lambda x: x["start"])
    overlap_warnings = []
    duplicate_warnings = []
    seen_tuples = set()
    prev_end = None
    for sess in timeline_sessions_sorted:
        key = (sess["start"], sess["end"], sess["duration"])
        if key in seen_tuples:
            duplicate_warnings.append(f"Duplicate timeline session: {to_str(sess['start'])} -> {to_str(sess['end'])} ({sess['duration']}s)")
        seen_tuples.add(key)
        if prev_end and sess["start"] < prev_end:
            overlap_warnings.append(f"Overlap: {to_str(sess['start'])} starts before previous end {to_str(prev_end)}")
        prev_end = sess["end"] if prev_end is None or sess["end"] > prev_end else prev_end

    # Validate duplicated session logs
    seen_logs = set()
    duplicate_log_warnings = []
    for rec in session_log_records:
        key = (rec["game_name"], rec["place_id"], rec["start"], rec["end"], rec["clipped_duration"])
        if key in seen_logs:
            duplicate_log_warnings.append(f"Duplicate session log: {rec['game_name']} | {rec['place_id']} | {to_str(rec['start'])} -> {to_str(rec['end'])} ({rec['clipped_duration']}s)")
        seen_logs.add(key)

    warning_lines = []
    warning_lines.extend(timeline_warnings)
    warning_lines.extend(log_warnings)
    warning_lines.extend(overlap_warnings)
    warning_lines.extend(duplicate_warnings)
    warning_lines.extend(duplicate_log_warnings)

    # Build report
    report_lines = [
        f"=== DEBUG ONLINE REPORT for {date_arg} ===",
        f"logical_day_key: {state.get('logical_day_key')}",
        f"is_active_logical_day: {is_active_logical_day}",
        f"date_key: {date_arg}",
        f"day_start: {to_str(day_start)}",
        f"day_end: {to_str(day_end)}",
        "",
        f"1. daily_timeline_collection docs: {len(docs)}",
        f"2. Number of merged timeline sessions: {len(timeline_sessions)}",
        f"3. Total duration from timeline sessions: {timeline_total}s ({format_seconds(timeline_total)})",
        f"4. Timeline sessions:",
    ]

    timeline_lines = []
    for idx, sess in enumerate(timeline_sessions_sorted, start=1):
        timeline_lines.append(f"  {idx}. {to_str(sess['start'])} -> {to_str(sess['end'])} | {sess['duration']}s ({format_seconds(sess['duration'])}) | doc={sess['source_doc']}")
    if open_session:
        report_lines.append(f"   - open current session portion included: {open_session['duration']}s ({format_seconds(open_session['duration'])})")

    summary_total = compute_logical_day_timeline_total(date_arg)
    report_lines.extend([
        "",
        f"5. session_logs records overlapping day: {len(session_log_records)}",
        f"6. Total clipped duration from session_logs: {session_logs_total}s ({format_seconds(session_logs_total)})",
        f"7. Total clipped duration from session_logs with place_id != null (Inside Maps): {session_logs_inside}s ({format_seconds(session_logs_inside)})",
        f"8. Session logs:",
    ])

    session_log_lines = []
    for idx, rec in enumerate(session_log_records, start=1):
        session_log_lines.append(
            f"  {idx}. {rec['game_name']} | {rec['place_id']} | {to_str(rec['start'])} -> {to_str(rec['end'])} | raw={rec['raw_duration']}s clipped={rec['clipped_duration']}s"
        )

    report_lines.extend([
        "",
        f"9. daily_stats.online_seconds: {stats_doc.get('online_seconds')}",
        f"10. daily_stats.games_time_seconds: {stats_doc.get('games_time_seconds')}",
        f"11. daily_stats.session_count: {stats_doc.get('session_count')}",
        f"12. daily_stats.logical_close_at: {to_str(_make_aware(logical_close_at)) if logical_close_at else 'None'}",
        "",
        f"13. date_key: {date_arg}",
        "",
        f"14. Precise Stats exact Total Online: {precise_total}s ({format_seconds(precise_total)})",
        f"15. Exact Inside Maps: {session_logs_inside}s ({format_seconds(session_logs_inside)})",
        f"16. Exact Outside Maps: {session_logs_outside}s ({format_seconds(session_logs_outside)})",
        f"17. Outside = Total - Inside: {precise_total}s - {session_logs_inside}s = {session_logs_outside}s",
        "",
        "18. Timeline validation:",
    ])

    if overlap_warnings or duplicate_warnings:
        report_lines.append(f"  Overlaps: {len(overlap_warnings)} | Duplicates: {len(duplicate_warnings)}")
    else:
        report_lines.append("  No timeline overlap or duplicate warnings found.")
    report_lines.append("19. Duplicated session logs: " + (str(len(duplicate_log_warnings)) if duplicate_log_warnings else "0"))
    report_lines.append("20. Impossible durations warnings: " + str(len(timeline_warnings) + len(log_warnings)))
    report_lines.append("21. Warnings:")
    if warning_lines:
        report_lines.extend([f"  - {w}" for w in warning_lines])
    else:
        report_lines.append("  None")
    cached_total = stats_doc.get('online_seconds', 0)
    summary_match = (summary_total == timeline_total == precise_total)
    report_lines.extend([
        "",
        "22. Final comparison:",
        f"   Timeline Total: {timeline_total}s ({format_seconds(timeline_total)})",
        f"   Session Logs Total: {session_logs_total}s ({format_seconds(session_logs_total)})",
        f"   Precise Stats Total: {precise_total}s ({format_seconds(precise_total)})",
        f"   Summary Total: {summary_total}s ({format_seconds(summary_total)})",
        f"   Cached daily_stats.online_seconds: {cached_total}s ({format_seconds(cached_total)})",
        f"   Difference Timeline vs Precise: {precise_total - timeline_total}s ({format_seconds(abs(precise_total - timeline_total))})",
        f"   Difference Timeline vs Session Logs: {session_logs_total - timeline_total}s ({format_seconds(abs(session_logs_total - timeline_total))})",
        f"   Summary matches Timeline+Precise: {'YES' if summary_match else 'NO'}",
    ])

    # Send the report in chunks if needed
    def chunk_lines(lines, max_size=1900):
        chunk = []
        size = 0
        for line in lines:
            if size + len(line) + 1 > max_size:
                yield chunk
                chunk = []
                size = 0
            chunk.append(line)
            size += len(line) + 1
        if chunk:
            yield chunk

    await ctx.send("```\n" + "\n".join(report_lines) + "\n```")

    if timeline_lines:
        for chunk in chunk_lines(["Timeline sessions:"] + timeline_lines):
            await ctx.send("```\n" + "\n".join(chunk) + "\n```")

    if session_log_lines:
        for chunk in chunk_lines(["Session logs:"] + session_log_lines):
            await ctx.send("```\n" + "\n".join(chunk) + "\n```")


@bot.command(name="rebuildsummary")
async def cmd_rebuild_summary(ctx, date_arg: str = None):
    """Repair the cached daily_stats.online_seconds value from the authoritative timeline."""
    if date_arg is None:
        await ctx.send("❌ استخدم: `!rebuildsummary YYYY-MM-DD`")
        return

    try:
        date_key = datetime.strptime(date_arg, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        await ctx.send("❌ تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD")
        return

    try:
        update_daily_online(None, None, date_key=date_key)
        computed_total = compute_logical_day_timeline_total(date_key)
        stats_doc = daily_stats_collection.find_one({"_id": date_key}) or {}
        cached_total = stats_doc.get("online_seconds", 0)
        await ctx.send(
            "✅ Rebuilt summary total for {}.\n"
            "Timeline-based total: {} ({})\n"
            "Cached daily_stats.online_seconds: {} ({})\n"
            "Summary total is now authoritative from timeline.\n"
            .format(
                date_key,
                computed_total,
                format_seconds(computed_total),
                cached_total,
                format_seconds(cached_total)
            )
        )
    except Exception as e:
        await ctx.send(f"❌ خطأ أثناء إعادة بناء الملخص: {e}")


@bot.command(name="precisestats")
async def cmd_precise_stats(ctx, date_arg: str = None):
    """عرض تقرير الإحصائيات الدقيقة في القناة المخصصة (Real-time only)."""
    if ctx.channel.id != PRECISE_STATS_CHANNEL_ID:
        await ctx.send("❌ هذا الأمر مسموح فقط في قناة إحصائيات الدقة.")
        return

    if date_arg:
        try:
            datetime.strptime(date_arg, "%Y-%m-%d")
            date_key = date_arg
        except Exception:
            await ctx.send("❌ تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD")
            return
    else:
        # Use logical day, not calendar date
        date_key = state.get("logical_day_key") or get_active_report_date()

    embed = build_precise_stats_embed(date_key)
    try:
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ خطأ أثناء إرسال الإحصائيات: {e}")

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
        date_key = state.get("logical_day_key") or get_active_report_date()
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
    normalize_timeline_session_start_for_current_day(now)
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
                        # Compute image hash for robust detection
                        current_avatar_hash = await fetch_image_hash(session, current_avatar_url)

                        # First run: store last avatar URL+hash silently
                        if state.get("last_avatar_url") is None and not state.get("last_avatar_hash"):
                            state["last_avatar_url"] = current_avatar_url
                            state["last_avatar_hash"] = current_avatar_hash
                        else:
                            changed = False
                            try:
                                # Prefer hash comparison when available to avoid CDN/URL churn
                                last_hash = state.get("last_avatar_hash")
                                if last_hash and current_avatar_hash:
                                    changed = (last_hash != current_avatar_hash)
                                else:
                                    last_url = state.get("last_avatar_url")
                                    if last_url and current_avatar_url:
                                        changed = (last_url != current_avatar_url)
                            except Exception:
                                changed = False

                            if changed:
                                # Increment daily avatar change counter (logical day)
                                try:
                                    logical_day = state.get("logical_day_key") or get_active_report_date()
                                    daily_stats_collection.update_one(
                                        {"_id": logical_day},
                                        {"$inc": {"avatar_changes": 1}},
                                        upsert=True
                                    )
                                except Exception as e:
                                    print(f"Error incrementing avatar_changes: {e}")

                                # Classify whether change happened after >=5 minutes offline
                                changed_while_offline_long = False
                                if status == 0:
                                    ref_time = state.get("offline_since") or state.get("last_online_time")
                                    if ref_time:
                                        ref_time = _make_aware(ref_time)
                                        try:
                                            offline_delta = now - ref_time
                                        except Exception:
                                            offline_delta = timedelta(seconds=0)
                                        if offline_delta >= timedelta(minutes=5):
                                            changed_while_offline_long = True

                                # Prepare embed with the new avatar image and timestamp and classification
                                avatar_time = datetime.now(ZoneInfo("Europe/Lisbon"))
                                avatar_time_str = avatar_time.strftime("%Y-%m-%d %I:%M %p")
                                embed_avatar = discord.Embed(
                                    title="🎭 [تغيير الأفاتار]",
                                    description=f"اللاعب غيّر الأفاتار\nالتوقيت: {avatar_time_str} (Europe/Lisbon)",
                                    color=0x9b59b6
                                )
                                embed_avatar.add_field(name="التوقيت", value=f"`{avatar_time_str}`", inline=True)

                                if changed_while_offline_long:
                                    offline_since = state.get("offline_since") or state.get("last_online_time")
                                    if offline_since:
                                        offline_since = _make_aware(offline_since)
                                        offline_dur_secs = int((now - offline_since).total_seconds())
                                        embed_avatar.add_field(name="الحالة أثناء التغيير", value=f"🔴 أوفلاين منذ **{format_seconds(offline_dur_secs)}**", inline=True)
                                    else:
                                        embed_avatar.add_field(name="الحالة أثناء التغيير", value="🔴 أوفلاين (مدة غير معروفة)", inline=True)
                                else:
                                    # Online now or recently online (<=5min)
                                    if status in [1,2,3]:
                                        embed_avatar.add_field(name="الحالة أثناء التغيير", value="🟢 أونلاين", inline=True)
                                    else:
                                        ref_time = state.get("offline_since") or state.get("last_online_time")
                                        if ref_time:
                                            ref_time = _make_aware(ref_time)
                                            seconds_since = int((now - ref_time).total_seconds())
                                            embed_avatar.add_field(name="الحالة أثناء التغيير", value=f"🟢 كان أونلاين قبل **{format_seconds(seconds_since)}**", inline=True)
                                        else:
                                            embed_avatar.add_field(name="الحالة أثناء التغيير", value="🟢 أونلاين (مؤكد)", inline=True)

                                try:
                                    if current_avatar_url:
                                        embed_avatar.set_image(url=current_avatar_url)
                                except Exception:
                                    pass

                                # Send to the dedicated avatar-change channel
                                avatar_channel = bot.get_channel(AVATAR_CHANGE_CHANNEL_ID)
                                if avatar_channel is None:
                                    try:
                                        avatar_channel = await bot.fetch_channel(AVATAR_CHANGE_CHANNEL_ID)
                                    except Exception as e:
                                        avatar_channel = None
                                        print(f"Error fetching avatar channel: {e}")

                                if avatar_channel:
                                    try:
                                        await avatar_channel.send(embed=embed_avatar)
                                    except Exception as e:
                                        print(f"Error sending avatar change embed: {e}")

                                # If change happened while offline, also send the privacy-style alert to alert_channel
                                if status == 0 and not state.get("privacy_alert_sent"):
                                    embed_privacy = discord.Embed(
                                        title="⚠️ [تحذير: تغيير الأفاتار أثناء الأوفلاين]",
                                        description="يبدو أن الهدف غيّر الأفاتار وهو في وضع عدم الظهور، قد يكون مخفي أونلاين رغم ظهوره كأوفلاين.",
                                        color=0xe74c3c
                                    )
                                    embed_privacy.add_field(name="⛔ الحالة الحالية", value="أوفلاين رسميًا لكن الأفاتار تغير", inline=False)
                                    embed_privacy.add_field(name="🧠 معنى ذلك", value="ممكن يكون المستخدم مستخدم الوضع الخاص لإخفاء ظهور الأونلاين.", inline=False)
                                    embed_privacy.add_field(name="🌐 رابط الأفاتار الجديد", value=current_avatar_url, inline=False)
                                    try:
                                        await alert_channel.send(embed=embed_privacy)
                                    except Exception as e:
                                        print(f"Error sending privacy embed: {e}")
                                    state["privacy_alert_sent"] = True

                                # Update stored avatar URL and hash and reset privacy flag if user is online
                                state["last_avatar_url"] = current_avatar_url
                                state["last_avatar_hash"] = current_avatar_hash
                                if status != 0:
                                    state["privacy_alert_sent"] = False

                    if state["pending_resume"] and state["pending_resume_leave_time"] and status != 2:
                        if now - state["pending_resume_leave_time"] > timedelta(minutes=10) and not state["session_recorded"]:
                            leave_duration = int((state["pending_resume_leave_time"] - state["game_session_start"]).total_seconds()) if state["game_session_start"] else 0
                            record_game_session(state["pending_resume_place_id"], state["pending_resume_game_name"], leave_duration, start_time=state["game_session_start"])

                            start_time_str = state["game_session_start"].strftime("%I:%M:%S %p") if state["game_session_start"] else "Unknown"
                            end_time_str = state["pending_resume_leave_time"].strftime("%I:%M:%S %p") if state["pending_resume_leave_time"] else "Unknown"
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

                        # Timeline: robust handling of resume/merge using 30-minute rule
                        try:
                            loff = state.get("timeline_last_offline_time")
                            if loff:
                                loff_aware = _make_aware(loff)
                                if loff_aware is None:
                                    loff_aware = loff
                                delta = now - loff_aware
                                if delta <= timedelta(minutes=30):
                                    # Resumed within merge window -> continue the existing session
                                    # Ensure we do NOT close or record the session; simply clear the offline marker
                                    state["timeline_last_offline_time"] = None
                                    # If session start was lost (e.g., restart), best-effort recovery:
                                    if not state.get("timeline_current_session_start"):
                                        # Attempt to recover start from DB for that date, else use loff_aware
                                        try:
                                            date_key = loff_aware.strftime("%Y-%m-%d")
                                            doc = daily_timeline_collection.find_one({"_id": date_key}) or {}
                                            sessions = doc.get("sessions", [])
                                            if sessions:
                                                # pick the last session whose end is <= loff_aware, if any
                                                cand = None
                                                for s in sessions:
                                                    try:
                                                        sed = s.get("end_time")
                                                        sed_a = _make_aware(sed) if sed else None
                                                        if sed_a and sed_a <= loff_aware:
                                                            if not cand or sed_a > _make_aware(cand.get("end_time")):
                                                                cand = s
                                                    except Exception:
                                                        continue
                                                if cand and cand.get("start_time"):
                                                    state["timeline_current_session_start"] = _make_aware(cand.get("start_time"))
                                                else:
                                                    state["timeline_current_session_start"] = loff_aware
                                            else:
                                                state["timeline_current_session_start"] = loff_aware
                                        except Exception:
                                            state["timeline_current_session_start"] = loff_aware
                                else:
                                    # Offline exceeded merge threshold -> close previous session if present, then start a new one
                                    try:
                                        if state.get("timeline_current_session_start"):
                                            record_timeline_session(_make_aware(state.get("timeline_current_session_start")), loff_aware)
                                    except Exception as e:
                                        print(f"Error recording timeline on resume path: {e}")
                                    state["timeline_current_session_start"] = now
                                    state["timeline_last_offline_time"] = None
                            else:
                                # No offline marker -> if there's no current session, start one
                                if not state.get("timeline_current_session_start"):
                                    state["timeline_current_session_start"] = now
                        except Exception:
                            pass
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

                    if status == 2 and previous_status == 2 and sanitize_game_key(game) != sanitize_game_key(state.get("last_game_name")):
                        # اللاعب غير اللعبة خلال حالة متصلة 2، اعتبر ذلك جلسة جديدة للماب الجديدة
                        if state["game_session_start"] and not state["session_recorded"]:
                            old_duration = int((now - state["game_session_start"]).total_seconds())
                            record_game_session(state.get("place_id"), state.get("last_game_name"), old_duration, start_time=state["game_session_start"])
                        state["pending_resume"] = False
                        state["pending_resume_leave_time"] = None
                        state["last_game_name"] = game
                        state["last_game_time"] = now
                        state["place_id"] = place_id
                        state["game_id"] = game_id
                        state["game_session_start"] = now
                        state["session_recorded"] = False
                        page_link = f"https://www.roblox.com/games/{place_id}"
                        join_link = build_direct_join_link(place_id, game_id)
                        embed = discord.Embed(title="🎮 [الهدف انتقل لماب جديدة]", description="اللاعب دخل ماب جديدة في نفس الجلسة الحالية.", color=0x2ecc71)
                        embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
                        embed.add_field(name="رابط الدخول المباشر وراه (JOIN LINK) 🔥", value=f"[اضغط هنا للدخول وراه السيرفر فوراً]({join_link})", inline=False)
                        await alert_channel.send(embed=embed)

                    elif status == 2 and state["status"] != 2:
                        resumed_same_session = False
                        if state["pending_resume"] and sanitize_game_key(game) == sanitize_game_key(state.get("pending_resume_game_name")):
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
                            join_link = build_direct_join_link(place_id, game_id)
                            embed = discord.Embed(title="🎮 [بدأ يلعب ماب جديدة الآن]", description=f"الهدف دخل سيرفر ماب جديد يعيش!", color=0x2ecc71)
                            embed.add_field(name="اسم الماب الحالية", value=f"**{game}**", inline=False)
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
                            embed_leave.add_field(name="وقت الخروج", value=f"`{now.strftime('%Y-%m-%d %I:%M:%S %p')}`", inline=False)
                            embed_leave.add_field(name="ملاحظة", value="لو رجع نفس الماب خلال 10 دقائق، الجلسة ستحسب كجلسة واحدة.", inline=False)
                            await alert_channel.send(embed=embed_leave)

                    if status == 0 and state["status"] != 0:
                        state["offline_since"] = now
                        state["offline_alert_sent"] = False

                    # Timeline: mark offline time and possibly close session after 30 minutes
                    if status == 0:
                        try:
                            # If there's no active timeline session, clear any stale last_offline_time
                            if not state.get("timeline_current_session_start") and state.get("timeline_last_offline_time"):
                                state["timeline_last_offline_time"] = None

                            # set last_offline_time if not already
                            if state.get("timeline_current_session_start") and not state.get("timeline_last_offline_time"):
                                state["timeline_last_offline_time"] = now

                            # if offline exceeded merge threshold, record the session and clear markers
                            loff = state.get("timeline_last_offline_time")
                            if state.get("timeline_current_session_start") and loff:
                                loff_a = _make_aware(loff)
                                if loff_a is None:
                                    loff_a = loff
                                current_start = _make_aware(state.get("timeline_current_session_start"))
                                if current_start and loff_a <= current_start:
                                    # Stale or crossed-day offline marker; clear markers to avoid invalid intervals.
                                    state["timeline_current_session_start"] = None
                                    state["timeline_last_offline_time"] = None
                                    save_state_data()
                                elif (now - loff_a) >= timedelta(minutes=30):
                                    try:
                                        record_timeline_session(current_start, loff_a)
                                    except Exception as e:
                                        print(f"Error recording timeline on offline threshold: {e}")
                                    # After closing/merging, always clear the offline marker to avoid stale values
                                    state["timeline_current_session_start"] = None
                                    state["timeline_last_offline_time"] = None
                                    save_state_data()
                        except Exception:
                            pass

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

                    # Logical-day close handled by maybe_close_logical_day() called earlier in the loop

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

# أمر لعرض كل أوامر البوت بشكل منظم
@bot.command(name="commands")
async def cmd_commands(ctx):
    """عرض كل أوامر البوت المتاحة وشرح مختصر لكل أمر"""
    try:
        groups = {}
        for c in bot.commands:
            if getattr(c, "hidden", False):
                continue
            cog = c.cog_name or "عام"
            entry_name = f"!{c.name} {c.signature}".strip()
            description = c.help or (getattr(c.callback, "__doc__", None) or "لا يوجد وصف متاح.")
            description = description.strip() if isinstance(description, str) else str(description)
            if cog not in groups:
                groups[cog] = []
            groups[cog].append((entry_name, description))

        embeds = []
        for cog_name in sorted(groups.keys()):
            embed = discord.Embed(title=f"📚 أوامر - {cog_name}", color=0x1abc9c)
            embed.set_footer(text="استخدم !<الأمر> للحصول على مزيد من التفاصيل إن وُجد")
            count = 0
            for entry_name, description in sorted(groups[cog_name], key=lambda x: x[0]):
                embed.add_field(name=entry_name, value=(description[:1000] if description else "لا يوجد وصف."), inline=False)
                count += 1
                if count >= 20:
                    embeds.append(embed)
                    embed = discord.Embed(title=f"📚 أوامر - {cog_name} (متابعة)", color=0x1abc9c)
                    embed.set_footer(text="متابعة")
                    count = 0
            embeds.append(embed)

        for e in embeds:
            await ctx.send(embed=e)
    except Exception as e:
        await ctx.send(f"حدث خطأ أثناء بناء قائمة الأوامر: {e}")


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
