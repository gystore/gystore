import streamlit as st
import pandas as pd 
from datetime import datetime

st.set_page_config(page_title="섭최량 분석기", page_icon="☕")
st.title("☕ 데일리 음료 섭취 분석기")

# 1. 데이터 저장소 초기화 (세션 상태)
if 'logs' not in st.session_state :
    # 예시 데이터를 미리 조금 넣어둔다
    st.session_state.logs = pd.DataFrame(columns = ["날자", "종류", "잔(Cups)"])

# 2. 사이드바 - 입력 섹션
with st.sidebar :
    st.header("기록하기")
    date = st.date_input("날짜 선택", datetime.now())
    drink_type = st.selectbox("종류", ["커피", "물", "차", "음료수"])
    count = st.number_input("섭취량(잔)", min_value=1, max_value=20, value=1)

    if st.button("기록 저장") :
        new_data = pd.DataFrame({
            '날짜' : [date],
            '종류' : [drink_type],
            '잔(Cups)' : [count]
        })
        # 기존 데이터프레임에 새 행 추가
        st.session_state.logs = pd.concat([st.session_state.logs, new_data], ignore_index=True)
        st.success("기록되었습니다!")

# 3. 메인 화면 - 시각화 섹션
col1, col2 = st.columns(2)

with col1 :
    st.subheader("📋 최근 기록")
    st.dataframe(st.session_state.logs, use_container_width=True)

with col2 :
    st.subheader("📊 종류별 통계")
    if not st.session_state.logs.empty :
        # 종류별로 그룹화하여 합계 계산
        stats = st.session_state.logs.groupby("종류")["잔(Cups)"].sum()
        st.bar_chart(stats)
    else :
        st.write("데이터가 없습니다.")

# 4. 시간 흐름에 따른 분석
st.subheader("📈 날짜별 섭취 추이")
if not st.session_state.logs.empty :
    #날짜별 합계 계산
    timeline = st.session_state.logs.groupby("날짜")["잔(Cups)"].sum()
    st.line_chart(timeline)

# 5. 데이터 초기화 버튼
if st.button("모든 데이터 초기화") :
    st.session_state.logs = pd.DataFrame(columns=["날짜", "종류", "잔(Cups)"])
    st.rerun()
