import streamlit as st
import requests
import os
import whisper
from gtts import gTTS  # Google TTS Backup for Cloud Bypass
from moviepy import (VideoFileClip, AudioFileClip, TextClip, 
                    CompositeVideoClip, concatenate_videoclips)

# ------------------- CLOUD CONFIG -------------------
os.environ["IMAGEMAGICK_BINARY"] = "/usr/bin/convert"
PEXELS_API_KEY = st.secrets.get("PEXELS_API_KEY", "")

st.set_page_config(page_title="AI Reel Maker", layout="centered")
st.title("🎬 Roman Urdu AI Faceless Reel Maker")
st.markdown("**Cloud Engine Active (Google Safe Mode)**")

# ================== SIDEBAR ==================
st.sidebar.header("🎯 Reel Settings")
text_input = st.sidebar.text_area("Script (Roman Urdu)", "Self love yani khud se muhabbat zindgi ki sab se barhi zaroorat hai. Har din khud ko apni value yaad dilayein.", height=130)

st.sidebar.markdown("---")
st.sidebar.subheader("🎥 Video Layout")

num_themes = st.sidebar.number_input("How many video clips (themes)?", min_value=1, max_value=10, value=3, step=1, key="num_themes_count")

active_themes = []
for i in range(int(num_themes)):
    st.sidebar.markdown(f"**Scene {i+1}**")
    is_removed = st.sidebar.checkbox(f"❌ Remove Scene {i+1}", key=f"remove_check_{i}")
    
    if not is_removed:
        default_val = "nature" if i == 0 else f"motivation {i+1}"
        theme_val = st.sidebar.text_input(f"Keyword for Scene {i+1}", value=default_val, key=f"theme_input_key_{i}", label_visibility="collapsed")
        active_themes.append(theme_val)
    else:
        st.sidebar.caption("*(This scene will be skipped)*")
    
    st.sidebar.markdown("---")

# --- MULTIPLE ACCENTS OPTIONS ---
voice_option = st.sidebar.selectbox(
    "Select Voice (Cloud Accent Mode)", 
    ["Urdu (Natural Pakistani)", "Hindi (Subcontinent Accent)", "English (UK Male Accent)"]
)

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
                padded_text = f"{clean_word}\n "
                
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

    if not active_themes or any(t == "" for t in active_themes):
        st.error("❌ Active scene keywords cannot be empty!")
        st.stop()

    with st.status("🏗️ Building your Custom Reel on Cloud...", expanded=True) as status:
        try:
            # 1. Voice Generation using Google (No-Block Bypass)
            st.write(f"🎙️ Generating Voice using Google Engine ({voice_option})...")
            
            # Map selection to language code
            if "Urdu" in voice_option:
                tts = gTTS(text=text_input, lang='ur', slow=False)
            elif "Hindi" in voice_option:
                tts = gTTS(text=text_input, lang='hi', slow=False)
            else:
                tts = gTTS(text=text_input, lang='en', tld='co.uk', slow=False)
                
            tts.save("voice.mp3")

            # 2. Media Download
            st.write(f"🔍 Downloading {len(active_themes)} Video Clips...")
            downloaded_files = []
            for idx, theme in enumerate(active_themes):
                st.write(f"  📥 Downloading active scene {idx+1}: {theme}...")
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
