import requests
import json
import streamlit as nn
import os
import time
import base64
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder, speech_to_text
from backend import search_sarees

# =========================================================================
# AVATAR IMAGES
# =========================================================================
MICKEY_SPEAKING_IMAGE = "mickey_mouse.gif"
MICKEY_LISTENING_IMAGE = "mickey_mouse.gif"
# =========================================================================
# PAGE CONFIG
# =========================================================================
nn.set_page_config(
    page_title="SareeAI Kiosk",
    page_icon="🛍️",
    layout="wide"
)

# Initialize tracking variables so greeting loops don't repeat infinitely
if "last_language" not in nn.session_state:
    nn.session_state["last_language"] = None
if "spoken_greeting" not in nn.session_state:
    nn.session_state["spoken_greeting"] = False

# =========================================================================
# TEXT TO SPEECH
# =========================================================================
def text_to_speech(text, lang_code='en'):
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_filename = "greeting.mp3"
        tts.save(audio_filename)

        with open(audio_filename, "rb") as f:
            audio_bytes = f.read()

        audio_b64 = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
        """
        nn.markdown(audio_html, unsafe_allow_html=True)
    except Exception:
        nn.warning("Unable to generate voice greeting.")

# =========================================================================
# OLLAMA EXTRACTION
# =========================================================================
def extract_requirements(transcript):
    prompt = f"""
You are an entity extraction assistant. Your job is to extract customer requirements from a statement and format them into JSON.

Rules:
1. Return ONLY a valid JSON object. Do not include any introductory or concluding text.
2. CRITICAL: If a specific field is NOT mentioned by the customer, you MUST set its value to "Any". Do not guess or assume values.
3. Budget must be an integer. If no budget is mentioned, set it to 999999.
4. Allowed Values for validation:
   - occasion: "Wedding", "Party", "Casual", "Farewell", or "Any"
   - fabric: "Silk", "Georgette", "Cotton", "Organza", or "Any"
   - color: "Red", "Blue", "Yellow", "Pink", or "Any"

Strict Prompt Examples:
- Input: "show me silk sarees"
  Output: {{"name": "Any", "occasion": "Any", "budget": 999999, "fabric": "Silk", "color": "Any"}}
- Input: "something for a party under 5000"
  Output: {{"name": "Any", "occasion": "Party", "budget": 5000, "fabric": "Any", "color": "Any"}}

Customer Statement to Process:
"{transcript}"

JSON Output:
"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma:2b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0  # Forces the model to be strict and stop guessing
                }
            },
            timeout=60
        )
        raw_text = response.json()["response"]
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1

        if start != -1 and end != -1:
            json_text = raw_text[start:end]
            return json.loads(json_text)
    except Exception as e:
        nn.error(f"LLM Error: {e}")

    return {
        "name": "Any",
        "occasion": "Any",
        "budget": 999999,
        "fabric": "Any",
        "color": "Any"
    }

# =========================================================================
# HEADER UI
# =========================================================================
nn.title("🛍️ SareeAI: Context-Aware Smart Retail Kiosk")
nn.subheader("AI-Powered Multilingual Smart Shopping Assistant")
nn.write("---")

# Default global filter values 
filters = {
    "occasion": "Any",
    "budget": 999999,
    "fabric": "Any",
    "color": "Any"
}

# =========================================================================
# TWO COLUMN LAYOUT (50/50 Screen Split)
# =========================================================================
col1, col2 = nn.columns([1, 1])

# =========================================================================
# LEFT PANEL (Avatar, Input Mechanics, and Processing Status)
# =========================================================================
with col1:
    nn.markdown("### 🤖 Customer Assistant Avatar")
    
    avatar_placeholder = nn.empty()
    status_placeholder = nn.empty()

    language = nn.selectbox(
        "🗣️ Select Your Language",
        ["English", "Hindi"]
    )

    lang_map = {"English": "en", "Hindi": "hi"}

    # Reset audio trigger state if customer swaps kiosk language input
    if nn.session_state["last_language"] != language:
        nn.session_state["last_language"] = language
        nn.session_state["spoken_greeting"] = False

    if language == "Hindi":
        greeting_text = "नमस्ते, मैं आपकी क्या मदद कर सकती हूँ?"
    else:
        greeting_text = "Hello, how can I help you today?"

    # --- CRITICAL FIX: Smart Audio Playback Control ---
    if not nn.session_state["spoken_greeting"]:
        avatar_placeholder.image(
            MICKEY_SPEAKING_IMAGE,
            caption="Welcome to SareeAI",
            use_container_width=True
        )
        status_placeholder.info("🗣️ Assistant State: Greeting Customer")
        text_to_speech(greeting_text, lang_code=lang_map[language])
        nn.session_state["spoken_greeting"] = True
        time.sleep(1.5) # Allow speech buffer window

    # --- CRITICAL FIX: Pinning elements inside left column container context ---
    nn.markdown("## 🎤 Voice Shopping Assistant")
    
    transcript = speech_to_text(
        start_prompt="🎙️ Click to Speak",
        stop_prompt="⏹️ Stop Recording",
        language=lang_map[language],
        just_once=True,
        use_container_width=True,
        key="kiosk_stt"
    )

    # Dynamic State Swap based on recording interaction
    if transcript:
        avatar_placeholder.image(
            MICKEY_SPEAKING_IMAGE,
            caption="Processing your request...",
            use_container_width=True
        )
        status_placeholder.success("🧠 Assistant State: Processing Context Entities")
    else:
        avatar_placeholder.image(
            MICKEY_LISTENING_IMAGE,
            caption="Listening carefully to your preferences...",
            use_container_width=True
        )
        status_placeholder.warning("🎧 Assistant State: Standing by / Listening for Input")
        transcript = ""

    nn.subheader("📝 Transcript")
    nn.text_area(
        "Customer Speech",
        transcript,
        height=100,
        placeholder="Your transcribed speech will appear here after recording stops..."
    )

    if transcript:
        extracted = extract_requirements(transcript)
        nn.subheader("🧠 Extracted Requirements")
        nn.json(extracted)

        filters = {
            "occasion": extracted.get("occasion", "Any"),
            "budget": int(extracted.get("budget", 999999)),
            "fabric": extracted.get("fabric", "Any"),
            "color": extracted.get("color", "Any")
        }

        nn.success(
            f"**Applied Filters:** Occasion: {filters['occasion']} | Fabric: {filters['fabric']} | Color: {filters['color']} | Budget: ₹{filters['budget']}"
        )

# =========================================================================
# RIGHT PANEL (Live Database Outputs matching Extract Values)
# =========================================================================
with col2:
    nn.markdown("### Recommendations")

    matches = search_sarees(
        occasion=filters["occasion"],
        max_budget=filters["budget"],
        fabric=filters["fabric"],
        color=filters["color"]
    )

    if len(matches) == 0:
        nn.error("No sarees found matching your filters in our catalog database.")
    else:
        nn.success(f"🎉 Found {len(matches)} match(es) specifically curated for you:")

        for saree in matches:
            with nn.container():
                inner_col1, inner_col2 = nn.columns([1, 2])
                
                with inner_col1:
                    if os.path.exists(saree["image_url"]):
                        nn.image(
                            saree["image_url"],
                            caption=saree["name"],
                            use_container_width=True
                        )
                    else:
                        nn.info("🖼️ Image Coming Soon")

                with inner_col2:
                    nn.markdown(f"#### {saree['name']}")
                    nn.markdown(f"**Occasion:** {saree['occasion']} | **Fabric:** {saree['fabric']} | **Color:** {saree['color']}")
                    nn.markdown(f"### ₹{saree['budget']:,}")

                nn.markdown("<hr style='border:1px dashed #ccc'>", unsafe_allow_html=True)