import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# --- КОНФИГУРАЦИЯ ---
# Используем секреты Streamlit для хранения ссылки
try:
    BACKEND_URL = st.secrets["MY_BACKEND_LINK"] + "/analyze"
except Exception:
    # Запасной вариант, если секреты не настроены
    BACKEND_URL = "https://julietta-aquicultural-samara.ngrok-free.dev/analyze"

st.set_page_config(page_title="Картограф концентраций", layout="wide")

# Инициализация состояния (чтобы данные не исчезали при обновлении страницы)
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
    if st.button("🚀 Запустить расчет", type="primary"):
        with st.spinner("Файл обрабатывается бэкендом..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(),
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                payload = {"radius": radius, "min_points": min_points}

                response = requests.post(BACKEND_URL, files=files, data=payload, timeout=60)

                if response.status_code == 200:
                    st.session_state.results = response.json()
                    st.success("Данные успешно получены!")
                else:
                    st.error(f"Ошибка связи с ПК. Код: {response.status_code}")
                    if response.status_code == 404:
                        st.warning("Проверьте, активен ли туннель Ngrok и запущен ли сервер на ПК.")
            except Exception as e:
                st.error(f"Не удалось достучаться до сервера: {e}")

# --- ВИЗУАЛИЗАЦИЯ ---
if st.session_state.results:
    res = st.session_state.results

    if res.get("status") == "ok":
        # 1. Метрики
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего точек", res.get("total_parsed", 0))
        c2.metric("Найдено зон", len(res.get("zones", [])))
        c3.metric("Радиус охвата", f"{radius} м")

        # 2. Создание карты
        # Центрируем на первой найденной зоне или на Москве
        if res.get("zones"):
            start_pos = res["zones"][0]["center"]
        elif res.get("all_points"):
            start_pos = res["all_points"][0]
        else:
            start_pos = [55.75, 37.62]

        # Создаем объект карты
        # tiles="openstreetmap" - стандартная карта (будет на русском)
        # attr=' ' - удаляет текстовый логотип и ссылки в углу
        m = folium.Map(
            location=start_pos, 
            zoom_start=11, 
            tiles="openstreetmap",
            attr=' '
        )

        # Рисуем все исходные точки (синие маркеры)
        if res.get("all_points"):
            for p in res["all_points"]:
                folium.CircleMarker(
                    location=p,
                    radius=3,
                    color="#1a73e8",
                    fill=True,
                    fill_opacity=0.4,
                    weight=1
                ).add_to(m)

        # Рисуем зоны концентрации (красные маркеры + круги)
        if res.get("zones"):
            for i, zone in enumerate(res["zones"]):
                # HTML-контент для всплывающего окна
                popup_text = f"""
                <div style='width:200px; font-family: sans-serif;'>
                    <b style='color: #d93025;'>Зона №{i + 1}</b><br>
                    <b>Точек в кластере:</b> {zone['count']}<br>
                    <b>Адрес:</b> {zone.get('address', 'Не определен')}
                </div>
                """
                
                # Ставим маркер-звезду
                folium.Marker(
                    location=zone["center"],
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Зона {i + 1}",
                    icon=folium.Icon(color="red", icon="star")
                ).add_to(m)

                # Рисуем круг радиуса
                folium.Circle(
                    location=zone["center"],
                    radius=radius,
                    color="#d93025",
                    fill=True,
                    fill_opacity=0.15,
                    weight=2
                ).add_to(m)

        # Отображение карты в Streamlit
        st.subheader("🗺️ Интерактивная карта")
        st_folium(m, width="100%", height=650, key="geo_map_final")

        # 3. Таблица результатов
        if res.get("zones"):
            st.subheader("📝 Список найденных зон")
            zones_df = pd.DataFrame(res["zones"])
            # Приводим названия колонок в порядок
            if len(zones_df.columns) >= 3:
                zones_df.columns = ['Центр (Lat, Lon)', 'Кол-во точек', 'Адрес']
            st.dataframe(zones_df, use_container_width=True)
            
            # Кнопка скачивания
            csv = zones_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Скачать список зон в CSV",
                data=csv,
                file_name="analis_results.csv",
                mime="text/csv",
            )
    else:
        st.error(f"Ошибка бэкенда: {res.get('message')}")

# Подвал
st.write("---")
st.caption("Система: Streamlit + Folium (OpenStreetMap) | Без логотипов и атрибуции")
