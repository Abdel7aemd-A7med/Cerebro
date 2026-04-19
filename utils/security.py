import re

class SecurityScanner:
    def __init__(self):
        # الكلمات المحظورة التي قد تدل على محاولة اختراق أو تخريب غير منطقي
        self.forbidden_patterns = [
            r"(\bDROP\b\s+\bTABLE\b)",      # حذف جداول
            r"(\bDROP\b\s+\bDATABASE\b)",   # حذف الداتا بيز كاملة
            r"(\bTRUNCATE\b)",              # تفريغ جداول
            r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)", # SQL Injection (OR 1=1)
            r"(--)",                        # التعليقات في SQL لتخطي الشروط
            r"(;)"                          # محاولة دمج أمرين (Batching)
        ]

    def scan_input(self, user_input: str):
        """فحص مدخلات المستخدم قبل إرسالها للوكيل"""
        clean_input = user_input.upper()
        for pattern in self.forbidden_patterns:
            if re.search(pattern, clean_input):
                return False, f"تم اكتشاف نمط محظور: {pattern}"
        return True, "Safe"

    def validate_sql(self, sql_query: str):
        """مراجعة الكود اللي الموديل كتبه قبل ما يتنفذ فعلياً"""
        # نمنع حذف الجداول الحيوية أو العمليات التخريبية
        dangerous_commands = ["DROP", "DELETE FROM", "TRUNCATE"]
        sql_upper = sql_query.upper()
        
        # مسموح بالـ DELETE فقط لو فيه شرط WHERE (لأمان الداتا)
        if "DELETE" in sql_upper and "WHERE" not in sql_upper:
            return False, "لا يمكن تنفيذ حذف شامل بدون شرط WHERE."
            
        return True, "Valid"