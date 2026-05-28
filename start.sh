#!/bin/bash
# تشغيل سكريبت الديسكورد في الخلفية
python Descord.py &

# تشغيل سكريبت الإنستاجرام في الخلفية 
python instagram.py &

# تشغيل الرادار الأساسي بتاع روبلوكس في الواجهة
python tracker.py
