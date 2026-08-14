import sqlite3
import os
import logging
import threading

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END

from core.state import AgentState
from core.nodes import agent_node  # فقط agent_node موجود الآن


# =============================
# LOGGING SETUP
# =============================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =============================
# PERSISTENT MEMORY
# =============================
os.makedirs("databases", exist_ok=True)

_thread_local = threading.local()

def get_db_connection():
    if not hasattr(_thread_local, "conn") or _thread_local.conn is None:
        _thread_local.conn = sqlite3.connect(
            "databases/agent_memory.db",
            check_same_thread=False,
            timeout=30.0
        )
        _thread_local.conn.execute("PRAGMA journal_mode=WAL")
        _thread_local.conn.execute("PRAGMA synchronous=NORMAL")
    return _thread_local.conn

memory = SqliteSaver(get_db_connection())


# =============================
# GRAPH INIT
# =============================
workflow = StateGraph(AgentState)


# =============================
# SINGLE NODE (Unified Agent)
# =============================
workflow.add_node("agent", agent_node)


# =============================
# ENTRY AND EXIT
# =============================
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)


# =============================
# COMPILE
# =============================
app = workflow.compile(
    checkpointer=memory,
    interrupt_after=[]  # No interrupts - agent handles everything internally
)