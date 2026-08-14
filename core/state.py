from typing import TypedDict, Annotated, List, Optional, Any, Dict
from langchain_core.messages import AnyMessage
import operator


class AgentState(TypedDict, total=False):
    # =============================
    # 🧠 Conversation Memory
    # =============================
    messages: Annotated[List[AnyMessage], operator.add]

    # =============================
    # ⚙️ Context
    # =============================
    selected_db: str

    # =============================
    # 🤖 Agent Outputs
    # =============================
    agent_message: str
    pending_sql: Optional[str]
    error_log: Optional[str]
    db_results: Any

    # =============================
    # 🛑 CONTROL FLOW
    # =============================
    stop_signal: bool

    # =============================
    # 🔥 DEBUG / STABILITY
    # =============================
    step: Optional[str]
    error: Optional[str]
    retry_count: Optional[int]

    # =============================
    #  STREAM CONTROL
    # =============================
    is_streaming: Optional[bool]
    stream_buffer: Optional[str]
    
    # =============================
    # MEMORY 
    # =============================
    conversation_history: Optional[List[Dict[str, str]]]  
    last_sql: Optional[str]  
    last_response: Optional[str]  
    waiting_for_confirmation: Optional[bool]  