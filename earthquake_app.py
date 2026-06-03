import streamlit as st
import requests
import math
import json
from datetime import datetime, timedelta

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="세계 지진 위험도 분석 시스템",
    page_icon="🌍",
    layout="centered",
)

# ── CSS 스타일 ───────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
    }
    
    .sub-text {
        color: #555;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    
    .risk-box {
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1.2rem;
        display: inline-block;
    }
    
    .risk-high   { background: #ffe0e0; color: #c0392b; border-left: 5px solid #c0392b; }
    .risk-medium { background: #fff3cd; color: #d68910; border-left: 5px solid #d68910; }
    .risk-low    { background: #d4efdf; color: #1e8449; border-left: 5px solid #1e8449; }
    
    .stButton > button {
        background-color: #2c3e7a;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #3d54a8;
    }
</style>
""", unsafe_allow_html=True)

# ── 타이틀 ───────────────────────────────────────────────────
st.markdown('<div class="main-title">세계 지진 위험도 분석 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">위도와 경도를 입력하면 주변 지진 데이터를 기반으로 위험도를 분석합니다.</div>', unsafe_allow_html=True)

# ── 입력 ─────────────────────────────────────────────────────
lat = st.number_input("위도 입력", min_value=-90.0, max_value=90.0, value=37.50, step=0.01, format="%.2f")
lon = st.number_input("경도 입력", min_value=-180.0, max_value=180.0, value=127.00, step=0.01, format="%.2f")

analyze = st.button("위험도 분석")

# ── USGS API에서 지진 데이터 가져오기 ────────────────────────
def fetch_earthquakes(lat, lon, radius_km=500, days=365):
    """USGS Earthquake Hazards Program API 사용"""
    end_time   = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format":    "geojson",
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime":   end_time.strftime("%Y-%m-%d"),
        "latitude":  lat,
        "longitude": lon,
        "maxradius": radius_km / 111,   # 도(degree) 단위로 변환
        "minmagnitude": 2.0,
        "orderby":   "magnitude",
        "limit":     200,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def calculate_risk(earthquakes, lat, lon):
    """지진 데이터로 위험도 점수 계산"""
    if not earthquakes or not earthquakes.get("features"):
        return "낮음", 0, []
    
    features = earthquakes["features"]
    score = 0
    eq_list = []
    
    for f in features:
        props = f["properties"]
        coords = f["geometry"]["coordinates"]
        eq_lon, eq_lat = coords[0], coords[1]
        mag  = props.get("mag", 0) or 0
        dist = haversine(lat, lon, eq_lat, eq_lon)
        
        # 거리·규모 가중치
        if dist < 100:
            weight = 5.0
        elif dist < 250:
            weight = 2.5
        else:
            weight = 1.0
        
        score += (mag ** 2) * weight
        
        # 지도 표시용 색상
        if mag >= 6.0:
            color = "red"
        elif mag >= 4.5:
            color = "orange"
        else:
            color = "green"
        
        eq_list.append({
            "lat":   eq_lat,
            "lon":   eq_lon,
            "mag":   mag,
            "place": props.get("place", "알 수 없음"),
            "color": color,
            "dist":  round(dist, 1),
        })
    
    if score > 5000:
        risk = "높음"
    elif score > 1000:
        risk = "중간"
    else:
        risk = "낮음"
    
    return risk, round(score, 1), eq_list

# ── 분석 실행 ────────────────────────────────────────────────
if analyze:
    with st.spinner("지진 데이터를 불러오는 중..."):
        data = fetch_earthquakes(lat, lon)
    
    risk, score, eq_list = calculate_risk(data, lat, lon)
    
    # 위험도 표시
    risk_class = {"높음": "risk-high", "중간": "risk-medium", "낮음": "risk-low"}[risk]
    risk_emoji = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}[risk]
    
    st.markdown(
        f'<div class="risk-box {risk_class}">{risk_emoji} 예상 위험도: {risk}</div>',
        unsafe_allow_html=True,
    )
    
    col1, col2, col3 = st.columns(3)
    col1.metric("분석 지진 수",    f"{len(eq_list)}건")
    col2.metric("위험도 점수",     f"{score:,.0f}")
    col3.metric("분석 반경",       "500 km")
    
    # ── Leaflet 지도 ─────────────────────────────────────────
    eq_json = json.dumps(eq_list)
    
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin:0; padding:0; }}
            #map {{ height:480px; width:100%; }}
        </style>
    </head>
    <body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{lat}, {lon}], 5);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // 입력 위치 핀
        var pinIcon = L.divIcon({{
            html: '<div style="font-size:28px;line-height:1;">📍</div>',
            iconSize:[30,30], iconAnchor:[15,28], className:''
        }});
        L.marker([{lat}, {lon}], {{icon: pinIcon}})
         .addTo(map)
         .bindPopup('<b>분석 위치</b><br>위도: {lat}, 경도: {lon}')
         .openPopup();
        
        // 지진 데이터 점
        var earthquakes = {eq_json};
        earthquakes.forEach(function(eq) {{
            var radius = Math.max(4, eq.mag * 2.5);
            L.circleMarker([eq.lat, eq.lon], {{
                radius:      radius,
                fillColor:   eq.color,
                color:       '#fff',
                weight:      1,
                opacity:     0.9,
                fillOpacity: 0.75,
            }}).addTo(map)
              .bindPopup(
                '<b>규모 ' + eq.mag.toFixed(1) + '</b><br>' +
                eq.place + '<br>' +
                '거리: ' + eq.dist + ' km'
              );
        }});
        
        // 범례
        var legend = L.control({{position:'bottomright'}});
        legend.onAdd = function(map) {{
            var div = L.DomUtil.create('div');
            div.style.cssText = 'background:white;padding:8px 12px;border-radius:6px;font-size:12px;line-height:1.8;box-shadow:0 1px 5px rgba(0,0,0,.3)';
            div.innerHTML =
                '<b>지진 규모</b><br>' +
                '<span style="color:red">●</span> M6.0+<br>' +
                '<span style="color:orange">●</span> M4.5–6.0<br>' +
                '<span style="color:green">●</span> M2.0–4.5';
            return div;
        }};
        legend.addTo(map);
    </script>
    </body>
    </html>
    """
    
    st.components.v1.html(map_html, height=490, scrolling=False)
    
    # ── 상위 지진 목록 ────────────────────────────────────────
    if eq_list:
        st.subheader("📋 주요 지진 목록 (규모 순)")
        top = sorted(eq_list, key=lambda x: x["mag"], reverse=True)[:10]
        table_rows = ""
        for i, eq in enumerate(top, 1):
            emoji = "🔴" if eq["color"] == "red" else ("🟠" if eq["color"] == "orange" else "🟢")
            table_rows += f"<tr><td>{i}</td><td>{emoji} M{eq['mag']:.1f}</td><td>{eq['place']}</td><td>{eq['dist']} km</td></tr>"
        
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;font-size:0.9rem">
            <thead>
                <tr style="background:#2c3e7a;color:white">
                    <th style="padding:8px">#</th>
                    <th style="padding:8px">규모</th>
                    <th style="padding:8px">위치</th>
                    <th style="padding:8px">거리</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """, unsafe_allow_html=True)
