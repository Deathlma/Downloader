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

# Critical FFmpeg configuration for Railway
FFMPEG_SETTINGS = {
    'ffmpeg_location': '/usr/bin/ffmpeg',  # Explicit path
    'postprocessor_args': [
        '-fflags', '+genpts',
        '-strict', '-2',  # Allow experimental codecs
        '-acodec', 'libmp3lame',  # Force MP3 codec
        '-vcodec', 'libx264'  # Force H.264
    ]
}

async def download_media(update: Update, media_type: str):
    try:
        url = update.message.text.split(maxsplit=1)[1]
        
        ydl_opts = {
            **FFMPEG_SETTINGS,  # Inherits our FFmpeg config
            'format': 'bestvideo[height<=720]+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
            'outtmpl': f'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
            'extract_flat': True,  # Check availability first
            'abort_on_error': False,
            'quiet': True,
            'no_warnings': True,
            
            # Platform-specific overrides
            'extractor_args': {
                'instagram': {'format': 'best'},
                'tiktok': {'format': 'bestvideo+bestaudio/best'},
                'twitter': {'format': 'bestvideo[height<=720]+bestaudio/best'}
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First check if content is available
            info = ydl.extract_info(url, download=False)
            
            if info.get('is_live'):
                await update.message.reply_text("❌ Live streams cannot be downloaded")
                return
                
            if not info.get('url'):
                await update.message.reply_text("❌ Content is unavailable or protected")
                return

            # Proceed with download
            await update.message.reply_text("⏳ Downloading...")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            # Send file
            with open(filename, 'rb') as f:
                if media_type == 'video':
                    await update.message.reply_video(
                        video=f,
                        caption=info.get('title', 'Video'),
                        supports_streaming=True
                    )
                else:
                    await update.message.reply_audio(
                        audio=f,
                        title=info.get('title', 'Audio'),
                        performer=info.get('uploader', 'Unknown')
                    )
            
            # Cleanup
            os.remove(filename)

    except IndexError:
        await update.message.reply_text("❌ Please provide a URL after the command")
    except yt_dlp.utils.DownloadError as e:
        if "DRM" in str(e):
            await update.message.reply_text("❌ DRM-protected content cannot be downloaded")
        else:
            await update.message.reply_text(f"❌ Download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("❌ An unexpected error occurred")

# Command handlers
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await download_media(update, 'audio')

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await download_media(update, 'video')

def main():
    # Create downloads directory if not exists
    os.makedirs('downloads', exist_ok=True)
    
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    app.add_handler(CommandHandler('mp3', mp3))
    app.add_handler(CommandHandler('mp4', mp4))
    app.run_polling()

if __name__ == '__main__':
    main()
