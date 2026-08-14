import sqlite3
import pandas as pd
import os
import re

class DatabaseManager:
    def __init__(self, db_directory="databases"):
        self.db_directory = db_directory
        os.makedirs(self.db_directory, exist_ok=True)
        self.current_db_name = None
        self.current_db_path = None

    def list_all_databases(self):
        try:
            files = [f for f in os.listdir(self.db_directory) if f.endswith('.db')]
            return files if files else []
        except Exception as e:
            return [f"Error listing databases: {str(e)}"]

    def create_database(self, db_name):
        """إنشاء قاعدة بيانات جديدة"""
        if not db_name.endswith('.db'):
            db_name += '.db'
        
        db_path = os.path.join(self.db_directory, db_name)
        
        if os.path.exists(db_path):
            return {"status": "exists", "message": f"Database '{db_name}' already exists.", "path": db_path}
        
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.close()
            return {"status": "success", "message": f"Database '{db_name}' created successfully.", "path": db_path}
        except Exception as e:
            return {"status": "error", "message": f"Error creating database: {str(e)}"}

    def switch_database(self, db_name):
        if not db_name:
            return False
        if not db_name.endswith('.db'):
            db_name += '.db'
        self.current_db_name = db_name
        self.current_db_path = os.path.join(self.db_directory, self.current_db_name)
        try:
            with sqlite3.connect(self.current_db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
            return True
        except Exception as e:
            print(f"Error switching database: {e}")
            return False

    def get_schema(self):
        if not self.current_db_path or not os.path.exists(self.current_db_path):
            return ""
        schema_info = []
        try:
            with sqlite3.connect(self.current_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for table in tables:
                    table_name = table[0]
                    if table_name == "sqlite_sequence":
                        continue
                    cursor.execute(f'PRAGMA table_info("{table_name}");')
                    columns = cursor.fetchall()
                    col_desc = [f"{col[1]} ({col[2]})" for col in columns]
                    cursor.execute(f'PRAGMA foreign_key_list("{table_name}");')
                    fks = cursor.fetchall()
                    fk_desc = [f"FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]})" for fk in fks]
                    table_schema = f"Table: {table_name}\nColumns: {', '.join(col_desc)}"
                    if fk_desc:
                        table_schema += f"\nRelationships: {', '.join(fk_desc)}"
                    schema_info.append(table_schema)
            return "\n\n".join(schema_info)
        except Exception as e:
            return f"Error retrieving schema: {str(e)}"

    def read_file_to_df(self, file_path):
        """قراءة الملف مرة واحدة وتحويله إلى DataFrame"""
        try:
            file_path_lower = file_path.lower()
            if file_path_lower.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path_lower.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            elif file_path_lower.endswith('.xml'):
                df = pd.read_xml(file_path)
            elif file_path_lower.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                return None, "Unsupported file format"
            
            # تنظيف أسماء الأعمدة
            df.columns = [str(c).strip().replace(" ", "_").replace("-", "_") for c in df.columns]
            return df, None
        except Exception as e:
            return None, str(e)

    def import_dataframe(self, df, table_name):
        """استيراد DataFrame مباشرة إلى قاعدة البيانات"""
        if not self.current_db_path:
            return {"status": "error", "message": "No database selected. Please create or switch to a database first."}
        try:
            with sqlite3.connect(self.current_db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            return {"status": "success", "message": f"✅ Imported {len(df)} rows into '{table_name}'.", "row_count": len(df)}
        except Exception as e:
            return {"status": "error", "message": f"Import error: {str(e)}"}

    def execute_query(self, sql):
        if not self.current_db_path:
            return {"status": "error", "message": "No active database selected."}
        try:
            sql = sql.strip()
            if not sql:
                return {"status": "error", "message": "Empty SQL query."}
            with sqlite3.connect(self.current_db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                is_read_query = re.match(r"^\s*(SELECT|WITH|PRAGMA)\b", sql, re.IGNORECASE)
                if is_read_query:
                    df = pd.read_sql_query(sql, conn)
                    return {"status": "success", "data": df, "type": "select"}
                else:
                    cursor = conn.cursor()
                    cursor.executescript(sql)
                    conn.commit()
                    return {"status": "success", "data": "Action executed successfully.", "type": "action"}
        except sqlite3.Error as e:
            return {"status": "error", "message": f"SQLite Error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"System Error: {str(e)}"}