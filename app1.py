import streamlit as st
import asyncio
import edge_tts
import requests
import os
import whisper
from moviepy import (VideoFileClip, AudioFileClip, TextClip, 
                    CompositeVideoClip, concatenate_videoclips)

# ------------------- CLOUD CONFIG -------------------
os.environ["IMAGEMAGICK_BINARY"] = "/usr/bin/convert"
PEXELS_API_KEY = st.secrets.get("PEXELS_API_KEY", "")

st.set_page_config(page_title="AI Reel Maker", layout="centered")
st.title("🎬 Dynamic AI Faceless Reel Maker")
st.markdown("**Cloud Engine Active with Dynamic Themes**")

# ================== SIDEBAR ==================
st.sidebar.header("🎯 Reel Settings")
text_input = st.sidebar.text_area("Script (Voiceover)", "Self love is the foundation of a happy life. Every single day, remind yourself of your worth and keep pushing forward.", height=130)

st.sidebar.markdown("---")
st.sidebar.subheader("🎥 Video Layout")

# Number input ko handle karne ka sabse stable tareeka widget key ke sath
num_themes = st.sidebar.number_input("How many video clips (themes)?", min_value=1, max_value=10, value=3, step=1, key="num_themes_count")

themes_list = []
# Har text input ko unique key dena zaroori hai taake Streamlit crash na ho
for i in range(int(num_themes)):
    default_val = "nature" if i == 0 else f"motivation {i+1}"
    theme_val = st.sidebar.text_input(f"Theme {i+1} (Scene Keyword)", value=default_val, key=f"theme_input_key_{i}")
    themes_list.append(theme_val)

st.sidebar.markdown("---")
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
            clean_word = word['word'].strip()
            if clean_word:
                padded_text = f"{clean_word}\n " # Hidden space hack
                
                txt = TextClip(
                    text=padded_text, 
                    font_size=55, 
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    method='label'
                ).with_start(word['start']).with_end(word['end']) \
                 .with_position(('center', 0.70), relative=True)
                subtitle_clips.append(txt)
    return subtitle_clips

# ================== GENERATION ==================
if generate_button:
    if not PEXELS_API_KEY:
        st.error("❌ PEXELS_API_KEY missing in Streamlit Secrets!")
        st.stop()

    if not themes_list or any(t == "" for t in themes_list):
        st.error("❌ Please fill all the theme keywords before generating!")
        st.stop()

    with st.status("🏗️ Building your Custom Reel on Cloud...", expanded=True) as status:
        try:
            # 1. Voice
            st.write("🎙️ Generating Voice...")
            asyncio.run(edge_tts.Communicate(text_input, voice_option).save("voice.mp3"))

            # 2. Dynamic Media Download
            st.write(f"🔍 Downloading {len(themes_list)} Video Clips...")
            downloaded_files = []
            for idx, theme in enumerate(themes_list):
                st.write(f"  📥 Downloading scene {idx+1}: {theme}...")
                file_path = download_video(theme, idx+1)
                if file_path:
                    downloaded_files.append(file_path)
                else:
                    st.error(f"Could not find video for theme: {theme}")
                    st.stop()

            # 3. Assemble Dynamic Timeline
            st.write("🎬 Stitching Timeline...")
            audio = AudioFileClip("voice.mp3")
            total_dur = audio.duration
            
            # Har video ka duration divide karna
            clip_duration = total_dur / len(downloaded_files)
            
            video_clips = []
            for file_path in downloaded_files:
                v_clip = VideoFileClip(file_path).resized((720, 1280)).with_duration(clip_duration)
                video_clips.append(v_clip)
            
            video = concatenate_videoclips(video_clips).with_audio(audio)

            # 4. Subtitles
            st.write("✍️ Adding AI Subtitles...")
            subs = create_subtitles("voice.mp3")
            final = CompositeVideoClip([video] + subs)

            # 5. Render
            st.write("⚡ Rendering Final MP4...")
            final.write_videofile("final_reel.mp4", fps=24, codec="libx264", audio_codec="aac")
            
            status.update(label="✅ Custom Reel Ready!", state="complete", expanded=False)
            
            st.video("final_reel.mp4")
            with open("final_reel.mp4", "rb") as f:
                st.download_button("📥 Download to Device", f, file_name="AI_Custom_Reel.mp4", use_container_width=True)

        except Exception as e:
            st.error(f"Rendering Failed: {e}")
