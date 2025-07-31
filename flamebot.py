from telebot import TeleBot
from dotenv import load_dotenv
import os

load_dotenv()
bot = TeleBot(os.getenv('BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, '🔥 FlameBot is active. Wallet hooks and alert modules loading...')

@bot.message_handler(commands=['tip'])
def send_tip(message):
    bot.reply_to(message, '✅ Simulated tip to MetaMask executed.')

if __name__ == '__main__':
    bot.polling()

