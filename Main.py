import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Fetch Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") # Provided automatically by Render

if not BOT_TOKEN or not HF_TOKEN:
    raise ValueError("Missing BOT_TOKEN or HF_TOKEN environment variables.")

# 2. Initialize Bot and Hugging Face OpenAI Client
bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

app = Flask(__name__)

# Helper function to bypass Telegram's 4096 character limit
def send_long_message(chat_id, text):
    max_length = 4096
    for i in range(0, len(text), max_length):
        bot.send_message(chat_id, text[i:i+max_length])

# 3. Handle incoming Telegram messages
@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Calling Hugging Face via OpenAI SDK
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1", # Using standard DeepSeek-R1 model id
            messages=[
                {"role": "user", "content": message.text}
            ],
            stream=False # Disabled streaming to avoid Telegram rate-limits
        )
        
        reply_text = response.choices[0].message.content
        send_long_message(message.chat.id, reply_text)
        
    except Exception as e:
        bot.reply_to(message, f"Sorry, I encountered an error: {str(e)}")

# 4. Flask Webhook Routes
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook_receive():
    # Receive updates from Telegram
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "", 200

@app.route('/')
def health_check():
    return "Bot is running perfectly on Render!", 200

if __name__ == "__main__":
    # Remove existing webhooks and set up the new one using Render's URL
    bot.remove_webhook()
    if RENDER_EXTERNAL_URL:
        # Render provides this env var automatically (e.g., https://your-app.onrender.com)
        bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}")
    else:
        print("Warning: RENDER_EXTERNAL_URL not found. Webhook not set.")

    # Render dynamically assigns a PORT. Default to 10000 locally.
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
