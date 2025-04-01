import os
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler

# Configure FFmpeg paths (critical for Railway)
FFMPEG_OPTS = {
    'ffmpeg_location': '/usr/bin/ffmpeg',
    'postprocessor_args': [
        '-fflags', '+genpts',
        '-strict', '-2'
    ]
}

async def download(update: Update, media_type: str):
    try:
        url = update.message.text.split()[1]
        
        ydl_opts = {
            **FFMPEG_OPTS,
            'format': 'best[height<=720]' if media_type == 'video' else 'bestaudio/best',
            'outtmpl': f'%(id)s.{media_type}',
            'noplaylist': True,
            'abort_on_error': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as f:
                if media_type == 'video':
                    await update.message.reply_video(f)
                else:
                    await update.message.reply_audio(f)
            
            os.remove(filename)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Command handlers
async def mp3(update: Update, context): await download(update, 'audio')
async def mp4(update: Update, context): await download(update, 'video')

app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
app.add_handler(CommandHandler('mp3', mp3))
app.add_handler(CommandHandler('mp4', mp4))
app.run_polling()
