import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
import queue
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
ALARM_PATH = os.path.join(SHARED_DIR, "alarm.wav")
MOTOR_GIF = os.path.join(ROOT_DIR, "images", "motor.gif")

TEXTS = {
    "EN": {
        "sidebar_title": "Control Center",
        "system_online": "System Online 🟢",
        "alarm_warning": "🔊 Please turn up your system volume to hear the alarm sound.",
        "history_window": "📊 Chart Window",
        "developer": "### 👨‍💻 Developer",
        "developer_name": "**Full Name:** Cüneyt Şahin",
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
        "waiting_data": "Waiting for incoming MQTT data...",
        "status_optimum": "OPTIMAL",
        "status_warning": "EARLY WARNING (Needs Review)",
        "status_risk": "HIGH FAILURE RISK",
        "language": "Language",
        "alarm_missing": "⚠️ Audio file not found.",
    },
    "TR": {
        "sidebar_title": "Kontrol Merkezi",
        "system_online": "Sistem Online 🟢",
        "alarm_warning": "🔊 Lütfen alarm sesini duyabilmek için sistem sesini açınız.",
        "history_window": "📊 Grafik Penceresi",
        "developer": "### 👨‍💻 Geliştirici",
        "developer_name": "**Ad Soyad:** Cüneyt Şahin",
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
        "waiting_data": "Gelen MQTT verileri bekleniyor...",
        "status_optimum": "OPTİMUM",
        "status_warning": "ERKEN UYARI (İncelenmeli)",
        "status_risk": "YÜKSEK ARIZA RİSKİ",
        "language": "Dil",
        "alarm_missing": "⚠️ Ses dosyası bulunamadı.",
    },
}

# --- GLOBAL KUYRUK ---
@st.cache_resource
def get_shared_queue():
    return queue.Queue()

# --- MQTT SETTINGS ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_SUBSCRIBE = "cum/iot/rulman_sonuc"

# --- SESSION STATE ---
if "full_archive" not in st.session_state:
    st.session_state.full_archive = pd.DataFrame(columns=["timestamp", "vibration", "temperature", "health_score", "status", "status_key"])

if "latest_data" not in st.session_state:
    st.session_state.latest_data = None

if "language" not in st.session_state:
    st.session_state.language = "EN"


def t(key, **kwargs):
    text = TEXTS[st.session_state.language][key]
    return text.format(**kwargs) if kwargs else text


def normalize_status(status_value):
    status_text = str(status_value).upper()
    if "UYARI" in status_text or "WARNING" in status_text:
        return "warning"
    if "OPT" in status_text or "OPTIMAL" in status_text:
        return "optimum"
    return "risk"


def get_status_label(status_key):
    return {
        "risk": t("status_risk"),
        "warning": t("status_warning"),
        "optimum": t("status_optimum"),
    }[status_key]


# --- MQTT CALLBACK ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        q = get_shared_queue()
        q.put(payload)
    except Exception as e:
        print(f"Hata: {e}")


# --- İSTEMCİ KURULUMU ---
if "mqtt_client_connected" not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(TOPIC_SUBSCRIBE)
        client.loop_start()
        st.session_state.mqtt_client_connected = True
    except Exception as e:
        st.error(f"MQTT Hatası: {e}")


header_left, header_right = st.columns([5, 1.2])
with header_left:
    st.title("IoT-Based Predictive Maintenance Platform")
    st.caption("End-to-End Prototyping with Simulated Bearing Data")
with header_right:
    st.session_state.language = st.selectbox(
        t("language"),
        options=["EN", "TR"],
        format_func=lambda code: "English" if code == "EN" else "Türkçe",
        index=["EN", "TR"].index(st.session_state.language),
        key="dashboard_language_selector",
        label_visibility="collapsed",
    )

st.markdown("---")


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


# --- ÇİZGİ GRAFİK ---
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
        st.error(t("alarm_missing"))


# --- YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830528.png", width=50)
    st.header(t("sidebar_title"))
    st.success(t("system_online"))
    st.warning(t("alarm_warning"))
    st.markdown("---")

    history_len = st.slider(t("history_window"), 50, 500, 100, 50)
    st.markdown("---")

    download_placeholder = st.empty()

    st.markdown("---")

    st.markdown(t("developer"))
    st.info(t("developer_name"))


# --- ANA SAYFA ---
dashboard_placeholder = st.empty()
sound_placeholder = st.empty()

while True:
    q = get_shared_queue()
    while not q.empty():
        data = q.get()
        st.session_state.latest_data = data

        status_key = normalize_status(data["status"])
        new_row = {
            "timestamp": data["timestamp"],
            "vibration": data["vibration"],
            "temperature": data["temperature"],
            "health_score": data["health_score"],
            "status": data["status"],
            "status_key": status_key,
        }
        st.session_state.full_archive = pd.concat([st.session_state.full_archive, pd.DataFrame([new_row])], ignore_index=True)

    if not st.session_state.full_archive.empty:
        with download_placeholder.container():
            csv = st.session_state.full_archive.to_csv(index=False).encode('utf-8')
            unique_key = f"dl_btn_{len(st.session_state.full_archive)}_{time.time()}"
            st.download_button(t("download_report"), csv, 'tum_bakim_verisi.csv', 'text/csv', key=unique_key)

    dashboard_placeholder.empty()
    with dashboard_placeholder.container():
        current_data = st.session_state.latest_data

        if current_data:
            status_key = normalize_status(current_data["status"])
            status = get_status_label(status_key)
            health = int(current_data["health_score"])
            chart_data = st.session_state.full_archive.tail(history_len)

            col_kpi1, col_kpi2, col_kpi3, col_donut = st.columns([1.5, 1, 1, 1.2])

            with col_kpi1:
                if status_key == "optimum":
                    bg_color = "#27AE60"
                    sound_placeholder.empty()
                elif status_key == "warning":
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