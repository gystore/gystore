import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar
import datetime


url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

type_labels = { "monthly" : "매월" , "weekly" : "매주"}

st.set_page_config(page_title="스케쥴 관리", layout="wide")
st.title("🗓️ Smart Todo Calendar")

def get_all_events() :
    all_events = []
    curr_date = datetime.date.today()

    # 예외 데이터 먼저 로드
    exceptions = supabase.table("recurring_exceptions").select("*").execute().data
    # 빠른 조회를 위해 (recurring_id, original_date 문자열) 세트 구축
    except_set = {(ex['recurring_id'], ex['original_date']) for ex in exceptions}
    
    # 1. 일반 일정 ( 완료시 취소선 텍스트 처리)
    todos = supabase.table("monthly").select("*").execute().data
    for t in todos :
        # 텍스트 취소선은 폰트 지원에 따라 ✔️ 이모지나 (완료) 문구로 대체가 가장 안정적
        prefix = "✅ " if t['is_completed'] else "📌 "
        all_events.append({
            "id" : f"todo_{t['id']}",
            "title" : f"{prefix}{t['title']}",
            "start" : t['target_date'],
            "end" : (datetime.datetime.strptime(t['end_date'], "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d") if t['end_date'] else t['target_date'],
            "is_completed" : t['is_completed'],
            "color" : "#999999" if t['is_completed'] else "#203864",
            "extendedProps" : {"type" : "todo", "db_id" : t['id'], "original_title" : t['title']} 
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
                        "title" : f"[월간] {r['title']}",
                        "start" : str(r_date),
                        "color" : "#1167b1",
                        "extendedProps" : {"type" : "recurring", "db_id" : r['id'], "original_title" : r['title']}
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
                date_str = target_date.strftime("%Y-%m-%d")
                if (r['id'], date_str) not in except_set :
                    all_events.append({
                        "id" : f"recur_{r['id']}_w_{target_date.strftime('%m%d')}",
                        "title" : f"[주간] {r['title']}",
                        "start" : str(target_date),
                        "color" : "#008080",
                        "extendedProps" : {"type" : "recurring", "db_id" : r['id'], "original_title" : r['title']}
                    })
                target_date += datetime.timedelta(weeks=1)
                
    # 3. 휴무일 (배경색 처리)
    holidays = supabase.table("holidays").select("*").execute().data
    for h in holidays :
        all_events.append({
            "id" : f"holiday_{h['id']}",
            "title" : f"[휴무] {h['title']}",
            "start" : h['holiday_date'],
            "display" : "background",
            "backgroundColor" : h.get('color_code', '#FFEDED'),
            "extendedProps" : {"type" : "holiday", "db_id" : h['id'], "original_title" : h['title']}
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
            original_title = e["extendedProps"]['original_title']
            etitle = f"{badge[etype]} {original_title}"

            if etype == "todo" :
                col1, col2, col3 = st.columns([0.6, 0.2, 0.2])

                # col1 : markdown, 완료 여부에 따른 텍스트 스타일링
                title_text = f"{badge[etype]} <del>{original_title}</del>" if e['is_completed'] else etitle
                col1.markdown(title_text, unsafe_allow_html=True)

                # col2 : 완료 토글 버튼
                btn_label = "미완료" if e['is_completed'] else "완료"
                if col2.button(btn_label, key=f"status_{e['id']}", use_container_width=True) :
                    supabase.table("monthly").update({"is_completed" : not e['is_completed']}).eq("id", id).execute()
                    st.rerun()

                # col3 : 수정 및 삭제 서브폼 (Expander 제어)
                with col3.expander("수정") :
                    with st.form(f"todo_edit_{e['id']}") :
                        edit_title = st.text_input("제목 수정", value = original_title)                        
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
                        edit_r_title = st.text_input("일정 변경", value = original_title)
                        new_date = st.date_input("변경할 날짜 선택", datetime.date.today())

                        sub_rc1, sub_rc2 = st.columns(2)
                        if sub_rc1.form_submit_button("저장", use_container_width=True) :
                            # 원래 날짜는 예외 처리로 차단
                            supabase.table("recurring_exceptions").insert({
                                "recurring_id" : id, "original_date" : str(selected_date)
                            }).execute()
                            # 새 날짜에 복사본 일반 일정으로 등록
                            supabase.table("monthly").insert({
                                "title" : f"[변경] {original_title}",
                                "target_date" : str(new_date),
                                "is_completed" : False
                            }).execute()
                            st.rerun()
                        if sub_rc2.form_submit_button("해제", key=f"skip_{e['id']}_{selected_date}", use_container_width=True) :
                            supabase.table("recurring_exceptions").insert({
                                "recurring_id" : id, "original_date" : str(selected_date)
                            }).execute()
                            st.success("이번 일정을 취소했습니다.")
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
        # 수정 모드 초기화
        if "edit_rule" not in st.session_state :
            st.session_state.edit_rule = None   # None이면 새 반복일정 등록모드, rule이면 수정 모드

        is_edit = st.session_state.edit_rule is not None
        rule = st.session_state.edit_rule

        st.subheader("반복 업무 수정" if is_edit else "반복 업무 등록")

        # 수정 모드일 때 기본값 셋팅
        default_type_index = list(type_labels.keys()).index(rule['type']) if is_edit else 0
        r_type = st.selectbox(
            "반복 주기", type_labels.keys(),
            key="r_type",
            index = default_type_index
        )

        with st.form("recurring_form", clear_on_submit=True) :
            r_title = st.text_input("반복 업무", value=rule['title'] if is_edit else "")

            if r_type == "monthly" :
                r_val = st.number_input("매달 반복일", 1, 31, value=rule['repeat_value'] if is_edit else 1)
            else :
                day_labels = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                default_day = rule['repeat_value'] if is_edit else 0
                r_labels = st.selectbox("요일지정", day_labels, index=default_day)
                r_val = day_labels.index(r_labels)

            r_desc = st.text_area("상세 설명(선택)", value=rule.get('description', '') if is_edit else "")

            col1, col2 = st.columns(2) 

            if is_edit :
                if col1.form_submit_button("수정 완료") :
                    if r_title :
                        supabase.table("recurrings").update({
                            "title" : r_titel,
                            "type" : r_type,
                            "repeat_value" : r_val,
                            "description" : r_desc
                        }).eq("id", rule['id']).execute()
                        st.session_state.edit_rule = None
                        st.rerun()

                if col2.form_submit_button("취소") :
                    st.session_state.edit_rule = None
                    st.rerun()

            else :
                if col1.form_submit_button("반복 업무 등록") :
                    if r_title :
                        supabase.table("recurrings").insert({
                            "title" : r_title,
                            "type" : r_type,
                            "repeat_value" : r_val,
                            "description" : r_desc
                        }).execute()
                        st.rerun()

        st.divider()
        st.subheader("등록된 반복 일정 관리")

        all_rules = supabase.table("recurrings").select("*").order("type").execute().data

        if not all_rules :
            st.caption("등록된 반복 일정이 없습니다.")

        for i, rule in enumerate(all_rules) :
            if rule['type'] == 'monthly' :
                rule_label = f"매달 {rule['repeat_value']}일"
            else :
                day_labels = ["월", "화", "수", "목", "금", "토", "일"]
                rule_label = f"매주 ({day_labels[rule['repeat_value']]}요일)"

            col1, col2, col3 = st.columns([4, 1, 1])
            col1.write(f"** {rule_label} ** - {rule['title']}")

            if col2.button("수정", key=f"edit_{i}") :
                st.session_state.edit_rule = rule   # 수정할 rule을 session_state에 저장
                st.rerun()

            if col3.button("삭제", key=f"del_{i}", type="primary") :
                supabase.table("recurrings").delete().eq("id", rule['id']).execute()
                st.rerun()


        # r_type = st.selectbox("반복 주기", type_labels.keys(), format_func=type_labels.get , key="r_type")
        # with st.form("recurring_form", clear_on_submit=True) :
        #     r_title = st.text_input("반복 업무")            
        #     if r_type == "monthly" :
        #         r_val = st.number_input("매달 반복일", 1, 31, value=1)
                
        #     else :
        #         # 요일을 선택받고 인덱스로 변환
        #         day_labels = ["월요일", "화요일","수요일", "목요일", "금요일", "토요일", "일요일"] 
        #         r_labels = st.selectbox("요일지정", day_labels)
        #         r_val = day_labels.index(r_labels)

        #     r_desc = st.text_area("상세 설명 (선택)")

        #     if st.form_submit_button("반복 업무 등록") :
        #         if r_title :
        #             supabase.table("recurrings").insert({
        #                 "title" : r_title,
        #                 "type" : r_type,
        #                 "repeat_value" : r_val,
        #                 "description" : r_desc
        #             }).execute()
        #             st.rerun()

        # st.divider()
        # st.subheader("등록된 반복 일정 관리")

        # # 실시간 DB 마스터 규칙 로드
        # all_rules = supabase.table("recurrings").select("*").order("type").execute().data

        # if not all_rules :
        #     st.caption("등록된 반복 일정이 없습니다")

        # for i, rule in enumerate(all_rules) :
        #     # 주기에 따른 라벨의 정의
        #     if rule['type'] == 'monthly' :
        #         rule_label = f"매달 {rule['repeat_value']}일"
        #     else :
        #         day_labels = ["월", "화", "수", "목", "금", "토", "일"]
        #         day_value = rule['repeat_value']
        #         rule_label = f"매주 ({day_labels[day_value]}요일)"

        #     # 각 규칙을 익스팬더로 감싸 공간 절약 및 수정 인터페이스 제공
        #     with st.expander(f"{rule_label} - {rule['title']}") :
        #         u_r_type = st.selectbox("반복 주기", type_labels.keys(), format_func=type_labels.get, key=f"u_r_type_{i}")
        #         with st.form(f"sb_rule_edit{rule['id']}") :
        #             u_r_title = st.text_input("규칙 이름 수정", value=rule['title'])
        #             if u_r_type == "monthly" :
        #                 u_r_val = st.number_input("매달 반복일", 1, 31, value=1)
                        
        #             else :
        #                 # 요일을 선택받고 인덱스로 변환
        #                 u_day_labels = ["월요일", "화요일","수요일", "목요일", "금요일", "토요일", "일요일"] 
        #                 u_r_labels = st.selectbox("요일지정", day_labels)
        #                 u_r_val = day_labels.index(r_labels)

        #             c1, c2 = st.columns(2)
        #             if c1.form_submit_button("규칙 수정") :
        #                 supabase.table("recurrings").update({"title" : u_r_title, "type" : u_r_type}).eq("id", rule['id']).execute()
        #                 st.rerun()

        #             if c2.form_submit_button("전체 삭제", type="primary") :
        #                 # CASCADE 제약조건으로 인해 예외 테이블 기록도 함께 날아간다.
        #                 supabase.table("recurrings").delete().eq("id", rule['id']).execute()
        #                 st.rerun()

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


