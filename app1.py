import streamlit as st
import asyncio
import edge_tts
import requests
import os
import math
import whisper
from moviepy import (VideoFileClip, ImageClip, AudioFileClip,
                    TextClip, CompositeVideoClip, concatenate_videoclips)

# ------------------- CONFIG FOR CLOUD -------------------
# Cloud (Linux) standard path for ImageMagick conversion
os.environ["IMAGEMAGICK_BINARY"] = "/usr/bin/convert"

# Securing API Key using Streamlit Secrets (GitHub pe exposed nahi hogi)
PEXELS_API_KEY = st.secrets.get("PEXELS_API_KEY", "")

st.set_page_config(page_title="AI Reel Maker", layout="centered")
st.title("🎬 AI Faceless Reel Maker")
st.markdown("**Simple & Easy Reel Generator (Cloud Engine)**")

# ================== SIDEBAR OPTIONS ==================
st.sidebar.header("🎯 Reel Settings")

text_input = st.sidebar.text_area(
    "Text to Speak (Voiceover)",
    "Psychology facts reveal the hidden reasons behind human thoughts, emotions, and everyday behavior. Self love is the foundation of a happy life.",
    height=130
)

theme1 = st.sidebar.text_input(
    "Theme 1 (First Scene)",
    "man practicing self love"
)

theme2 = st.sidebar.text_input(
    "Theme 2 (Second Scene)",
    "man thinking deeply psychology"
)

voice_option = st.sidebar.selectbox(
    "Select Voice",
    ["en-US-ChristopherNeural (Male)", "en-US-EmmaNeural (Female)"]
)

generate_button = st.sidebar.button("🚀 Generate Reel", type="primary", use_container_width=True)

# ================== HELPER FUNCTIONS ==================
def download_media(theme, index):
    """Try Video first, then Image"""
    print(f"🔍 Searching: {theme}")
    
    # Try Video First
    for orientation in ["portrait", "landscape"]:
        url = f"https://api.pexels.com/videos/search?query={theme}&per_page=5&orientation={orientation}"
        headers = {"Authorization": PEXELS_API_KEY}
        try:
            response = requests.get(url, headers=headers).json()
            videos = response.get('videos', [])
            if videos:
                video_files = videos[0]['video_files']
                best = max(video_files, key=lambda x: x.get('width', 0) * x.get('height', 0))
                video_url = best['link']
                filename = f"media_{index}.mp4"
                
                with open(filename, 'wb') as f:
                    f.write(requests.get(video_url).content)
                return filename, "video"
        except Exception:
            pass
            
    # Try Image
    url = f"https://api.pexels.com/v1/search?query={theme}&per_page=5&orientation=portrait"
    headers = {"Authorization": PEXELS_API_KEY}
    try:
        response = requests.get(url, headers=headers).json()
        photos = response.get('photos', [])
        if photos:
            image_url = photos[0]['src']['large2x']
            filename = f"media_{index}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(requests.get(image_url).content)
            return filename, "image"
    except Exception:
        pass
        
    return None, None


def create_clip(media_tuple, duration):
    file, file_type = media_tuple
    REEL_W, REEL_H = 720, 1280
    
    if file_type == "video":
        clip = VideoFileClip(file)
        w, h = clip.size
        target_ratio = REEL_W / REEL_H
        if w / h > target_ratio:
            new_w = int(h * target_ratio)
            x1 = (w - new_w) // 2
            clip = clip.cropped(x1=x1, x2=x1 + new_w)
        else:
            new_h = int(w / target_ratio)
            y1 = (h - new_h) // 2
            clip = clip.cropped(y1=y1, y2=y1 + new_h)
        clip = clip.resized((REEL_W, REEL_H))
        
    else:  # Image
        clip = ImageClip(file).resized((REEL_W, REEL_H))
        clip = clip.with_effects([clip.fx("resize", lambda t: 1 + 0.015 * t)])
   
    clip = clip.with_duration(duration)
    return clip


def create_subtitles(VOICE_FILE):
    # Downloads model to cloud cache automatically
    model = whisper.load_model("base")
    result = model.transcribe(VOICE_FILE, fp16=False, word_timestamps=True)
    
    subtitle_clips = []
    REEL_W = 720
    subtitle_width = int(REEL_W * 0.85)

    for segment in result['segments']:
        for word in segment.get('words', []):
            word_text = word['word'].strip()
            if not word_text:
                continue
            
            # Linux servers use standard names like 'Arial' or 'Liberation-Sans'
            txt = TextClip(
                text=word_text,
                font_size=50,
                color='white',
                stroke_color='black',
                stroke_width=4,
                #font="DejaVuSans", 
                size=(subtitle_width, None),
                bg_color=(0, 0, 0, 160),
                method='caption'
            ).with_start(word['start']).with_end(word['end']) \
             .with_position(('center', 0.78), relative=True)
            subtitle_clips.append(txt)
    return subtitle_clips


# ================== MAIN GENERATION ==================
if generate_button:
    if not text_input or not theme1 or not theme2:
        st.error("Please fill all fields")
        st.stop()

    # Dynamic status display inside Streamlit UI
    with st.status("🎬 Processing Factory Engine...", expanded=True) as status:
        
        st.write("🎙️ Step 1: Generating Voiceover...")
        try:
            voice_name = voice_option.split(" ")[0]
            communicate = edge_tts.Communicate(text_input, voice_name)
            asyncio.run(communicate.save("voiceover.mp3"))
        except Exception as e:
            st.error(f"Voice Error: {e}")
            st.stop()

        st.write("🔍 Step 2: Extracting Assets from Pexels...")
        THEMES = [theme1, theme2]
        media_files = []
        for i, theme in enumerate(THEMES):
            file, ftype = download_media(theme, i+1)
            if file:
                media_files.append((file, ftype))

        if len(media_files) < 1:
            st.error("No media found on Pexels!")
            st.stop()

        st.write("🧠 Step 3: AI Transcribing Subtitles & Stitching Timeline...")
        try:
            audio = AudioFileClip("voiceover.mp3")
            total_duration = audio.duration

            seg_duration = total_duration / len(media_files)
            segments = [create_clip(media, seg_duration) for media in media_files]
            video = concatenate_videoclips(segments)
            video = video.with_audio(audio)

            subs = create_subtitles("voiceover.mp3")
            final = CompositeVideoClip([video] + subs)

            st.write("⚡ Step 4: Server Rendering Final MP4...")
            final.write_videofile("generated_reel.mp4", fps=24, codec="libx264",
                                threads=4, preset="medium", audio_codec="aac")

            status.update(label="🎉 Reel Successfully Generated!", state="complete", expanded=False)

        except Exception as e:
            st.error(f"Error during video creation: {e}")
            st.stop()

    # Display video on mobile/browser screen
    st.video("generated_reel.mp4")
    
    # Download button for Mobile phone storage
    with open("generated_reel.mp4", "rb") as file:
        st.download_button(
            label="📥 Download Reel to Device",
            data=file,
            file_name="AI_Faceless_Reel.mp4",
            mime="video/mp4",
            use_container_width=True
        )

    # Cleanup temporary local storage files on server
    for f, _ in media_files:
        if os.path.exists(f): os.remove(f)
    if os.path.exists("voiceover.mp3"): os.remove("voiceover.mp3")
