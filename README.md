# Telegram HTML Decoder Bot

## Setup
1. Telegram-এ `@BotFather` দিয়ে bot তৈরি করে token নাও।
2. Python 3.10+ install করো।
3. `pip install -r requirements.txt`
4. Token environment variable হিসেবে সেট করো, তারপর `python bot.py` চালাও।

Linux/macOS:
`export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"`

Windows PowerShell:
`$env:TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"`

## কাজ
- সর্বোচ্চ 5 MB-এর HTML/HTM/JS/TXT নেয়।
- সাধারণ JS escapes ও কিছু Base64 text pattern পরীক্ষা করে।
- cleaned file এবং report ফেরত দেয়।
- আপলোড করা JavaScript execute করে না।

## সীমাবদ্ধতা
এটি universal decryptor নয়। Custom encryption, secret key বা runtime checks থাকলে আসল source ফিরে নাও আসতে পারে। Output চালানোর আগে code review করো। শুধু নিজের বা অনুমতিপ্রাপ্ত ফাইল ব্যবহার করো।
