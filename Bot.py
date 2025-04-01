import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN environment variable found!")
    exit(1)

# Verify token doesn't contain invalid characters
try:
    BOT_TOKEN.encode('ascii')
except UnicodeEncodeError:
    logger.error("BOT_TOKEN contains non-ASCII characters!")
    exit(1)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send /mp3 [URL] to download audio\n"
        "🎥 Send /mp4 [URL] to download video"
    )

# Download MP3
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split()) < 2:
            await update.message.reply_text("❌ Please provide a URL after /mp3")
            return

        url = update.message.text.split()[1]
        await update.message.reply_text("⏳ Downloading audio...")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': '%(title)s.%(ext)s',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3")
            with open(filename, 'rb') as audio_file:
                await update.message.reply_audio(audio=audio_file)
            os.remove(filename)

    except Exception as e:
        logger.error(f"MP3 Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Download MP4
async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split()) < 2:
            await update.message.reply_text("❌ Please provide a URL after /mp4")
            return

        url = update.message.text.split()[1]
        await update.message.reply_text("⏳ Downloading video...")

        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': '%(title)s.%(ext)s',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
            os.remove(filename)

    except Exception as e:
        logger.error(f"MP4 Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("mp3", mp3))
        app.add_handler(CommandHandler("mp4", mp4))
        
        logger.info("Starting bot...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Bot failed: {e}")

if __name__ == '__main__':
    main()