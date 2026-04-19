import re
import json
from langchain_ollama import OllamaLLM
from database.db_manager import DatabaseManager
from prompts.system_prompts import (
    get_security_prompt, 
    get_architect_prompt, 
    get_reporter_prompt, 
    get_router_prompt
)

# 1. إعداد المحرك (تأكد من اختيار الموديل المستقر لجهازك)
llm = OllamaLLM(
    model="deepseek-coder-v2:lite", 
    num_ctx=2048, 
    temperature=0,  # صفر ضروري عشان الدقة في الـ SQL
    top_p=0.9, 
    repeat_penalty=1.1, 
    num_predict=1024, # زودنا الرقم عشان الكود ميبقاش مقطوع
    num_thread=4
)

db = DatabaseManager()

# --- 1. نود الأمان (Guard Node) ---
def guard_node(state):
    logs = state.get("thinking_logs", [])
    logs.append("🛡️ فحص أمان المدخلات...")
    mcp_security = get_security_prompt(state["user_input"])
    response = llm.invoke(mcp_security["template"])
    if "UNSAFE" in response.upper():
        return {"error_log": "⚠️ تم حظر الطلب لدواعي أمنية.", "thinking_logs": logs}
    return {"thinking_logs": logs, "error_log": ""}

# --- 2. نود الموجه (Router Node) ---
def router_node(state):
    logs = state.get("thinking_logs", [])
    logs.append("🧠 تحليل نية المستخدم...")
    router_prompt = get_router_prompt(state["user_input"])
    intent = llm.invoke(router_prompt["template"]).upper()
    decision = "database" if "DB_ACTION" in intent else "chat"
    return {"thinking_logs": logs, "error_log": decision}

# --- 3. نود المخطط (Planner Node) ---
def planner_node(state):
    logs = state.get("thinking_logs", [])
    
    # تحسين: لو اليوزر قال "كمل" نعدي التخطيط فوراً
    user_input = state["user_input"].lower()
    if any(word in user_input for word in ["كمل", "تمام", "أبدأ", "go", "continue"]):
        logs.append("⏩ المستخدم وافق على البدء في التنفيذ...")
        return {"is_complex": True, "thinking_logs": logs}

    logs.append("📋 تقييم حجم المهمة...")
    planner_prompt = f"""
    حلل الطلب: "{state['user_input']}"
    إذا كان يحتاج إنشاء أكثر من 3 جداول اجعل is_complex = true وقسمه لمراحل.
    رد بـ JSON فقط:
    {{ "is_complex": true/false, "steps": ["مرحلة 1:...", "مرحلة 2:..."] }}
    """
    
    response = llm.invoke(planner_prompt)
    try:
        clean_json = re.search(r"\{.*\}", response, re.DOTALL).group()
        plan = json.loads(clean_json)
        if plan.get("is_complex"):
            report = "الطلب ده محتاج تقسيم يا هندسة. دي الخطة:\n" + "\n".join(plan["steps"]) + "\n\n**اكتب 'كمل' عشان أبدأ في أول مرحلة.**"
            return {
                "is_complex": True,
                "plan_steps": plan["steps"],
                "current_step": 0,
                "thinking_logs": logs,
                "final_report": report
            }
    except: pass
    return {"is_complex": False, "thinking_logs": logs}

# --- 4. نود المهندس (Architect Node) - التعديل الجوهري هنا ---
def architect_node(state):
    logs = state.get("thinking_logs", [])
    current_step_text = ""
    
    if state.get("is_complex") and state.get("plan_steps"):
        step_idx = state.get("current_step", 0)
        current_step_text = f"\nالمهمة الحالية: {state['plan_steps'][step_idx]}"
        logs.append(f"🏗️ تنفيذ {state['plan_steps'][step_idx]}...")

    schema = db.get_schema()
    mcp_architect = get_architect_prompt(schema, state["user_input"] + current_step_text)
    
    # إجبار الموديل على صيغة محددة جداً
    prompt_with_force = mcp_architect["template"] + "\nIMPORTANT: Provide ONLY the SQL code inside a ```sql code ``` block. No explanations."

    response = llm.invoke(prompt_with_force)
    
    # استخراج الكود بـ Regex أقوى (بيصطاد الكود حتى لو الموديل غلط في الكتابة)
    sql_match = re.search(r"```sql\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
    sql_code = sql_match.group(1).strip() if sql_match else ""
    
    # لو ملقاش بلوك، يحاول يدور على أي حاجة تبدأ بـ CREATE أو INSERT
    if not sql_code:
        fallback_match = re.search(r"(CREATE|INSERT|UPDATE|SELECT|DELETE).*?;", response, re.DOTALL | re.IGNORECASE)
        sql_code = fallback_match.group(0).strip() if fallback_match else ""

    if not sql_code:
        return {"error_log": "فشل الموديل في توليد كود SQL.", "thinking_logs": logs}

    return {"generated_sql": sql_code, "thinking_logs": logs, "error_log": "" }

# --- 5. نود المنفذ (Executor Node) ---
def executor_node(state):
    logs = state.get("thinking_logs", [])
    logs.append(f"⚡ تنفيذ الاستعلام على قاعدة البيانات...")
    
    result = db.execute_query(state["generated_sql"])
    
    if result["status"] == "error":
        logs.append(f"❌ خطأ في التنفيذ: {result['message']}")
        return {"error_log": result["message"], "thinking_logs": logs}
    
    return {"db_results": result["data"], "thinking_logs": logs, "error_log": "" }

# --- 6. نود المحلل (Reporter Node) ---
def reporter_node(state):
    logs = state.get("thinking_logs", [])
    
    # لو كنا بنعرض خطة المخطط، مش محتاجين نكلم الموديل تاني
    if state.get("final_report") and "الخطة" in state["final_report"]:
        return {"thinking_logs": logs}

    logs.append("📊 تحليل النتائج وصياغة الرد...")
    data_str = str(state["db_results"])
    mcp_reporter = get_reporter_prompt(data_str, state["user_input"])
    report = llm.invoke(mcp_reporter["template"])
    
    return {"final_report": report, "thinking_logs": logs}

# --- 7. نود الدردشة (Chat Node) ---
def chat_node(state):
    logs = state.get("thinking_logs", [])
    logs.append("💬 رد دردشة عامة...")
    response = llm.invoke(f"أنت DB-Cerebro. رد بذكاء على: {state['user_input']}")
    return {"final_report": response, "thinking_logs": logs}