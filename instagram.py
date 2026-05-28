import time
import random
import os
import requests
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from instagrapi import Client

# ==================== الإعدادات الأساسية ====================
SESSION_ID = "28227353802%3A4SeUP8Q6ltIZqy%3A1%3AAYhA5aI0tXVvvlH1GkKlYBqTev5rJ56SY6WW5uL0xg"  
TARGET_USER_ID = "62464376993"       
WEBHOOK_URL = "https://discord.com/api/webhooks/1509381394382716998/PXxpSyW764UGoxYYtlxZQTZEWotQZd71hn3lcueGwETLs8OPUXX_KMYNhXgwieN1fHeo"
SAVE_PATH = "./stories_downloads"
CACHE_FILE = "seen_stories.txt"

BOT_TOKEN = "MTUwOTU0OTE2NDc1NTY4MTQzMg.GrHDLg.Zkeis6jBP-c4u2esNkwlBWFjhOrelqXuHPmsnU"
COMMANDS_CHANNEL_ID = 1509381347012120617

# Instagram Bot Setup
intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix="!", intents=intents)
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
        
        new_stories_found = 0
        for index, story in enumerate(stories, 1):
            story_id = story.id
            
            if story_id in seen_stories_cache:
                print(f"ℹ️ الستوري رقم {index} (ID: {story_id}) متسجلة في الذاكرة الدائمة كـ Seen. تم التخطي.")
                continue
                
            new_stories_found += 1
            print(f"🔥 لقطنا ستوري جديدة كلياً للحساب @{current_username} (ID: {story_id})!")
            
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
                seen_stories_cache.add(story_id)
                save_seen_story(story_id)
            else:
                print(f"❌ فشل إرسال الستوري للـ Webhook. كود الخطأ: {status}")
        
        if new_stories_found == 0:
            print(f"ℹ️ لا توجد ستوريات جديدة للإرسال تلقائياً في هذا الفحص.")
                
    except Exception as e:
        print(f"❌ حصلت مشكلة أثناء الفحص: {e}")

# التشغيل الفوري
print("🚀 إطلاق الرادار المطور بالذاكرة الحديدية فوراً...")

@discord_bot.event
async def on_ready():
    print(f"\n{'='*70}")
    print(f"📸 Instagram Monitor Bot Ready as: {discord_bot.user.name}")
    print(f"{'='*70}\n")
    instagram_monitor_loop.start()

@discord_bot.command(name="commands")
async def cmd_commands(ctx):
    """عرض جميع أوامر رادار إنستاجرام"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    embed = discord.Embed(title="📖 قائمة أوامر رادار إنستاجرام (Instagram Monitor Commands)", color=0xE1306C)
    
    embed.add_field(
        name="� !check",
        value="التحقق من وجود ستوريات جديدة وعدد الستوريات المتاحة\n**مثال:** `!check`",
        inline=False
    )
    
    embed.add_field(
        name="📤 !send",
        value="إرسال جميع الستوريات الجديدة الموجودة الآن مرة واحدة\n**مثال:** `!send`",
        inline=False
    )
    
    embed.add_field(
        name="📊 !what",
        value="عرض حالة الستوريات (Seen أم Not Seen) مع العدد والتفاصيل\n**مثال:** `!what`",
        inline=False
    )
    
    embed.add_field(
        name="📸 !stories",
        value="فحص آخر الستوريات الجديدة من الحساب المراقب\n**مثال:** `!stories`",
        inline=False
    )
    
    embed.add_field(
        name="👤 !account",
        value="عرض معلومات حساب إنستاجرام المراقب\n**مثال:** `!account`",
        inline=False
    )
    
    embed.add_field(
        name="🔔 التنبيهات التلقائية",
        value="**النظام يرسل إشعارات تلقائية متى:**\n"
              "📸 **استوري جديدة** - تحميل وإرسال فوري إلى الـ Webhook\n"
              "👤 **تغيير اسم الحساب** - إشعار أمني فوري\n"
              "📁 **حفظ الستوريات محلياً** - في مجلد stories_downloads\n"
              "🔐 **تتبع ذاكرة الستوريات** - عدم إرسال نفس الستوري مرتين",
        inline=False
    )
    
    embed.set_footer(text="الرادار يفحص آخر الستوريات كل 30-120 دقيقة عشوائياً 🔍")
    await ctx.send(embed=embed)

@discord_bot.command(name="stories")
async def cmd_stories(ctx):
    """فحص الستوريات الجديدة"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    await ctx.send("📸 جاري فحص آخر الستوريات من الحساب المراقب...")
    check_stories()
    await ctx.send("✅ تم الفحص! أي ستوريات جديدة سيتم إرسالها تلقائياً.")

@discord_bot.command(name="account")
async def cmd_account(ctx):
    """عرض معلومات الحساب المراقب"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    try:
        user_info = cl.user_info(TARGET_USER_ID)
        embed = discord.Embed(
            title=f"👤 معلومات حساب {user_info.username}",
            color=0xE1306C
        )
        embed.add_field(name="📝 اسم المستخدم", value=f"@{user_info.username}", inline=False)
        embed.add_field(name="👤 الاسم الكامل", value=user_info.full_name or "لا يوجد", inline=False)
        embed.add_field(name="📄 البايو", value=user_info.biography or "بدون بايو", inline=False)
        embed.add_field(name="👨‍👩‍👦 المتابعون", value=f"{user_info.follower_count:,}", inline=True)
        embed.add_field(name="👀 يتابع", value=f"{user_info.following_count:,}", inline=True)
        embed.add_field(name="📸 المنشورات", value=f"{user_info.media_count:,}", inline=True)
        embed.set_thumbnail(url=user_info.profile_pic_url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ خطأ في جلب بيانات الحساب: {str(e)}")

@discord_bot.command(name="check")
async def cmd_check(ctx):
    """التحقق من وجود ستوريات جديدة"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    await ctx.send("🔍 جاري التحقق من وجود ستوريات جديدة...")
    try:
        user_info = cl.user_info(TARGET_USER_ID)
        stories = cl.user_stories(TARGET_USER_ID)
        
        if not stories:
            embed = discord.Embed(
                title="📭 لا توجد ستوريات حالياً",
                description=f"الحساب @{user_info.username} لم ينشر أي ستوريات في هذه اللحظة.",
                color=0xFF6B6B
            )
            await ctx.send(embed=embed)
            return
        
        # تقسيم الستوريات إلى seen و new
        new_stories = []
        seen = []
        
        for story in stories:
            if story.id in seen_stories_cache:
                seen.append(story)
            else:
                new_stories.append(story)
        
        embed = discord.Embed(
            title="📊 حالة الستوريات الحالية",
            color=0xE1306C
        )
        embed.add_field(
            name="👤 الحساب",
            value=f"@{user_info.username}",
            inline=False
        )
        embed.add_field(
            name="📸 إجمالي الستوريات المتاحة",
            value=f"`{len(stories)}`",
            inline=True
        )
        embed.add_field(
            name="✨ ستوريات جديدة (لم ترسل بعد)",
            value=f"`{len(new_stories)}`",
            inline=True
        )
        embed.add_field(
            name="✅ ستوريات مرسلة بالفعل",
            value=f"`{len(seen)}`",
            inline=True
        )
        
        if new_stories:
            embed.add_field(
                name="🆕 تفاصيل الستوريات الجديدة",
                value=f"هناك **{len(new_stories)}** ستوريات جديدة جاهزة للإرسال\nاستخدم `!send` لإرسالها جميعاً",
                inline=False
            )
        
        embed.set_thumbnail(url=user_info.profile_pic_url)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ خطأ في التحقق: {str(e)}")

@discord_bot.command(name="send")
async def cmd_send(ctx):
    """إرسال الستوريات الجديدة الموجودة الآن"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    await ctx.send("📤 جاري إرسال الستوريات المتاحة حالياً (بغض النظر عن حالة الإرسال السابقة)...")
    try:
        user_info = cl.user_info(TARGET_USER_ID)
        stories = cl.user_stories(TARGET_USER_ID)
        
        if not stories:
            await ctx.send("📭 لا توجد ستوريات للإرسال حالياً!")
            return
        
        embed_start = discord.Embed(
            title=f"📤 إرسال {len(stories)} ستوري",
            description=f"🎬 جاري إرسال جميع الستوريات المتاحة من @{user_info.username}...",
            color=0x2ECC71
        )
        await ctx.send(embed=embed_start)
        
        sent_count = 0
        
        for index, story in enumerate(stories, 1):
            try:
                # تحميل الستوري
                file_path = cl.story_download(story.id, folder=SAVE_PATH)
                
                ext = os.path.splitext(file_path)[1]
                new_file_name = f"{user_info.username}_{story.id}{ext}"
                new_file_path = os.path.join(SAVE_PATH, new_file_name)
                
                if os.path.exists(file_path):
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                    os.replace(file_path, new_file_path)
                
                time_ago = get_time_ago(story.taken_at)
                
                # رسالة توضيحية إذا كانت الستوري قد أُرسلت من قبل
                status_note = "" 
                if story.id in seen_stories_cache:
                    status_note = " (أُرسلت مسبقاً في فحص سابق)"

                msg = f"📸 **ستوري رقم {index} من {len(stories)}**{status_note}\n👤 @{user_info.username}\n⏳ {time_ago}"
                
                status = send_to_discord_webhook(msg, file_path=new_file_path)
                if status in [200, 204]:
                    # لا يزال يتم حفظها في الكاش لكي لا يرسلها الرادار التلقائي مرة أخرى
                    seen_stories_cache.add(story.id)
                    save_seen_story(story.id)
                    sent_count += 1
                    embed_success = discord.Embed(
                        description=f"✅ تم إرسال الستوري **{index}/{len(stories)}** بنجاح",
                        color=0x2ECC71
                    )
                    await ctx.send(embed=embed_success)
                else:
                    embed_error = discord.Embed(
                        description=f"❌ فشل إرسال الستوري {index}/{len(stories)}",
                        color=0xFF6B6B
                    )
                    await ctx.send(embed=embed_error)
            except Exception as e:
                await ctx.send(f"❌ خطأ في الستوري {index}: {str(e)[:50]}")
        
        embed_done = discord.Embed(
            title="✅ تم إنهاء الإرسال",
            description=f"تم إرسال **{sent_count}** ستوريات (تضمنت بعض الستوريات المعاد إرسالها بناءً على طلبك).",
            color=0x2ECC71
        )
        await ctx.send(embed=embed_done)
        
    except Exception as e:
        await ctx.send(f"❌ خطأ في الإرسال: {str(e)}")

@discord_bot.command(name="what")
async def cmd_what(ctx):
    """عرض حالة الستوريات (seen أم no) وعددها"""
    if ctx.channel.id != COMMANDS_CHANNEL_ID:
        return
    
    await ctx.send("🔍 جاري جمع معلومات الستوريات...")
    try:
        user_info = cl.user_info(TARGET_USER_ID)
        stories = cl.user_stories(TARGET_USER_ID)
        
        if not stories:
            embed = discord.Embed(
                title="📭 لا توجد ستوريات",
                description=f"الحساب @{user_info.username} بدون ستوريات حالياً",
                color=0xFF6B6B
            )
            embed.set_thumbnail(url=user_info.profile_pic_url)
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📊 تفاصيل الستوريات - @{user_info.username}",
            color=0xE1306C
        )
        
        total_stories = len(stories)
        seen_count = sum(1 for s in stories if s.id in seen_stories_cache)
        new_count = total_stories - seen_count
        
        embed.add_field(
            name="📊 الإحصائيات",
            value=f"📈 **إجمالي الستوريات:** `{total_stories}`\n"
                  f"✅ **ستوريات مرسلة (Seen):** `{seen_count}`\n"
                  f"🆕 **ستوريات جديدة (Not Seen):** `{new_count}`",
            inline=False
        )
        
        # عرض تفاصيل كل ستوري
        stories_list = ""
        for idx, story in enumerate(stories, 1):
            status = "✅ Seen" if story.id in seen_stories_cache else "🆕 Not Seen"
            time_ago = get_time_ago(story.taken_at)
            stories_list += f"{idx}. {status} | {time_ago}\n"
        
        embed.add_field(
            name="📋 قائمة الستوريات التفصيلية",
            value=stories_list if stories_list else "لا توجد ستوريات",
            inline=False
        )
        
        # معلومات إضافية
        embed.add_field(
            name="💡 معلومة إضافية",
            value="✅ = تم إرسالها بالفعل\n🆕 = جديدة ولم تُرسل بعد",
            inline=False
        )
        
        embed.set_thumbnail(url=user_info.profile_pic_url)
        embed.set_footer(text=f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ خطأ في جلب المعلومات: {str(e)}")

@tasks.loop(minutes=1)
async def instagram_monitor_loop():
    """مراقبة محدثة كل دقيقة من البوت"""
    pass

def run_bot_and_monitor():
    """تشغيل البوت والرادار معاً"""
    import threading
    
    def run_monitor():
        # حلقة الرادار الأساسية
        check_stories()
        while True:
            wait_time = random.randint(1800, 7200)
            print(f"💤 الفحص القادم هيكون عشوائياً بعد {wait_time // 60} دقيقة...")
            time.sleep(wait_time)
            check_stories()
    
    # تشغيل الرادار في خيط منفصل
    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
    monitor_thread.start()
    
    # تشغيل البوت
    discord_bot.run(BOT_TOKEN)

if __name__ == "__main__":
    print("🚀 إطلاق نظام مراقبة إنستاجرام المتقدم...")
    run_bot_and_monitor()
