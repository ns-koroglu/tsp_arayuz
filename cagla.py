import streamlit as st
import pandas as pd
import requests
import sys
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math
import json
from io import BytesIO # Excel/CSV içeriğini bellekte tutmak için
import traceback # Hataları daha detaylı görmek için

# --- Ayarlar ve Sabitler ---
TARGET_CITY = "Kayseri"
TARGET_CITY_CODE = 38 # Opet API'si için Kayseri il kodu
TARGET_DISTRICTS = {"MELİKGAZİ", "KOCASİNAN", "TALAS"} # Hedef ilçeler
COST_SCALING_FACTOR = 10000

# --- Backend Fonksiyonları ---
# (Fonksiyonların döndürdüğü mesajlar zaten çoğunlukla Türkçe)

@st.cache_data(ttl=3600) # Fiyatları 1 saat boyunca önbellekte tut
def get_opet_fuel_prices(city_code, target_districts):
    """
    Opet API'sini kullanarak belirtilen il kodundaki HEDEF İLÇELER için
    güncel yakıt fiyatlarını alır. Hata mesajı da döndürür.
    """
    api_url = "https://api.opet.com.tr/api/fuelprices/prices"
    params = {"provinceCode": city_code}
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    target_districts_str = ", ".join(target_districts)
    # Türkçe mesajlar
    status_messages = [f"Opet API'sinden il kodu {city_code} ({TARGET_CITY}) için yakıt fiyatları alınıyor..."]
    status_messages.append(f"(Sadece şu ilçeler dikkate alınacak: {target_districts_str})")

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or not data:
            return None, status_messages + [f"Hata: API yanıtı beklenen formatta değil (ilçe listesi bekleniyordu). Yanıt: {str(data)[:200]}..."]

        prices = {}
        found_benzin = False
        found_motorin = False
        data_found_in_district = None

        for district_data in data:
            if not isinstance(district_data, dict): continue
            district_name_raw = district_data.get('districtName', '')
            district_name_upper = district_name_raw.upper()

            if district_name_upper not in target_districts: continue

            status_messages.append(f"'{district_name_raw}' hedef ilçesi kontrol ediliyor...")
            price_list = district_data.get('prices')
            if not isinstance(price_list, list) or not price_list: continue

            for fuel_item in price_list:
                 if not isinstance(fuel_item, dict) or 'productName' not in fuel_item or 'amount' not in fuel_item: continue
                 fuel_name = fuel_item['productName']
                 try:
                     price_float = float(fuel_item['amount'])
                     # Türkçe Ürün İsimleri Kontrolü (API'den geldiği gibi)
                     if not found_benzin and fuel_name == "Kurşunsuz Benzin 95":
                         prices['benzin'] = price_float
                         status_messages.append(f"  > Bulunan Benzin Fiyatı ({district_name_raw}): {price_float:.2f} TRY/L")
                         found_benzin = True
                         if data_found_in_district is None: data_found_in_district = district_name_raw
                     elif not found_motorin and fuel_name == "Motorin EcoForce":
                         prices['motorin'] = price_float
                         status_messages.append(f"  > Bulunan Motorin Fiyatı ({district_name_raw}): {price_float:.2f} TRY/L ({fuel_name})")
                         found_motorin = True
                         if data_found_in_district is None: data_found_in_district = district_name_raw
                     elif not found_motorin and fuel_name == "Motorin UltraForce":
                         prices['motorin'] = price_float
                         status_messages.append(f"  > Bulunan Motorin Fiyatı ({district_name_raw}): {price_float:.2f} TRY/L ({fuel_name})")
                         found_motorin = True
                         if data_found_in_district is None: data_found_in_district = district_name_raw
                 except (ValueError, TypeError): pass

            if found_benzin and found_motorin:
                status_messages.append(f"'{data_found_in_district}' hedef ilçesinden gerekli fiyatlar başarıyla alındı.")
                break

        if not found_benzin or not found_motorin:
            error_msg = f"Hata: Hedeflenen ilçelerde ({target_districts_str}) Benzin veya Motorin fiyatlarından biri veya ikisi de bulunamadı."
            # Hata mesajına bulunanları da ekleyelim (varsa)
            error_msg += f" Bulunanlar: {prices}"
            return None, status_messages + [error_msg]

        return prices, status_messages

    except requests.exceptions.RequestException as e:
        return None, status_messages + [f"Hata: Opet API'sine bağlanılamadı: {e}"]
    except json.JSONDecodeError:
        return None, status_messages + ["Hata: Opet API yanıtı JSON formatında değil."]
    except Exception as e:
        # Hata detayını ekle
        exc_info = traceback.format_exc()
        return None, status_messages + [f"Hata: Fiyatlar alınırken beklenmedik hata: {e}", exc_info]

def read_distance_matrix(uploaded_file):
    """Yüklenen dosyadan mesafe matrisini okur."""
    if uploaded_file is None:
        return None, ["Hata: Lütfen bir mesafe matrisi dosyası yükleyin."]
    try:
        df = pd.read_csv(uploaded_file, header=0, index_col=0)
        distance_matrix = df.values.astype(int).tolist()
        num_rows = len(distance_matrix)
        if num_rows == 0 or not all(len(row) == num_rows for row in distance_matrix):
             return None, ["Hata: Yüklenen dosya geçerli bir kare matris içermiyor."]

        return distance_matrix, [f"Başarıyla okunan mesafe matrisi boyutu: {num_rows}x{num_rows}"]
    except ValueError as e:
         return None, [f"Hata: CSV dosyasındaki değerler tamsayıya dönüştürülemedi. Lütfen dosya içeriğini kontrol edin. ({e})"]
    except Exception as e:
        exc_info = traceback.format_exc()
        return None, [f"Hata: CSV dosyası okunurken hata oluştu: {e}", exc_info]

def run_tsp_solver(distance_matrix, fuel_price, consumption, time_limit, cost_scaling_factor):
    """OR-Tools çözücüsünü çalıştırır ve sonucu döndürür."""
    status_messages = []
    if not distance_matrix:
        return None, None, None, ["Hata: Geçersiz mesafe matrisi."]

    num_locations = len(distance_matrix)
    data = {}
    data['distance_matrix'] = distance_matrix
    data['num_vehicles'] = 1
    data['depot'] = 0

    manager = None
    routing = None
    try:
        manager = pywrapcp.RoutingIndexManager(num_locations, data['num_vehicles'], data['depot'])
        routing = pywrapcp.RoutingModel(manager)
    except Exception as e:
         # Manager veya Model oluşturulurken hata olursa
         return None, None, None, [f"Hata: Rota modeli oluşturulamadı: {e}", traceback.format_exc()]


    # Yakıt maliyeti fonksiyonu (içerik aynı)
    def fuel_cost_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        if from_node == to_node: return 0
        try:
            dist_value = data['distance_matrix'][from_node][to_node]
            if not isinstance(dist_value, (int, float)): return sys.maxsize
            distance_meters = int(dist_value)
        except IndexError: return sys.maxsize
        except Exception: return sys.maxsize

        distance_km = distance_meters / 1000.0
        fuel_liters = (distance_km / 100.0) * consumption
        cost_try = fuel_liters * fuel_price
        integer_cost = math.ceil(cost_try * cost_scaling_factor)
        return integer_cost

    try:
        transit_callback_index = routing.RegisterTransitCallback(fuel_cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = time_limit
        search_parameters.log_search = False

        status_messages.append(f"Çözücü çalıştırılıyor (süre sınırı: {time_limit} saniye)...")
        solution = routing.SolveWithParameters(search_parameters)
        status_messages.append(f"Çözücü tamamlandı. Durum: {routing.status()}") # Durumu mesaja ekle
        return solution, manager, routing, status_messages

    except Exception as e:
         return None, manager, routing, status_messages + [f"Hata: Çözücü çalıştırılırken hata oluştu: {e}", traceback.format_exc()]


def process_and_save_results(solution, manager, routing, distance_matrix, cost_scaling_factor, fuel_price_used, consumption_used, output_base_filename):
    """Sonuçları işler, özet oluşturur ve dosya içeriklerini döndürür."""
    if not solution:
        return None, None, None, None, ["Hata: Geçersiz çözüm nesnesi."]
    if not manager or not routing:
         return None, None, None, None, ["Hata: Geçersiz rota yöneticisi veya model nesnesi."]


    try:
        # Sonuçları al
        total_cost_try = solution.ObjectiveValue() / cost_scaling_factor
        route_indices = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route_indices.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route_indices.append(manager.IndexToNode(index))

        route_df = pd.DataFrame(route_indices, columns=['Konum_Indeksi'])
        route_df.index.name = 'Adim' # Türkçe: Adım

        # Özet Bilgileri Hesapla ve Türkçe Başlıklar
        num_locations = len(distance_matrix)
        start_node = manager.IndexToNode(routing.Start(0))
        route_distance_meters = 0
        for i in range(len(route_indices) - 1):
            from_node = route_indices[i]
            to_node = route_indices[i+1]
            if 0 <= from_node < num_locations and 0 <= to_node < num_locations:
                dist_value = distance_matrix[from_node][to_node]
                if isinstance(dist_value, (int, float)):
                    route_distance_meters += dist_value

        summary_dict = {
            'Toplam Yakıt Maliyeti (TRY)': f"{total_cost_try:.2f}",
            'Toplam Mesafe (km)': f"{route_distance_meters / 1000.0:.2f}",
            'Kullanılan Yakıt Fiyatı (TRY/L)': f"{fuel_price_used:.4f}",
            'Araç Tüketimi (Litre/100km)': f"{consumption_used:.1f}", # Birimi netleştirdik
            'Konum Sayısı': num_locations,
            'Başlangıç/Bitiş Konum İndeksi': start_node, # Daha açıklayıcı
            'Ziyaret Edilen Konum Sayısı (Depo Hariç)': len(route_indices) - 2 if len(route_indices) > 1 else 0 # Depo başlangıç ve bitişte var
        }
        # Özet DataFrame'i Türkçe sütunlarla
        summary_df = pd.DataFrame(summary_dict.items(), columns=['Ölçüt', 'Değer'])


        # Dosyaları Belleğe Yazdır
        csv_buffer = BytesIO()
        route_df.to_csv(csv_buffer, index=True, encoding='utf-8')
        csv_content = csv_buffer.getvalue()

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            route_df.to_excel(writer, sheet_name='Rota Detayı', index=True) # Türkçe sayfa adı
            summary_df.to_excel(writer, sheet_name='Özet Bilgiler', index=False) # Türkçe sayfa adı
        excel_content = excel_buffer.getvalue()

        return summary_dict, route_df, csv_content, excel_content, ["Sonuçlar başarıyla işlendi ve dosyalar hazırlandı."]

    except Exception as e:
         return None, None, None, None, [f"Hata: Sonuçlar işlenirken hata oluştu: {e}", traceback.format_exc()]


# --- Streamlit Arayüzü (Tamamen Türkçe Metinler) ---

st.set_page_config(page_title="TSP Yakıt Optimizasyonu", layout="wide")

st.title("🚚 Gezgin Satıcı Problemi (TSP) - Yakıt Maliyeti Optimizasyonu")
st.write(f"""
Bu araç, yüklenen `.csv` formatındaki mesafe matrisini kullanarak en uygun rotayı hesaplar.
Maliyet hesabı, **{TARGET_CITY}** ili için (**{', '.join(TARGET_DISTRICTS)}** ilçeleri) Opet'ten alınan güncel yakıt fiyatlarına
ve sizin belirlediğiniz araç tüketimine göre yapılır. Amaç, toplam yakıt maliyetini minimize etmektir.
""")

# --- Dosya Yükleme ---
uploaded_file = st.file_uploader(
    "Mesafe Matrisi Yükleyin (.csv formatında, Örn: Talas_Tekstil_Konteyner_240x240_Mesafe_Matrisi.csv)",
    type="csv",
    help="İlk satır ve ilk sütun konum etiketlerini, geri kalan hücreler ise konumlar arası mesafeleri (metre cinsinden, tamsayı) içermelidir."
)

# --- Parametreler (Sidebar) ---
st.sidebar.header("⚙️ Ayarlar")
fuel_type = st.sidebar.radio(
    "Yakıt Türü:",
    ('Motorin', 'Benzin'), # Seçenekleri baş harf büyük yaptık
    index=0, # Varsayılan Motorin
    captions=["Dizel araçlar için.", "Benzinli araçlar için."] # Açıklama eklendi
)
# Seçimi küçük harfe çevir (kodun geri kalanı küçük harf bekliyor)
fuel_type_internal = fuel_type.lower()

vehicle_consumption = st.sidebar.number_input(
    "Araç Tüketimi (Litre/100km):",
    min_value=1.0,
    max_value=50.0,
    value=8.0, # Varsayılan değer
    step=0.1,
    format="%.1f",
    help="Aracınızın 100 kilometrede ortalama kaç litre yakıt tükettiğini girin."
)

time_limit = st.sidebar.slider(
    "Çözücü Süre Sınırı (saniye):",
    min_value=5,
    max_value=300,
    value=60, # Varsayılan değer
    step=5,
    help="Çözücünün en iyi rotayı bulmak için harcayacağı maksimum süre. Süre dolduğunda o ana kadar bulunan en iyi sonuç gösterilir."
)

output_filename = st.sidebar.text_input(
    "Çıktı Dosya Adı (Uzantısız):",
    value="TSP_Rota_Sonucu", # Varsayılan değer güncellendi
    help="İndirilecek CSV ve Excel dosyalarının temel adı."
)

# --- Çalıştırma Butonu ---
st.divider()
col1, col2, col3 = st.columns([2,1,2])
with col2:
    run_button = st.button("✅ En Uygun Rotayı Hesapla", type="primary", use_container_width=True) # Buton metni güncellendi
st.divider()

# --- Sonuç Alanı ---
results_placeholder = st.empty() # İlk başta boş

if run_button:
    results_placeholder.info("İşlem başlatılıyor...")

    # 1. Mesafe Matrisini Oku
    distance_matrix, matrix_msgs = read_distance_matrix(uploaded_file)
    with st.expander("Dosya Okuma Detayları", expanded=(distance_matrix is None)):
        for msg in matrix_msgs:
             if "Hata:" in msg: st.error(msg)
             else: st.info(msg)

    if distance_matrix is None:
        results_placeholder.error("❌ Mesafe matrisi okunamadı. Lütfen yukarıdaki detayları kontrol edin.")
        st.stop()

    # 2. Yakıt Fiyatlarını Al
    fuel_prices = None
    selected_fuel_price = None
    with st.spinner("⛽ Güncel yakıt fiyatları Opet API'sinden alınıyor..."):
        fuel_prices, price_msgs = get_opet_fuel_prices(TARGET_CITY_CODE, TARGET_DISTRICTS)
        with st.expander("Yakıt Fiyatı Alma Detayları", expanded=(fuel_prices is None)):
             for msg in price_msgs:
                  if "Hata:" in msg: st.error(msg)
                  else: st.info(msg)

    if fuel_prices is None:
         results_placeholder.error("❌ Yakıt fiyatları alınamadı.")
         st.stop()

    selected_fuel_price = fuel_prices.get(fuel_type_internal) # Küçük harf ile kontrol et
    if selected_fuel_price is None:
         results_placeholder.error(f"❌ '{fuel_type}' tipi için hedeflenen ilçelerde fiyat bulunamadı.")
         st.stop()

    results_placeholder.success(f"✅ Hesaplamada kullanılacak {fuel_type} fiyatı: {selected_fuel_price:.4f} TRY/L")

    # 3. TSP Çözücüsünü Çalıştır
    solution = None
    manager = None
    routing = None
    try:
        with st.spinner(f"⏳ En düşük maliyetli rota aranıyor (En Fazla {time_limit} sn)... Lütfen bekleyin."):
            solution, manager, routing, solver_msgs = run_tsp_solver(
                distance_matrix,
                selected_fuel_price,
                vehicle_consumption,
                time_limit,
                COST_SCALING_FACTOR
            )
            with st.expander("Çözücü Çalışma Detayları"):
                 for msg in solver_msgs:
                      if "Hata:" in msg: st.error(msg)
                      else: st.info(msg)
    except Exception as e:
        st.error(f"❌ Çözücü çalıştırılırken kritik bir hata oluştu: {e}")
        st.code(traceback.format_exc())
        st.stop()


    # 4. Sonuçları İşle ve Göster
    if solution:
        results_placeholder.success("🎉 Çözüm başarıyla bulundu!")
        with st.spinner("📊 Sonuçlar işleniyor ve dosyalar hazırlanıyor..."):
            summary_dict, route_df, csv_content, excel_content, process_msgs = process_and_save_results(
                solution, manager, routing, distance_matrix,
                COST_SCALING_FACTOR, selected_fuel_price, vehicle_consumption,
                output_filename
            )
            with st.expander("Sonuç İşleme Detayları"):
                 for msg in process_msgs:
                      if "Hata:" in msg: st.error(msg)
                      else: st.info(msg)

            if summary_dict and route_df is not None and csv_content and excel_content:
                st.subheader("📊 Özet Bilgiler")
                col_a, col_b, col_c = st.columns(3)
                # Özet metrikler (anahtar kontrolü ekleyelim)
                col_a.metric("Toplam Yakıt Maliyeti", f"{summary_dict.get('Toplam Yakıt Maliyeti (TRY)', 'N/A')} TRY")
                col_b.metric("Toplam Mesafe", f"{summary_dict.get('Toplam Mesafe (km)', 'N/A')} km")
                col_c.metric("Ziyaret Sayısı (Depo Hariç)", summary_dict.get('Ziyaret Edilen Konum Sayısı (Depo Hariç)', 'N/A'))

                # Diğer özet bilgileri tablo olarak göster
                summary_display_df = pd.DataFrame(summary_dict.items(), columns=['Ölçüt', 'Değer'])
                st.dataframe(summary_display_df, hide_index=True, use_container_width=True)


                st.subheader("📍 Hesaplanan Rota Adımları")
                st.dataframe(route_df, use_container_width=True) # Sütunlar Türkçe ('Adim', 'Konum_Indeksi')

                st.subheader("💾 Sonuçları İndir")
                col_d, col_e = st.columns(2)
                with col_d:
                    st.download_button(
                        label="⬇️ CSV Olarak İndir", # İkon eklendi
                        data=csv_content,
                        file_name=f"{output_filename}_rota_maliyet.csv",
                        mime='text/csv',
                        use_container_width=True
                    )
                with col_e:
                    st.download_button(
                        label="⬇️ Excel Olarak İndir", # İkon eklendi
                        data=excel_content,
                        file_name=f"{output_filename}_rota_maliyet.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )
            else:
                results_placeholder.error("❌ Sonuçlar işlenirken veya dosyalar hazırlanırken bir hata oluştu. Detayları kontrol edin.")

    else:
        status_name = 'Bilinmiyor'
        solver_status = 'UNKNOWN' # Varsayılan durum
        if routing:
             try:
                  # OR-Tools durum kodlarını metne çevirelim (varsa)
                  status_map = {
                       0: 'ROUTING_NOT_SOLVED', 1: 'ROUTING_SUCCESS', 2: 'ROUTING_FAIL',
                       3: 'ROUTING_FAIL_TIMEOUT', 4: 'ROUTING_INVALID'
                  }
                  solver_status = status_map.get(routing.status(), f'Bilinmeyen Durum ({routing.status()})')
             except Exception: pass
        results_placeholder.warning(f"⚠️ Çözüm bulunamadı! Çözücü durumu: {solver_status}")
        st.info("Süre sınırını artırmayı veya girdi verilerini kontrol etmeyi deneyebilirsiniz.")


# Streamlit uygulamasını çalıştırmak için talimat
st.sidebar.divider()
st.sidebar.markdown("Uygulamayı çalıştırmak için terminalde şu komutu kullanın:")
st.sidebar.code("streamlit run <dosya_adı>.py") # Kullanıcı kendi dosya adını yazmalı