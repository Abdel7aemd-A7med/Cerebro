import sqlite3
import pandas as pd
import os

class DatabaseManager:
    def __init__(self, db_path="database/cerebro_vault.db"):
        self.db_path = db_path
        # التأكد من وجود الفولدر الخاص بالداتا بيز
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_schema(self):
        """تستخرج الهيكل الكامل ليقرأه الموديل ويصمم بناءً عليه."""
        schema_info = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    if table_name == "sqlite_sequence": continue 
                    
                    cursor.execute(f"PRAGMA table_info('{table_name}');")
                    columns = cursor.fetchall()
                    col_desc = [f"{col[1]} ({col[2]})" for col in columns]
                    schema_info.append(f"Table: {table_name}\nColumns: {', '.join(col_desc)}")
            
            return "\n\n".join(schema_info) if schema_info else "Database is currently empty."
        except Exception as e:
            return f"Error: {str(e)}"

    def execute_query(self, sql):
        """تنفيذ كود SQL مع دعم تنفيذ عدة أوامر في وقت واحد (executescript)."""
        try:
            # تنظيف الكود من أي فراغات زائدة
            sql = sql.strip()
            if not sql:
                return {"status": "error", "message": "Empty SQL query."}

            with sqlite3.connect(self.db_path) as conn:
                # 1. حالة الاستعلام (SELECT)
                if sql.upper().startswith("SELECT"):
                    df = pd.read_sql_query(sql, conn)
                    return {"status": "success", "data": df}
                
                # 2. حالة الأوامر الهيكلية (CREATE, INSERT, إلخ)
                else:
                    cursor = conn.cursor()
                    # استخدام executescript للسماح بتنفيذ عدة أوامر SQL مفصولة بـ ;
                    cursor.executescript(sql)
                    conn.commit()
                    return {"status": "success", "data": "Action executed successfully."}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reset_database(self):
        """حذف القاعدة للبدء من جديد."""
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
                return "Database reset complete."
            except Exception as e:
                return f"Error during reset: {str(e)}"
        return "No database file found."