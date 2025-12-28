import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- КОНФИГУРАЦИЯ ---
# ЗАМЕНИТЕ НА ВАШУ АКТУАЛЬНУЮ ССЫЛКУ ИЗ NGROK
BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"

st.set_page_config(page_title="Картограф концентраций", layout="wide")

# Инициализация состояния (чтобы данные не исчезали)
if "results" not in st.session_state:
    st.session_state.results = None

st.title("📊 Глобальный анализатор координат")
st.info("Интерфейс работает в облаке, вычисления — на вашем ПК дома.")

# --- ПАРАМЕТРЫ В БОКОВОЙ ПАНЕЛИ ---
with st.sidebar:
    st.header("⚙️ Настройки анализа")
    radius = st.number_input("Радиус зоны (метры)", min_value=10, max_value=5000, value=500)
    min_points = st.number_input("Мин. точек для зоны", min_value=1, max_value=100, value=5)
    st.write("---")
    if st.button("🗑️ Сбросить всё"):
        st.session_state.results = None
        st.rerun()

# --- ЗАГРУЗКА И ОТПРАВКА ---
uploaded_file = st.file_uploader("Загрузите файл Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    if st.button("🚀 Запустить расчет на домашнем ПК", type="primary"):
        with st.spinner("Файл обрабатывается вашим компьютером..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(),
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                payload = {"radius": radius, "min_points": min_points}

                response = requests.post(BACKEND_URL, files=files, data=payload)

                if response.status_code == 200:
                    st.session_state.results = response.json()
                    st.success("Данные успешно получены!")
                else:
                    st.error(f"Ошибка связи с ПК. Код: {response.status_code}")
            except Exception as e:
                st.error(f"Не удалось достучаться до сервера: {e}")

# --- ВИЗУАЛИЗАЦИЯ ---
if st.session_state.results:
    res = st.session_state.results

    if res.get("status") == "ok":
        # Метрики
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего точек", res.get("total_parsed", 0))
        c2.metric("Найдено зон", len(res.get("zones", [])))
        c3.metric("Радиус", f"{radius} м")

        # Создание карты
        # Центрируем на первой точке или на Москве по умолчанию
        start_pos = res["all_points"][0] if res.get("all_points") else [55.75, 37.62]
        m = folium.Map( location=start_pos, zoom_start=11, tiles='{z}/{x}/{y}.png', attr='OpenStreetMap Russia' )

        # 1. Рисуем все исходные точки (маленькие синие кружки)
        if res.get("all_points"):
            for p in res["all_points"]:
                folium.CircleMarker(
                    location=p,
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_opacity=0.4,
                    weight=1
                ).add_to(m)

        # 2. Рисуем зоны концентрации (красные маркеры + круги)
        if res.get("zones"):
            for i, zone in enumerate(res["zones"]):
                # Маркер с адресом в Popup
                popup_text = f"""
                <div style='width:200px'>
                    <b>Зона №{i + 1}</b><br>
                    <b>Точек:</b> {zone['count']}<br>
                    <b>Адрес:</b> {zone.get('address', 'Не определен')}
                </div>
                """
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Зона {i + 1} ({zone['count']} точ.)",
                    icon=folium.Icon(color="red", icon="star")
                ).add_to(m)

                # Круг радиуса
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="red",
                    fill=True,
                    fill_opacity=0.15
                ).add_to(m)

        # Отображение
        st.subheader("🗺️ Интерактивная карта результатов")
        st_folium(m, width="100%", height=650, key="geo_map")

        # Таблица результатов
        if res.get("zones"):
            st.subheader("📝 Список зон")
            zones_df = pd.DataFrame(res["zones"])
            # Немного причешем таблицу для отображения
            zones_df.columns = ['Центр (Lat, Lon)', 'Кол-во точек', 'Адрес']
            st.dataframe(zones_df, use_container_width=True)
    else:
        st.error(f"Ошибка бэкенда: {res.get('message')}")

# Подвал
st.write("---")

st.caption("Разработка: Python + FastAPI + Streamlit + Ngrok")






