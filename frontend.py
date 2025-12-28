import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
from folium.plugins import BeautifyIcon

# --- КОНФИГУРАЦИЯ ---
# ВНИМАНИЕ: Убедитесь, что эта ссылка совпадает с той, что выдал ngrok при запуске
BACKEND_URL = "https://julietta-aquicultural-samara.ngrok-free.dev/analyze"

st.set_page_config(page_title="Картограф зон", layout="wide")

# Инициализация состояния
if "results" not in st.session_state:
    st.session_state.results = None

st.title("🛰️ Анализатор гео-концентраций")

# --- САЙДБАР ---
with st.sidebar:
    st.header("⚙️ Настройки")
    radius = st.number_input("Радиус охвата (м)", 10, 5000, 500)
    min_pts = st.number_input("Мин. точек в зоне", 1, 100, 5)
    st.write("---")
    if st.button("🗑️ Очистить данные"):
        st.session_state.results = None
        st.rerun()

# --- ЗАГРУЗКА ФАЙЛА ---
uploaded_file = st.file_uploader("Загрузите Excel (.xlsx) с координатами", type=["xlsx"])

if uploaded_file:
    if st.button("🚀 Провести анализ", type="primary"):
        with st.spinner("Запрос к вашему ПК через ngrok..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), 
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                data = {"radius": radius, "min_points": min_pts}
                
                response = requests.post(BACKEND_URL, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    st.session_state.results = response.json()
                    st.success("Данные получены!")
                else:
                    st.error(f"Сервер на ПК ответил ошибкой: {response.status_code}")
                    st.info("Проверьте, запущен ли скрипт бэкенда на компьютере.")
            except Exception as e:
                st.error(f"Не удалось соединиться с ПК: {e}")

# --- КАРТА И РЕЗУЛЬТАТЫ ---
if st.session_state.results:
    res = st.session_state.results
    
    if res.get("status") == "ok":
        # Метрики сверху
        m1, m2, m3 = st.columns(3)
        m1.metric("Обработано точек", res.get("total_parsed", 0))
        m2.metric("Найдено зон", len(res.get("zones", [])))
        m3.metric("Радиус", f"{radius} м")

        # Настройка карты
        center = res["zones"][0]["center"] if res.get("zones") else [55.75, 37.62]
        m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

        # 1. Отрисовка всех точек (синие мелкие)
        if res.get("all_points"):
            for p in res["all_points"]:
                folium.CircleMarker(
                    location=p, radius=2, color="#3498db", fill=True, weight=1
                ).add_to(m)

        # 2. Отрисовка Зон (логотипы-маркеры)
        if res.get("zones"):
            for i, zone in enumerate(res["zones"]):
                # Создаем стильный логотип-маркер
                b_icon = BeautifyIcon(
                    icon='star', 
                    inner_icon_style='color:white;font-size:14px;',
                    background_color='#e74c3c',
                    border_color='#c0392b',
                    border_width=2,
                    number=i+1
                )
                
                # Попап с информацией
                html_info = f"""
                <div style='width:180px; font-family:sans-serif;'>
                    <b style='color:#e74c3c;'>Зона №{i+1}</b><br>
                    <b>Точек:</b> {zone['count']}<br>
                    <b>Адрес:</b> {zone.get('address', 'н/д')}
                </div>
                """
                
                folium.Marker(
                    location=zone["center"],
                    tooltip=f"Зона {i+1}",
                    popup=folium.Popup(html_info, max_width=250),
                    icon=b_icon
                ).add_to(m)

                # Круг радиуса
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="#e74c3c",
                    fill=True,
                    fill_opacity=0.1,
                    weight=1
                ).add_to(m)

        # Вывод карты
        st_folium(m, width="100%", height=600, key="main_map")

        # Таблица внизу
        with st.expander("Посмотреть таблицу зон"):
            df = pd.DataFrame(res["zones"])
            st.dataframe(df, use_container_width=True)
    else:
        st.error(f"Бэкенд вернул ошибку: {res.get('message')}")

st.write("---")
st.caption("Статус туннеля: ngrok активен")
