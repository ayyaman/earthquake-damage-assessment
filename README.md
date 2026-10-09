# Deprem Karar Destek Sistemi

## 1. Projenin Amacı

Deprem Karar Destek Sistemi, deprem sonrası karar verme süreçlerinde kullanılabilecek görsel analiz ve durumsal farkındalık bileşenlerini bir araya getiren bir mezuniyet projesidir. Sistem; tek bina görüntüsü üzerinden bina hasar seviyesi tahmini, senaryo temelli risk analizi ve afet öncesi/sonrası uydu görüntülerinden bölgesel değişim analizi üretir.

Sistem kesin can kaybı, kesin ekonomik kayıp veya kesin yıkılan bina sayısı tahmini yapmaz. Üretilen çıktılar karar destek amacıyla yorumlanmalıdır.

Dokümantasyonda proje kökü aşağıdaki adla ifade edilir:

```text
DepremKararDestekSistemi/
```

## 2. Sistem Mimarisi

Sistem iki bağımsız katmandan oluşur:

1. **Durumsal Farkındalık Katmanı**
   - Türkiye haritası
   - Fay hattı katmanı
   - Son deprem noktaları
   - Deprem büyüklüğüne göre renklendirilmiş işaretleyiciler
   - Son 24 saat istatistikleri

2. **Yapay Zekâ Analiz Katmanı**
   - Bina Hasar Analizi
   - Risk Analizi
   - Bölgesel Analiz

Harita ve yapay zekâ analizleri doğrudan birbirine bağlanmamıştır. Bunun nedeni, kullanılan görüntü veri setlerinde konum bilgisinin bulunmamasıdır. Bu ayrım teknik olarak daha doğru ve savunulabilir bir mimari sağlar.

## 3. Durumsal Farkındalık Katmanı

Durumsal Farkındalık Katmanı, Türkiye haritası üzerinde son deprem verilerini ve fay hatlarını gösterir. Bu katman yapay zekâ tahmini üretmez; güncel deprem aktivitesini görselleştirerek kullanıcıya genel durum bilgisi sağlar.

Durumsal Farkındalık Katmanı, AFAD canlı deprem verilerini kullanacak şekilde tasarlanmıştır. İnternet bağlantısı veya servis erişimi olmadığı durumlarda sistem demo veri setine geri dönerek arayüzün çalışmaya devam etmesini sağlar. Arayüzde veri kaynağı açıkça gösterilir:

```text
Veri Kaynağı: AFAD Canlı Veri
Veri Kaynağı: Demo Veri
```

AFAD canlı veri için backend üzerinde proxy endpointleri kullanılır:

```text
GET /earthquakes/last-24-hours
GET /earthquakes/latest
```

Bu yapı, tarayıcı tarafında oluşabilecek CORS sorunlarını azaltmak ve servis erişimi başarısız olduğunda kontrollü biçimde demo veriye dönmek için tercih edilmiştir.

Deprem işaretleyici renkleri:

```text
0.0 - 2.9  : Yeşil
3.0 - 3.9  : Sarı
4.0 - 4.9  : Turuncu
5.0 ve üstü: Kırmızı
```

İlk aşamada örnek deprem verisi kullanılmaktadır:

```text
frontend/public/data/sample_earthquakes.json
```

Fay hattı verisi için örnek GeoJSON dosyası:

```text
frontend/public/data/fault_lines.geojson
```

Bu dosya daha sonra MTA veya uygun açık veri kaynaklarından alınacak gerçek fay hattı verileriyle değiştirilebilir.

## 4. Yapay Zekâ Analiz Katmanı

### 4.1 Bina Hasar Analizi

Bina Hasar Analizi modülü, tek bina veya enkaz görüntüsünden hasar seviyesini sınıflandırır.

Sınıflar:

```text
Hasar Yok
Hasarlı
Çöktü
```

Teknik karşılıkları:

```text
no_damage
damaged
collapsed
```

Model yaklaşımı:

```text
EfficientNetB0 transfer learning
```

Bu modül 224x224 giriş boyutu, veri artırma, erken durdurma ve model kontrol noktası yaklaşımıyla çalışır.

### 4.2 Risk Analizi

Risk Analizi modülü, bina hasar seviyesi, bina türü ve zaman bilgisine göre tekil yapı için senaryo temelli karar destek çıktısı üretir.

Çıktılar:

```text
Tahmini nüfus aralığı
Olası can kaybı aralığı
Risk seviyesi
Tahmini ekonomik kayıp aralığı
Ekonomik kayıp kırılımı
```

Risk seviyeleri:

```text
Çok Düşük
Düşük
Orta
Yüksek
Kritik
```

Bu modül büyük ölçekli afetlerde toplam can kaybını hesaplamak için kullanılmaz. Çok sayıda il ve yapıyı etkileyen depremler bölgesel ölçekte değerlendirilmelidir.

### 4.3 Bölgesel Analiz

Bölgesel Analiz modülü, afet öncesi ve afet sonrası uydu görüntülerini karşılaştırır. Bölgesel değişim skoru ve öncelik seviyesi üretir.

Kullanılan metrikler:

```text
Piksel farkı
Yapısal benzerlik değişimi
Görsel özellik değişimi
Değişim alanı oranı
Şiddetli değişim oranı
Etkilenen bölge sayısı
```

Öncelik seviyeleri:

```text
Çok Düşük
Düşük
Orta
Yüksek
Çok Yüksek
```

Değişim haritası, deprem öncesi ve sonrası görüntüler arasındaki değişim yoğunluğunu gösterir. Sıcak renkler, değişimin yoğun olduğu ve hasar açısından öncelikli incelenmesi gereken bölgeleri ifade eder. Bu harita doğrudan kesin yıkılmış bina sayısını vermez; potansiyel hasarlı veya değişmiş bölgeleri görselleştirir.

Bu çalışma bina maskesi veya nesne tespit etiketi içermediği için kesin yıkılan bina sayısı hesaplamaz. Bunun yerine değişim haritasındaki yoğun değişim bölgelerini sayarak tahmini etkilenen bölge sayısı üretir.

## 5. Kullanılan Teknolojiler

```text
Python
TensorFlow / Keras
EfficientNetB0
OpenCV
scikit-image
pandas
FastAPI
React
TailwindCSS
Leaflet / React Leaflet
```

## 6. Veri Seti Yapısı

Bina hasar veri seti:

```text
final_dataset/
 ├── no_damage/
 ├── damaged/
 └── collapsed/
```

Bölgesel afet öncesi/sonrası veri seti:

```text
regional_dataset/
 └── images/
      ├── mexico-earthquake_00000000_pre_disaster.png
      ├── mexico-earthquake_00000000_post_disaster.png
      ├── mexico-earthquake_00000001_pre_disaster.png
      └── mexico-earthquake_00000001_post_disaster.png
```

Kod, dosya adındaki ortak kimlik üzerinden afet öncesi ve sonrası görüntüleri eşleştirir.

## 7. Kurulum

```powershell
cd DepremKararDestekSistemi
pip install -r requirements.txt
```

Frontend bağımlılıkları:

```powershell
cd frontend
npm install
```

## 8. Çalıştırma

Backend:

```powershell
uvicorn app:app --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Tarayıcı adresi:

```text
http://127.0.0.1:5173
```

Bina hasar modelini eğitmek için:

```powershell
python split_dataset.py
python train_model.py
```

Tek bina görüntüsü tahmini:

```powershell
python predict.py
```

Tek bölgesel çift analizi:

```powershell
python predict_regional.py --pre "regional_dataset/images/ornek_pre_disaster.png" --post "regional_dataset/images/ornek_post_disaster.png"
```

Tüm bölgesel çiftleri analiz etmek için:

```powershell
python batch_regional_analysis.py
```

## 9. Sonuçların Yorumlanması

Model ve analiz çıktıları karar destek amacı taşır. Olası can kaybı aralığı, tahmini ekonomik kayıp aralığı ve bölgesel değişim skoru kesin değer olarak yorumlanmamalıdır.

Risk Analizi modülü tekil yapı ölçeğinde çalışır. Bölgesel Analiz modülü ise afet öncesi ve sonrası uydu görüntüleri arasındaki değişim yoğunluğunu değerlendirir.

## 10. Sınırlılıklar

- Görüntü veri setlerinde konum bilgisi bulunmadığı için yapay zekâ çıktıları harita üzerinde doğrudan konumlandırılmaz.
- Bölgesel analiz kesin yıkılan bina sayısı üretmez.
- Risk analizi resmi can kaybı veya ekonomik kayıp tahmini değildir.
- Fay hattı verisi ilk aşamada örnek GeoJSON ile temsil edilir.
- AFAD canlı veri bağlantısı için servis katmanı hazırdır, ancak ilk aşamada örnek veri kullanılmaktadır.

## 11. Geliştirilebilir Yönler

- Canlı AFAD veri entegrasyonu
- Gerçek MTA fay hattı GeoJSON verisi
- Analiz geçmişi için veritabanı entegrasyonu
- Kullanıcı bazlı raporlama
- Bölgesel analizde bina maskesi veya nesne tespit modeli kullanımı
- Harita üzerinde kullanıcı tarafından seçilen bölgeye bağlı raporlama
