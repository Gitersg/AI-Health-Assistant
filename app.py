import os
import re
# pyrefly: ignore [missing-import]
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App Configuration
st.set_page_config(
    page_title="AI Health Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Streamlit structure resets */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    
    /* Main body padding optimization */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1000px !important;
    }
    
    /* Clean up default Streamlit headers and footers */
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    footer {
        visibility: hidden !important;
        height: 0px !important;
    }
    
    /* Custom Sidebar decoration */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        color: #06b6d4;
        font-weight: 700;
    }
    
    /* Brand Logo / Title */
    .app-title {
        background: linear-gradient(90deg, #38bdf8, #0ea5e9, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Overwrite Streamlit default chat messages to make them look glassmorphic */
    [data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.35) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        margin-bottom: 1rem !important;
        padding: 1.25rem !important;
    }
    
    [data-testid="stChatMessage"][data-test-role="user"] {
        background: rgba(14, 165, 233, 0.12) !important;
        border: 1px solid rgba(14, 165, 233, 0.2) !important;
    }
    
    /* Premium Cards & Containers */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .disclaimer-card {
        border-left: 4px solid #ef4444;
        background: rgba(239, 68, 68, 0.05);
    }
    
    .emergency-card {
        border-left: 4px solid #ef4444;
        background: rgba(239, 68, 68, 0.12);
        animation: card-pulse-glow 2s infinite;
    }
    
    @keyframes card-pulse-glow {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.35); }
        70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    
    /* Contact List entries in emergency panel */
    .contact-item {
        background: rgba(15, 23, 42, 0.5);
        padding: 0.65rem;
        border-radius: 8px;
        margin-bottom: 0.4rem;
        border: 1px solid rgba(255, 255, 255, 0.04);
    }
    
    .contact-number {
        font-size: 1.2rem;
        font-weight: 700;
        color: #ef4444;
        display: block;
        margin-bottom: 0.1rem;
    }
    
    .contact-label {
        font-size: 0.75rem;
        color: #94a3b8;
    }
    
    /* Form inputs and buttons styling */
    .stButton > button {
        background: linear-gradient(135deg, #0d9488, #0f766e);
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #0f766e, #115e59) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3) !important;
    }
    
    .stChatInput {
        border-radius: 12px;
        background-color: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# Urgency Keywords for Fast Detection
URGENT_KEYWORDS = [
    r"\bchest\s+pain\b", r"\bheart\s+attack\b", r"\bbreathing\s+difficulty\b", 
    r"\bdifficulty\s+breathing\b", r"\bshortness\s+of\s+breath\b", r"\bchoking\b",
    r"\bunconscious\b", r"\bloss\s+of\s+consciousness\b", r"\bpassed\s+out\b",
    r"\bheavy\s+bleeding\b", r"\buncontrolled\s+bleeding\b", r"\bsevere\s+bleeding\b",
    r"\bsevere\s+pain\b", r"\bstroke\b", r"\bspeech\s+slur\b", r"\bslurred\s+speech\b",
    r"\bparalysis\b", r"\bface\s+droop\b", r"\bseizure\b", r"\bconvulsion\b",
    r"\bpoisoning\b", r"\boverdose\b", r"\bsevere\s+burn\b", r"\banaphylaxis\b",
    r"\bsevere\s+allergic\s+reaction\b", r"\bsuicidal\b", r"\bharm\s+myself\b"
]

def check_urgency(text):
    """
    Check if the user input contains emergency/urgent symptoms.
    """
    text_lower = text.lower()
    for pattern in URGENT_KEYWORDS:
        if re.search(pattern, text_lower):
            return True
    return False

# Initialize Login State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #06b6d4; margin-top: 10vh;'>🩺 AI Health Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Please authenticate to access your secure health assistant.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            user_name = st.text_input("Your Name", placeholder="e.g., John Doe")
            user_api_key = st.text_input("Gemini API Key", type="password", placeholder="Paste your API key here...")
            submit_button = st.form_submit_button("Access Assistant")
            
            if submit_button:
                if user_name and user_api_key:
                    st.session_state.user_name = user_name
                    st.session_state.api_key = user_api_key
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Please provide both your name and API key to continue.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Hide sidebar when not logged in
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
        </style>
    """, unsafe_allow_html=True)
    st.stop()

# Initialize Chat Session States
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"👋 **Welcome to the AI Health Assistant, {st.session_state.user_name}!**\n\nI am here to help you understand your symptoms, discuss potential common causes, and offer general home care tips for mild issues.\n\n💬 *Describe how you are feeling in natural language, and I will assist you. Please remember to consult a healthcare professional for accurate medical diagnosis.*"
        }
    ]

if "emergency_triggered" not in st.session_state:
    st.session_state.emergency_triggered = False

api_key = st.session_state.api_key

# Sidebar Content
with st.sidebar:
    # Logo / Header
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #06b6d4; font-weight: 800; margin-bottom: 0.5rem;'>🩺 AI Assistant</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; color: #10b981; font-size: 0.8rem; margin-bottom: 1.5rem;'><span style='display: inline-block; width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 6px #10b981; margin-right: 4px;'></span>User: <b>{st.session_state.user_name}</b></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Permanent Disclaimer
    st.markdown("""
    <div class="glass-card disclaimer-card">
        <h4 style="color: #ef4444; margin-top: 0; font-weight: 700;">⚠️ Strict Medical Disclaimer</h4>
        <p style="font-size: 0.85rem; line-height: 1.4; margin-bottom: 0; color: #cbd5e1;">
            This assistant is an AI-powered conversational tool for informational and educational purposes only. 
            It is <strong>NOT</strong> a replacement for professional medical advice, diagnosis, or treatment. 
            Always seek the advice of your physician or other qualified health providers with any questions you may have regarding a medical condition.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Emergency Contacts Section
    st.markdown("""
    <div class="glass-card emergency-card">
        <h4 style="color: #ef4444; margin-top: 0; display: flex; align-items: center; gap: 5px; font-weight: 700;">🚨 Emergency Contacts (India)</h4>
        <p style="font-size: 0.85rem; line-height: 1.4; margin-bottom: 10px; color: #cbd5e1;">
            If you are facing a medical emergency, do not wait. Call emergency services immediately:
        </p>
        <div class="contact-item">
            <span class="contact-number">112</span>
            <div class="contact-label">National Emergency Number (All-in-One)</div>
        </div>
        <div class="contact-item">
            <span class="contact-number">108</span>
            <div class="contact-label">Ambulance Services</div>
        </div>
        <div class="contact-item">
            <span class="contact-number">102</span>
            <div class="contact-label">Free Ambulance / Maternity Helpline</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Reliable Resources
    st.markdown("### 📚 Trusted Health Resources")
    st.markdown("""
    - [World Health Organization (WHO)](https://www.who.int)
    - [Mayo Clinic](https://www.mayoclinic.org)
    - [CDC (Centers for Disease Control)](https://www.cdc.gov)
    - [NHS Health A-Z](https://www.nhs.uk/conditions/)
    - [Ministry of Health & Family Welfare (MoHFW) India](https://www.mohfw.gov.in)
    """)
    
    # Find Doctors & Hospitals
    st.markdown("### 🔍 Find Nearby Healthcare")
    st.markdown("""
    Need to consult a doctor or find a hospital? Use these tools:
    - 📍 **[Google Maps: Hospitals Near Me](https://www.google.com/maps/search/hospitals+near+me)**
    - 📍 **[Google Maps: Doctors Near Me](https://www.google.com/maps/search/doctors+near+me)**
    - 🩺 **[Practo - Find & Book Doctors](https://www.practo.com)**
    """)

# Main Content Layout
st.markdown('<div class="app-title">🩺 AI Health Assistant</div>', unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-top: -10px;'>Your intelligent companion for symptom guidance, home care tips, and emergency awareness.</p>", unsafe_allow_html=True)

# Main Warning Banner (Persistent at the top if emergency is detected)
if st.session_state.emergency_triggered:
    st.markdown("""
    <div class="glass-card emergency-card" style="margin-bottom: 20px;">
        <h3 style="color: #ef4444; margin-top: 0;">🚨 Critical Health Alert</h3>
        <p style="font-size: 1.05rem; line-height: 1.5; margin-bottom: 10px;">
            The symptoms you described (or previous inputs) suggest a potential medical emergency. 
            <strong>Please do not rely on this AI assistant.</strong> 
            Take action immediately:
        </p>
        <ul>
            <li><strong>Call 112 or 108 immediately (India)</strong> or your local emergency line.</li>
            <li>Go to the nearest hospital's Emergency Department.</li>
            <li>Contact a family member, neighbor, or friend to assist you.</li>
        </ul>
        <div style="margin-top: 15px;">
            <a href="https://www.google.com/maps/search/emergency+hospitals+near+me" target="_blank" style="background-color: #ef4444; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: bold;">📍 Find Emergency Hospital on Google Maps</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Box
if user_query := st.chat_input("Describe your symptoms (e.g., 'I have a mild sore throat for 2 days' or 'My head hurts')"):
    
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
        
    # 2. Urgency Detection Layer 1: Heuristics
    urgency_detected = check_urgency(user_query)
    if urgency_detected:
        st.session_state.emergency_triggered = True
        
    # 3. Process with Gemini API
    if not api_key:
        with st.chat_message("assistant"):
            st.error("Please configure your Google Gemini API Key in the sidebar to get responses.")
    else:
        try:
            # Configure API
            genai.configure(api_key=api_key)
            
            # Setup Model
            system_instruction = (
                "You are an empathetic, professional AI Health Assistant. Your goal is to guide users inquiring about symptoms.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. If the user mentions any potential emergency or high-urgency symptoms (like chest pain, severe breathing difficulty, sudden slurred speech, facial drooping, loss of consciousness, heavy bleeding, poisoning, severe allergic reactions), you MUST start your response with a very prominent, clear, and urgent directive to CALL EMERGENCY SERVICES (112 or 108 in India) and seek immediate medical attention.\n"
                "2. When dealing with mild, non-emergency issues, follow these structure steps:\n"
                "   - Empathy & Verification: Acknowledge the user's situation and ask 2-3 relevant follow-up questions to gain more context (e.g., duration, triggers, severity).\n"
                "   - Possible Causes: List a few common potential causes in bullet points. Clearly emphasize these are just possibilities, not a diagnosis.\n"
                "   - Home Care: Provide general, safe, and actionable home care tips suitable for mild concerns.\n"
                "   - Medical Referral: Recommend consulting a healthcare professional for actual diagnosis.\n"
                "3. ALWAYS include a brief, clear medical disclaimer at the end of every message, stating that you are an AI assistant and not a medical doctor.\n"
                "4. Maintain a supportive, reassuring, but highly responsible and safe medical tone. Never diagnose or prescribe specific medications. Recommend OTC relief only with a strong advisory to check with a pharmacist or doctor."
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            # Convert session messages to Gemini's format
            # Gemini expects chat format with role "user" and "model"
            gemini_history = []
            # We skip the very first system-style greeting to avoid confusing the api, or convert appropriately.
            for msg in st.session_state.messages[1:-1]: # exclude initial greeting and the current query we're generating response for
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})
                
            chat = model.start_chat(history=gemini_history)
            
            # Show spinner while generating
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # Request streamed response
                response_stream = chat.send_message(user_query, stream=True)
                
                for chunk in response_stream:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
                
                # Check if model detected urgency and stated it (Layer 2)
                # If model response mentions 'emergency', '112', '108', 'immediate medical attention', etc., flag it.
                lower_response = full_response.lower()
                emergency_words = ["emergency", "call 112", "call 108", "hospital immediately", "emergency room", "emergency department", "immediate medical attention"]
                if any(w in lower_response for w in emergency_words):
                    # Trigger emergency state if the AI itself flags it
                    st.session_state.emergency_triggered = True
                
                message_placeholder.markdown(full_response)
                
            # Save assistant response to state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # If emergency state was triggered just now, rerun to show the main emergency banner
            if urgency_detected or st.session_state.emergency_triggered:
                st.rerun()
                
        except Exception as e:
            with st.chat_message("assistant"):
                st.error(f"An error occurred while connecting to the Gemini API: {str(e)}")
                st.info("Please verify that your API key is correct and you have an active internet connection.")
