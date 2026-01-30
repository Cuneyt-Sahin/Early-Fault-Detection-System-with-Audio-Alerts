import paho.mqtt.client as mqtt
import json
from sklearn.ensemble import IsolationForest
from collections import deque
import warnings
import os
import pickle

warnings.filterwarnings("ignore")

# --- AYARLAR ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_INPUT = "cum/iot/rulman_data"
TOPIC_OUTPUT = "cum/iot/rulman_sonuc"
    
# --- ML AYARLARI ---
TRAIN_LIMIT = 200
training_data = []
is_trained = False 
model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)

# --- MODEL
BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
SHARED_DIR = os.path.join(ROOT_DIR, "SHARED_FILES")
MODEL_PATH = os.path.join(SHARED_DIR, "model.pkl")
STATE_PATH = os.path.join(SHARED_DIR, "state.json")

os.makedirs(SHARED_DIR, exist_ok=True)

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, "rb") as file_handle:
        model = pickle.load(file_handle)
    is_trained = True
    print(f"Model yüklendi: {MODEL_PATH}")

last_processed_ts = None
if os.path.exists(STATE_PATH):
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as state_handle:
            state_data = json.load(state_handle)
            last_processed_ts = state_data.get("last_processed_ts")
    except Exception as e:
        print(f"Durum dosyası okunamadı: {e}")

# --- GEÇMİŞ HAFIZASI (Daha kararlı sonuçlar için) ---
history_buffer = deque(maxlen=5) # Son 5 tahmini hatırla

def calculate_health(raw_score):
    # raw_score genelde 0.15 (süper) ile -0.15 (kötü) arasındadır.
    # Pozitifler (Normal) -> 50-100 arası
    # Negatifler (Anomali) -> 0-50 arası
    
    normalized = (raw_score + 0.15) / 0.30 * 100
    
    if normalized > 100: normalized = 99.9
    if normalized < 0: normalized = 1.0 
    
    return round(normalized, 1)

def on_connect(client, userdata, flags, rc):
    print(f"Broker'a Bağlanıldı! Kod: {rc}")
    client.subscribe(TOPIC_INPUT)
    print(f"Dinleniyor: {TOPIC_INPUT}")

def on_message(client, userdata, msg):
    global is_trained, training_data
    
    try:
        payload = json.loads(msg.payload.decode())
        vib = payload["vibration"]
        temp = payload["temperature"]
        ts = payload["timestamp"]
        
        features = [vib, temp]

        if last_processed_ts is not None and ts <= last_processed_ts:
            return
        
        # --- EĞİTİM ---
        if not is_trained:
            training_data.append(features)
            kalan = TRAIN_LIMIT - len(training_data)
            if len(training_data) % 50 == 0:
                print(f"[EĞİTİM] Veri Toplanıyor... Kalan: {kalan}")
            
            if len(training_data) >= TRAIN_LIMIT:
                print("\n--- MODEL EĞİTİMİ TAMAMLANDI: Normal Davranış Öğrenildi ---\n")
                model.fit(training_data)
                is_trained = True
                with open(MODEL_PATH, "wb") as file_handle:
                    pickle.dump(model, file_handle)
                print(f"Model kaydedildi: {MODEL_PATH}")
        
        # --- ANALİZ ---
        else:
            raw_score = model.decision_function([features])[0]
            health_score = calculate_health(raw_score)
            
            # Anlık Durum
            status = "DANGER" if raw_score < 0 else "NORMAL"
            history_buffer.append(status)
            
            # KARAR MEKANİZMASI (Daha Akıllı)
            danger_count = history_buffer.count("DANGER")
            
            if danger_count >= 4: # Son 5 verinin 4'ü bozuksa
                final_decision = "YÜKSEK ARIZA RİSKİ" 
                color = "red"
                health_score = health_score / 2 
                
            elif danger_count >= 2: # Arada sırada bozukluk varsa
                final_decision = "ERKEN UYARI (İncelenmeli)"
                color = "orange"
            else:
                final_decision = "OPTİMUM" 
                color = "green"
            
            # Sağlık Puanı Kozmetik Düzeltme
            if final_decision == "OPTİMUM" and health_score < 60:
                health_score = 85.0 + (health_score/10) 
            
            if final_decision == "OPTİMUM":
                 print(f"[{ts}] Durum: {final_decision} | Sağlık: %{health_score} | V:{vib:.4f}")
            else:
                 print(f"[{ts}] !!! {final_decision} !!! | Sağlık: %{health_score} | T:{temp}")

            result_payload = {
                "timestamp": ts,
                "vibration": vib,
                "temperature": temp,
                "health_score": health_score,
                "status": final_decision,
                "color": color
            }
            client.publish(TOPIC_OUTPUT, json.dumps(result_payload))

        with open(STATE_PATH, "w", encoding="utf-8") as state_handle:
            json.dump({"last_processed_ts": ts}, state_handle)

    except Exception as e:
        print(f"Hata: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Kestirimci Bakım Analiz Motoru Başlatılıyor...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()