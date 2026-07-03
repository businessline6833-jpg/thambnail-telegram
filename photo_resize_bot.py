"""
5 Feet Photo Resize Telegram Bot
--------------------------------
কী করে:
  ইউজার bot-কে যেকোনো ছবি পাঠালে, bot সেই ছবিকে "৫ ফিট" সাইজে (বড় প্রিন্ট/স্ট্যান্ডি/ব্যানার সাইজে)
  resize করে একটা high-resolution ফাইল হিসেবে ফেরত পাঠায়।

সেটআপ (প্রথমবার):
  1) Python 3.9+ ইনস্টল থাকতে হবে।
  2) টার্মিনালে লিখো:
         pip install pyTelegramBotAPI pillow
  3) নিচে CONFIG সেকশনে তোমার BOT_TOKEN বসাও (অথবা এনভায়রনমেন্ট ভ্যারিয়েবল ব্যবহার করো, নিচে বলা আছে)।
  4) রান করো:
         python photo_resize_bot.py
  5) Telegram-এ গিয়ে তোমার bot-কে যেকোনো ছবি পাঠাও — কিছুক্ষণের মধ্যে resize করা ফাইল ফেরত পাবে।

নিরাপত্তা নোট:
  Bot token কখনো পাবলিকলি শেয়ার/কমিট করো না। এই স্ক্রিপ্টে token সরাসরি বসানোর বদলে
  এনভায়রনমেন্ট ভ্যারিয়েবল ব্যবহার করাই ভালো অভ্যাস।
"""

import os
import io
import logging
from PIL import Image
import telebot
from telebot import types

# ============================
# CONFIG - এখানে তোমার সেটিংস বসাও
# ============================

# Option 1: সরাসরি এখানে বসাও (টেস্টের জন্য, প্রোডাকশনে না করাই ভালো)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")

# ৫ ফিট = 60 ইঞ্চি। প্রিন্ট কোয়ালিটির জন্য DPI নিচে সেট করা যায়।
# বড় স্ট্যান্ডি/ব্যানারের জন্য 100-150 DPI যথেষ্ট (কাছ থেকে না দেখলে)।
# হাই কোয়ালিটি প্রিন্ট চাইলে 150-200 DPI ব্যবহার করো।
TARGET_FEET = 5
DPI = 150  # চাইলে বাড়াতে/কমাতে পারো (বেশি DPI = বড় ফাইল সাইজ)

# ছবির কোন দিকটা ৫ ফিট হবে তা ঠিক করো:
#   "height" -> ছবির উচ্চতা ৫ ফিট হবে, প্রস্থ অনুপাত অনুযায়ী স্কেল হবে (স্ট্যান্ডি/কাটআউটের জন্য সাধারণ)
#   "width"  -> ছবির প্রস্থ ৫ ফিট হবে (ব্যানারের জন্য উপযোগী)
#   "longest" -> ছবির যে দিকটা বড়, সেটাই ৫ ফিট হবে
TARGET_SIDE = "height"

# ============================
# END CONFIG
# ============================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

TARGET_INCHES = TARGET_FEET * 12
TARGET_PIXELS = TARGET_INCHES * DPI  # ৫ ফিট = কত পিক্সেল, নির্বাচিত DPI অনুযায়ী


def resize_to_target(img: Image.Image) -> Image.Image:
    """ছবিকে TARGET_SIDE অনুযায়ী resize করে, aspect ratio ঠিক রেখে।"""
    w, h = img.size

    if TARGET_SIDE == "height":
        new_h = TARGET_PIXELS
        new_w = int(w * (new_h / h))
    elif TARGET_SIDE == "width":
        new_w = TARGET_PIXELS
        new_h = int(h * (new_w / w))
    else:  # "longest"
        if w >= h:
            new_w = TARGET_PIXELS
            new_h = int(h * (new_w / w))
        else:
            new_h = TARGET_PIXELS
            new_w = int(w * (new_h / h))

    # LANCZOS = ভালো কোয়ালিটির upscale/downscale-এর জন্য
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    return resized


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    text = (
        "স্বাগতম! 👋\n\n"
        f"আমাকে যেকোনো ছবি পাঠাও, আমি সেটাকে {TARGET_FEET} ফিট সাইজে "
        f"({DPI} DPI, প্রিন্ট/স্ট্যান্ডির জন্য উপযোগী) resize করে ফেরত পাঠাবো।\n\n"
        "ছবিটা 'Compressed photo' হিসেবে না পাঠিয়ে 'File/Document' হিসেবে পাঠালে "
        "সবচেয়ে ভালো কোয়ালিটি পাবে (Telegram-এ ফাইল আইকনে ক্লিক করে ছবি অ্যাটাচ করো)।"
    )
    bot.reply_to(message, text)


def _process_and_reply(message, file_id, original_filename=None):
    try:
        bot.send_chat_action(message.chat.id, "upload_document")

        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        img = Image.open(io.BytesIO(downloaded))
        img = img.convert("RGB")  # JPEG এক্সপোর্টের জন্য

        resized = resize_to_target(img)

        output = io.BytesIO()
        output.name = "resized_5feet.jpg"
        resized.save(output, format="JPEG", quality=95, dpi=(DPI, DPI))
        output.seek(0)

        caption = (
            f"হয়ে গেছে ✅\n"
            f"সাইজ: {resized.width} x {resized.height} পিক্সেল "
            f"(~{TARGET_FEET} ফিট @ {DPI} DPI)"
        )

        # document হিসেবে পাঠানো হচ্ছে যাতে Telegram আবার compress না করে
        bot.send_document(message.chat.id, output, caption=caption, visible_file_name="resized_5feet.jpg")

    except Exception as e:
        logger.exception("Error processing image")
        bot.reply_to(message, f"দুঃখিত, একটা সমস্যা হয়েছে: {e}")


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    # সবচেয়ে বড় রেজোলিউশনের ভার্সন নেওয়া হচ্ছে (photos লিস্টের শেষটা সবচেয়ে বড়)
    file_id = message.photo[-1].file_id
    _process_and_reply(message, file_id)


@bot.message_handler(content_types=["document"])
def handle_document(message):
    # ইউজার যদি ফাইল/ডকুমেন্ট হিসেবে ছবি পাঠায় (আনকমপ্রেসড, বেশি কোয়ালিটি)
    mime = message.document.mime_type or ""
    if mime.startswith("image/"):
        _process_and_reply(message, message.document.file_id, message.document.file_name)
    else:
        bot.reply_to(message, "এটা একটা ছবি ফাইল না মনে হচ্ছে। একটা ছবি পাঠাও।")


if __name__ == "__main__":
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        print("⚠️  BOT_TOKEN সেট করো নাই। কোডের CONFIG সেকশনে token বসাও অথবা")
        print("    এনভায়রনমেন্ট ভ্যারিয়েবল ব্যবহার করো: export BOT_TOKEN='তোমার-টোকেন'")
    else:
        print("Bot চালু হচ্ছে... (বন্ধ করতে Ctrl+C চাপো)")
        bot.infinity_polling()

