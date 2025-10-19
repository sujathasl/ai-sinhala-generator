# app.py
import os
import tempfile
from flask import Flask, render_template, request, send_file
from google.cloud import texttospeech
import requests
from dotenv import load_dotenv
import subprocess

load_dotenv()  # loads .env if exists

app = Flask(__name__)

# Set path to your Google TTS service account JSON (or set GOOGLE_APPLICATION_CREDENTIALS env)
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "keys/google-tts-key.json")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS

# Example: your video generator API info (replace with real provider)
VIDEO_API_URL = os.getenv("VIDEO_API_URL", "")  # e.g., "https://api.runwayml.com/v1/generate"
VIDEO_API_KEY = os.getenv("VIDEO_API_KEY", "")

def synthesize_sinhala(text, out_path):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)

    # voice selection - change if provider offers better Sinhala voice
    voice = texttospeech.VoiceSelectionParams(
        language_code="si-LK",  # Sinhala locale
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )

    with open(out_path, "wb") as out:
        out.write(response.audio_content)

def generate_video_from_text(prompt, out_video_path):
    """
    Placeholder function.
    Replace this with calls to your chosen video API (Runway / Pika / Kaiber).
    Example flow: POST prompt -> receive video_url or binary -> save to out_video_path
    """
    if VIDEO_API_URL and VIDEO_API_KEY:
        headers = {"Authorization": f"Bearer {VIDEO_API_KEY}"}
        data = {"prompt": prompt, "duration": 6}
        # Example (pseudo) request -- adapt per provider spec
        resp = requests.post(VIDEO_API_URL, json=data, headers=headers, stream=True)
        if resp.status_code == 200:
            with open(out_video_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            return False
    else:
        # If no API configured, use a local sample video as placeholder
        sample = os.path.join("static", "sample_video.mp4")
        if os.path.exists(sample):
            # copy sample to out_video_path
            with open(sample, "rb") as src, open(out_video_path, "wb") as dst:
                dst.write(src.read())
            return True
        return False

def mux_audio_video(video_path, audio_path, output_path):
    # Use ffmpeg to combine (ensure ffmpeg installed)
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-strict", "experimental",
        output_path
    ]
    subprocess.run(cmd, check=True)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/make", methods=["POST"])
def make():
    text = request.form.get("text", "").strip()
    if not text:
        return "No text provided", 400

    # Create temp files
    tmpdir = tempfile.mkdtemp()
    audio_path = os.path.join(tmpdir, "speech.mp3")
    video_path = os.path.join(tmpdir, "video.mp4")
    final_path = os.path.join(tmpdir, "final.mp4")

    # 1) Create Sinhala speech
    try:
        synthesize_sinhala(text, audio_path)
    except Exception as e:
        return f"Error creating TTS: {e}", 500

    # 2) Create or get video from video API
    ok = generate_video_from_text(text, video_path)
    if not ok:
        return "Video generation failed or not configured.", 500

    # 3) Merge audio + video using ffmpeg
    try:
        mux_audio_video(video_path, audio_path, final_path)
    except Exception as e:
        return f"Error merging audio+video: {e}", 500

    return send_file(final_path, as_attachment=True, download_name="ai_video.mp4")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
