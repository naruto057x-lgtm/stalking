import time
import random
import os
import requests
from datetime import datetime, timezone
from instagrapi import Client

# ==================== الإعدادات الأساسية ====================
SESSION_ID = "28227353802%3AkoKSWQ93I1lXwG%3A11%3AAYgM_1krietG8JcIiEn1Rzy1PqLNJ4sSyJBgNMnYB_c"  
TARGET_USER_ID = "62464376993"       
WEBHOOK_URL = "https://discord.com/api/webhooks/1509381394382716998/PXxpSyW764UGoxYYtlxZQTZEWotQZd71hn3lcueGwETLs8OPUXX_KMYNhXgwieN1fHeo"
SAVE_PATH = "./stories_downloads"
CACHE_FILE = "seen_stories.txt" # ملف الذاكرة الدائمة 📁
# ============================================================

if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

# دالة لقراءة الذاكرة من الملف الخارجي عند تشغيل السكريبت
def load_seen_stories():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

# دالة لحفظ الـ ID الجديد في الملف الخارجي فوراً
def save_seen_story(story_id):
    with open(CACHE_FILE, "a") as f:
        f.write(f"{story_id}\n")

seen_stories_cache = load_seen_stories()
current_cached_username = None 

cl = Client()
print("🔄 جاري تسجيل الدخول إلى إنستاجرام باستخدام الـ Session ID...")
try:
    cl.login_by_sessionid(SESSION_ID)
    print(f"✅ تم تسجيل الدخول بنجاح! الذاكرة محملة بـ {len(seen_stories_cache)} ستوري سابقة.")
except Exception as e:
    print(f"❌ فشل تسجيل الدخول، تأكد من الـ Session ID: {e}")
    exit()

def send_to_discord_webhook(text, file_path=None):
    payload = {"content": text}
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size <= 10: 
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                res = requests.post(WEBHOOK_URL, data=payload, files=files)
        else:
            payload["content"] += f"\n⚠️ **تنبيه:** حجم الستوري كبير ({file_size:.2f} MB)، تم حفظ الملف محلياً في الفولدر!"
            res = requests.post(WEBHOOK_URL, json=payload)
    else:
        res = requests.post(WEBHOOK_URL, json=payload)
    return res.status_code

def get_time_ago(post_time):
    now = datetime.now(timezone.utc)
    if post_time.tzinfo is None:
        post_time = post_time.replace(tzinfo=timezone.utc)
        
    diff = now - post_time
    seconds = diff.total_seconds()
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"منذ {hours} ساعة و {minutes} دقيقة" if minutes > 0 else f"منذ {hours} ساعة"
    elif minutes > 0:
        return f"منذ {minutes} دقيقة"
    else:
        return "منذ ثوانٍ قليلة"

def check_stories():
    global current_cached_username
    print(f"🔍 [فحص] جاري تحديث بيانات الحساب من الـ ID: {TARGET_USER_ID}...")
    try:
        user_info = cl.user_info(TARGET_USER_ID)
        current_username = user_info.username
        
        if current_cached_username and current_username != current_cached_username:
            change_msg = f"⚠️ **إشعار أمني للرادار:** الحساب المستهدف قام بتغيير اسمه المستعار!\n🔹 **الاسم القديم:** `@{current_cached_username}`\n🔥 **الاسم الجديد الحالي:** `@{current_username}`"
            print(change_msg)
            send_to_discord_webhook(change_msg)
        
        current_cached_username = current_username
        stories = cl.user_stories(TARGET_USER_ID)
        
        if not stories:
            print(f"📭 الحساب @{current_username} مش منزل أي ستوريات حالياً.")
            return

        print(f"📸 وجدنا {len(stories)} ستوري متاحين على الحساب.")
        
        for index, story in enumerate(stories, 1):
            story_id = story.id
            
            # المقارنة بالذاكرة الدائمة المحمية من القفل والفتح ✅
            if story_id in seen_stories_cache:
                print(f"ℹ️ الستوري رقم {index} (ID: {story_id}) متسجلة في الذاكرة الدائمة كـ Seen. تم التخطي بأمان.")
                continue
                
            print(f"🔥 لقطنا ستوري جديدة كلياً للحساب @{current_username}!")
            
            # التحميل صامت
            file_path = cl.story_download(story.id, folder=SAVE_PATH)
            
            ext = os.path.splitext(file_path)[1]
            new_file_name = f"{current_username}_{story_id}{ext}"
            new_file_path = os.path.join(SAVE_PATH, new_file_name)
            
            if os.path.exists(file_path):
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                os.replace(file_path, new_file_path)
            
            time_ago = get_time_ago(story.taken_at)
            
            msg = f"🔔 **رادار إنستاجرام قفش ستوري جديدة!**\n👤 **اليوزر الحالي:** `@{current_username}`\n🆔 **Instagram ID:** `{TARGET_USER_ID}`\n⏳ **وقت النشر:** `{time_ago}`\nترتيبها في بروفايله: {index}"
            
            status = send_to_discord_webhook(msg, file_path=new_file_path)
            if status in [200, 204]:
                print(f"✅ تم إرسال الستوري بنجاح إلى ديسكورد!")
                # حفظ في الكاش الداخلي وفي الملف النصي فوراً
                seen_stories_cache.add(story_id)
                save_seen_story(story_id)
            else:
                print(f"❌ فشل إرسال الستوري للـ Webhook. كود الخطأ: {status}")
                
    except Exception as e:
        print(f"❌ حصلت مشكلة أثناء الفحص: {e}")

# التشغيل الفوري
print("🚀 إطلاق الرادار المطور بالذاكرة الحديدية فوراً...")
check_stories()

while True:
    wait_time = random.randint(1800, 7200)
    print(f"💤 الفحص القادم هيكون عشوائياً بعد {wait_time // 60} دقيقة...")
    time.sleep(wait_time)
    check_stories()