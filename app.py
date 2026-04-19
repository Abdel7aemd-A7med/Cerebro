import streamlit as st
import pandas as pd
from core.graph import app as cerebro_app

# 1. إعدادات الصفحة
st.set_page_config(page_title="DB-Cerebro AI", layout="centered", page_icon="🧠")

# 2. CSS لمحاكاة ChatGPT Dark Mode بالظبط
st.markdown("""
    <style>
    .stApp {
        background-color: #212121;
        color: #ececec;
    }
    [data-testid="stSidebar"] {
        background-color: #171717;
        border-right: 1px solid #333;
    }
    .stChatInput {
        border-radius: 10px;
        border: 1px solid #4d4d4d !important;
        background-color: #2f2f2f !important;
    }
    /* تنسيق زر التوقف */
    .stop-button {
        display: flex;
        justify-content: center;
        margin-top: 10px;
    }
    div.stButton > button:first-child {
        background-color: #444654;
        color: white;
        border: 1px solid #565869;
        border-radius: 5px;
    }
    div.stButton > button:hover {
        background-color: #343541;
        border-color: #acacbe;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧠 DB-Cerebro</h2>", unsafe_allow_html=True)
    st.divider()
    st.info("🤖 **Model:** DeepSeek-Coder-V2")
    st.success("💾 **Engine:** SQLite Live")
    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.stop_execution = False
        st.rerun()

# 4. إدارة الحالة (State Management)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stop_execution" not in st.session_state:
    st.session_state.stop_execution = False

# 5. عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "data" in msg and msg["data"] is not None:
            st.dataframe(msg["data"], use_container_width=True)

# 6. منطقة الإدخال والمعالجة
if user_input := st.chat_input("Message DB-Cerebro..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.stop_execution = False # إعادة ضبط زر التوقف
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # إنشاء حاوية لزر التوقف
        stop_col = st.columns([4, 1, 4])[1]
        stop_btn = stop_col.button("🛑 Stop")
        
        with st.status("Cerebro is thinking...", expanded=True) as status:
            initial_state = {
                "user_input": user_input,
                "history": st.session_state.messages,
                "thinking_logs": [],
                "error_log": "",
                "generated_sql": "",
                "db_results": None,
                "final_report": "",
                "is_complex": False,
                "plan_steps": [],
                "current_step": 0,
                "retry_count": 0
            }
            
            final_output = None
            try:
                # الـ Loop اللي بيستلم الـ Nodes واحدة بواحدة
                for output in cerebro_app.stream(initial_state):
                    # فحص إذا كان المستخدم ضغط على Stop
                    if stop_btn or st.session_state.stop_execution:
                        st.session_state.stop_execution = True
                        st.warning("⚠️ Generation halted by user.")
                        break
                    
                    for key, value in output.items():
                        if "thinking_logs" in value and value["thinking_logs"]:
                            st.write(f"✅ {value['thinking_logs'][-1]}")
                    final_output = output
                
                if not st.session_state.stop_execution:
                    status.update(label="Response Ready", state="complete", expanded=False)
            except Exception as e:
                status.update(label="System Error", state="error")
                st.error(f"Error: {str(e)}")

        # عرض النتائج لو لم يتم التوقف
        if final_output and not st.session_state.stop_execution:
            # الوصول لآخر نود اشتغلت
            node_name = list(final_output.keys())[0]
            res = final_output[node_name]
            
            report = res.get("final_report", "I've processed that for you.")
            db_data = res.get("db_results")
            sql = res.get("generated_sql")

            st.markdown(report)
            if sql:
                with st.expander("View SQL Architecture"):
                    st.code(sql, language="sql")
            
            if isinstance(db_data, pd.DataFrame) and not db_data.empty:
                st.dataframe(db_data, use_container_width=True)
                st.session_state.messages.append({"role": "assistant", "content": report, "data": db_data})
            else:
                st.session_state.messages.append({"role": "assistant", "content": report})