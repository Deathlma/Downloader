import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Critical FFmpeg configuration
FFMPEG_SETTINGS = {
    'ffmpeg_location': '/usr/bin/ffmpeg',
    'postprocessor_args': [
        '-fflags', '+genpts',
        '-strict', 'experimental',
        '-movflags', '+faststart',
        '-acodec', 'libmp3lame',
        '-vcodec', 'libx264'
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fixed start command handler"""
    await update.message.reply_text(
        "🎵 Send /mp3 [URL] to download audio\n"
        "🎥 Send /mp4 [URL] to download video\n\n"
        "Supports: YouTube, Instagram, TikTok, Twitter/X"
    )

async def download_media(update: Update, media_type: str):
    try:
        url = update.message.text.split(maxsplit=1)[1]
        
        ydl_opts = {
            **FFMPEG_SETTINGS,
            'format': 'bestvideo[height<=720]+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
            'restrictfilenames': True,
            'merge_output_format': 'mp4',
            'retries': 3,
            
            # Fix for corrupt files:
            'fixup': 'detect_or_warn',
            'concurrent_fragment_downloads': 3,
            
            # Platform optimizations
            'extractor_args': {
                'instagram': {'format': 'best'},
                'tiktok': {'format': 'bestvideo+bestaudio/best'},
                'twitter': {'format': 'bestvideo[height<=720]+bestaudio/best'}
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await update.message.reply_text("⏳ Processing your request...")
            
            # First check availability
            info = ydl.extract_info(url, download=False)
            if not info.get('url'):
                await update.message.reply_text("❌ Content is unavailable or protected")
                return

            # Download with progress
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '0%')
                    if float(percent.strip('%')) % 10 == 0:  # Update every 10%
                        logger.info(f"Download progress: {percent}")

            ydl_opts['progress_hooks'] = [progress_hook]
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            # Verify file integrity before sending
            if os.path.getsize(filename) == 0:
                raise ValueError("Downloaded file is empty")

            # Send file
            await update.message.reply_text("📤 Uploading to Telegram...")
            with open(filename, 'rb') as f:
                if media_type == 'video':
                    await update.message.reply_video(
                        video=f,
                        caption=info.get('title', 'Video'),
                        supports_streaming=True,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
                else:
                    await update.message.reply_audio(
                        audio=f,
                        title=info.get('title', 'Audio')[:64],  # Telegram limits
                        performer=info.get('uploader', 'Unknown')[:64]
                    )
            
            # Cleanup
            os.remove(filename)

    except IndexError:
        await update.message.reply_text("❌ Please provide a URL after the command")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Failed: {str(e)}")

def main():
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    app.add_handler(CommandHandler('start', start))  # Fixed start handler
    app.add_handler(CommandHandler('mp3', lambda u,c: download_media(u, 'audio')))
    app.add_handler(CommandHandler('mp4', lambda u,c: download_media(u, 'video')))
    
    logger.info("Bot started successfully")
    app.run_polling()

if __name__ == '__main__':
    main()
