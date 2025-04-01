import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Missing BOT_TOKEN!")
    exit(1)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send /mp3 [URL] to download audio\n"
        "🎥 Send /mp4 [URL] to download video"
    )

async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split()) < 2:
            await update.message.reply_text("❌ Please provide a YouTube URL after /mp3")
            return

        url = update.message.text.split()[1]
        await update.message.reply_text("⏳ Downloading audio...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': '/usr/bin/ffmpeg',  # Critical for Railway
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3")
            
            # Send audio with progress updates
            await update.message.reply_text("📤 Uploading audio...")
            with open(filename, 'rb') as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    title=info.get('title', 'audio'),
                    performer=info.get('uploader', 'unknown artist')
                )
            os.remove(filename)

    except Exception as e:
        logger.error(f"MP3 Error: {str(e)}")
        await update.message.reply_text(f"❌ Failed: {str(e)}")

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split()) < 2:
            await update.message.reply_text("❌ Please provide a YouTube URL after /mp4")
            return

        url = update.message.text.split()[1]
        await update.message.reply_text("⏳ Downloading video...")

        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'ffmpeg_location': '/usr/bin/ffmpeg',  # Critical for Railway
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Send video with progress updates
            await update.message.reply_text("📤 Uploading video...")
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=info.get('title', 'video')
                )
            os.remove(filename)

    except Exception as e:
        logger.error(f"MP4 Error: {str(e)}")
        await update.message.reply_text(f"❌ Failed: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mp3", mp3))
    app.add_handler(CommandHandler("mp4", mp4))
    
    logger.info("Starting bot...")
    app.run_polling()

if __name__ == '__main__':
    main()
