import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="CF Risk Matrix", layout="wide")

# --- STYLING (Yellow Accents like Cyber_Folks) ---
st.markdown("""
    <style>
    .stButton>button {
        background-color: #FFD700;
        color: black;
        font-weight: bold;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Cyber_Folks: Risk & Opportunity Matrix")
st.markdown("Dynamic generator for the 'Investment Risks' section.")

# --- 1. SESSION STATE (Memory) ---
if 'events' not in st.session_state:
    # Dodajmy przykładowe dane na start, żebyś widział efekt od razu
    st.session_state['events'] = [
        {"Event": "PrestaShop Acquisition Success", "Probability (%)": 75, "Impact Score": 8},
        {"Event": "Regulatory: No Chinese Packages", "Probability (%)": 60, "Impact Score": 6},
        {"Event": "Debt Costs Increase (WIBOR)", "Probability (%)": 40, "Impact Score": -4},
        {"Event": "Integration Failure", "Probability (%)": 20, "Impact Score": -8}
    ]

# --- 2. SIDEBAR - INPUTS ---
with st.sidebar:
    st.header("📝 Add Strategic Event")
    st.markdown("Use this to map risks for the CFA Report.")
    
    # Input fields
    name = st.text_input("Event Name", placeholder="e.g. AI Disruption")
    prob = st.slider("Probability of Occurrence (%)", 0, 100, 50)
    impact = st.slider("Valuation Impact (-10 to +10)", -10, 10, 0, 
                       help="Negative = Risk, Positive = Opportunity")
    
    col1, col2 = st.columns(2)
    
    # ADD Button
    if col1.button("➕ Add Point"):
        if name:
            st.session_state['events'].append({
                "Event": name,
                "Probability (%)": prob,
                "Impact Score": impact
            })
            st.success(f"Added: {name}")
        else:
            st.error("Please enter a name!")

    # UNDO Button
    if col2.button("Undo Last"):
        if st.session_state['events']:
            st.session_state['events'].pop()
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear All Data"):
        st.session_state['events'] = []
        st.rerun()

# --- 3. CHART VISUALIZATION ---

if st.session_state['events']:
    df = pd.DataFrame(st.session_state['events'])
    
    # Layout: Chart on top, Table below
    st.subheader("📊 Strategic Matrix (Ready for Report)")
    
    # Create Figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # --- A. BACKGROUND SHADING (Tło) ---
    # Left Side (Risk) - Light Red
    ax.axvspan(-11, 0, color='#ff9999', alpha=0.15) 
    # Right Side (Opportunity) - Light Green
    ax.axvspan(0, 11, color='#99ff99', alpha=0.15)
    
    # --- B. AXIS LINES ---
    ax.axhline(50, color='gray', linestyle='--', linewidth=1, alpha=0.6) # 50% Prob
    ax.axvline(0, color='black', linestyle='-', linewidth=1.5, alpha=0.8) # Center Line
    
    # --- C. SCATTER POINTS ---
    # Logic: Green dots for opportunities, Red for risks
    colors = ['#d62728' if x < 0 else '#2ca02c' for x in df['Impact Score']]
    
    # Draw points with black edge for contrast
    ax.scatter(df['Impact Score'], df['Probability (%)'], c=colors, s=300, alpha=0.9, edgecolors='black', linewidth=1.5, zorder=3)
    
    # --- D. LABELS & ANNOTATIONS ---
    for i, txt in enumerate(df['Event']):
        # Smart positioning of text to avoid overlap with dot
        ax.annotate(txt, (df['Impact Score'][i], df['Probability (%)'][i]), 
                    xytext=(0, 10), textcoords='offset points', 
                    ha='center', fontsize=10, fontweight='bold', 
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.7))

    # --- E. CYBER_FOLKS STYLING ---
    # Titles
    ax.set_title("RISK & OPPORTUNITY MATRIX | CYBER_FOLKS S.A.", fontsize=16, fontweight='bold', color='black', pad=20)
    ax.set_xlabel("Impact on Valuation (Negative <--------------------> Positive)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Probability of Occurrence (%)", fontsize=11, fontweight='bold')
    
    # Quadrant Descriptions (Watermarks)
    ax.text(-9.5, 95, "KEY THREATS\n(Mitigation Required)", color='#8B0000', fontsize=12, fontweight='bold', alpha=0.7)
    ax.text(5.5, 95, "KEY DRIVERS\n(Upside Potential)", color='#006400', fontsize=12, fontweight='bold', alpha=0.7)
    
    # Footer / Source
    fig.text(0.99, 0.01, 'Source: Team Estimates, CFA Research Report 2025', 
             ha='right', fontsize=9, color='gray', style='italic')

    # Axis Limits
    ax.set_xlim(-10.5, 10.5)
    ax.set_ylim(0, 105)
    
    # Grid
    ax.grid(True, linestyle=':', alpha=0.4, zorder=0)
    
    # Display Plot
    st.pyplot(fig)
    
    # Show Data Table below
    with st.expander("See Data Table"):
        st.dataframe(df, use_container_width=True)

else:
    st.info(" Add events in the sidebar to generate the Cyber_Folks matrix.")