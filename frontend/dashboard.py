# dashboard.py (전체 코드)
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="SmartCare Dashboard", layout="wide")

# API 호출
@st.cache_data(ttl=10)
def get_stats():
    return requests.get('http://localhost:8000/api/stats').json()

@st.cache_data(ttl=10)
def get_activities():
    return requests.get('http://localhost:8000/api/activities?limit=100').json()

@st.cache_data(ttl=10)
def get_summary():
    return requests.get('http://localhost:8000/api/activities/summary').json()

# 헤더
st.title("🏠 SmartCare Dashboard")
st.markdown("AI 기반 생활 패턴 모니터링")

# 통계 카드
stats = get_stats()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("오늘 활동", stats['activities']['today'], "건")
with col2:
    st.metric("총 활동", stats['activities']['total'], "건")
with col3:
    st.metric("오늘 감지", stats['events']['today'], "건")
with col4:
    st.metric("총 감지", stats['events']['total'], "건")

st.divider()

# 탭
tab1, tab2, tab3 = st.tabs(["📊 활동 요약", "📈 차트", "📋 로그"])

with tab1:
    st.subheader("오늘의 활동 요약")
    summary = get_summary()
    
    if summary['summary']:
        summary_data = []
        for activity, data in summary['summary'].items():
            summary_data.append({
                '활동': activity,
                '총 시간': data['total_time'],
                '횟수': data['count']
            })
        
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True)
    else:
        st.info("오늘 활동 데이터가 없습니다.")

with tab2:
    st.subheader("활동 분포")
    activities = get_activities()
    
    if activities:
        # 활동별 카운트
        activity_counts = {}
        for act in activities:
            name = act['activity']
            activity_counts[name] = activity_counts.get(name, 0) + 1
        
        df_chart = pd.DataFrame({
            '활동': list(activity_counts.keys()),
            '횟수': list(activity_counts.values())
        })
        
        fig = px.bar(df_chart, x='활동', y='횟수', color='활동')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

with tab3:
    st.subheader("최근 활동 로그")
    
    if activities:
        log_data = []
        for act in activities[:20]:
            log_data.append({
                'ID': act['id'],
                '활동': act['activity'],
                '구역': act['zone'] or '-',
                '시간': datetime.fromisoformat(act['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                '지속시간(초)': act['duration'] or '-'
            })
        
        df_log = pd.DataFrame(log_data)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("로그가 없습니다.")

# 자동 새로고침
st.button("🔄 새로고침")