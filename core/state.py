# core/state.py
from typing import TypedDict, List, Union, Optional, Any
import pandas as pd

class AgentState(TypedDict):
    # --- مدخلات المستخدم الأساسية ---
    user_input: str
    
    # تاريخ المحادثة (لتخزين السياق)
    history: List[dict]
    
    # --- المسار التقني للبيانات (SQL Path) ---
    current_schema: str
    generated_sql: str
    
    # النتائج: يمكن أن تكون DataFrame (عند الاستعلام) أو String (رسائل تأكيد)
    db_results: Any 
    
    # سجل الأخطاء: يستخدم للتوجيه الشرطي وللتصحيح الذاتي
    error_log: str
    
    # --- نظام التفكير واللوجز ---
    thinking_logs: List[str]
    final_report: str

    # --- 🆕 حقول إدارة المشروع (The Planner Logic) ---
    
    # هل المهمة تتطلب تقسيم لمراحل؟ (True/False)
    is_complex: bool
    
    # قائمة بأسماء المراحل (مثال: ["بناء الجداول", "إدخال بيانات"])
    plan_steps: List[str]
    
    # مؤشر للمرحلة الحالية التي يعمل عليها العميل
    current_step: int
    
    # عداد لمحاولات التصحيح (لمنع الـ Infinite Loop في الـ SQL)
    retry_count: int