import pandas as pd
import time
import json
import os
import paho.mqtt.client as mqtt

# --- SETTINGS ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "cum/iot/rulman_data"

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
CSV_FILE = os.path.join(ROOT_DIR, "SHARED_FILES", "sensor_data.csv")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"BAŞARILI: MQTT Broker'a ({MQTT_BROKER}) bağlanıldı!")
        print(f"Konu Başlığı (Topic): {MQTT_TOPIC}")
        print("-" * 40)
    else:
        print(f"HATA: Bağlanılamadı. Hata kodu: {rc}")


client = mqtt.Client()
client.on_connect = on_connect

print("Sunucuya bağlanılıyor...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"Bağlantı Hatası: {e}")
    exit()

client.loop_start()

try:
    df = pd.read_csv(CSV_FILE)
    print(f"Veri seti yüklendi. Toplam {len(df)} satır veri var.")
    time.sleep(2)

    while True:
        for index, row in df.iterrows():
            payload = {
                "timestamp": row["timestamp"],
                "vibration": float(row["vibration"]),
                "temperature": float(row["temperature"]),
            }

            payload_str = json.dumps(payload)
            client.publish(MQTT_TOPIC, payload_str)

            print(
                f"[{index + 1}/{len(df)}] Veri Gönderildi: V:{payload['vibration']:.4f} | T:{payload['temperature']:.2f}"
            )
            time.sleep(0.5)

        print("\n--- Veri seti bitti, başa dönülüyor ---\n")
        time.sleep(2)

except KeyboardInterrupt:
    print("\nSimülasyon durduruldu.")
    client.loop_stop()
    client.disconnect()
except FileNotFoundError:
    print(f"HATA: '{CSV_FILE}' dosyası bulunamadı!")
