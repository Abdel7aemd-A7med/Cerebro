import re
import json
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from database.db_manager import DatabaseManager

# =============================
# LOGGING SETUP
# =============================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# =============================
# INIT MODEL WITH STREAMING
# =============================
llm = ChatOpenAI(
    openai_api_base="http://localhost:5001/v1",
    openai_api_key="sk-no-key-needed",
    model_name="qwen-3.5-9b",
    streaming=True,
    temperature=0,
    max_tokens=2500,
)

db = DatabaseManager()

# =============================
# INTERNAL HELPERS
# =============================
def extract_sql(text: str) -> str:
    """Extract SQL from text"""
    if not text:
        return ""
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER).*?;', text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(0).strip()
    
    return ""

def is_sqlite_safe(sql: str) -> bool:
    """Check SQL safety"""
    if not sql:
        return False
    forbidden = ["RIGHT JOIN", "FULL OUTER JOIN", "AUTO_INCREMENT", "SERIAL"]
    sql_up = sql.upper()
    return not any(f in sql_up for f in forbidden)

def get_table_names(db_name: str) -> List[str]:
    """Get list of table names in current database"""
    try:
        db.switch_database(db_name)
        schema = db.get_schema()
        if not schema:
            return []
        
        tables = []
        lines = schema.split('\n')
        for line in lines:
            if line.startswith('Table: '):
                table_name = line.replace('Table: ', '').strip()
                tables.append(table_name)
        return tables
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        return []

def format_number(num: int) -> str:
    """Format large numbers with commas"""
    return f"{num:,}"

def execute_sql(sql: str, db_name: str, show_sql: bool = True) -> Dict[str, Any]:
    """Execute SQL query and return results"""
    result = {"success": False, "data": None, "message": "", "error": None, "count": None, "sql": sql if show_sql else None}
    
    if not sql:
        result["message"] = "No SQL query found."
        return result
    
    if not is_sqlite_safe(sql):
        result["message"] = "Query contains unsupported SQLite syntax."
        return result
    
    try:
        if not db.switch_database(db_name):
            result["message"] = f"Failed to connect to database: {db_name}"
            return result
        
        query_result = db.execute_query(sql)
        
        if query_result.get("status") == "error":
            result["message"] = f"Execution error: {query_result.get('message')}"
            return result
        
        data = query_result.get("data")
        
        is_count_query = re.search(r'COUNT\s*\(', sql, re.IGNORECASE) is not None
        is_delete_query = re.search(r'DELETE\s+FROM', sql, re.IGNORECASE) is not None
        is_create_query = re.search(r'CREATE\s+TABLE', sql, re.IGNORECASE) is not None
        
        if isinstance(data, pd.DataFrame):
            if is_count_query:
                count_value = int(data.iloc[0, 0]) if len(data) > 0 else 0
                result["count"] = count_value
                result["message"] = f"{format_number(count_value)}"
            else:
                data_dict = data.to_dict(orient="records")
                result["data"] = data_dict
                result["count"] = len(data_dict)
                if is_delete_query:
                    result["message"] = f"Deleted {format_number(len(data_dict))} rows."
                else:
                    result["message"] = f"{format_number(len(data_dict))} rows"
        elif isinstance(data, list):
            if is_count_query and len(data) == 1:
                count_value = int(list(data[0].values())[0]) if data else 0
                result["count"] = count_value
                result["message"] = f"{format_number(count_value)}"
            else:
                result["data"] = data
                result["count"] = len(data)
                if is_delete_query:
                    result["message"] = f"Deleted {format_number(len(data))} rows."
                else:
                    result["message"] = f"{format_number(len(data))} rows"
        elif isinstance(data, str):
            result["message"] = data
            result["success"] = True
            return result
        else:
            if is_create_query:
                result["message"] = "Table created successfully."
                result["success"] = True
                return result
            result["data"] = [{"result": str(data)}]
            result["count"] = 1
        
        result["success"] = True
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "no such table" in error_msg.lower():
            table_match = re.search(r"no such table: (\w+)", error_msg, re.IGNORECASE)
            if table_match:
                missing_table = table_match.group(1)
                tables = get_table_names(db_name)
                if tables:
                    result["message"] = f"Table '{missing_table}' not found. Available tables: {', '.join(tables)}"
                else:
                    result["message"] = f"Table '{missing_table}' not found."
            else:
                result["message"] = f"{error_msg}"
        else:
            result["message"] = f"Error: {error_msg}"
        result["error"] = error_msg
        return result

def get_db_schema(db_name: str) -> str:
    """Get database schema"""
    if not db_name:
        return ""
    try:
        db.switch_database(db_name)
        schema = db.get_schema()
        return schema if schema else "No tables found."
    except Exception as e:
        return f"Error reading schema: {str(e)}"

# =============================
# UNIFIED AGENT NODE WITH MEMORY
# =============================
def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    UNIFIED AGENT NODE - Handles everything internally with Memory
    """
    
    default_return = {
        "messages": [],
        "agent_message": "",
        "pending_sql": None,
        "db_results": None,
        "error_log": None,
        "stop_signal": state.get("stop_signal", False),
        # =============================
        # 🧠 MEMORY - Keep conversation history
        # =============================
        "conversation_history": state.get("conversation_history", []),
        "last_sql": state.get("last_sql", None),
        "last_response": state.get("last_response", None),
        "waiting_for_confirmation": state.get("waiting_for_confirmation", False)
    }

    try:
        if state.get("stop_signal"):
            default_return["messages"] = [AIMessage(content="Stopped.")]
            default_return["agent_message"] = "Stopped"
            return default_return

        db_name = state.get("selected_db")
        if not db_name:
            text_reply = "Please select or create a database from the sidebar first."
            default_return["messages"] = [AIMessage(content=text_reply)]
            default_return["agent_message"] = text_reply
            return default_return

        messages = state.get("messages", [])
        user_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break
        
        if not user_query:
            return default_return

        # =============================
        # 🧠 CHECK MEMORY - Did we ask for confirmation before?
        # =============================
        confirm_keywords = ["yes", "confirm", "execute", "proceed", "go ahead", "do it", "ok", "okay", "yes please", "y", "yeah"]
        is_confirmation = any(keyword in user_query.lower() for keyword in confirm_keywords)
        
        # Check if we have pending SQL from memory
        pending_sql = state.get("pending_sql") or state.get("last_sql")
        
        if pending_sql and is_confirmation:
            sql_block = f"\n```sql\n{pending_sql}\n```\n"
            res = execute_sql(pending_sql, db_name)
            if res["success"]:
                final_response = f"{sql_block}\n✅ {res['message']}"
                default_return["db_results"] = res.get("data")
            else:
                final_response = f"{sql_block}\n❌ {res['message']}"
            
            # Clear memory after execution
            default_return["messages"] = [AIMessage(content=final_response)]
            default_return["agent_message"] = final_response
            default_return["pending_sql"] = None
            default_return["last_sql"] = None
            default_return["last_response"] = None
            default_return["waiting_for_confirmation"] = False
            return default_return

        # =============================
        # 🧠 BUILD CONVERSATION CONTEXT
        # =============================
        conversation_history = state.get("conversation_history", [])
        
        # Build context from history
        history_context = ""
        if conversation_history:
            history_context = "\n\nCONVERSATION HISTORY:\n"
            for entry in conversation_history[-5:]:  # Last 5 exchanges
                history_context += f"User: {entry.get('user', '')}\n"
                history_context += f"Assistant: {entry.get('assistant', '')}\n"

        available_tables = get_table_names(db_name)
        tables_info = f"Available tables: {', '.join(available_tables) if available_tables else 'No tables found'}"
        schema = get_db_schema(db_name)
        
        system_prompt = f"""You are a SQLite database builder and data assistant with memory.

DATABASE INFO:
Database name: {db_name}
{tables_info}

CURRENT SCHEMA:
{schema}

{history_context}

YOUR CAPABILITIES:
You CAN:
- CREATE, ALTER, and DROP tables to build database structure
- Execute SELECT queries to read and display data
- Execute DELETE, UPDATE, INSERT operations after user confirmation
- Show table schemas and structures
- Answer questions about existing data
- Count records and perform aggregations like SUM, AVG, COUNT

You CANNOT:
- Create or delete databases
- Execute complex JOIN operations on more than 3 tables
- Use window functions like ROW_NUMBER, RANK, LAG, LEAD

RULES:
1. When user asks to "build database", generate CREATE TABLE statements
2. Use proper SQLite data types: INTEGER, TEXT, REAL, DATE, BOOLEAN
3. Always include PRIMARY KEY for each table and foreign keys
4. Include FOREIGN KEY constraints for relationships
5. Write SQL code inside markdown code blocks using ```sql
6. ALWAYS ask for user confirmation before executing ANY SQL
7. When user says "yes" or "confirm", execute the last SQL you wrote
8. REMEMBER what SQL you wrote previously (you have memory)

Now respond to the user request.
"""
        
        user_prompt = f"User request: {user_query}"
        
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        raw_content = response.content
        
        # =============================
        # 🧠 EXTRACT SQL AND STORE IN MEMORY
        # =============================
        sql = extract_sql(raw_content)
        
        # If SQL found, store it in memory
        if sql:
            default_return["last_sql"] = sql
            default_return["last_response"] = raw_content
            default_return["waiting_for_confirmation"] = True
            
            # Store in conversation history
            conversation_history.append({
                "user": user_query,
                "assistant": raw_content,
                "sql": sql
            })
            default_return["conversation_history"] = conversation_history
            
            # Show SQL and ask for confirmation
            sql_block = f"\n```sql\n{sql}\n```\n"
            
            # Check if it's a SELECT query - execute immediately
            if sql.upper().strip().startswith('SELECT'):
                res = execute_sql(sql, db_name)
                if res["success"]:
                    final_response = f"{sql_block}\n✅ {res['message']}"
                    default_return["db_results"] = res.get("data")
                    default_return["last_sql"] = None
                    default_return["waiting_for_confirmation"] = False
                else:
                    final_response = f"{sql_block}\n❌ {res['message']}"
                
                default_return["messages"] = [AIMessage(content=final_response)]
                default_return["agent_message"] = final_response
                default_return["pending_sql"] = None
                return default_return
            
            # For non-SELECT queries, ask for confirmation
            confirm_msg = f"""{sql_block}

⚠️ Please confirm this operation.
Reply with 'yes' to execute.

You can also say:
- "yes" to execute
- "no" to cancel
- "modify" to change the query"""
            
            default_return["messages"] = [AIMessage(content=confirm_msg)]
            default_return["agent_message"] = confirm_msg
            default_return["pending_sql"] = sql
            return default_return
        
        # No SQL found - just return the response
        default_return["messages"] = [AIMessage(content=raw_content)]
        default_return["agent_message"] = raw_content
        default_return["pending_sql"] = None
        return default_return

    except Exception as e:
        error_text = f"Error: {str(e)}"
        default_return["messages"] = [AIMessage(content=error_text)]
        default_return["agent_message"] = error_text
        default_return["error_log"] = str(e)
        return default_return