# 🧠 Turinoo - AI-Powered SQLite Database Assistant

**Turinoo** is an intelligent agent system built with **LangGraph** and **LangChain** that enables users to interact with SQLite databases using natural language. The system generates and executes SQL queries automatically without requiring SQL knowledge from the user.

![Project Status](https://img.shields.io/badge/Status-Under%20Development-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![Framework](https://img.shields.io/badge/Framework-LangGraph-orange.svg)
![LLM](https://img.shields.io/badge/LLM-Qwen--3.5--9B-lightgrey.svg)
![Frontend](https://img.shields.io/badge/Frontend-Streamlit-red.svg)

---

## 📋 Table of Contents

- [What is Turinoo?](#what-is-turinoo)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [How to Use](#how-to-use)
- [Team](#team)
- [License](#license)

---

## 🧠 What is Turinoo?

Turinoo is an **AI agent** that bridges the gap between natural language and database management. It allows users to:

- **Ask questions** in plain English and get answers from their databases
- **Upload files** (CSV, Excel, JSON, XML) and automatically create databases
- **Execute SQL queries** on SQLite without writing SQL manually

The agent handles **SQL generation** → **execution** → **result presentation** in an autonomous loop.

---

## ✨ Key Features

### 🗣️ Natural Language to SQL
- Convert plain English questions into SQL queries
- Support for basic queries: SELECT, JOIN, aggregations
- Instant execution with real-time results

### 📂 File Upload & Auto-Database Creation
- Upload CSV, Excel (XLSX/XLS), JSON, or XML files
- Automatic database creation with schema detection
- Support for files up to 20,000+ rows

### 🧠 Conversation Memory
- Remembers previous questions and context
- Maintains conversation history within the session
- Uses LangGraph's persistent memory

### 🔒 Basic Security
- Confirmation required before destructive operations (DELETE, UPDATE, DROP)
- SQL injection protection

### 🎯 Smart Query Execution
- SELECT queries execute immediately
- DELETE/UPDATE/INSERT operations require user confirmation
- Basic error detection and handling

### 📊 Data Display
- Automatic table display for query results
- Clean, responsive UI

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **AI Framework** | LangChain + LangGraph |
| **LLM** | Qwen-3.5-9B (via KoboldCPP) |
| **Database** | SQLite |
| **Frontend** | Streamlit |
| **Language** | Python 3.10+ |

## 📁 Project Structure

```
turinoo/
├── app.py                          # 🖥️ Streamlit frontend interface
├── core/                           # 🧠 Agent core logic
│   ├── state.py                    # 📋 LangGraph state schema
│   ├── nodes.py                    # 🤖 Agent intelligence & execution
│   └── graph.py                    # 🔄 Workflow orchestration & routing
├── database/                       # 🗄️ Database operations
│   └── db_manager.py               # 📊 SQLite & file ingestion manager
├── databases/                      # 💾 Local SQLite databases & memory
├── models/                         # 🤗 LLM models (download separately)
├── scripts/                        # 🔧 Utility scripts
├── requirements.txt                # 📦 Python dependencies
├── LICENSE                         # 📜 MIT License
└── README.md                       # 📖 Project documentation
```

## 📋 Prerequisites

- **Python Version:** `Python >= 3.10` (Check using `python --version`)
- **Package Manager:** `pip` (Ensure it is upgraded to the latest version)
- **Disk Space:** At least ~6 GB of free disk space (to store the `Qwen3.5-9B-Q4_1.gguf` model weights)

### 📦 Install Python Dependencies

Make sure to install all required framework libraries using the `requirements.txt` file:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Quick Start
1. Download and setup dependencies

```bash
python -m venv venv
.\venv\Scripts\activate   # On Linux/macOS: source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install huggingface_hub
```

2. Download KoboldCPP & model weights

```bash
# Download KoboldCPP executable (Windows)
curl.exe -L -o koboldcpp.exe https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe

# Download Qwen 3.5 9B GGUF weights
mkdir models
huggingface-cli download Qwen/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_1.gguf --local-dir ./models --local-dir-use-symlinks False
```

3. Start the local LLM engine

```bash
# Download KoboldCPP executable (Windows)
.\koboldcpp.exe --model .\models\Qwen3.5-9B-Q4_1.gguf --port 5001 --contextsize 4096 --smartcontext --contextshift --threads 8   # terminal 1
```

4. Start the Turinoo UI & Agent

```bash
streamlit run app.py   # terminal 2
```
