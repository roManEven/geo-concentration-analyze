import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- КОНФИГУРАЦИЯ ---
# Убедитесь, что бэкенд запущен и ссылка актуальна
BACKEND_URL = "https://julietta-aquicultural-samara.ngrok-free.dev/analyze"

st.set_page_config(
    page_title="Картограф концентраций", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Инициализация состояния
if "results" not in st.session_state:
    st.session_state.results = None

st.title("📊 Глобальный анализатор координат")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_html=True)

# --- ПАРАМЕТРЫ В БОКОВОЙ ПАНЕЛИ ---
with st.sidebar:
    st.header("⚙️ Настройки анализа")
    radius = st.number_input("Радиус зоны (метры)", min_value=10, max_value=10000, value=500, step=50)
    min_points = st.number_input("Мин. точек для зоны", min_value=1, max_value=500, value=5)
    
    st.write("---")
    if st.button("🗑️ Сбросить всё", use_container_width=True):
        st.session_state.results = None
        st.rerun()
    
    st.info("Интерфейс отправляет Excel-файл на ваш локальный сервер через ngrok.")

# --- ЗАГРУЗКА И ОТПРАВКА ---
uploaded_file = st.file_uploader("Загрузите файл Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    if st.button("🚀 Запустить расчет", type="primary", use_container_width=True):
        with st.spinner("Связь с сервером..."):
            try:
                # Подготовка файла для отправки
                files = {
                    "file": (
                        uploaded_file.name, 
                        uploaded_file.getvalue(), 
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                }
                payload = {"radius": radius, "min_points": min_points}

                response = requests.post(BACKEND_URL, files=files, data=payload, timeout=60)

                if response.status_code == 200:
                    st.session_state.results = response.json()
                    st.success("✅ Данные успешно обработаны!")
                else:
                    st.error(f"❌ Ошибка бэкенда. Код: {response.status_code}")
                    st.write(response.text)
            except Exception as e:
                st.error(f"📡 Не удалось достучаться до сервера: {e}")

# --- ВИЗУАЛИЗАЦИЯ ---
if st.session_state.results:
    res = st.session_state.results

    if res.get("status") == "ok":
        # 1. Метрики
        total_points = res.get("total_parsed", 0)
        zones_found = len(res.get("zones", []))
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего точек", total_points)
        col2.metric("Найдено зон", zones_found)
        col3.metric("Радиус поиска", f"{radius} м")

        # 2. Карта
        st.subheader("🗺️ Интерактивная карта результатов")
        
        # Определяем центр карты
        if zones_found > 0:
            center_coords = res["zones"][0]["center"]
        elif total_points > 0 and res.get("all_points"):
            center_coords = res["all_points"][0]
        else:
            center_coords = [55.75, 37.62] # Москва

        m = folium.Map(location=center_coords, zoom_start=12, tiles="CartoDB positron")

        # Отрисовка исходных точек
        if res.get("all_points"):
            for p in res["all_points"]:
                folium.CircleMarker(
                    location=p,
                    radius=2,
                    color="#3186cc",
                    fill=True,
                    fill_opacity=0.4,
                    weight=1
                ).add_to(m)

        # Отрисовка найденных зон (кластеров)
        if res.get("zones"):
            for i, zone in enumerate(res["zones"]):
                lat_lon = zone["center"]
                count = zone["count"]
                address = zone.get("address", "Адрес не определен")

                popup_content = f"""
                <div style="font-family: Arial, sans-serif; width: 200px;">
                    <h4 style="margin:0 0 10px 0;">Зона №{i+1}</h4>
                    <b>Точек:</b> {count}<br>
                    <b>Адрес:</b> {address}
                </div>
                """
                
                # Основной маркер (иконка)
                folium.Marker(
                    location=lat_lon,
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f"Зона {i+1}: {count} точ.",
                    icon=folium.Icon(color="red", icon="info-sign", prefix="glyphicon")
                ).add_to(m)

                # Визуальный круг радиуса
                folium.Circle(
                    location=lat_lon,
                    radius=radius,
                    color="red",
                    weight=1,
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.1
                ).add_to(m)

        # Вывод карты в Streamlit
        st_folium(m, width="100%", height=600, key="map_output")

        # 3. Таблица с данными
        if res.get("zones"):
            st.subheader("📝 Детальный список зон")
            df_display = pd.DataFrame(res["zones"])
            # Переименуем колонки для красоты
            df_display.columns = ["Координаты центра", "Количество точек", "Адрес"]
            st.dataframe(df_display, use_container_width=True)
            
            # Кнопка скачивания CSV
            csv = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Скачать результат в CSV",
                data=csv,
                file_name="result_zones.csv",
                mime="text/csv",
            )
    else:
        st.error(f"Ошибка алгоритма: {res.get('message')}")

# Подвал
st.write("---")
st.caption("Система анализа гео-данных | Streamlit + Folium")
