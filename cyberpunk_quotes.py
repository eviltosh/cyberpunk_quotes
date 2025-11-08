import streamlit as st
import yfinance as yf
import requests
from io import BytesIO
from PIL import Image
import datetime
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Streamlit page setup ---
st.set_page_config(page_title="Cyberpunk Stock Tracker", page_icon="💹", layout="wide")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Controls")
tickers_input = st.sidebar.text_input("Enter stock tickers (comma-separated):", "AAPL, TSLA, NVDA")
period = st.sidebar.selectbox("Select time range:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds):", 10, 300, 60)
theme_choice = st.sidebar.radio("Theme:", ["Cyberpunk Glow", "Classic Trading Chart"])

# --- Apply Cyberpunk CSS for title ---
with open("cyberpunk_style_embedded.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Title with Cyberpunk CSS ---
st.markdown("<h1 class='cyberpunk-title'>💹 CYBERPUNK QUOTES</h1>", unsafe_allow_html=True)

# --- Parse tickers ---
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# --- Caching ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker, period):
    return yf.Ticker(ticker).history(period=period)

@st.cache_data(ttl=3600)
def get_info_cached(ticker):
    return yf.Ticker(ticker).get_info()

@st.cache_data(ttl=1800)
def get_company_news(symbol):
    FINNHUB_API_KEY = "d46sh99r01qgc9eud1e0d46sh99r01qgc9eud1eg"
    FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"
    today = datetime.date.today()
    past = today - datetime.timedelta(days=30)
    params = {"symbol": symbol, "from": past.isoformat(), "to": today.isoformat(), "token": FINNHUB_API_KEY}
    try:
        response = requests.get(FINNHUB_NEWS_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [item for item in data if item.get("headline") and item.get("url")]
        return []
    except:
        return []

# --- Live Refresh ---
placeholder = st.empty()

while True:
    with placeholder.container():
        for ticker in tickers:
            try:
                info = get_info_cached(ticker)
                hist = get_stock_data(ticker, period)

                if hist.empty:
                    st.warning(f"No data available for {ticker}")
                    continue

                # --- Company Header: logo + name ---
                logo_url = info.get("logo_url")
                if not logo_url:
                    domain = info.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]
                    if domain:
                        logo_url = f"https://logo.clearbit.com/{domain}"

                header_col1, header_col2 = st.columns([1, 4])
                with header_col1:
                    if logo_url:
                        try:
                            r = requests.get(logo_url, timeout=5)
                            if r.status_code == 200:
                                st.image(Image.open(BytesIO(r.content)), width=100)
                        except:
                            st.write("")
                with header_col2:
                    st.markdown(f"### {info.get('shortName', ticker)}")
                    st.caption(f"{info.get('sector', 'N/A')} | {info.get('industry', 'N/A')}")

                # --- Chart ---
                if theme_choice == "Cyberpunk Glow":
                    import matplotlib.pyplot as plt
                    import mplcyberpunk
                    plt.style.use("cyberpunk")
                    fig, ax = plt.subplots(figsize=(10,5))
                    ax.plot(hist.index, hist["Close"], label=ticker, linewidth=2)
                    ax.set_title(f"{ticker} Stock Price ({period})", fontsize=14)
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Price ($)")
                    plt.legend()
                    mplcyberpunk.add_glow_effects()
                    st.pyplot(fig)
                else:
                    # Classic Trading Chart (Plotly)
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7,0.3])
                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name='Price',
                        increasing_line_color='green',
                        decreasing_line_color='red'
                    ), row=1, col=1)
                    fig.add_trace(go.Bar(
                        x=hist.index,
                        y=hist['Volume'],
                        name='Volume',
                        marker_color='blue',
                        opacity=0.3
                    ), row=2, col=1)

                    fig.update_layout(
                        template='plotly_white',
                        title=f"{ticker} Classic Trading Chart",
                        xaxis=dict(rangeslider_visible=False),
                        yaxis=dict(title="Price ($)"),
                        yaxis2=dict(title="Volume"),
                        hovermode="x unified",
                        height=700,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                # --- Metrics & Summary ---
                col1, col2, col3, col4 = st.columns(4)
                price = info.get("currentPrice")
                cap = info.get("marketCap")
                high = info.get("fiftyTwoWeekHigh")
                low = info.get("fiftyTwoWeekLow")
                with col1: st.metric("Current Price", f"${price:,.2f}" if price else "N/A")
                with col2: st.metric("Market Cap", f"${cap:,.0f}" if cap else "N/A")
                with col3: st.metric("52w High / Low", f"${high} / ${low}")
                with col4:
                    hist_5d = get_stock_data(ticker, "5d")
                    if len(hist_5d) >= 2:
                        change = hist_5d["Close"].iloc[-1] - hist_5d["Close"].iloc[-2]
                        pct = (change / hist_5d["Close"].iloc[-2]) * 100
                        st.metric("Daily Change", f"${change:.2f}", f"{pct:.2f}%")

                st.write(info.get("longBusinessSummary", "No company description available."))
                st.markdown("---")

                # --- News ---
                st.subheader(f"📰 {ticker} Recent News")
                news = get_company_news(ticker)
                if news:
                    for article in news[:5]:
                        dt = datetime.datetime.fromtimestamp(article.get("datetime", 0))
                        t_str = dt.strftime("%b %d, %Y")
                        st.markdown(f"<div class='news-card'><a href='{article.get('url')}' target='_blank'><b>{article.get('headline')}</b></a><br><small>{article.get('source', 'Unknown')} | {t_str}</small></div>", unsafe_allow_html=True)
                else:
                    st.info("No recent news available.")

                st.markdown("<hr style='border: 1px solid #00f5ff; opacity: 0.3;'>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Could not load info for {ticker}: {e}")

        st.caption(f"🔁 Auto-refreshing every {refresh_rate} seconds... (Theme: {theme_choice})")

    time.sleep(refresh_rate)
    st.rerun()
