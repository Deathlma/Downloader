import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import tempfile
import subprocess
import time
from functools import wraps

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
TIMEOUT = 120  # seconds

def retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}")
                    time.sleep(delay)
        return wrapper
    return decorator

async def safe_execute(cmd, timeout=TIMEOUT):
    """Execute shell command with timeout and error handling"""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {' '.join(cmd)}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr.decode().strip()}")
        return False

@retry(max_retries=MAX_RETRIES)
async def download_media(update: Update, media_type: str):
    try:
        # Step 1: Validate input
        try:
            url = update.message.text.split(maxsplit=1)[1]
        except IndexError:
            await update.message.reply_text("❌ Please provide a URL after the command")
            return

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Step 2: Download with yt-dlp
            ydl_opts = {
                'ffmpeg_location': '/usr/bin/ffmpeg',
                'outtmpl': f'{tmp_dir}/original.%(ext)s',
                'format': 'bestvideo[height<=720]+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {
                    'tiktok': {
                        'headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        }
                    }
                }
            }

            await update.message.reply_text("⬇️ Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                original_file = ydl.prepare_filename(info)

                # Verify download
                if not os.path.exists(original_file) or os.path.getsize(original_file) < 1024:
                    raise ValueError("Download failed or file too small")

            # Step 3: Convert for Telegram
            output_ext = 'mp4' if media_type == 'video' else 'mp3'
            output_file = f"{tmp_dir}/converted.{output_ext}"
            
            await update.message.reply_text("🔄 Converting format...")
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', original_file,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                output_file
            ]
            
            if not await safe_execute(ffmpeg_cmd):
                raise ValueError("File conversion failed")

            # Step 4: Upload to Telegram
            await update.message.reply_text("📤 Uploading to Telegram...")
            with open(output_file, 'rb') as f:
                if media_type == 'video':
                    await update.message.reply_video(
                        video=f,
                        caption=info.get('title', '')[:1024],
                        supports_streaming=True,
                        read_timeout=TIMEOUT,
                        write_timeout=TIMEOUT
                    )
                else:
                    await update.message.reply_audio(
                        audio=f,
                        title=info.get('title', '')[:64],
                        performer=info.get('uploader', '')[:64]
                    )

    except Exception as e:
        logger.error(f"Final error: {str(e)}")
        await update.message.reply_text(f"❌ Failed after {MAX_RETRIES} attempts. Please try a different URL.\nError: {str(e)}")

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send /mp3 [URL] for audio\n"
        "🎥 Send /mp4 [URL] for video\n\n"
        "Supports: YouTube, TikTok, Instagram, Twitter"
    )

def main():
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('mp3', lambda u,c: download_media(u, 'audio')))
    app.add_handler(CommandHandler('mp4', lambda u,c: download_media(u, 'video')))
    
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
