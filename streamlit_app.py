import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- 1. Supabase 연결 설정 (secrets로 불러옴)--- 
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# 클라이언트 생성
@st.cache_resource  # 매번 연결하지 않도록 캐싱
def get_supabase() -> Client :
    return create_client(url, key)

supabase = get_supabase()


# --- 앱 실행부 ---
st.title("☕ 데일리 음료 섭취 분석기(DB)")

# 입력 섹션 (사이드 바)
with st.sidebar :
    st.header("기록하기")
    date_input = st.date_input("날짜", datetime.now()).strftime('%Y-%m-%d')
    type_input = st.selectbox("종류", ["커피", "물", "차", "음료수"])
    count_input = st.number_input("잔", 1, 10, 1)\
    
    if st.button("저장하기") :
        # supabase에 데이터 삽입 (딕셔너리 형태)
        data = {
            "date" : date_input,
            "drink_type" : type_input,
            "count" : count_input
        }

        response = supabase.table("drinks").insert(data).execute()

        if response :
            st.success("저장되었습니다.")
            st.rerun()

# 데이터 불러오기
response = supabase.table("drinks").select("*").execute()
df = pd.DataFrame(response.data)

# 화면 표시
if not df.empty :
    col1, col2 = st.columns(2)
    with col1 :
        st.subheader("📋 전체 로그")
        st.dataframe(df[["date", "drink_type", "count"]], use_container_width=True)

    with col2 :
        st.subheader("📊 통계")
        stats = df.groupby("drink_type")["count"].sum()
        st.bar_chart(stats)

else :
    st.info("아직 저장된 데이터가 없습니다.")
