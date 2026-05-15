import streamlit as st
import asyncio
import edge_tts
import requests
import os
import whisper
from moviepy import (VideoFileClip, AudioFileClip, TextClip, 
                    CompositeVideoClip, concatenate_videoclips)

# ------------------- CLOUD CONFIG -------------------
# ImageMagick path for Linux (Streamlit Cloud)
os.environ["IMAGEMAGICK_BINARY"] = "/usr/bin/convert"

# Fetching API Key from Streamlit Secrets
PEXELS_API_KEY = st.secrets.get("PEXELS_API_KEY", "")

st.set_page_config(page_title="AI Reel Maker", layout="centered")
st.title("🎬 AI Faceless Reel Maker")
st.markdown("**Cloud Engine Active**")

# ================== SIDEBAR ==================
st.sidebar.header("🎯 Reel Settings")
text_input = st.sidebar.text_area("Script (Voiceover)", "Self love is the foundation of a happy life.", height=130)
theme1 = st.sidebar.text_input("Theme 1", "nature")
theme2 = st.sidebar.text_input("Theme 2", "peaceful meditation")
voice_option = st.sidebar.selectbox("Select Voice", ["en-US-ChristopherNeural", "en-US-EmmaNeural"])
generate_button = st.sidebar.button("🚀 Generate Reel", type="primary", use_container_width=True)

# ================== FUNCTIONS ==================
def download_video(theme, index):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={theme}&per_page=1&orientation=portrait"
    try:
        response = requests.get(url, headers=headers).json()
        if 'videos' in response and len(response['videos']) > 0:
            video_url = response['videos'][0]['video_files'][0]['link']
            filename = f"media_{index}.mp4"
            with open(filename, 'wb') as f:
                f.write(requests.get(video_url).content)
            return filename
    except Exception as e:
        st.error(f"Download Error for {theme}: {e}")
    return None

def create_subtitles(VOICE_FILE):
    model = whisper.load_model("base")
    result = model.transcribe(VOICE_FILE, fp16=False, word_timestamps=True)
    subtitle_clips = []
    
    for segment in result['segments']:
        for word in segment.get('words', []):
            # No font name specified to avoid Linux errors - it will use system default
            txt = TextClip(
                text=word['word'].strip(),
                font_size=65,
                color='white',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(600, None)
            ).with_start(word['start']).with_end(word['end']).with_position(('center', 0.8), relative=True)
            subtitle_clips.append(txt)
    return subtitle_clips

# ================== GENERATION ==================
if generate_button:
    if not PEXELS_API_KEY:
        st.error("❌ PEXELS_API_KEY missing in Streamlit Secrets!")
        st.stop()

    with st.status("🏗️ Building your Reel on Cloud...", expanded=True) as status:
        try:
            # 1. Voice
            st.write("🎙️ Generating Voice...")
            asyncio.run(edge_tts.Communicate(text_input, voice_option).save("voice.mp3"))

            # 2. Media
            st.write("🔍 Downloading Assets...")
            file1 = download_video(theme1, 1)
            file2 = download_video(theme2, 2)

            if not file1 or not file2:
                st.error("Could not find videos on Pexels.")
                st.stop()

            # 3. Assemble
            st.write("🎬 Stitching Timeline...")
            audio = AudioFileClip("voice.mp3")
            total_dur = audio.duration
            
            # Simple resize to Reel format (9:16)
            v1 = VideoFileClip(file1).resized((720, 1280)).with_duration(total_dur/2)
            v2 = VideoFileClip(file2).resized((720, 1280)).with_duration(total_dur/2)
            
            video = concatenate_videoclips([v1, v2]).with_audio(audio)

            # 4. Subtitles
            st.write("✍️ Adding AI Subtitles...")
            subs = create_subtitles("voice.mp3")
            final = CompositeVideoClip([video] + subs)

            # 5. Render
            st.write("⚡ Rendering Final MP4...")
            final.write_videofile("final_reel.mp4", fps=24, codec="libx264", audio_codec="aac")
            
            status.update(label="✅ Reel Ready!", state="complete", expanded=False)
            
            st.video("final_reel.mp4")
            with open("final_reel.mp4", "rb") as f:
                st.download_button("📥 Download to Device", f, file_name="AI_Reel.mp4")

        except Exception as e:
            st.error(f"Rendering Failed: {e}")
