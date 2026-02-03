import streamlit as st
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Ważne Pytanie ❤️",
    page_icon="💌",
    layout="centered"
)

# --- STYLIZACJA (CSS) ---
# Tutaj ustawiamy różowe tło, czerwone napisy i styl przycisków
st.markdown("""
    <style>
    /* Tło całej strony */
    .stApp {
        background: linear-gradient(to bottom, #ffcccc, #ffe6e6);
    }
    
    /* Styl nagłówków */
    h1 {
        color: #cc0000;
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        font-size: 3.5rem !important;
        text-shadow: 2px 2px 4px #ff9999;
    }
    
    h3 {
        color: #ff3333;
        text-align: center;
        font-style: italic;
    }
    
    /* Wyśrodkowanie przycisków */
    .stButton button {
        width: 100%;
        font-size: 20px;
        font-weight: bold;
        border-radius: 15px;
        padding: 15px;
    }
    
    /* Kontener na wynik */
    .success-box {
        padding: 20px;
        background-color: white;
        border-radius: 15px;
        border: 2px solid #ff3333;
        text-align: center;
        color: #cc0000;
        font-size: 1.2rem;
        margin-top: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- TREŚĆ APLIKACJI ---

# Odstęp od góry
st.write("") 
st.write("") 

# Główne pytanie
st.title("Gosiu! 🌹")
st.markdown("### Czy zostaniesz moją Walentynką?")
st.write("") # Odstęp

# Układ kolumn dla przycisków
col1, col2, col3 = st.columns([1, 4, 1]) # Środkujemy
with col2:
    # Używamy stanu sesji, żeby zapamiętać wybór
    if 'odpowiedz' not in st.session_state:
        st.session_state.odpowiedz = None

    # PRZYCISKI
    col_tak, col_nie = st.columns(2)
    
    with col_tak:
        if st.button("TAK 😍", type="primary"):
            st.session_state.odpowiedz = "tak"
            
    with col_nie:
        if st.button("NIE 🤔"):
            st.session_state.odpowiedz = "nie"

# --- LOGIKA ODPOWIEDZI ---

if st.session_state.odpowiedz == "tak":
    st.balloons() # Balony lecą do góry!
    st.markdown("""
        <div class="success-box">
            <h2>🎉 GRATULACJE! 🎉</h2>
            <p>Wybrałaś jedyną słuszną opcję!</p>
            <p><b>Proszę się skontaktować ze mną w ramach ustalenia terminu i aktywności! 🥂</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    # Opcjonalnie: serduszka spadające (śnieg)
    try:
        st.snow()
    except:
        pass

elif st.session_state.odpowiedz == "nie":
    st.error("⛔ Błąd systemu!")
    st.warning("Coś Ci się chyba pomyliło! Spróbuj ponownie! 😉")
    
    # Reset przycisku po chwili (opcjonalne, żeby mogła kliknąć znowu)
    if st.button("Spróbuj ponownie"):
        st.session_state.odpowiedz = None
        st.rerun()