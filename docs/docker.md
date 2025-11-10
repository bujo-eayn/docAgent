# Docker Guide - docAgent

Comprehensive guide for Docker deployment of docAgent.

## Architecture

The application uses Docker Compose with three services:

```
┌─────────────────────────────────────────┐
│         Docker Compose Stack            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │  Frontend    │  │   Backend      │  │
│  │  (Streamlit) │→ │   (FastAPI)    │  │
│  │  Port: 8501  │  │   Port: 8000   │  │
│  └──────────────┘  └────────┬───────┘  │
│                              │          │
│                              ↓          │
│  ┌─────────────────────────────────┐   │
│  │  PostgreSQL + pgvector          │   │
│  │  Port: 5432                     │   │
│  │  Volume: postgres_data          │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Network: docAgent-network              │
└─────────────────────────────────────────┘
         ↓ (host.docker.internal)
    ┌──────────┐
    │  Ollama  │
    │  :11434  │
    └──────────┘
```

---

## Services

### 1. PostgreSQL (pgvector/pgvector:pg18)
**Container:** `docAgent-postgres`
**Purpose:** Database with vector similarity search

**Configuration:**
```yaml
image: pgvector/pgvector:pg18
ports:
  - "5432:5432"
environment:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  POSTGRES_DB: docAgent
volumes:
  - postgres_data:/var/lib/postgresql/data
```

**Features:**
- PostgreSQL 18 with pgvector extension
- Persistent storage via named volume
- Health check with `pg_isready`
- Automatic extension creation on first run

### 2. Backend (FastAPI)
**Container:** `docAgent-backend`
**Purpose:** REST API server

**Configuration:**
```yaml
build:
  context: .
  dockerfile: Dockerfile
ports:
  - "8000:8000"
depends_on:
  postgres:
    condition: service_healthy
volumes:
  - ./app:/app/app
  - ./services:/app/services
  - ./data:/app/data
extra_hosts:
  - "host.docker.internal:host-gateway"
```

**Features:**
- Hot reload with volume mounts
- Waits for database health check
- Accesses host Ollama via `host.docker.internal`
- Data persistence via `./data` volume

### 3. Frontend (Streamlit)
**Container:** `docAgent-frontend`
**Purpose:** Web UI

**Configuration:**
```yaml
build:
  context: .
  dockerfile: Dockerfile.frontend
ports:
  - "8501:8501"
depends_on:
  - backend
environment:
  BACKEND_URL: http://backend:8000
```

**Features:**
- Connects to backend via Docker network
- Hot reload support
- Streamlit on port 8501

---

## Dockerfile Details

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/images

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Frontend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-frontend.txt .
RUN pip install --no-cache-dir -r requirements-frontend.txt

# Copy frontend code
COPY home.py .

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "home.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

---

## Docker Compose Commands

### Basic Operations
```bash
# Start all services
docker compose up

# Start in detached mode (background)
docker compose up -d

# Stop services (preserves data)
docker compose down

# Stop and remove volumes (deletes all data)
docker compose down -v

# Restart a specific service
docker compose restart backend
docker compose restart frontend
docker compose restart postgres
```

### Viewing Logs
```bash
# All services
docker compose logs

# Follow logs (real-time)
docker compose logs -f

# Specific service
docker compose logs backend
docker compose logs -f frontend

# Last 100 lines
docker compose logs --tail=100 backend
```

### Rebuilding Images
```bash
# Rebuild all services
docker compose build

# Rebuild specific service
docker compose build backend

# Rebuild and restart
docker compose up --build

# Force rebuild (no cache)
docker compose build --no-cache
```

### Service Management
```bash
# List running containers
docker compose ps

# Execute command in container
docker compose exec backend bash
docker compose exec postgres psql -U postgres -d docAgent

# View resource usage
docker compose stats
```

---

## Volume Management

### Named Volumes
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect docAgent_postgres_data

# Remove volume (WARNING: deletes data)
docker volume rm docAgent_postgres_data
```

### Bind Mounts
The following directories are mounted for hot reload:
- `./app` → Backend application code
- `./services` → Backend services
- `./data` → Persistent data storage
- `./home.py` → Frontend code

**Changes to these files trigger automatic reload!**

---

## Networking

### Docker Network
All services communicate via `docAgent-network`:
- Frontend → Backend: `http://backend:8000`
- Backend → PostgreSQL: `postgres:5432`
- Backend → Host Ollama: `host.docker.internal:11434`

### Port Mappings
| Service | Internal | External | Purpose |
|---------|----------|----------|---------|
| Frontend | 8501 | 8501 | Streamlit UI |
| Backend | 8000 | 8000 | FastAPI |
| PostgreSQL | 5432 | 5432 | Database |

### Accessing Services
- **From Host:** Use `localhost:PORT`
- **Between Containers:** Use service name (e.g., `backend:8000`)
- **To Host Services:** Use `host.docker.internal` (Ollama)

---

## Environment Variables

### Backend Environment
```bash
OLLAMA_URL=http://host.docker.internal:11434
MODEL_NAME=gemma3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=docAgent
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATA_DIR=/app/data
```

### Frontend Environment
```bash
BACKEND_URL=http://backend:8000
```

### Customizing Variables
Create `.env` file in project root:
```bash
# .env
POSTGRES_PASSWORD=secure_password
MODEL_NAME=llama2
```

Docker Compose automatically loads `.env` file.

---

## Database Operations

### Access PostgreSQL
```bash
# Enter PostgreSQL container
docker compose exec postgres psql -U postgres -d docAgent

# Run SQL command
docker compose exec postgres psql -U postgres -d docAgent -c "SELECT COUNT(*) FROM chats;"
```

### Backup Database
```bash
# Create backup
docker compose exec postgres pg_dump -U postgres docAgent > backup.sql

# Restore backup
docker compose exec -T postgres psql -U postgres docAgent < backup.sql
```

### Reset Database
```bash
# Delete and recreate
docker compose down -v
docker compose up -d postgres
# Wait for postgres to be ready
docker compose up backend
```

---

## Troubleshooting

### Container won't start
```bash
# Check container status
docker compose ps

# View logs for errors
docker compose logs backend

# Check if ports are in use
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

### Database connection errors
```bash
# Verify postgres is healthy
docker compose ps

# Check database logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U postgres -d docAgent -c "SELECT 1;"
```

### Ollama connection fails
```bash
# Verify Ollama is running on host
curl http://localhost:11434/api/tags

# Check backend can reach Ollama
docker compose exec backend curl http://host.docker.internal:11434/api/tags
```

### Volume permission issues
```bash
# Linux: Fix permissions
sudo chown -R $USER:$USER ./data

# Windows: Check Docker Desktop settings
# Settings → Resources → File Sharing
```

### Out of disk space
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything (WARNING)
docker system prune -a --volumes
```

---

## Production Considerations

### Security
1. **Change Default Passwords:**
   ```bash
   POSTGRES_PASSWORD=strong_random_password
   ```

2. **Use Secrets Management:**
   ```yaml
   services:
     backend:
       secrets:
         - postgres_password
   ```

3. **Don't Expose Ports:**
   - Remove port mappings for postgres if not needed externally
   - Use reverse proxy (nginx) for backend/frontend

### Performance
1. **Resource Limits:**
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 4G
   ```

2. **Database Tuning:**
   ```yaml
   postgres:
     environment:
       POSTGRES_SHARED_BUFFERS: 256MB
       POSTGRES_WORK_MEM: 16MB
   ```

### Monitoring
1. **Health Checks:**
   ```yaml
   backend:
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
       interval: 30s
       timeout: 10s
       retries: 3
   ```

2. **Logging:**
   ```yaml
   services:
     backend:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

---

## Useful Commands Reference

```bash
# Quick start
docker compose up -d

# View logs
docker compose logs -f

# Restart backend only
docker compose restart backend

# Access database
docker compose exec postgres psql -U postgres -d docAgent

# Clean restart
docker compose down && docker compose up --build

# Complete cleanup
docker compose down -v && docker system prune -a

# Scale service (if stateless)
docker compose up -d --scale backend=3

# Export logs
docker compose logs > logs.txt

# Check configuration
docker compose config
```

---

## Next Steps

- [Setup Guide](setup.md) - Installation instructions
- [API Documentation](api.md) - API endpoint details
- [README](../README.md) - Project overview
