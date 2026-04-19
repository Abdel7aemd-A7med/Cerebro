from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.nodes import (
    guard_node, 
    router_node,
    planner_node, 
    architect_node, 
    executor_node, 
    reporter_node, 
    chat_node
)

# 1. تعريف الجراف
workflow = StateGraph(AgentState)

# 2. إضافة النودز
workflow.add_node("guard", guard_node)      
workflow.add_node("router", router_node)    
workflow.add_node("planner", planner_node)    
workflow.add_node("architect", architect_node) 
workflow.add_node("executor", executor_node)   
workflow.add_node("reporter", reporter_node)   
workflow.add_node("chat", chat_node)           

# 3. نقطة البداية
workflow.set_entry_point("guard")

# 4. من الأمان للموجه
workflow.add_edge("guard", "router")

# 5. التوجيه بعد الموجه (Router Decision)
def route_after_router(state: AgentState):
    decision = state.get("error_log") 
    if decision == "database":
        return "planner"
    return "chat"

workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "planner": "planner",
        "chat": "chat"
    }
)

# 6. التوجيه بعد المخطط (Planner Decision)
def route_after_planner(state: AgentState):
    # حالة 1: المستخدم وافق على الخطة (كتب كمل) أو الطلب بسيط أصلاً
    # في نود الـ planner إحنا ضفنا شرط يخلي is_complex يفضل True بس يعدي للتنفيذ
    
    user_go_ahead = any(word in state["user_input"].lower() for word in ["كمل", "تمام", "أبدأ", "ok", "go"])
    
    if state.get("is_complex"):
        if user_go_ahead:
            return "execute_plan" # يبدأ في أول خطوة
        else:
            return "ask_permission" # يعرض الخطة ويوقف
    
    return "execute_plan" # لو مش معقد يروح ينفذ علطول

workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "ask_permission": "reporter", 
        "execute_plan": "architect"   
    }
)

# 7. مسار التنفيذ التقني مع التصحيح الذاتي
workflow.add_edge("architect", "executor")

def check_execution_status(state: AgentState):
    error = state.get("error_log")
    # لو فيه رسالة خطأ حقيقية مش "database" ولا "chat"
    if error and error not in ["database", "chat", ""]:
        return "retry"
    return "success"

workflow.add_conditional_edges(
    "executor",
    check_execution_status,
    {
        "retry": "architect",
        "success": "reporter"
    }
)

# 8. نهاية المسارات
workflow.add_edge("reporter", END)
workflow.add_edge("chat", END)

# 9. التجميع النهائي
app = workflow.compile()