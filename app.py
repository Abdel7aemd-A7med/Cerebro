import streamlit as st
import pandas as pd
import os
import time
import tempfile
import re
from database.db_manager import DatabaseManager
from langchain_core.messages import HumanMessage
from core.graph import app as cerebro_app

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="Turinoo",
    layout="wide",
    page_icon="🧠"
)

db = DatabaseManager()

# =============================
# SESSION STATE
# =============================
def init_session_state():
    defaults = {
        "thread_id": str(int(time.time())),
        "messages": [],
        "stop_generation": False,
        "current_db": None,
        "pending_import": None,
        "show_import_preview": False,
        "last_sql": None,
        "last_response": None,
        "waiting_for_confirmation": False,
        "conversation_history": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# =============================
# FUNCTIONS
# =============================
def sanitize_name(name):
    name = re.sub(r'[^\w\-]', '_', name)
    return name

def switch_to_database(db_name):
    if db.switch_database(db_name):
        st.session_state.current_db = db_name
        return True
    return False

def create_empty_database(db_name):
    result = db.create_database(db_name)
    if result["status"] == "success":
        switch_to_database(db_name)
        return True, result["message"]
    elif result["status"] == "exists":
        switch_to_database(db_name)
        return True, f"Database '{db_name}' already exists. Switched to it."
    else:
        return False, result["message"]

def read_file_to_dataframe(file_path, file_type):
    try:
        if file_type == '.csv':
            df = pd.read_csv(file_path)
        elif file_type in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_type == '.json':
            df = pd.read_json(file_path)
        elif file_type == '.xml':
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()
            data = []
            for child in root:
                row = {}
                for subchild in child:
                    row[subchild.tag] = subchild.text
                data.append(row)
            df = pd.DataFrame(data)
        else:
            return None, "Unsupported file format"
        return df, None
    except Exception as e:
        return None, str(e)

def get_state_safe():
    try:
        state = cerebro_app.get_state(config)
        return state
    except:
        return None

def extract_sql_from_text(text):
    if not text:
        return None
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER).*?;', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return None

def execute_sql_direct(sql):
    """تنفيذ SQL مباشرة مع التحقق من وجود قاعدة بيانات"""
    if not st.session_state.current_db:
        return {"status": "error", "message": "No active database selected. Please connect to a database first."}
    
    if not db.current_db_path:
        db.switch_database(st.session_state.current_db)
    
    return db.execute_query(sql)

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("🗄️ Database Manager")
    
    st.subheader("📀 1. Select Existing DB")
    
    dbs = db.list_all_databases()
    
    if dbs:
        selected_db = st.selectbox("Choose database:", [""] + dbs, key="select_db")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 Connect", use_container_width=True) and selected_db:
                if switch_to_database(selected_db):
                    st.success(f"Connected to {selected_db}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"✅ Connected to database `{selected_db}`. You can now ask me questions about your data."
                    })
                    st.session_state.waiting_for_confirmation = False
                    st.session_state.last_sql = None
                    st.rerun()
                else:
                    st.error(f"Failed to connect to {selected_db}")
    else:
        st.caption("No databases found. Create one using options below.")
    
    st.divider()
    
    st.subheader("🆕 2. Create Empty DB")
    
    new_db_name = st.text_input("Database name:", key="new_db_name", placeholder="e.g., shop, sales, company")
    
    if st.button("✨ Create Database", use_container_width=True, type="primary"):
        if new_db_name:
            clean_name = sanitize_name(new_db_name)
            success, message = create_empty_database(clean_name)
            if success:
                st.success(message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"✅ {message} You can now upload data or create tables."
                })
                st.session_state.waiting_for_confirmation = False
                st.session_state.last_sql = None
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please enter a database name")
    
    st.divider()
    
    st.subheader("📂 3. Upload File → Auto DB")
    st.caption("Upload a file to automatically create a database and import data")
    
    uploaded_file = st.file_uploader(
        "CSV / Excel / JSON / XML",
        type=["csv", "xlsx", "xls", "json", "xml"],
        key="file_uploader"
    )
    
    if uploaded_file:
        suggested_table = os.path.splitext(uploaded_file.name)[0]
        suggested_table = sanitize_name(suggested_table)
        
        table_name = st.text_input("Table name:", suggested_table, key="table_name_input")
        
        if st.button("📋 Preview & Create", use_container_width=True, type="primary"):
            with st.spinner("Reading file..."):
                suffix = os.path.splitext(uploaded_file.name)[1].lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    temp_path = tmp.name
                
                df, error = read_file_to_dataframe(temp_path, suffix)
                
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                if error:
                    st.error(f"Error: {error}")
                else:
                    db_name = sanitize_name(os.path.splitext(uploaded_file.name)[0])
                    
                    st.session_state.pending_import = {
                        "df": df,
                        "table_name": table_name,
                        "file_name": uploaded_file.name,
                        "total_rows": len(df),
                        "columns": list(df.columns),
                        "db_name": db_name
                    }
                    st.session_state.show_import_preview = True
                    st.rerun()
    
    st.divider()
    
    st.subheader("📊 Current Status")
    if st.session_state.current_db:
        st.success(f"**Active DB:** `{st.session_state.current_db}`")
    else:
        st.warning("**No active database**")
        st.caption("Use one of the options above to connect or create a database")
    
    st.divider()
    
    st.subheader("⚙️ Controls")
    
    if st.button("🧹 New Chat", use_container_width=True):
        st.session_state.thread_id = str(int(time.time()))
        st.session_state.messages = []
        st.session_state.stop_generation = False
        st.session_state.waiting_for_confirmation = False
        st.session_state.last_sql = None
        st.session_state.last_response = None
        st.rerun()
    
    if st.button("🛑 Stop Generation", use_container_width=True):
        st.session_state.stop_generation = True
        try:
            cerebro_app.update_state(config, {"stop_signal": True})
        except:
            pass
        st.warning("Stopping model...")

# =============================
# IMPORT PREVIEW
# =============================
if st.session_state.show_import_preview and st.session_state.pending_import:
    pending = st.session_state.pending_import
    df = pending["df"]
    
    st.info(f"📄 **File:** {pending['file_name']}")
    st.write(f"📊 **Rows:** {pending['total_rows']} | **Columns:** {len(pending['columns'])}")
    
    with st.expander("📊 Data Preview (first 5 rows)", expanded=True):
        st.dataframe(df.head(5), use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Confirm Import", use_container_width=True, type="primary"):
            with st.spinner(f"Creating database and importing {pending['total_rows']} rows..."):
                # Step 1: Create database
                success, message = create_empty_database(pending['db_name'])
                
                if success:
                    # Step 2: Import data using DatabaseManager
                    res = db.import_dataframe(df, pending['table_name'])
                    
                    if res.get("status") == "success":
                        st.success(f"✅ Database '{pending['db_name']}.db' created and {res.get('message')}")
                        
                        # Notify agent
                        try:
                            cerebro_app.invoke(
                                {
                                    "messages": [
                                        HumanMessage(
                                            content=f"""Database '{pending['db_name']}.db' was created and table '{pending['table_name']}' was imported with {pending['total_rows']} rows.
Columns: {', '.join(pending['columns'][:10])}
The user can now ask questions about this data."""
                                        )
                                    ],
                                    "selected_db": pending['db_name'],
                                    "stop_signal": False
                                },
                                config
                            )
                        except Exception as e:
                            st.warning(f"Agent notification: {e}")
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"✅ Database `{pending['db_name']}.db` created and table `{pending['table_name']}` imported with {pending['total_rows']} rows. You can now ask me questions about your data!"
                        })
                        
                        st.session_state.pending_import = None
                        st.session_state.show_import_preview = False
                        st.rerun()
                    else:
                        st.error(res.get("message"))
                else:
                    st.error(message)
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.pending_import = None
            st.session_state.show_import_preview = False
            st.rerun()
    
    st.stop()

# =============================
# MAIN UI
# =============================
if st.session_state.current_db:
    st.title(f"🧠 Turinoo [`{st.session_state.current_db}`]")
else:
    st.title("🧠 Turinoo")
    st.info("👈 Use the sidebar to:\n\n1️⃣ Select an existing database\n2️⃣ Create a new empty database\n3️⃣ Upload a file to auto-create a database")

# CHAT HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if msg.get("sql"):
            with st.expander("SQL"):
                st.code(msg["sql"], language="sql")
        
        if msg.get("data") is not None:
            data = msg["data"]
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    st.dataframe(pd.DataFrame(data))
                else:
                    st.write(data)
            elif isinstance(data, str):
                st.success(data)

# =============================
# EXECUTOR CHECK
# =============================
try:
    state = get_state_safe()
    is_paused = "executor" in (state.next or []) if state else False
    pending_sql = state.values.get("pending_sql") if state else None
except:
    is_paused = False
    pending_sql = None

# =============================
# HUMAN CONFIRMATION
# =============================
if is_paused and pending_sql:
    with st.chat_message("assistant"):
        st.warning("⚠️ SQL ready for execution")
        st.code(pending_sql, language="sql")
        
        c1, c2 = st.columns(2)
        
        if c1.button("✅ Execute", key="execute_sql"):
            try:
                result = cerebro_app.invoke(None, config)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("agent_message", ""),
                    "sql": pending_sql,
                    "data": result.get("db_results")
                })
                st.rerun()
            except Exception as e:
                st.error(f"Execution error: {e}")
        
        if c2.button("❌ Cancel", key="cancel_sql"):
            try:
                cerebro_app.update_state(config, {"pending_sql": None})
            except:
                pass
            st.session_state.messages.append({
                "role": "user",
                "content": "❌ Cancelled execution"
            })
            st.rerun()

# =============================
# 🧠 CHECK MEMORY FOR PENDING SQL
# =============================
if st.session_state.get("waiting_for_confirmation") and st.session_state.get("last_sql"):
    pending_sql_memory = st.session_state.last_sql
    with st.chat_message("assistant"):
        st.warning("⚠️ SQL pending confirmation from memory")
        st.code(pending_sql_memory, language="sql")
        
        c1, c2 = st.columns(2)
        
        if c1.button("✅ Execute from Memory", key="execute_memory"):
            try:
                # استخدام الدالة الجديدة execute_sql_direct
                res = execute_sql_direct(pending_sql_memory)
                if res.get("status") == "error":
                    st.error(f"Execution error: {res.get('message')}")
                else:
                    data = res.get("data")
                    if isinstance(data, pd.DataFrame):
                        data = data.to_dict(orient="records")
                    st.success("✅ Query executed successfully!")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "✅ Query executed successfully!",
                        "sql": pending_sql_memory,
                        "data": data
                    })
                    st.session_state.waiting_for_confirmation = False
                    st.session_state.last_sql = None
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        if c2.button("❌ Cancel Memory", key="cancel_memory"):
            st.session_state.waiting_for_confirmation = False
            st.session_state.last_sql = None
            st.rerun()
    
    st.stop()

# =============================
# CHAT + STREAMING
# =============================
if not is_paused and st.session_state.current_db:
    user_input = st.chat_input("Ask something about your data...")
    
    if user_input:
        # Check if this is a confirmation response
        confirm_keywords = ["yes", "confirm", "execute", "proceed", "go ahead", "do it", "ok", "okay", "yes please", "y", "yeah"]
        is_confirmation = any(keyword in user_input.lower() for keyword in confirm_keywords)
        
        # If we have pending SQL in memory and user confirms
        if st.session_state.get("waiting_for_confirmation") and st.session_state.get("last_sql") and is_confirmation:
            with st.chat_message("user"):
                st.markdown(user_input)
            
            with st.chat_message("assistant"):
                try:
                    # استخدام الدالة الجديدة execute_sql_direct
                    res = execute_sql_direct(st.session_state.last_sql)
                    if res.get("status") == "error":
                        st.error(f"Execution error: {res.get('message')}")
                    else:
                        data = res.get("data")
                        if isinstance(data, pd.DataFrame):
                            data = data.to_dict(orient="records")
                        st.success("✅ Query executed successfully!")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "✅ Query executed successfully!",
                            "sql": st.session_state.last_sql,
                            "data": data
                        })
                        st.session_state.waiting_for_confirmation = False
                        st.session_state.last_sql = None
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            st.stop()
        
        # Normal chat flow
        st.session_state.stop_generation = False
        
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            sql_found = None
            
            try:
                stream = cerebro_app.stream(
                    {
                        "messages": [HumanMessage(content=user_input)],
                        "selected_db": st.session_state.current_db.replace('.db', ''),
                        "stop_signal": False
                    },
                    config,
                    stream_mode="messages"
                )
                
                for msg, _ in stream:
                    if st.session_state.stop_generation:
                        try:
                            cerebro_app.update_state(config, {"stop_signal": True})
                        except:
                            pass
                        full_response += "\n\n⛔ Stopped by user."
                        break
                    
                    if hasattr(msg, "content") and msg.content:
                        full_response += msg.content
                        placeholder.markdown(full_response + "▌")
                        
                        if not sql_found:
                            sql_found = extract_sql_from_text(msg.content)
                
                placeholder.markdown(full_response)
                
                # Check if the agent is waiting for confirmation
                if sql_found and ("yes" in full_response.lower() or "confirm" in full_response.lower()):
                    st.session_state.last_sql = sql_found
                    st.session_state.last_response = full_response
                    st.session_state.waiting_for_confirmation = True
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "sql": sql_found
                    })
                else:
                    final_state = get_state_safe()
                    final_values = final_state.values if final_state else {}
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "data": final_values.get("db_results")
                    })
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                placeholder.markdown(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })