import subprocess
import sys
import time

print("🔥 جاري تشغيل الـ 3 رادارات مع بعض في السحاب فوراً...")

# تشغيل السكريبتات الثلاثة في عمليات منفصلة بالخلفية
p1 = subprocess.Popen([sys.executable, "tracker.py"])
p2 = subprocess.Popen([sys.executable, "Descord.py"])
p3 = subprocess.Popen([sys.executable, "instagram.py"])

print("✅ رادار روبلوكس، ديسكورد، وإنستاجرام شغالين دلوقتي 24 ساعة!")

try:
    # حلقة مستمرة تضمن إن السكريبت الأساسي ميفصلش
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    print("⚠️ جاري إغلاق جميع السكريبتات...")
    p1.terminate()
    p2.terminate()
    p3.terminate()
