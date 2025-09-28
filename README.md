# AI Image Agent

This project is a minimal AI Agent that allows users to **upload images through a Streamlit interface**, stores the images and metadata in a **SQLite database**, and uses **Gemma (via Ollama)** to generate descriptions of the uploaded images. The goal is to build an **AI agent from scratch** without using orchestration frameworks like LangChain or LlamaIndex.

---

## 🚀 What It Does

1. **Upload images** from the Streamlit frontend.
2. **Save images** locally and register them in a SQLite database.
3. **Send the image to Gemma (Ollama)** for description.
4. **Display the AI-generated description** back in the frontend.
5. **Store conversation history** for memory across sessions.

---

## 🏗️ Architecture Reasoning

I split the project into **three simple layers**:

* **Frontend (Streamlit)**
  Provides an easy-to-use UI where users upload images and see AI-generated descriptions.

* **Backend (FastAPI)**
  Handles API requests, saves images, interacts with the database, and calls the AI model.

* **AI Model (Gemma via Ollama)**
  Provides the intelligence: analyzing uploaded images and returning human-readable descriptions.

* **Database (SQLite)**
  Stores past interactions (metadata, file paths, and AI responses) to give the agent memory.

This separation keeps things **modular and transparent**, making debugging and scaling easier.

---

## ⚙️ Technology Choices

* **Streamlit** → Lightweight frontend for quick prototyping.
* **FastAPI** → High-performance backend with clear async support.
* **Ollama (Gemma model)** → Local LLM for image understanding and description.
* **SQLite** → Simple file-based database for storing interactions without extra setup.

---

## ▶️ Launching the Project

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Ollama with Gemma

Make sure [Ollama](https://ollama.ai) is installed and the **Gemma model** is pulled:

```bash
ollama pull gemma
```

### 3. Start the Backend (FastAPI)

```bash
uvicorn app.main:app --reload
```

### 4. Start the Frontend (Streamlit)

```bash
streamlit run home.py
```

---

## 🗄️ Working with the Database

The project uses **SQLite** (`agent_memory.db`) to store metadata.

### Open SQLite CLI

```bash
sqlite3 agent_memory.db
```

### Show all tables

```sql
.tables
```

### Inspect table schema

```sql
.schema interactions
```

### Query stored interactions

```sql
SELECT * FROM interactions LIMIT 10;
```

### Exit

```sql
.exit
```

---

## 🔮 Next Steps

* Add support for conversation context (multi-turn memory).
* Improve AI descriptions with richer prompts.
* Containerize with Docker for deployment.

---

👨‍💻 Built as a minimal "from scratch" AI Agent MVP without orchestration frameworks.
