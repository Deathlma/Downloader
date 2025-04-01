import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import tempfile
import subprocess

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

FFMPEG_SETTINGS = {
    'ffmpeg_location': '/usr/bin/ffmpeg',
    'postprocessor_args': [
        '-movflags', '+faststart',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '192k'
    ]
}

async def safe_ffmpeg_convert(input_path, output_path):
    """Convert media with proper error handling"""
    try:
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-movflags', '+faststart',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',  # Overwrite without asking
            output_path
        ]
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if not os.path.exists(output_path):
            raise ValueError("FFmpeg failed to create output file")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return False

async def download_media(update: Update, media_type: str):
    try:
        url = update.message.text.split(maxsplit=1)[1]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Download original file
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
                'outtmpl': f'{tmp_dir}/original.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'ffmpeg_location': '/usr/bin/ffmpeg'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await update.message.reply_text("⬇️ Downloading content...")
                info = ydl.extract_info(url, download=True)
                original_file = ydl.prepare_filename(info)

                # 2. Verify download
                if not os.path.exists(original_file):
                    raise ValueError("Download failed - no file created")
                
                if os.path.getsize(original_file) < 1024:
                    raise ValueError("File too small - likely corrupted")

                # 3. Convert for Telegram
                output_ext = 'mp4' if media_type == 'video' else 'mp3'
                output_file = f"{tmp_dir}/converted.{output_ext}"
                
                await update.message.reply_text("🔄 Optimizing for Telegram...")
                if not await safe_ffmpeg_convert(original_file, output_file):
                    raise ValueError("File conversion failed")
                
                # 4. Send to Telegram
                await update.message.reply_text("📤 Uploading...")
                with open(output_file, 'rb') as f:
                    if media_type == 'video':
                        await update.message.reply_video(
                            video=f,
                            caption=info.get('title', '')[:1024],
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

    except IndexError:
        await update.message.reply_text("❌ Please provide a URL after the command")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Failed: {str(e)}")

# ... (keep the rest of your code unchanged) ...
