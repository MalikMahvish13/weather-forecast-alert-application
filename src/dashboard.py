"""Streamlit client for the FastAPI weather service."""
from __future__ import annotations

import json
import os
from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("WEATHER_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="SkyWatch | Weather Intelligence", page_icon="🌦️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;color:#172B45}
.stApp, [data-testid="stAppViewContainer"] {background:linear-gradient(135deg,#f5f8ff 0%,#f7f9fc 55%,#eff8f8 100%);color:#172B45}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp li,.stApp label,.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stMarkdownContainer"] {color:#172B45}
.stApp h1,.stApp h2,.stApp h3,.stApp h4 {font-family:'Manrope',sans-serif;letter-spacing:-.035em}
.brand {font-family:'Manrope',sans-serif;font-weight:800;font-size:1.05rem;color:#102542;letter-spacing:-.04em}
.brand span {color:#2563EB}
.eyebrow {color:#52647D;text-transform:uppercase;letter-spacing:.12em;font-size:.72rem;font-weight:700}
.weather-hero {background:linear-gradient(120deg,#12315b,#22568b 62%,#28769c);color:#fff;padding:30px 34px;border-radius:24px;box-shadow:0 18px 45px #183c6326}
.weather-hero .eyebrow {color:#D7E8FF!important}.weather-hero h2 {color:#fff!important;margin:0}.weather-hero p {color:#E7F0FC!important;margin:.4rem 0 0}
.alert-card {padding:16px 18px;margin:8px 0;border-radius:14px;background:#fff;border:1px solid #E5EAF2;border-left:5px solid #D98200;box-shadow:0 5px 18px #183c630d}
.alert-critical {border-left-color:#C6283D}.alert-warning {border-left-color:#B86B00}.alert-title {font-weight:700;color:#182b45!important}.alert-message {color:#4D5F77!important;font-size:.91rem;margin-top:4px}
div[data-testid="stMetric"] {background:#fff;border:1px solid #DCE4EF;padding:16px 18px;border-radius:16px;box-shadow:0 6px 20px #183c6308}
div[data-testid="stMetric"] label,div[data-testid="stMetric"] [data-testid="stMetricLabel"] {color:#52647D!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {color:#132B49!important}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {color:#3E5876!important}
section[data-testid="stSidebar"] {background:#fff!important;border-right:1px solid #DCE4EF;color:#172B45}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] h4,section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#172B45!important}
/* Keep form controls legible even when the browser or OS prefers dark mode. */
.stApp input,.stApp textarea,[data-baseweb="input"] input,[data-baseweb="base-input"] input {background:#fff!important;color:#172B45!important;-webkit-text-fill-color:#172B45!important;caret-color:#172B45;border-color:#AAB8CA!important}
.stApp input::placeholder,.stApp textarea::placeholder {color:#65758A!important;-webkit-text-fill-color:#65758A!important;opacity:1}
[data-baseweb="select"]>div {background:#fff!important;color:#172B45!important;border-color:#AAB8CA!important}
[data-baseweb="select"] input,[data-baseweb="select"] span,[data-baseweb="select"] div {color:#172B45}
[data-baseweb="popover"],[role="listbox"],[role="option"] {background:#fff!important;color:#172B45!important}
[role="option"]:hover {background:#EAF1FB!important}
.stApp button[kind="primary"] {background:#2563EB!important;color:#fff!important;border:1px solid #1D4ED8!important}
.stApp button[kind="primary"] p {color:#fff!important}
.stApp button:not([kind="primary"]) {background:#fff;color:#172B45;border:1px solid #AAB8CA}
.stApp button:not([kind="primary"]) p {color:#172B45!important}
div[data-testid="stAlert"] {border-radius:12px;color:#172B45!important}
div[data-testid="stAlert"] p,div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {color:#172B45!important}
[data-testid="stDataFrame"],[data-testid="stTable"] {background:#fff;color:#172B45}
.footer {color:#53657C;font-size:.78rem;padding-top:22px}
.footer a {color:#1D4ED8!important}
@media(max-width:760px) {
  [data-testid="stAppViewBlockContainer"] {padding-left:1rem;padding-right:1rem;padding-top:1.25rem}
  .weather-hero {padding:22px 20px;border-radius:18px}
  .weather-hero h2 {font-size:1.65rem}
  [data-testid="stHorizontalBlock"] {flex-wrap:wrap;gap:.55rem}
  [data-testid="column"] {min-width:46%!important;flex:1 1 46%!important}
  div[data-testid="stMetric"] {padding:12px}
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=90, show_spinner=False)
def request_weather(params: dict) -> dict:
    """The dashboard delegates all data work and report creation to FastAPI."""
    try:
        response = requests.get(f"{API_URL}/weather", params=params, timeout=35)
    except requests.ConnectionError as exc:
        raise RuntimeError(f"Can't connect to the weather backend at {API_URL}. Start it with `uvicorn src.api:app --reload` and refresh.") from exc
    except requests.Timeout as exc:
        raise RuntimeError("The backend took too long to respond. Please try again.") from exc
    if response.status_code == 404:
        raise ValueError(response.json().get("detail", "City not found. Check the spelling."))
    if response.status_code >= 400:
        detail = response.json().get("detail", "The backend could not complete this request.")
        raise RuntimeError(str(detail))
    return response.json()


def render_alerts(alerts: list[dict]) -> None:
    if not alerts:
        st.success("No configured weather alerts for this forecast.")
        return
    for alert in alerts:
        severity = escape(alert.get("severity", "warning"))
        st.markdown(
            f"<div class='alert-card alert-{severity}'><div class='alert-title'>{escape(alert.get('title','Weather alert'))} · {severity.upper()}</div>"
            f"<div class='alert-message'>{escape(alert.get('message',''))}</div></div>", unsafe_allow_html=True)


with st.sidebar:
    st.markdown("<div class='brand'>🌦️ Sky<span>Watch</span></div>", unsafe_allow_html=True)
    st.caption("WEATHER INTELLIGENCE")
    st.markdown("---")
    page = st.radio("Workspace", ["Overview", "5-day forecast", "Alerts"], label_visibility="collapsed")
    st.markdown("#### Forecast settings")
    mode_label = st.selectbox("Data source", ["Live forecast", "Simulation"], index=1)
    mode = "live" if mode_label == "Live forecast" else "simulation"
    city = st.text_input("Search city", "London", placeholder="e.g. Mumbai")
    scenario = "normal"
    if mode == "simulation":
        scenario = st.selectbox("Simulation scenario", ["normal", "high_temperature", "heavy_rain", "high_humidity", "strong_wind", "thunderstorm"],
                                format_func=lambda x: x.replace("_", " ").title())
    with st.expander("Alert thresholds", expanded=False):
        heat = st.number_input("Temperature (°C)", value=35.0, step=1.0)
        humidity = st.number_input("Humidity (%)", value=85.0, min_value=1.0, max_value=100.0)
        rain = st.number_input("Rain probability (%)", value=70.0, min_value=1.0, max_value=100.0)
        wind = st.number_input("Wind speed (km/h)", value=50.0, min_value=1.0)
    refresh = st.button("↻  Refresh weather", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption(f"Backend · `{API_URL}`")

st.markdown("<div class='eyebrow'>WEATHER MONITORING · LIVE INSIGHTS</div>", unsafe_allow_html=True)
st.title("Weather overview")
st.caption("A clear view of the conditions ahead, with configurable alerts for your location.")

if refresh or "weather_report" not in st.session_state:
    if not city.strip():
        st.error("Enter a city name to request a forecast.")
    else:
        if refresh:
            request_weather.clear()
        params = {"city": city.strip(), "mode": mode, "scenario": scenario, "heat_c": heat,
                  "humidity_percent": humidity, "rain_probability_percent": rain, "wind_kmh": wind}
        with st.spinner("Connecting to the forecast service…"):
            try:
                st.session_state.weather_report = request_weather(params)
                st.session_state.weather_request_params = params
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))

report = st.session_state.get("weather_report")
if report:
    current = report.get("current", {})
    generated = report.get("generated_at_utc", "")
    updated = datetime.fromisoformat(generated.replace("Z", "+00:00")).strftime("%b %d, %H:%M UTC") if generated else ""
    source_text = "SIMULATED DATA" if report.get("mode") == "simulation" else "OPEN-METEO LIVE DATA"
    if report.get("mode") == "simulation":
        st.info(f"Simulation mode · {report.get('scenario','normal').replace('_',' ').title()} scenario · synthetic data, not a live forecast")
    st.markdown(f"<div class='weather-hero'><div class='eyebrow' style='color:#b9d5f5'>{escape(source_text)} · {escape(updated)}</div>"
                f"<h2>{escape(report.get('city',''))}{', ' + escape(report.get('country','')) if report.get('country') else ''}</h2>"
                f"<p>{escape(report.get('attribution',''))}</p></div>", unsafe_allow_html=True)

    if page == "Overview":
        st.markdown("### Current conditions")
        st.markdown(f"#### {escape(str(current.get('condition') or 'Weather conditions'))}")
        metrics = st.columns(6)
        vals = [
            ("Temperature", current.get("temperature_c"), "°C"),
            ("Feels like", current.get("feels_like_c"), "°C"),
            ("Humidity", current.get("humidity_percent"), "%"),
            ("Wind", current.get("wind_kmh"), "km/h"),
            ("Rain now", current.get("precipitation_mm"), "mm"),
            ("Rain chance", current.get("precipitation_probability_percent"), "%"),
        ]
        for col, (label, value, unit) in zip(metrics, vals):
            col.metric(label, f"{value:g} {unit}" if isinstance(value, (int, float)) else "—")
        st.markdown("### Weather alerts")
        render_alerts(report.get("alerts", []))
        days = report.get("forecast_days", [])
        if days:
            st.markdown("### At a glance · next five days")
            cols = st.columns(min(5, len(days)))
            for col, day in zip(cols, days):
                date = day.get("date", "")
                col.metric(datetime.fromisoformat(date).strftime("%a · %b %d") if date else "Forecast",
                           f"{day['temperature_max_c']:.0f}° / {day['temperature_min_c']:.0f}°" if day.get("temperature_max_c") is not None and day.get("temperature_min_c") is not None else "—",
                           f"Rain chance {day.get('precipitation_probability_max_percent')}%" if day.get("precipitation_probability_max_percent") is not None else None)
        location = report.get("location", {})
        lat, lon = location.get("latitude"), location.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            st.markdown("### Location")
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon], "marker_size": [30], "marker_color": ["#4387f5"]}),
                   size="marker_size", color="marker_color", width="stretch")

    elif page == "5-day forecast":
        st.markdown("### Five-day outlook")
        days = report.get("forecast_days", [])
        st.dataframe(pd.DataFrame(days), width="stretch", hide_index=True)
        hours = report.get("forecast_hours", [])
        if hours:
            frame = pd.DataFrame(hours)
            frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
            frame = frame.dropna(subset=["time"])
            st.markdown("### Temperature trend")
            fig = px.line(frame, x="time", y="temperature_c", markers=True, labels={"time": "Local time", "temperature_c": "Temperature (°C)"},
                          color_discrete_sequence=["#4387f5"])
            fig.update_layout(template="plotly_white", height=340, margin=dict(l=10,r=10,t=25,b=10), hovermode="x unified",
                              paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family="DM Sans, sans-serif", color="#26364B"),
                              xaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3", zerolinecolor="#D6DEE8"),
                              yaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3", zerolinecolor="#D6DEE8"),
                              legend=dict(font=dict(color="#26364B")))
            st.plotly_chart(fig, width="stretch")
            st.markdown("### Rain probability")
            fig = px.area(frame, x="time", y="precipitation_probability_percent", labels={"time": "Local time", "precipitation_probability_percent": "Probability (%)"},
                          color_discrete_sequence=["#42a5c5"])
            fig.update_layout(template="plotly_white", height=300, margin=dict(l=10,r=10,t=20,b=10), yaxis_range=[0,100],
                              paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family="DM Sans, sans-serif", color="#26364B"),
                              xaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3"),
                              yaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3", title_font=dict(color="#26364B")))
            st.plotly_chart(fig, width="stretch")
            st.markdown("### Wind speed")
            fig = px.bar(frame, x="time", y="wind_kmh", labels={"time": "Local time", "wind_kmh": "Wind (km/h)"}, color="wind_kmh", color_continuous_scale="Blues")
            fig.update_layout(template="plotly_white", height=280, margin=dict(l=10,r=10,t=15,b=10), showlegend=False,
                              paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family="DM Sans, sans-serif", color="#26364B"),
                              xaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3"),
                              yaxis=dict(color="#26364B", gridcolor="#E5EAF1", linecolor="#B8C4D3", title_font=dict(color="#26364B")))
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning("Hourly forecast values are not available for this response.")

    else:
        st.markdown("### Active weather alerts")
        render_alerts(report.get("alerts", []))
        st.caption("Alert thresholds are configurable examples. Follow official local warnings for safety decisions.")

    st.markdown("### Download this report")
    a, b = st.columns(2)
    a.download_button("Download JSON report", json.dumps(report, indent=2), file_name=f"{report.get('city','weather').replace(' ','_').lower()}_weather_report.json", mime="application/json", width="stretch")
    csv_frame = pd.DataFrame(report.get("forecast_hours", []))
    current = report.get("current", {})
    csv_frame.insert(0, "date", csv_frame["time"].astype(str).str[:10] if "time" in csv_frame else "")
    for key, value in reversed(list({
        "city": report.get("city"), "country": report.get("country"), "mode": report.get("mode"),
        "source": report.get("source"), "report_generated_at_utc": report.get("generated_at_utc"),
        "weather_time": current.get("time"), "current_temperature_c": current.get("temperature_c"),
        "current_feels_like_c": current.get("feels_like_c"), "current_humidity_percent": current.get("humidity_percent"),
        "current_precipitation_mm": current.get("precipitation_mm"),
        "current_rain_probability_percent": current.get("precipitation_probability_percent"),
        "current_wind_kmh": current.get("wind_kmh"), "current_condition": current.get("condition"),
        "alerts": json.dumps(report.get("alerts", [])),
    }.items())):
        csv_frame.insert(0, key, value)
    csv_data = csv_frame.to_csv(index=False)
    b.download_button("Download hourly CSV", csv_data, file_name=f"{report.get('city','weather').replace(' ','_').lower()}_forecast.csv", mime="text/csv", width="stretch")
    st.markdown("<div class='footer'>Forecast data © <a href='https://open-meteo.com/' target='_blank'>Open-Meteo</a> · This dashboard is educational and is not an official warning service.</div>", unsafe_allow_html=True)
else:
    st.info("Choose a city and data source in the sidebar, then refresh to load weather.")
