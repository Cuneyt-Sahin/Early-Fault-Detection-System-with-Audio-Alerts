import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, confusion_matrix
import matplotlib.dates as mdates
from collections import deque

# --- AYARLAR ---
DOSYA_ADI = 'sensor_data.csv'
VERI_KOLONU = 'vibration'
ZAMAN_KOLONU = 'timestamp'

# --- 1. VERİ İŞLEME ---
print(f"Grafik hazırlanıyor: {DOSYA_ADI}...")
df = pd.read_csv(DOSYA_ADI)

try:
    df[ZAMAN_KOLONU] = pd.to_datetime(df[ZAMAN_KOLONU], format='%Y.%m.%d.%H.%M.%S')
    df = df.set_index(ZAMAN_KOLONU)
except:
    print("! Uyarı: Zaman formatı düzeltilemedi.")

df['smooth_data'] = df[VERI_KOLONU].rolling(window=5, min_periods=1).mean()
data = df['smooth_data'].values.reshape(-1, 1)
zaman_ekseni = df.index

# --- 2. LİMİT BELİRLEME (Ground Truth) ---
BASELINE_LEN = 200
baseline_mean = np.mean(data[:BASELINE_LEN])
baseline_std = np.std(data[:BASELINE_LEN])
FIZIKSEL_LIMIT = baseline_mean + (4 * baseline_std)
y_true = np.where(data > FIZIKSEL_LIMIT, 1, 0)

# --- 3. MODEL VE AKILLI HAFIZA (History Buffer) ---
model = IsolationForest(n_estimators=200, contamination='auto', random_state=42)
model.fit(data[:BASELINE_LEN])

# Modelin ham tahminleri (-1 veya 1)
raw_preds = model.predict(data)
y_pred_final = np.zeros(len(raw_preds))

# --- AKILLI KARAR MEKANİZMASI ---
# Son 5 tahmini tutan bir pencere (buffer)
history_buffer = deque(maxlen=5)

for i in range(len(raw_preds)):
    # IsolationForest -1'i anomali kabul eder
    current_status = 1 if raw_preds[i] == -1 else 0
    history_buffer.append(current_status)
    
    # Eğer son 5 verinin en az 4'ü anomali ise ARIZA kararı ver
    if history_buffer.count(1) >= 4:
        y_pred_final[i] = 1
    else:
        y_pred_final[i] = 0


y_pred = y_pred_final

# --- 4. SONUÇLAR ---
genel_dogruluk = accuracy_score(y_true, y_pred) * 100
cm = confusion_matrix(y_true, y_pred)

plt.style.use('seaborn-v0_8-whitegrid')
fig = plt.figure(figsize=(12, 16), dpi=300)

ax1 = fig.add_subplot(3, 1, 1)
ax1.plot(zaman_ekseni, data, color='#34495e', linewidth=1, alpha=0.7, label='Sensör Verisi', zorder=1)

gercek_idx = np.where(y_true == 1)[0]
ax1.scatter(zaman_ekseni[gercek_idx], data[gercek_idx],
            color='#2ecc71', s=100, marker='o', alpha=0.4, 
            edgecolors='#27ae60', linewidth=1, label='Gerçek Hasar Bölgesi', zorder=2)


model_idx = np.where(y_pred == 1)[0]
ax1.scatter(zaman_ekseni[model_idx], data[model_idx],
            color='#e74c3c', marker='x', s=40, linewidth=2, 
            label='Akıllı Model Tespiti (Filtrelenmiş)', zorder=3)

ax1.axhline(y=FIZIKSEL_LIMIT, color='#9b59b6', linestyle='--', linewidth=2, label='Kritik Eşik')
ax1.set_title(f'Akıllı Kestirimci Bakım Analizi (Doğruluk: %{genel_dogruluk:.1f})', fontsize=14, fontweight='bold')
ax1.set_ylabel('Titreşim (g)')
ax1.legend(loc='upper left', fontsize=10, frameon=True, framealpha=0.9)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

# --- GRAFİK 2: DOĞRULUK ---
ax2 = fig.add_subplot(3, 1, 2)
acc_trend = [accuracy_score(y_true[:i+1], y_pred[:i+1])*100 for i in range(BASELINE_LEN, len(y_true))]
plot_zaman = zaman_ekseni[BASELINE_LEN:]
ax2.plot(plot_zaman, acc_trend, color='#2980b9', linewidth=2.5)
ax2.axhline(y=genel_dogruluk, color='red', linestyle=':', linewidth=2, label=f'Ortalama: %{genel_dogruluk:.1f}')
ax2.fill_between(plot_zaman, 0, acc_trend, alpha=0.15, color='#2980b9')
ax2.set_ylim(50, 105)
ax2.set_ylabel('Doğruluk (%)')
ax2.set_title('Akıllı Karar Mekanizması Performansı', fontsize=12, fontweight='bold')
ax2.legend(loc='lower right')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

# --- GRAFİK 3: CONFUSION MATRIX ---
ax3 = fig.add_subplot(3, 1, 3)
tn, fp, fn, tp = cm.ravel()
labels = [f"NORMAL\n(Doğru)\n{tn}", f"YANLIŞ ALARM\n{fp}",
          f"KAÇIRILAN\n(Risk!)\n{fn}", f"ARIZA TESPİTİ\n(Başarılı)\n{tp}"]
labels = np.asarray(labels).reshape(2,2)

sns.heatmap(cm, annot=labels, fmt='', cmap='Greens', ax=ax3,
            xticklabels=['Normal', 'Arıza'], yticklabels=['Normal', 'Arıza'],
            cbar=False, annot_kws={"size": 12, "weight": "bold"},
            linewidths=1.5, linecolor='white')
ax3.set_title('Hata Matrisi (Akıllı Filtreleme Sonucu)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Model Tahmini')
ax3.set_ylabel('Gerçek Durum')

plt.tight_layout()
plt.savefig('Rapor.png')
print("\n✓ Akıllı filtreleme uygulandı. 'Rapor.png' oluşturuldu.")
plt.show()