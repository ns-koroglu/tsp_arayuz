# 🚚 Gezgin Satıcı Problemi (TSP) - Yakıt Maliyeti Optimizasyonu (Streamlit Arayüzü)

Bu proje, belirli konumlar arasındaki mesafeleri içeren bir CSV dosyasını kullanarak Gezgin Satıcı Problemini (TSP) çözen ve **yakıt maliyetini minimize eden** en uygun rotayı bulan interaktif bir web uygulamasıdır. Uygulama, Streamlit kütüphanesi ile geliştirilmiştir ve Google OR-Tools optimizasyon aracını kullanır.

Maliyet hesaplaması, Kayseri (Melikgazi, Kocasinan, Talas ilçeleri) için Opet API'sinden alınan **güncel motorin/benzin fiyatları** ve kullanıcı tarafından belirlenen **araç yakıt tüketimi** değerine göre yapılır.

**Web üzerinden kullanmak için şu adrese gidin: [https://tsparayuz-y9ekign8dd69qhugroecdz.streamlit.app/](https://tsparayuz-y9ekign8dd69qhugroecdz.streamlit.app/)**

## ✨ Özellikler

* Kullanıcı dostu **Streamlit** web arayüzü.
* Konumlar arası mesafeleri içeren **CSV dosyası yükleme**.
*(Mesafe hesaplamak için şu repoma göz atın: https://github.com/ns-koroglu/DistanceCalculatorViaOSMnx)*
* **Opet API**'si üzerinden Kayseri (Melikgazi, Kocasinan, Talas) için **güncel yakıt fiyatlarını** otomatik çekme.
* Ayarlanabilir **araç yakıt tüketimi** (Litre/100km) ve **çözücü süre sınırı**.
* **Google OR-Tools** kullanarak en düşük yakıt maliyetli rotanın optimizasyonu.
* Hesaplanan **toplam maliyet**, **toplam mesafe** ve **rota adımlarının** gösterimi.
* Sonuçların **CSV** ve **Excel** formatlarında indirilebilmesi.

## 🛠️ Kullanılan Teknolojiler

* **Python 3**
* **Streamlit:** Web arayüzü oluşturma.
* **Google OR-Tools:** TSP optimizasyonu.
* **Pandas:** CSV dosyası okuma ve veri işleme.
* **Requests:** Opet API'sinden veri çekme.
* **Openpyxl:** Excel dosyası oluşturma.

## 🚀 Kurulum ve Çalıştırma (Yerel Makinede)

Uygulamayı kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

1.  **Depoyu Klonlayın:**
    ```bash
    https://github.com/ns-koroglu/tsp_arayuz.git
    ```

2.  **Gerekli Kütüphaneleri Yükleyin:**
    * Python 3 ve pip'in kurulu olduğundan emin olun.
    * Terminalde aşağıdaki komutu çalıştırın:
        ```bash
        pip install -r requirements.txt
        ```
        *(veya `python3 -m pip install -r requirements.txt`)*

3.  **Streamlit Uygulamasını Başlatın:**
    * Terminalde aşağıdaki komutu çalıştırın:
        ```bash
        streamlit run tsp_arayuz.py
        ```
        *(Python dosyanızın adı farklıysa onu kullanın)*

4.  Tarayıcınızda açılan yerel adreste (genellikle `http://localhost:8501`) uygulamayı kullanmaya başlayın.

##  Kulanım

1.  **Mesafe Matrisini Yükleyin:** "Mesafe Matrisi Yükleyin" bölümünü kullanarak `.csv` formatındaki dosyanızı seçin.
2.  **Ayarları Yapılandırın:** Sol kenar çubuğundan (sidebar) kullanmak istediğiniz Yakıt Türünü, Aracınızın Yakıt Tüketimini, Çözücü Süre Sınırını ve Çıktı Dosya Adını ayarlayın.
3.  **Hesapla Düğmesine Tıklayın:** "✅ En Uygun Rotayı Hesapla" düğmesine basın.
4.  Uygulama yakıt fiyatlarını çekecek, optimizasyonu yapacak ve sonuçları (Özet Bilgiler, Rota Adımları Tablosu, İndirme Düğmeleri) ekranda gösterecektir.

## 📄 Giriş Dosyası Formatı (`.csv`)

Uygulamanın doğru çalışması için yükleyeceğiniz CSV dosyası şu formatta olmalıdır:

* **Karakter Kodlaması:** UTF-8 (Genellikle varsayılan).
* **Ayırıcı:** Virgül (`,`).
* **İlk Satır:** Başlık satırı olmalı ve ilk hücre boş veya indeks adı, sonraki hücreler ise konum etiketlerini içermelidir.
* **İlk Sütun:** Satır etiketlerini (indeks) içermeli ve ilk hücre boş veya indeks adı olmalıdır.
* **Diğer Hücreler:** Konumlar arasındaki mesafeleri **metre cinsinden ve tamsayı olarak** içermelidir.
* **Yapı:** Matris **kare** olmalıdır (satır sayısı = sütun sayısı).
* **Not:** Kare matris verisi girmeniz gerekmektedir.

**Örnek:**

```csv
,Konum0,Konum1,Konum2
Konum0,0,1500,3000
Konum1,1650,0,2100
Konum2,3100,2050,0
