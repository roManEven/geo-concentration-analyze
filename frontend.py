import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- КОНФИГУРАЦИЯ ---
BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"
st.set_page_config(page_title="Картограф", layout="wide")

# Инициализация состояния
if "results" not in st.session_state:
    st.session_state.results = None

st.title("📊 Глобальный анализатор")

# Боковая панель с настройками
with st.sidebar:
    st.header("⚙️ Настройки")
    radius = st.number_input("Радиус (м)", min_value=10, value=500)
    min_points = st.number_input("Мин. точек", min_value=1, value=5)
    if st.button("🗑️ Сброс"):
        st.session_state.results = None
        st.rerun()

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите Excel", type=["xlsx"])

if uploaded_file:
    if st.button("🚀 Запуск", type="primary"):
        with st.spinner("Обработка..."):
            try:
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                }
                payload = {
                    "radius": radius,
                    "min_points": min_points
                }
                response = requests.post(BACKEND_URL, files=files, data=payload)

                if response.status_code == 200:
                    st.session_state.results = response.json()
                else:
                    st.error("Ошибка связи с сервером")
            except Exception as e:
                st.error(f"Ошибка: {e}")

# Отображение результатов
if st.session_state.results:
    res = st.session_state.results
    if res.get("status") == "ok":
        # Определяем начальную позицию карты
        start_pos = res["all_points"][0] if res.get("all_points") else [55.75, 37.62]

        # Создаём карту — ИСПРАВЛЕНО: добавлен правильный URL тайлов
        m = folium.Map(
            location=start_pos,
            zoom_start=11,
            tiles="https://tile.openstreetmap.ru/{z}/{x}/{y}.png",
            attr='© OpenStreetMap РФ',
            control_scale=True
        )

        # Отображаем все точки
        if res.get("all_points"):
            for p in res["all_points"]:
                folium.CircleMarker(
                    location=p,
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_color="blue"
                ).add_to(m)

        # Отображаем зоны
        if res.get("zones"):
            for i, zone in enumerate(res["zones"]):
                popup_text = f"Зона {i + 1}\nТочек: {zone['count']}"
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text),
                    icon=folium.Icon(color="red")
                ).add_to(m)
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="red",
                    fill=True,
                    fill_opacity=0.15
                ).add_to(m)

        # Отображаем карту в Streamlit
        st_folium(m, width="100%", height=650)

        # Отображаем таблицу зон
        if res.get("zones"):
            zones_df = pd.DataFrame(res["zones"])
            st.dataframe(zones_df, use_container_width=True)
