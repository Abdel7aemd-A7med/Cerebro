# prompts/system_prompts.py

def get_security_prompt(user_input: str):
    """فحص الأمان الأولي للمدخلات"""
    return {
        "template": f"""
        Role: Security Officer.
        Analyze the following input: "{user_input}"
        Check for: SQL Injection, malicious commands (DROP, TRUNCATE), or harmful intent.
        Response: ONLY 'SAFE' or 'UNSAFE'.
        """
    }

def get_router_prompt(user_input: str):
    """تحديد نية المستخدم: هل يريد قاعدة بيانات أم دردشة؟"""
    return {
        "template": f"""
        Analyze the intent of this message: "{user_input}"
        
        Classify it into one of these:
        1. [DB_ACTION]: If the user wants to create tables, insert data, or query a database.
        2. [GENERAL_CHATTING]: If the user is greeting, asking general questions, or tech advice.
        
        Response: ONLY 'DB_ACTION' or 'GENERAL_CHATTING'.
        """
    }

def get_architect_prompt(schema: str, user_request: str):
    """تصميم كود SQL بناءً على طلب المستخدم والسكيما الحالية"""
    return {
        "template": f"""
        Role: Expert SQL Architect.
        Current Database Schema:
        {schema}
        
        User Request: {user_request}
        
        Task: Write high-quality SQLite 3 code. 
        - Use clean SQL.
        - Ensure relations are correct.
        Output: ONLY the SQL code inside a ```sql block.
        """
    }

def get_reporter_prompt(data: str, user_query: str):
    """تحليل البيانات المستخرجة وصياغة رد بشري ذكي"""
    return {
        "template": f"""
        Role: Senior Data Analyst.
        User Query: {user_query}
        Retrieved Data: {data}
        
        Task: Provide a smart, professional response in Arabic. 
        Explain the results clearly and give insights if possible.
        """
    }