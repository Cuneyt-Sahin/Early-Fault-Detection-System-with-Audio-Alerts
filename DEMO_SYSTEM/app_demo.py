import streamlit as st
import json
import pandas as pd
import time
import altair as alt
import base64
import os

st.set_page_config(page_title="Predictive Maintenance Platform", page_icon="🏭", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #1E1E1E;
    }
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
SHARED_DIR = os.path.join(ROOT_DIR, "SHARED_FILES")
CSV_PATH = os.path.join(SHARED_DIR, "sensor_data.csv")
ALARM_PATH = os.path.join(SHARED_DIR, "alarm.wav")
MOTOR_GIF = os.path.join(ROOT_DIR, "images", "motor.gif")

TEXTS = {
    "EN": {
        "page_title": "Predictive Maintenance Platform",
        "header_title": "IoT-Based Predictive Maintenance Platform",
        "header_caption": "End-to-End Prototyping with Simulated Bearing Data",
        "sidebar_title": "Control Center",
        "demo_online": "Demo Online 🟢",
        "sound_warning": "🔊 Please turn up your system volume to hear the alarm sound.",
        "start": "▶️ Start",
        "stop": "⏹️ Stop",
        "running": "System is running",
        "stopped": "System stopped",
        "history_window": "📊 Chart Window",
        "developer": "### 👨‍💻 Developer",
        "developer_name": "**Full Name:** Cüneyt Şahin",
        "start_prompt": "Press Start from the sidebar to launch the system.",
        "csv_missing": "ERROR: File not found: '{path}'",
        "csv_empty": "ERROR: CSV file is empty.",
        "download_report": "📥 Download Report (CSV)",
        "system_status": "SYSTEM STATUS",
        "vibration": "📡 Vibration (G)",
        "temperature": "🌡️ Temperature (°C)",
        "last_time": "🕒 Last Data Time",
        "total_data": "💾 Total Data",
        "general_health": "General Health",
        "live_analysis": "### 📈 Live Sensor Analysis",
        "vibration_trend": "**Vibration Trend**",
        "temperature_trend": "**Temperature Trend**",
        "critical_events": "⚠️ Recent Critical Events",
        "digital_twin": "### 🏗️ Digital Twin Simulation",
        "motor_status": "**Motor Status:** Active\n\n**RPM:** 1500\n\n**Connection:** MQTT/TCP",
        "motor_caption": "Real-Time Motor Model (Illustrative)",
        "motor_missing": "⚠️ 'motor.gif' not found. Please add a GIF to the project folder.",
        "waiting_data": "System starting... Waiting for data...",
        "status_optimum": "OPTIMAL",
        "status_warning": "EARLY WARNING (Needs Review)",
        "status_risk": "HIGH FAILURE RISK",
        "language": "Language",
    },
    "TR": {
        "page_title": "Öngörülü Bakım Platformu",
        "header_title": "IoT Tabanlı Öngörülü Bakım Platformu",
        "header_caption": "Simüle rulman verileriyle uçtan uca prototipleme",
        "sidebar_title": "Kontrol Merkezi",
        "demo_online": "Demo Online 🟢",
        "sound_warning": "🔊 Alarm sesini duyabilmek için lütfen sistem sesini açın.",
        "start": "▶️ Başlat",
        "stop": "⏹️ Durdur",
        "running": "Sistem çalışıyor",
        "stopped": "Sistem durduruldu",
        "history_window": "📊 Grafik Penceresi",
        "developer": "### 👨‍💻 Geliştirici",
        "developer_name": "**Ad Soyad:** Cüneyt Şahin",
        "start_prompt": "Sistemi başlatmak için yan menüden Başlat'a basın.",
        "csv_missing": "HATA: '{path}' dosyası bulunamadı!",
        "csv_empty": "HATA: CSV dosyası boş.",
        "download_report": "📥 Raporu İndir (CSV)",
        "system_status": "SİSTEM DURUMU",
        "vibration": "📡 Titreşim (G)",
        "temperature": "🌡️ Sıcaklık (°C)",
        "last_time": "🕒 Son Veri Saati",
        "total_data": "💾 Toplam Veri",
        "general_health": "Genel Sağlık",
        "live_analysis": "### 📈 Canlı Sensör Analizi",
        "vibration_trend": "**Titreşim Trendi**",
        "temperature_trend": "**Sıcaklık Trendi**",
        "critical_events": "⚠️ Son Kaydedilen Kritik Olaylar",
        "digital_twin": "### 🏗️ Dijital İkiz (Digital Twin) Simülasyonu",
        "motor_status": "**Motor Durumu:** Aktif\n\n**RPM:** 1500\n\n**Bağlantı:** MQTT/TCP",
        "motor_caption": "Gerçek Zamanlı Motor Modeli (Temsili)",
        "motor_missing": "⚠️ 'motor.gif' dosyası bulunamadı. Lütfen proje klasörüne bir GIF ekleyin.",
        "waiting_data": "Sistem Başlatılıyor... Veri Bekleniyor...",
        "status_optimum": "OPTİMUM",
        "status_warning": "ERKEN UYARI (İncelenmeli)",
        "status_risk": "YÜKSEK ARIZA RİSKİ",
        "language": "Dil",
    },
}

# --- SESSION STATE ---
if "full_archive" not in st.session_state:
    st.session_state.full_archive = pd.DataFrame(columns=["timestamp", "vibration", "temperature", "health_score", "status_key", "status"])

if "latest_data" not in st.session_state:
    st.session_state.latest_data = None

if "run_system" not in st.session_state:
    st.session_state.run_system = False

if "demo_df" not in st.session_state:
    st.session_state.demo_df = None

if "demo_index" not in st.session_state:
    st.session_state.demo_index = 0

if "baseline_mean" not in st.session_state:
    st.session_state.baseline_mean = None

if "baseline_std" not in st.session_state:
    st.session_state.baseline_std = None

if "language" not in st.session_state:
    st.session_state.language = "EN"


def t(key, **kwargs):
    text = TEXTS[st.session_state.language][key]
    return text.format(**kwargs) if kwargs else text

# --- DONUT CHART ---
def make_donut(input_response, input_text):
    if input_response > 80:
        chart_color = ['#27AE60', '#222222']
    elif input_response > 50:
        chart_color = ['#F39C12', '#222222']
    else:
        chart_color = ['#E74C3C', '#222222']

    source = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100 - input_response, input_response]
    })

    plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=20).encode(
        theta="% value",
        color=alt.Color(
            "Topic:N",
            scale=alt.Scale(domain=[input_text, ''], range=chart_color),
            legend=None,
        ),
    ).properties(width=130, height=130)

    text = plot.mark_text(
        align='center',
        color=chart_color[0],
        font="Lato",
        fontSize=20,
        fontWeight=700,
        fontStyle="italic",
    ).encode(text=alt.value(f'{input_response} %'))
    return plot + text

# --- LINE CHART ---
def make_line_chart(data, y_col, title, color):
    chart_data = data.reset_index(drop=True).reset_index()
    min_x = chart_data['index'].min()
    max_x = chart_data['index'].max()

    base = alt.Chart(chart_data).encode(
        x=alt.X('index', title='Zaman Adımları', axis=alt.Axis(labels=True), scale=alt.Scale(domain=[min_x, max_x], nice=False))
    )

    line = base.mark_line(strokeWidth=3, color=color).encode(
        y=alt.Y(y_col, title=title, scale=alt.Scale(zero=False)),
        tooltip=[y_col, 'timestamp']
    )

    area = base.mark_area(opacity=0.3, color=color).encode(
        y=alt.Y(y_col, scale=alt.Scale(zero=False))
    )

    return (line + area).properties(height=280)

# --- SESLİ UYARI FONKSİYONU ---
def play_alarm_sound():
    audio_file = ALARM_PATH

    try:
        with open(audio_file, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()

        mime_type = "audio/wav"
        unique_id = time.time()

        sound_placeholder.empty()
        time.sleep(0.1)

        sound_placeholder.markdown(
            f"""
            <audio autoplay=True>
                <source src="data:{mime_type};base64,{b64}" type="{mime_type}">
            </audio>
            """,
            unsafe_allow_html=True
        )

    except FileNotFoundError:
        st.error(f"⚠️ {os.path.basename(audio_file)} not found!")


def get_status_key(z_score):
    if z_score >= 4:
        return "risk"
    if z_score >= 2:
        return "warning"
    return "optimum"


def get_status_label(status_key):
    return {
        "risk": t("status_risk"),
        "warning": t("status_warning"),
        "optimum": t("status_optimum"),
    }[status_key]

# --- YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830528.png", width=50)
    st.header(t("sidebar_title"))
    st.success(t("demo_online"))
    st.warning(t("sound_warning"))
    st.markdown("---")

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button(t("start"), use_container_width=True):
            st.session_state.run_system = True
    with col_stop:
        if st.button(t("stop"), use_container_width=True):
            st.session_state.run_system = False

    if st.session_state.run_system:
        st.success(t("running"))
    else:
        st.info(t("stopped"))

    st.markdown("---")

    history_len = st.slider(t("history_window"), 50, 500, 100, 50)
    st.markdown("---")

    download_placeholder = st.empty()

    st.markdown("---")

    st.markdown(t("developer"))
    st.info(t("developer_name"))

# --- ANA SAYFA ---
header_col1, header_col2 = st.columns([5, 1.4])
with header_col1:
    st.title("IoT-Based Predictive Maintenance Platform")
    st.caption("End-to-End Prototyping with Simulated Bearing Data")
with header_col2:
    st.session_state.language = st.selectbox(
        t("language"),
        options=["EN", "TR"],
        format_func=lambda code: "English" if code == "EN" else "Türkçe",
        index=["EN", "TR"].index(st.session_state.language),
        key="language_selector",
        label_visibility="collapsed",
    )
st.markdown("---")

dashboard_placeholder = st.empty()
sound_placeholder = st.empty()

if not st.session_state.run_system:
    st.info(t("start_prompt"))
    st.stop()

if st.session_state.demo_df is None:
    try:
        st.session_state.demo_df = pd.read_csv(CSV_PATH)
        baseline_len = min(200, len(st.session_state.demo_df))
        baseline_slice = st.session_state.demo_df["vibration"].iloc[:baseline_len]
        st.session_state.baseline_mean = float(baseline_slice.mean()) if not baseline_slice.empty else 0.0
        st.session_state.baseline_std = float(baseline_slice.std()) if not baseline_slice.empty else 1.0
    except FileNotFoundError:
        st.error(t("csv_missing", path=CSV_PATH))
        st.stop()

while True:
    df = st.session_state.demo_df
    if df.empty:
        st.error(t("csv_empty"))
        st.stop()

    row = df.iloc[st.session_state.demo_index]
    st.session_state.demo_index += 1
    if st.session_state.demo_index >= len(df):
        st.session_state.demo_index = 0

    vibration = float(row["vibration"])
    temperature = float(row["temperature"])
    mean = st.session_state.baseline_mean or 0.0
    std = st.session_state.baseline_std or 1.0
    z_score = (vibration - mean) / std if std > 0 else 0.0

    status_key = get_status_key(z_score)
    status = get_status_label(status_key)

    health_score = max(1.0, min(99.9, 100 - (max(z_score, 0) * 15)))

    payload = {
        "timestamp": row["timestamp"],
        "vibration": vibration,
        "temperature": temperature,
        "health_score": float(health_score),
        "status_key": status_key,
        "status": status
    }

    st.session_state.latest_data = payload
    new_row = {
        "timestamp": payload["timestamp"],
        "vibration": payload["vibration"],
        "temperature": payload["temperature"],
        "health_score": payload["health_score"],
        "status_key": payload["status_key"],
        "status": payload["status"],
    }
    st.session_state.full_archive = pd.concat([
        st.session_state.full_archive,
        pd.DataFrame([new_row])
    ], ignore_index=True)

    if not st.session_state.full_archive.empty:
        with download_placeholder.container():
            csv = st.session_state.full_archive.to_csv(index=False).encode('utf-8')
            unique_key = f"dl_btn_{len(st.session_state.full_archive)}_{time.time()}"
            st.download_button(t("download_report"), csv, 'tum_bakim_verisi.csv', 'text/csv', key=unique_key)

    dashboard_placeholder.empty()
    with dashboard_placeholder.container():
        current_data = st.session_state.latest_data

        if current_data:
            status = get_status_label(current_data["status_key"])
            health = int(current_data["health_score"])
            chart_data = st.session_state.full_archive.tail(history_len)

            col_kpi1, col_kpi2, col_kpi3, col_donut = st.columns([1.5, 1, 1, 1.2])

            with col_kpi1:
                if current_data["status_key"] == "optimum":
                    bg_color = "#27AE60"
                    sound_placeholder.empty()
                elif current_data["status_key"] == "warning":
                    bg_color = "#F39C12"
                    play_alarm_sound()
                else:
                    bg_color = "#E74C3C"
                    play_alarm_sound()

                st.markdown(f"""
                <div style="background-color:{bg_color};padding:15px;border-radius:10px;color:white;box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);">
                    <h5 style="margin:0; opacity:0.8;">{t('system_status')}</h5>
                    <h2 style="margin:0; font-weight:bold;">{status}</h2>
                </div>
                """, unsafe_allow_html=True)

            with col_kpi2:
                st.metric(t("vibration"), f"{current_data['vibration']:.4f}")
                st.metric(t("temperature"), f"{current_data['temperature']:.1f} °C")

            with col_kpi3:
                try:
                    ts_str = str(current_data["timestamp"]).split('.')
                    time_disp = f"{ts_str[-3]}:{ts_str[-2]}:{ts_str[-1]}" if len(ts_str) >= 3 else "..."
                except Exception:
                    time_disp = str(current_data["timestamp"])

                st.metric(t("last_time"), time_disp)
                st.metric(t("total_data"), len(st.session_state.full_archive))

            with col_donut:
                donut = make_donut(health, "")
                st.altair_chart(donut, use_container_width=True)
                st.markdown(f"<p style='text-align: center; font-weight: bold; margin-top: -10px;'>{t('general_health')}</p>", unsafe_allow_html=True)

            st.markdown("### 📈 Live Sensor Analysis")
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown(t("vibration_trend"))
                chart_vib = make_line_chart(chart_data, 'vibration', '', '#00B4D8')
                st.altair_chart(chart_vib, use_container_width=True)

            with col_g2:
                st.markdown(t("temperature_trend"))
                chart_temp = make_line_chart(chart_data, 'temperature', '', '#FF6B6B')
                st.altair_chart(chart_temp, use_container_width=True)

            risky = st.session_state.full_archive[st.session_state.full_archive['status_key'] != "optimum"].tail(5)
            if not risky.empty:
                st.error(t("critical_events"))
                display_risky = risky[['timestamp', 'status_key', 'vibration', 'temperature']].copy()
                display_risky["status"] = display_risky["status_key"].map(get_status_label)
                st.dataframe(display_risky[['timestamp', 'status', 'vibration', 'temperature']].sort_index(ascending=False), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🏗️ Digital Twin Simulation")

            col_twin1, col_twin2 = st.columns([1, 2])
            with col_twin1:
                st.info(t("motor_status"))

            with col_twin2:
                try:
                    st.image(MOTOR_GIF, caption=t("motor_caption"), use_container_width=True)
                except Exception:
                    st.warning(t("motor_missing"))

        else:
            st.info(t("waiting_data"))
            st.progress(0)

    time.sleep(0.5)
