import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar
import datetime


url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="스케쥴 관리", layout="wide")
st.title("🗓️ Smart Todo Calendar")

def get_all_events() :
    all_events = []

    # 1. 일반 일정 ( 완료시 취소선 텍스트 처리)
    todos = supabase.table("monthly").select("*").execute().data
    for t in todos :
        # 텍스트 취소선은 폰트 지원에 따라 ✔️ 이모지나 (완료) 문구로 대체가 가장 안정적
        prefix = "✅ " if t['is_completed'] else "📌 "
        all_events.append({
            "id" : f"todo_{t['id']}",
            "title" : f"{prefix}{t['title']}",
            "start" : t['target_date'],
            "end" : t['end_date'] if t['end_date'] else t['target_date'],
            "color" : "#999999" if t['is_completed'] else "#203864",
            "extendedProps" : {"type" : "todo", "db_id" : t['id']}
        })

    # 2. 반복 일정 (매달 생성)
    recurrings = supabase.table("recurrings").select("*").execute().data
    curr_date = datetime.date.today()
    for r in recurrings :
        for m in range(1, 13) :
            try :
                r_date = datetime.date(curr_date.year, m, int(r['repeat_day']))
                all_events.append({
                    "id" : f"recur_{r['id']}_{m}",
                    "title" : f"🔄 {r['title']}",
                    "start" : str(r_date),
                    "color" : "#1167b1",
                    "extendedProps" : {"type" : "recurring", "db_id" : r['id']}
                })
            except ValueError : # 2월 30일 같은 예외 처리
                continue

    # 3. 휴무일 (배경색 처리)
    holidays = supabase.table("holidays").select("*").execute().data
    for h in holidays :
        all_events.append({
            "id" : f"holiday_{h['id']}",
            "title" : h['title'],
            "start" : h['holiday_date'],
            "display" : "background",
            "backgroundColor" : h.get('color_code', '#FFEDED'),
            "extendedProps" : {"type" : "holiday", "db_id" : h['id']}
        })

    return all_events

events = get_all_events()
calendar_options = {

        "headerToolbar" : {
        "left" : "prev,next,today",
        "center" : "title",
        "right" : "dayGridMonth"
    },
    "timeZone" : "Asia/Seoul",
    "initialView" : "dayGridMonth",
    "selectable" : True,    # 날짜 선택 가능하게 설정
    "navLinks" :False,   # 날짜 클릭 가능하게 설정
    "selectMirror" : True,    
    "locale" : "ko",
}

# --- 달력 렌더링 ---
state = calendar(events=events, options=calendar_options, callbacks=["select"], key="calendar_v5")

if "clicked_date" not in st.session_state :
    st.session_state["clicked_date"] = None

if state.get("callback") == "select" :
    st.session_state["clicked_date"] = state["select"]["start"][:10]

if st.session_state["clicked_date"] :
    selected_date = st.session_state["clicked_date"]
    st.divider()
    st.subheader(f"📅{selected_date} 일정")

    # 해당 날짜의 데이터만 필터링
    day_events = [e for e in events if e["start"] == selected_date]

    if day_events :
        for e in day_events :
            badge = {"todo": "🔵", "recurring": "🟢", "holiday": "🔴"}
            etype = e["extendedProps"]["type"]
            st.write(f"{badge[etype]} **{e['title']}** ({etype})")


with st.sidebar :
    st.header("➕ 일정 추가")


    # 사이드바 내부 탭 구성
    tab1, tab2, tab3 = st.tabs(["일반", "반복", "휴무"])

    # --- tab 1 : 일반 일정 추가 ---
    with tab1 :
        with st.form("todo_form", clear_on_submit=True) :
            t_title = st.text_input("일반 할 일")
            col1, col2 = st.columns(2)
            s_date = col1.date_input("시작일", datetime.date.today())
            e_date = col2.date_input("종료일(선택)", value=None)
            if st.form_submit_button("일반 등록") :
                if t_title :
                    supabase.table("monthly").insert({
                        "title" : t_title,
                        "target_date" : str(s_date),
                        "end_date" : str(e_date) if e_date else None,
                        "is_completed" : False
                    }).execute()
                    st.rerun()

    # --- tab 2 : 반복 일정 추가 ---
    with tab2 :
        with st.form("recurring_form", clear_on_submit=True) :
            r_title = st.text_input("반복 업무")
            r_day = st.number_input("매달 반복일", 1, 31, value=1)
            if st.form_submit_button("반복 업무 등록") :
                if r_title :
                    supabase.table("recurrings").insert({
                        "title" : r_title,
                        "repeat_day" : r_day
                    }).execute()
                    st.rerun()

    # --- tab 3 : 휴무일/공휴일 지정 ---
    with tab3 :
        with st.form("holiday_form", clear_on_submit=True) :
            h_title = st.text_input("휴무일")
            h_reason = st.text_input("휴무 사유")
            h_date = st.date_input("날짜 지정", datetime.date.today())
            # 색상 선택 기능 추가
            h_color = st.color_picker("배경색 선택", "#FFEDED")
            if st.form_submit_button("휴무일 등록") :
                if h_title :
                    supabase.table("holidays").insert({
                        "title" : h_title,
                        "reason" : h_reason,
                        "holiday_date" : str(h_date),
                        "color_code" : h_color
                    }).execute()
                    st.rerun()


