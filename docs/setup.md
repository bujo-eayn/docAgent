# Setup Guide - docAgent

This guide covers installation and setup for the docAgent document chat application.

## Prerequisites

### Required Software
- **Docker & Docker Compose** (recommended) OR
- **Python 3.10+** for local development
- **PostgreSQL 14+** with pgvector extension
- **Ollama** with models installed

### Required Ollama Models
```bash
# Install required models
ollama pull gemma3
ollama pull mxbai-embed-large
```

---

## Option 1: Docker Setup (Recommended)

### 1. Clone Repository
```bash
git clone <repository-url>
cd docAgent
```

### 2. Environment Configuration
Create a `.env` file (optional - defaults work for Docker):
```bash
# Ollama Configuration
OLLAMA_URL=http://host.docker.internal:11434
MODEL_NAME=gemma3

# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=docAgent
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Data Directory
DATA_DIR=./data
```

### 3. Start Services
```bash
# Start all services
docker compose up

# Or start in detached mode
docker compose up -d
```

### 4. Access Application
- **Frontend (Streamlit):** http://localhost:8501
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

### 5. Stop Services
```bash
# Stop services
docker compose down

# Stop and remove volumes (deletes data)
docker compose down -v
```

---

## Option 2: Local Development Setup

### 1. Install PostgreSQL with pgvector
```bash
# macOS
brew install postgresql@14
brew install pgvector

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
# Install pgvector from source (see pgvector docs)

# Start PostgreSQL
pg_ctl -D /usr/local/var/postgres start
```

### 2. Create Database
```bash
# Connect to PostgreSQL
psql postgres

# Create database and enable extension
CREATE DATABASE docAgent;
\c docAgent
CREATE EXTENSION vector;
\q
```

### 3. Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
pip install -r requirements-frontend.txt
```

### 4. Configure Environment
Create `.env` file:
```bash
OLLAMA_URL=http://localhost:11434
MODEL_NAME=gemma3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=docAgent
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATA_DIR=./data
```

### 5. Start Backend
```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start Frontend (New Terminal)
```bash
# Activate venv
source venv/bin/activate

# Set backend URL
export BACKEND_URL=http://localhost:8000  # On Windows: set BACKEND_URL=http://localhost:8000

# Start Streamlit
streamlit run home.py --server.port 8501
```

### 7. Access Application
- **Frontend:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

---

## Verification

### Check Backend Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Check Database Connection
```bash
# Connect to database
psql -h localhost -U postgres -d docAgent

# Check tables exist
\dt

# Should show: chats, chat_contexts, messages
```

### Check Ollama Connection
```bash
curl http://localhost:11434/api/tags
# Should list installed models
```

---

## Troubleshooting

### Backend won't start
**Error:** `ModuleNotFoundError: No module named 'pydantic_settings'`
```bash
pip install pydantic-settings
```

**Error:** `could not connect to server: Connection refused`
- Check PostgreSQL is running
- Verify connection details in `.env`

### Frontend won't connect to backend
**Error:** Connection errors in Streamlit
```bash
# Verify BACKEND_URL is set correctly
echo $BACKEND_URL

# For Docker: should be http://backend:8000
# For local: should be http://localhost:8000
```

### Ollama not accessible
**Error:** `OllamaServiceException`
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama service
ollama serve
```

### Database extension not found
**Error:** `extension "vector" does not exist`
```bash
# Connect to database
psql -U postgres -d docAgent

# Enable extension
CREATE EXTENSION vector;
```

### Permission errors on Windows
**Error:** Docker can't access files
- Ensure Docker Desktop has access to the project directory
- Check Docker Desktop > Settings > Resources > File Sharing

---

## Development Tips

### Hot Reload
Both backend and frontend support hot reload:
- **Backend:** Uses `--reload` flag (automatic)
- **Frontend:** Streamlit auto-reloads on file changes

### View Logs
```bash
# Docker logs
docker compose logs -f backend
docker compose logs -f frontend

# Local logs
# Check terminal where uvicorn/streamlit is running
```

### Reset Database
```bash
# Docker
docker compose down -v
docker compose up

# Local
psql -U postgres -d docAgent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python -c "from models import create_tables; create_tables()"
```

### Access Database
```bash
# Docker
docker compose exec postgres psql -U postgres -d docAgent

# Local
psql -U postgres -d docAgent
```

---

## Next Steps

After setup is complete:
- See [Docker Guide](docker.md) for Docker-specific information
- See [API Documentation](api.md) for API endpoint details
- Try uploading a document and asking questions!

---

## Support

If you encounter issues:
1. Check logs for error messages
2. Verify all prerequisites are installed
3. Check configuration in `.env`
4. Review troubleshooting section above
