import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
import requests  # নতুন যোগ করা হয়েছে
import re        # নতুন যোগ করা হয়েছে
from flask import Flask, jsonify, make_response, request # request যোগ করা হয়েছে
from supabase import create_client
import threading
import time
import random

# ================= CONFIGURATION =================
BOT_TOKEN = "8628213901:AAFvfHBpZ6tok40ZQuhIDLAVIMrHeiheMNY"
SUPABASE_URL = "https://yctirvnryrzygoxbpvoy.supabase.co"
SUPABASE_KEY = "sb_publishable_aBcD-atruskWwoCiLr0lWw_inT8GLoN"
WEB_APP_URL = "https://rony90790.github.io/Forward-bot/index.html" 

ADMIN_IDS = [7307789267]
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)
admin_states = {}

BOT_ID = None

# ================= FLASK API ROUTES =================
@app.route('/')
def index():
    return "Bot and API are Running smoothly! 🚀"

@app.route('/api/videos')
def api_videos():
    try:
        res = supabase.table('videos').select('*').order('id', desc=True).execute()
        response = make_response(jsonify(res.data))
    except Exception as e:
        print(f"API Error: {e}")
        response = make_response(jsonify([]))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# 🔥 নতুন যোগ করা হলো: Stripchat থেকে লাইভ লিঙ্ক (.m3u8) বের করার API
@app.route('/api/get_stream')
def get_stream():
    target_url = request.args.get('url')
    if not target_url:
        response = make_response(jsonify({"error": "No URL provided"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 400
    
    try:
        # লিঙ্ক থেকে মডেলের নাম বের করা
        model_name = target_url.strip('/').split('/')[-1].split('?')[0].lower()
        
        # স্ট্রিপচ্যাটের সবচেয়ে কমন এইচএলএস (HLS) প্যাটার্ন
        # আমরা সরাসরি এই লিঙ্কটি রিটার্ন করব, এতে সার্ভার ব্লক হওয়ার ভয় নেই
        stream_url = f"https://b-hls-05.doppiocdn.com/hls/{model_name}/master/{model_name}.m3u8"
        
        response = make_response(jsonify({"stream_url": stream_url}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        # এরর হলে আসল কারণ দেখার জন্য
        response = make_response(jsonify({"error": str(e)}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
        
# ================= TELEGRAM BOT COMMANDS =================
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type != 'private':
        try:
            bot_username = bot.get_me().username
            bot_link = f"https://t.me/{bot_username}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🎬 Watch Videos Now", url=bot_link))
            bot.reply_to(message, "🔥 <b>Watch Premium Viral Videos for FREE!</b>\n\n👉 Click the button below to watch:", parse_mode="HTML", reply_markup=markup)
        except Exception as e: print(e)
        return

    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        args = message.text.split()
        referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

        user_check = supabase.table('referrals').select('*').eq('user_id', user_id).execute()
        if not user_check.data: 
            supabase.table('referrals').insert({
                'user_id': user_id, 
                'referral_count': 0, 
                'referrer_id': referrer_id if referrer_id != user_id else None
            }).execute()

            if referrer_id and referrer_id != user_id:
                ref_data = supabase.table('referrals').select('referral_count').eq('user_id', referrer_id).execute()
                if ref_data.data:
                    new_count = ref_data.data[0]['referral_count'] + 1
                    supabase.table('referrals').update({'referral_count': new_count}).eq('user_id', referrer_id).execute()
                    try:
                        bot.send_message(referrer_id, f"🎉 <b>{first_name}</b> has joined using your link!\n\nInvites completed: <b>{new_count}</b>", parse_mode="HTML")
                    except Exception as e: pass

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Play Video 🔞", web_app=WebAppInfo(url=WEB_APP_URL)))
        welcome_text = f"Hello {first_name}! 👋\n\nWatch premium viral videos by clicking the button below 👇"
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    except Exception as e: print(e)

@bot.message_handler(content_types=['new_chat_members'])
def on_added_to_group(message):
    global BOT_ID
    if BOT_ID is None:
        try: BOT_ID = bot.get_me().id
        except: pass
            
    for user in message.new_chat_members:
        if user.id == BOT_ID:
            try:
                supabase.table('groups').insert({"group_id": message.chat.id, "group_name": message.chat.title, "added_by": message.from_user.id}).execute()
                bot_username = bot.get_me().username
                bot_link = f"https://t.me/{bot_username}"
                welcome_msg = f"✅ <b>Bot successfully joined!</b>\n\n🔥 Watch Premium Viral Videos for FREE!\nJoin my bot to watch without limits.\n\n👉 <b>Start Bot:</b> {bot_link}"
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("🎬 Watch Viral Videos", url=bot_link))
                bot.send_message(message.chat.id, welcome_msg, parse_mode="HTML", reply_markup=markup)
            except Exception as e: print(e)

# ================= ADMIN COMMANDS =================
@bot.message_handler(commands=['stats', 'users'])
def bot_stats(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        users = supabase.table('referrals').select('user_id', count='exact').execute()
        videos = supabase.table('videos').select('*', count='exact').execute()
        groups = supabase.table('groups').select('group_id', count='exact').execute()
        stat_msg = f"📊 <b>বটের বর্তমান স্ট্যাটাস:</b>\n\n👥 মোট ইউজার: <code>{users.count or 0}</code> জন\n🎬 মোট ভিডিও: <code>{videos.count or 0}</code> টি\n📢 মোট গ্রুপ: <code>{groups.count or 0}</code> টি"
        bot.send_message(message.chat.id, stat_msg, parse_mode="HTML")
    except Exception as e: print(e)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id not in ADMIN_IDS: return
    msg = bot.send_message(message.chat.id, "📢 <b>ব্রডকাস্ট মোড অন হয়েছে!</b>\n\nসবার কাছে যা পাঠাতে চান দিন। (বাতিল করতে /cancel)", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ ব্রডকাস্ট বাতিল করা হয়েছে।")
        return
    bot.send_message(message.chat.id, "⏳ ব্রডকাস্ট শুরু হয়েছে...")
    try:
        res = supabase.table('referrals').select('user_id').execute()
        success, failed = 0, 0
        for u in res.data:
            try:
                bot.copy_message(chat_id=u['user_id'], from_chat_id=message.chat.id, message_id=message.message_id)
                success += 1
                time.sleep(0.05)
            except: failed += 1
        bot.send_message(message.chat.id, f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\nসফল: {success} জন\nব্যর্থ: {failed} জন", parse_mode="HTML")
    except Exception as e: print(e)

@bot.message_handler(commands=['png', 'addvideo'])
def add_png(message):
    try:
        if message.from_user.id not in ADMIN_IDS: return
        parts = message.text.split()
        
        needed_ref = 3
        duration = "random"
        thumbnail_url = ""

        if len(parts) == 4 and parts[1].isdigit():
            needed_ref = int(parts[1])
            duration = parts[2]
            thumbnail_url = parts[3]
        elif len(parts) == 3 and parts[1].isdigit():
            needed_ref = int(parts[1])
            thumbnail_url = parts[2]
        elif len(parts) == 2 and not parts[1].isdigit():
            thumbnail_url = parts[1]
        else:
            msg = "❌ <b>সঠিক নিয়ম:</b>\n\n1️⃣ <code>/png 0 1:35 https://link.jpg</code>\n2️⃣ <code>/png 0 https://link.jpg</code>\n3️⃣ <code>/png https://link.jpg</code>"
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
            return

        packed_thumb = f"{thumbnail_url}||{duration}"
        admin_states[message.chat.id] = {"step": 1, "thumbnail_url": packed_thumb, "needed_ref": needed_ref}
        
        reply_msg = f"✅ <b>ছবি ও টাইম সেট হয়েছে!</b>\n\n🎯 টার্গেট রেফার: <b>{needed_ref}</b>\n\nএখন Video Link বা Telegram Post Link দিন। (বাতিল করতে /cancel)"
        bot.send_message(message.chat.id, reply_msg, parse_mode="HTML")
    except Exception as e: print(e)

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    if message.chat.id in admin_states:
        admin_states.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ প্রসেস বাতিল করা হয়েছে।")

@bot.message_handler(func=lambda m: admin_states.get(m.chat.id, {}).get("step") == 1)
def add_video_step(message):
    try:
        if message.text.startswith('/'):
            bot.send_message(message.chat.id, "❌ প্রসেস বাতিল করা হয়েছে।")
            admin_states.pop(message.chat.id, None)
            return
            
        video_url = message.text.strip()
        thumb_url = admin_states[message.chat.id]["thumbnail_url"]
        needed_ref = admin_states[message.chat.id]["needed_ref"]
        
        supabase.table('videos').insert({
            "video_url": video_url, 
            "thumbnail_url": thumb_url,
            "needed_ref": needed_ref
        }).execute()
        
        bot.send_message(message.chat.id, f"🎉 <b>ভিডিও সফলভাবে অ্যাড হয়েছে!</b>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ ডাটাবেজে সেভ করতে সমস্যা।")
        print(e)
    finally:
        admin_states.pop(message.chat.id, None)

def auto_post_to_groups():
    time.sleep(60) 
    while True:
        try:
            groups = supabase.table('groups').select('group_id').execute().data
            if groups:
                bot_username = bot.get_me().username
                bot_link = f"https://t.me/{bot_username}"
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("🔥 Watch Videos Now", url=bot_link))
                post_msg = f"🔥 <b>Premium Viral Videos Updated!</b>\n\n👉 <b>Click here to watch:</b> {bot_link}"
                for g in groups:
                    try:
                        bot.send_message(g['group_id'], post_msg, parse_mode="HTML", reply_markup=markup)
                        time.sleep(2)
                    except Exception as e:
                        if any(x in str(e).lower() for x in ["kicked", "not a member", "chat not found", "forbidden"]):
                            try: supabase.table('groups').delete().eq('group_id', g['group_id']).execute()
                            except: pass
        except: pass
        time.sleep(random.randint(3600, 7200))

def run_flask(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    bot.remove_webhook()
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_post_to_groups, daemon=True).start()
    print("🤖 Bot is starting...")
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=15)
        except: time.sleep(5)
