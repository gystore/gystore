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
    curr_date = datetime.date.today()
    
    # 1. 일반 일정 ( 완료시 취소선 텍스트 처리)
    todos = supabase.table("monthly").select("*").execute().data
    for t in todos :
        # 텍스트 취소선은 폰트 지원에 따라 ✔️ 이모지나 (완료) 문구로 대체가 가장 안정적
        prefix = "✅ " if t['is_completed'] else "📌 "
        all_events.append({
            "id" : f"todo_{t['id']}",
            "title" : f"{prefix} {t['title']}",
            "start" : t['target_date'],
            "end" : t['end_date'] if t['end_date'] else t['target_date'],
            "is_completed" : t['is_completed'],
            "color" : "#999999" if t['is_completed'] else "#203864",
            "extendedProps" : {"type" : "todo", "db_id" : t['id']}
        })

    # 2. 반복 일정 (매달 생성)
    recurrings = supabase.table("recurrings").select("*").execute().data
    
    for r in recurrings :
        if r['type'] == "monthly" :
            for m in range(1, 13) :
                try :
                    r_date = datetime.date(curr_date.year, m, int(r['repeat_value']))
                    all_events.append({
                        "id" : f"recur_{r['id']}_m_{m}",
                        "title" : f"[매월]{r['title']}",
                        "start" : str(r_date),
                        "color" : "#1167b1",
                        "extendedProps" : {"type" : "recurring", "db_id" : r['id']}
                    })
                except ValueError : # 2월 30일 같은 예외 처리
                    continue
        elif r['type'] == 'weekly' :
            # 매주 반복 (올해 시작일부터 연말까지 해당 요일 계산)
            start_of_year = datetime.date(curr_date.year, 1, 1)
            # 첫번째 해당 요일 찾기
            days_ahead = r['repeat_value'] - start_of_year.weekday()
            if days_ahead < 0 :
                days_ahead += 7
            target_date = start_of_year + datetime.timedelta(days=days_ahead)

            # 1년치 주간 일정 생성
            while target_date.year == curr_date.year :
                all_events.append({
                    "id" : f"recur_{r['id']}_w_{target_date.strftime('%m%d')}",
                    "title" : f"[주간] {r['title']}",
                    "start" : str(target_date),
                    "color" : "#008080",
                    "extendedProps" : {"type" : "recurring", "db_id" : r['id']}
                })
                target_date += datetime.timedelta(weeks=1)
                
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
            db_id = e["extendedProps"]["db_id"]
            # st.write(f"{badge[etype]} **{e['title']}** ({etype})")
            id = e['id'].split("_")[1]
            etitle = f"{badge[etype]} {e['title']}"

            if etype == "todo" :
                col1, col2, col3 = st.columns([0.6, 0.2, 0.2])

                # col1 : markdown, 완료 여부에 따른 텍스트 스타일링
                title_text = f"{badge[etype]} <del>{e['title']}</del>" if e['is_completed'] else etitle
                col1.markdown(title_text, unsafe_allow_html=True)

                # col2 : 완료 토글 버튼
                btn_label = "미완료" if e['is_completed'] else "완료"
                if col2.button(btn_label, key=f"status_{e['id']}", use_container_width=True) :
                    supabase.table("monthly").update({"is_completed" : not e['is_completed']}).eq("id", id).execute()
                    st.rerun()

                # col3 : 수정 및 삭제 서브폼 (Expander 제어)
                with col3.expander("수정") :
                    with st.form(f"todo_edit_{e['id']}") :
                        edit_title = st.text_input("제목 수정", value = e['title'])                        
                        edit_start_date = st.date_input("시작일 변경", value = e['start'])
                        edit_end_date = st.date_input("종료일 변경", value = e['end'])                        

                        sub_c1, sub_c2 = st.columns(2)
                        if sub_c1.form_submit_button("저장") :
                            if edit_end_date != e['end'] :
                               supabase.table("monthly").update({"title" : edit_title, "target_date" : str(edit_start_date), "end_date" : str(edit_end_date)}).eq("id", id).execute() 
                            supabase.table("monthly").update({"title" : edit_title, "target_date" : str(edit_start_date)}).eq("id", id).execute()
                            st.rerun()
                        if sub_c2.form_submit_button("삭제") :
                            supabase.table("monthly").delete().eq("id", id).execute()
                            st.rerun()

            # (2) 반복 규칙 리스트 (규칙 수정, 삭제)
            elif etype == "recurring" :
                col1, col2 = st.columns([0.8, 0.2])
                col1.write(etitle)

                with col2.expander("변경") :
                    with st.form(f"recur_edit_{e['id']}") :
                        edit_r_title = st.text_input("일정 변경", value = e['title'])

                        sub_rc1, sub_rc2 = st.columns(2)
                        if sub_rc1.form_submit_button("저장") :
                            supabase.table("recurrings").update({"title" : edit_r_title}).eq("id", id).execute()
                            st.rerun()
                        if sub_rc2.form_submit_button("해제", type="primary") :
                            supabase.table("recurrings").delete().eq("id", id).execute()
                            st.rerun()
            
            # (3) 휴무일 리스트
            elif etype == "holiday" :
                col1, col2 = st.columns([0.8, 0.2])
                col1.write(etitle)

                if col2.button("삭제", key=f"hol_{e['id']}", type="primary", use_container_width=True) :
                    supabase.table("holidays").delete().eq("id", id).execute()
                    st.rerun()



    else :
        st.info("등록된 일정 없음")



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
        r_type = st.selectbox("반복 주기", ["매월", "매주"])
        with st.form("recurring_form", clear_on_submit=True) :
            r_title = st.text_input("반복 업무")            
            if r_type == "매월" :
                r_val = st.number_input("매달 반복일", 1, 31, value=1)
                db_type = "monthly"
            else :
                # 요일을 선택받고 인덱스로 변환
                day_labels = ["월요일", "화요일","수요일", "목요일", "금요일", "토요일", "일요일"] 
                r_labels = st.selectbox("요일지정", day_labels)
                r_val = day_labels.index(r_labels)
                db_type = "weekly"

            r_desc = st.text_area("상세 설명 (선택)")

            if st.form_submit_button("반복 업무 등록") :
                if r_title :
                    supabase.table("recurrings").insert({
                        "title" : r_title,
                        "type" : db_type,
                        "repeat_value" : r_val,
                        "description" : r_desc
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


