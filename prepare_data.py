import pandas as pd
import os
import numpy as np
import random

DATA_DIR = "second_test"
OUTPUT_PATH = os.path.join("SHARED_FILES", "sensor_data.csv")

def veri_birlestir():
    
    data_list = []
    
    filenames = sorted(os.listdir(DATA_DIR))
    

    total_files = len(filenames)
    
    for i, filename in enumerate(filenames):
        filepath = os.path.join(DATA_DIR, filename)
        
        if os.path.isfile(filepath):
            try:
                if i % 100 == 0:
                    print(f"İşleniyor: {i}/{total_files}")

                df = pd.read_csv(filepath, sep='\t', header=None)
                

                vib_mean = np.mean(np.abs(df[0]))
                
                # 2. SENTETİK SICAKLIK (TEMPERATURE) VERİSİ
                # Mantık: Normal sıcaklık 35 derece olsun.
                # Titreşim arttıkça sıcaklık da artsın.
                # Formül: Baz Sıcaklık + (Titreşim * Çarpan) + Rastgele Gürültü
                
                base_temp = 35.0
                heat_factor = vib_mean * 200 
                random_noise = random.uniform(-1.5, 1.5)
                
                generated_temp = base_temp + heat_factor + random_noise
                
                data_list.append({
                    "timestamp": filename,
                    "vibration": round(vib_mean, 5),
                    "temperature": round(generated_temp, 2)
                })
                
            except Exception as e:
                print(f"Hata: {filename} okunamadı. {e}")

    final_df = pd.DataFrame(data_list)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    final_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nİŞLEM TAMAM! Toplam {len(final_df)} satır veri '{OUTPUT_PATH}' dosyasına kaydedildi.")

if __name__ == "__main__":
    if os.path.exists(DATA_DIR):
        veri_birlestir()
    else:
        print(f"HATA: '{DATA_DIR}' klasörü bulunamadı.")