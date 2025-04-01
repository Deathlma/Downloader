import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import tempfile

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# FFmpeg configuration
FFMPEG_SETTINGS = {
    'ffmpeg_location': '/usr/bin/ffmpeg',
    'postprocessor_args': [
        '-movflags', '+faststart',
        '-acodec', 'libmp3lame',
        '-vcodec', 'libx264',
        '-f', 'mp4'  # Force container format
    ]
}

async def download_media(update: Update, media_type: str):
    try:
        url = update.message.text.split(maxsplit=1)[1]
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                **FFMPEG_SETTINGS,
                'format': 'bestvideo[height<=720]+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
                'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
                'restrictfilenames': True,
                'merge_output_format': 'mp4',
                'fixup': 'force',  # Always repair files
                'extractor_args': {
                    'tiktok': {
                        'headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        }
                    }
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await update.message.reply_text("⏳ Downloading content...")
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                # Verify file integrity
                if os.path.getsize(filename) < 1024:  # At least 1KB
                    raise ValueError("File too small - likely corrupted")

                await update.message.reply_text("🔄 Finalizing file for Telegram...")
                
                # Re-encode with FFmpeg for Telegram compatibility
                temp_file = f"{tmp_dir}/telegram_ready.{'mp4' if media_type == 'video' else 'mp3'}"
                os.system(
                    f"ffmpeg -i '{filename}' -c:v libx264 -preset fast -movflags +faststart "
                    f"-c:a aac -b:a 192k -y '{temp_file}'"
                )

                # Send file
                with open(temp_file, 'rb') as f:
                    if media_type == 'video':
                        await update.message.reply_video(
                            video=f,
                            caption=info.get('title', ''),
                            supports_streaming=True,
                            read_timeout=120,
                            write_timeout=120
                        )
                    else:
                        await update.message.reply_audio(
                            audio=f,
                            title=info.get('title', '')[:64],
                            performer=info.get('uploader', '')[:64]
                        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Failed to process: {str(e)}")

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
    app.run_polling()

if __name__ == '__main__':
    main()
