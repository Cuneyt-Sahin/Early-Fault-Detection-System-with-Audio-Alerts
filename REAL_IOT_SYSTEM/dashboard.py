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

# --- GLOBAL KUYRUK ---
@st.cache_resource
def get_shared_queue():
    return queue.Queue()

# --- MQTT SETTİNGS ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_SUBSCRIBE = "cum/iot/rulman_sonuc"

# --- SESSION STATE ---
if "full_archive" not in st.session_state:
    st.session_state.full_archive = pd.DataFrame(columns=["timestamp", "vibration", "temperature", "health_score", "status"])

if "latest_data" not in st.session_state:
    st.session_state.latest_data = None

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
SHARED_DIR = os.path.join(ROOT_DIR, "SHARED_FILES")
ALARM_PATH = os.path.join(SHARED_DIR, "alarm.wav")
MOTOR_GIF = os.path.join(ROOT_DIR, "images", "motor.gif")

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
        "% value": [100-input_response, input_response]
    })
    
    plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=20).encode(
        theta="% value",
        color= alt.Color("Topic:N",
                        scale=alt.Scale(
                            domain=[input_text, ''],
                            range=chart_color),
                        legend=None),
    ).properties(width=130, height=130)
    
    text = plot.mark_text(align='center', color=chart_color[0], font="Lato", fontSize=20, fontWeight=700, fontStyle="italic").encode(text=alt.value(f'{input_response} %'))
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
        import time
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
        st.error(f"⚠️ Ses dosyası ({audio_file}) bulunamadı!")

# --- YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830528.png", width=50)
    st.header("Kontrol Merkezi")
    st.success("Sistem Online 🟢")
    st.warning("🔊 Lütfen alarm sesini duyabilmek için sistem sesini açınız.")
    st.markdown("---")
    
    history_len = st.slider("📊 Grafik Penceresi", 50, 500, 100, 50)
    st.markdown("---")
    
    download_placeholder = st.empty()
    
    st.markdown("---")
    
    st.markdown("### 👨‍💻 Geliştirici")
    st.info(
        """
        **Ad Soyad:** Cüneyt Şahin  
        
        """
    )

# --- ANA SAYFA ---
st.title("IoT-Based Predictive Maintenance Platform")
st.caption("End-to-End Prototyping with Simulated Bearing Data")
st.markdown("---")

dashboard_placeholder = st.empty()
sound_placeholder = st.empty()

while True:
    q = get_shared_queue()
    while not q.empty():
        data = q.get()
        st.session_state.latest_data = data
        
        new_row = {
            "timestamp": data["timestamp"],
            "vibration": data["vibration"],
            "temperature": data["temperature"],
            "health_score": data["health_score"],
            "status": data["status"]
        }
        st.session_state.full_archive = pd.concat([st.session_state.full_archive, pd.DataFrame([new_row])], ignore_index=True)

    if not st.session_state.full_archive.empty:
        with download_placeholder.container():
            csv = st.session_state.full_archive.to_csv(index=False).encode('utf-8')
            unique_key = f"dl_btn_{len(st.session_state.full_archive)}_{time.time()}"
            st.download_button("📥 Raporu İndir (CSV)", csv, 'tum_bakim_verisi.csv', 'text/csv', key=unique_key)
    dashboard_placeholder.empty()
    with dashboard_placeholder.container():
        current_data = st.session_state.latest_data
        
        if current_data:
            status = current_data["status"]
            health = int(current_data["health_score"])
            chart_data = st.session_state.full_archive.tail(history_len)
            

            col_kpi1, col_kpi2, col_kpi3, col_donut = st.columns([1.5, 1, 1, 1.2])
            
            with col_kpi1:
                if status == "OPTİMUM":
                    bg_color = "#27AE60"
                    sound_placeholder.empty()
                elif "UYARI" in status: # ERKEN UYARI
                    bg_color = "#F39C12"
                    play_alarm_sound() 
                else:
                    bg_color = "#E74C3C" # KIRMIZI ALARM
                    play_alarm_sound()
                
                st.markdown(f"""
                <div style="background-color:{bg_color};padding:15px;border-radius:10px;color:white;box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);">
                    <h5 style="margin:0; opacity:0.8;">SİSTEM DURUMU</h5>
                    <h2 style="margin:0; font-weight:bold;">{status}</h2>
                </div>
                """, unsafe_allow_html=True)

            with col_kpi2:
                st.metric("📡 Titreşim (G)", f"{current_data['vibration']:.4f}")
                st.metric("🌡️ Sıcaklık (°C)", f"{current_data['temperature']:.1f} °C")

            with col_kpi3:
                try:
                    ts_str = str(current_data["timestamp"]).split('.')
                    time_disp = f"{ts_str[-3]}:{ts_str[-2]}:{ts_str[-1]}" if len(ts_str) >= 3 else "..."
                except:
                    time_disp = str(current_data["timestamp"])
                    
                st.metric("🕒 Son Veri Saati", time_disp)
                st.metric("💾 Toplam Veri", len(st.session_state.full_archive))

            with col_donut:
                donut = make_donut(health, "")
                st.altair_chart(donut, use_container_width=True)
                st.markdown("<p style='text-align: center; font-weight: bold; margin-top: -10px;'>Genel Sağlık</p>", unsafe_allow_html=True)

            # 2. GRAFİKLER
            st.markdown("### 📈 Canlı Sensör Analizi")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("**Titreşim Trendi**")
                chart_vib = make_line_chart(chart_data, 'vibration', '', '#00B4D8')
                st.altair_chart(chart_vib, use_container_width=True)
            
            with col_g2:
                st.markdown("**Sıcaklık Trendi**")
                chart_temp = make_line_chart(chart_data, 'temperature', '', '#FF6B6B')
                st.altair_chart(chart_temp, use_container_width=True)
                
            # 3. SON ALARMLAR
            risky = st.session_state.full_archive[st.session_state.full_archive['status'] != "OPTİMUM"].tail(5)
            if not risky.empty:
                st.error("⚠️ Son Kaydedilen Kritik Olaylar")
                st.dataframe(risky[['timestamp', 'status', 'vibration', 'temperature']].sort_index(ascending=False), use_container_width=True, hide_index=True)

            # 4. DİJİTAL İKİZ
            st.markdown("---")
            st.markdown("### 🏗️ Dijital İkiz (Digital Twin) Simülasyonu")
            
            col_twin1, col_twin2 = st.columns([1, 2])
            with col_twin1:
                st.info("**Motor Durumu:** Aktif\n\n**RPM:** 1500\n\n**Bağlantı:** MQTT/TCP")
            
            with col_twin2:
                try:
                    st.image(MOTOR_GIF, caption="Gerçek Zamanlı Motor Modeli (Temsili)", use_container_width=True)
                except:
                    st.warning("⚠️ 'motor.gif' dosyası bulunamadı. Lütfen proje klasörüne bir GIF ekleyin.")

        else:
            st.info("Sistem Başlatılıyor... Veri Bekleniyor...")
            st.progress(0)

    time.sleep(0.5) 