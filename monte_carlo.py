import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Mastercard Valuation", layout="wide")
st.title("💎 Advanced Monte Carlo Valuation (3-Stage DCF)")
st.markdown("""
**Target:** Mastercard (MA) style valuation.
Includes **3-Stage Growth Fade** (High -> Transition -> Stable) and **Dual Terminal Value Methods**.
""")

# --- SECTION 1: SIDEBAR INPUTS ---
with st.sidebar:
    st.header("1. Financials (Base Case - USD)")
    
    # Dane szacunkowe dla Mastercard (w mld USD, akcje w mln)
    fcf_year_0 = st.number_input("FCF (Year 0) [$ bn]", value=11.5, help="Free Cash Flow (TTM)")
    net_debt = st.number_input("Net Debt [$ bn]", value=5.0, help="Total Debt - Cash. MA often has low/negative net debt.")
    shares = st.number_input("Shares Outstanding [m]", value=930.0, help="Diluted Shares")
    
    st.markdown("---")
    st.header("2. Growth Stages")
    
    # STAGE 1
    st.subheader("Stage 1: High Growth (Y1-Y5)")
    g_high_mean = st.slider("Avg. Growth (CAGR) [%]", 0.0, 25.0, 14.0) / 100
    g_high_std = st.number_input("St. Dev Stage 1 (+/- %)", value=2.0) / 100
    
    # STAGE 2 (Transition is Automatic)
    st.info("ℹ️ Stage 2 (Y6-Y10) will linearly fade from Stage 1 Growth down to Terminal Growth.")

    st.markdown("---")
    st.header("3. Terminal Value & WACC")
    
    # WACC INPUTS
    col_wacc1, col_wacc2 = st.columns(2)
    with col_wacc1:
        wacc_mean = st.number_input("Target WACC [%]", value=8.0, step=0.1) / 100
    with col_wacc2:
        wacc_std = st.number_input("WACC Volatility", value=0.8, step=0.1) / 100
        
    # TERMINAL METHOD SELECTION
    tv_method = st.radio("Terminal Value Method", ["Gordon Growth (Perpetuity)", "Exit Multiple (EV/FCF)"])
    
    if tv_method == "Gordon Growth (Perpetuity)":
        g_term_mean = st.number_input("Terminal Growth (g) [%]", value=2.5, step=0.1) / 100
        g_term_std = st.number_input("Volatility g (+/-)", value=0.5, step=0.1) / 100
    else:
        # Exit Multiple Inputs
        st.write("**Exit Multiple Assumptions (Year 10)**")
        exit_mult_mean = st.number_input("Target EV/FCF Multiple [x]", value=20.0, step=0.5)
        exit_mult_std = st.number_input("Multiple Volatility [x]", value=2.0, step=0.5)

    st.markdown("---")
    simulations = st.select_slider("Iterations", options=[1000, 5000, 10000, 20000], value=5000)

# --- SECTION 2: CALCULATION ENGINE (3-STAGE) ---
def run_advanced_simulation():
    # 1. Randomize Inputs
    wacc_sim = np.random.normal(wacc_mean, wacc_std, simulations)
    
    # Growth Vectors
    g_stage1_sim = np.random.normal(g_high_mean, g_high_std, simulations)
    
    # Terminal Inputs based on Method
    if tv_method == "Gordon Growth (Perpetuity)":
        g_term_sim = np.random.normal(g_term_mean, g_term_std, simulations)
    else:
        # For Fade calculation, we still need a 'proxy' long-term growth 
        # to fade towards, typically inflation (2-3%)
        g_term_sim = np.full(simulations, 0.025) 
        exit_mult_sim = np.random.normal(exit_mult_mean, exit_mult_std, simulations)

    # 2. PROJECTION LOOP (10 YEARS)
    pv_projection = np.zeros(simulations)
    current_fcf = np.full(simulations, fcf_year_0)
    last_g = g_stage1_sim # Start with high growth
    
    # We will store Year 10 FCF for Terminal Calculation
    fcf_year_10 = np.zeros(simulations)

    for year in range(1, 11):
        if year <= 5:
            # Stage 1: High Growth
            growth_rate = g_stage1_sim
        else:
            # Stage 2: Linear Fade (Interpolation)
            # Year 6 is 20% faded, Year 10 is 100% faded towards terminal
            fade_factor = (year - 5) / 5.0 
            growth_rate = g_stage1_sim * (1 - fade_factor) + g_term_sim * fade_factor
            
        current_fcf = current_fcf * (1 + growth_rate)
        discount_factor = (1 + wacc_sim) ** year
        pv_projection += current_fcf / discount_factor
        
        if year == 10:
            fcf_year_10 = current_fcf

    # 3. TERMINAL VALUE CALCULATION
    if tv_method == "Gordon Growth (Perpetuity)":
        # Gordon Growth on Year 11 FCF
        fcf_year_11 = fcf_year_10 * (1 + g_term_sim)
        denominator = np.maximum(wacc_sim - g_term_sim, 0.005) # Safety buffer
        tv = fcf_year_11 / denominator
    else:
        # Exit Multiple on Year 10 FCF
        tv = fcf_year_10 * exit_mult_sim
        
    # Discount TV back 10 years
    pv_tv = tv / ((1 + wacc_sim) ** 10)
    
    # 4. VALUATION
    enterprise_value = pv_projection + pv_tv
    equity_value = enterprise_value - net_debt
    share_price = np.maximum(equity_value *1000 / shares, 0)
    
    return share_price

# --- SECTION 3: DASHBOARD ---
if st.button("🔥 Run 3-Stage Monte Carlo"):
    
    with st.spinner('Calculating 3-Stage DCF with Linear Growth Fade...'):
        results = run_advanced_simulation()
        
        mean_val = np.mean(results)
        low_val = np.percentile(results, 5.0)   # 5% Conservative
        high_val = np.percentile(results, 95.0) # 95% Optimistic
        
        # --- METRICS ---
        st.write(f"### Valuation Results ({tv_method})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Conservative (5%)", f"${low_val:.2f}", delta="Buy Zone?")
        c2.metric("Mean Intrinsic Value", f"${mean_val:.2f}")
        c3.metric("Optimistic (95%)", f"${high_val:.2f}", delta="Sell Zone?")
        
        # --- VISUALIZATION ---
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.histplot(results, bins=100, kde=True, color="#3498db", element="step", alpha=0.5, ax=ax)
        
        # Add Lines
        ax.axvline(mean_val, color='red', linestyle='-', linewidth=2, label='Mean')
        ax.axvline(low_val, color='green', linestyle='--', label='5% Conf.')
        ax.axvline(high_val, color='green', linestyle='--', label='95% Conf.')
        
        ax.set_title(f"Mastercard Valuation Distribution (n={simulations})", fontsize=12)
        ax.set_xlabel("Share Price [$]")
        ax.legend()
        st.pyplot(fig)
        
        # --- EXPLANATION ---
        st.info(f"""
        **Methodology Note:**
        This model uses a **3-Stage approach**. 
        1. **Years 1-5:** High growth based on your input ({g_high_mean*100:.1f}%).
        2. **Years 6-10:** Growth smoothly **fades** linearly down to the terminal rate.
        3. **Terminal:** Calculated using **{tv_method}**.
        """)