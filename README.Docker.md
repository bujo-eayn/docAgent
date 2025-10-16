# README.Docker.md

# Docker Setup Guide for docAgent

This guide will help you set up and run the docAgent project using Docker.

## Prerequisites

### Required
- **Docker Desktop** (version 20.10+)
  - [Install for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - [Install for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - [Install for Linux](https://docs.docker.com/desktop/install/linux-install/)
- **Docker Compose** (included with Docker Desktop)
- **At least 8GB RAM** available for Docker
- **20GB free disk space** (for models and images)

### Optional (for GPU acceleration)
- **NVIDIA GPU** with CUDA support
- **NVIDIA Container Toolkit** installed
  ```bash
  # For Ubuntu/Debian
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
  curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
  curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
  sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
  sudo systemctl restart docker
  ```

## Project Structure

```
docAgent/
├── app/
│   ├── main.py
│   └── faiss_indexer.py
├── services/
│   ├── ollama_service.py
│   ├── database_service.py
│   ├── file_service.py
│   └── context_service.py
├── config.py
├── models.py
├── home.py
├── Dockerfile
├── Dockerfile.frontend
├── compose.yaml
├── requirements.txt
├── requirements-frontend.txt
├── .dockerignore
└── README.Docker.md
```

## Quick Start

### 1. Clone the Repository
```bash
git clone 
cd docAgent
```

### 2. Build and Start Services
```bash
# Build all services
docker compose build

# Start all services in detached mode
docker compose up -d
```

This will start:
- **Ollama** service (port 11434) - LLM backend
- **Backend API** (port 8000) - FastAPI application
- **Frontend** (port 8501) - Streamlit interface
- **Model Init** - Downloads required models (runs once)

### 3. Wait for Models to Download
The first time you run this, it will download the required models (~4-6GB). Monitor progress:

```bash
# Watch model download progress
docker compose logs -f model-init

# You should see:
# "Pulling gemma3 model..."
# "Pulling mxbai-embed-large model..."
# "Models downloaded successfully!"
```

### 4. Access the Application
Once all services are running:
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

### Basic Operations

1. **Upload an Image**
   - Navigate to http://localhost:8501
   - Click "Browse files" to upload an image
   - Enter a prompt (e.g., "Describe this image in detail")
   - Click "Send to Agent"
   <!-- - Watch the response stream in real-time -->

2. **View Context**
   - After receiving a response, expand "📚 Context Sent to Model"
   - See what previous similar images were used for context

3. **List Stored Images**
   - Click "List stored images" button
   - View all previously analyzed images and their captions

### Docker Commands

#### View Running Services
```bash
docker compose ps
```

#### View Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs backend
docker compose logs frontend
docker compose logs ollama

# Follow logs (real-time)
docker compose logs -f backend
```

#### Stop Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

#### Restart Services
```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart backend
```

#### Rebuild After Code Changes
```bash
# Rebuild and restart
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build backend
```

## Configuration

### Environment Variables

Edit `compose.yaml` to customize:

```yaml
backend:
  environment:
    - OLLAMA_URL=http://ollama:11434  # Ollama service URL
    - MODEL_NAME=gemma3                # LLM model to use
    - DATA_DIR=/app/data               # Data storage directory
```

### Using Different Models

To use a different model:

1. Edit `compose.yaml`:
   ```yaml
   backend:
     environment:
       - MODEL_NAME=llama2  # or llama3, mistral, etc.
   ```

2. Update `model-init` service:
   ```yaml
   model-init:
     command:
       - |
         echo "Pulling llama2 model..."
         ollama pull llama2
         ollama pull mxbai-embed-large
   ```

3. Restart services:
   ```bash
   docker compose down
   docker compose up -d
   ```

### CPU-Only Mode

If you don't have a GPU, the services will automatically run on CPU. However, you should comment out the GPU configuration in `compose.yaml`:

```yaml
ollama:
  # Comment out or remove this section for CPU-only
  # deploy:
  #   resources:
  #     reservations:
  #       devices:
  #         - driver: nvidia
  #           count: all
  #           capabilities: [gpu]
```

## Data Persistence

### Volumes

The project uses Docker volumes to persist data:

- **`ollama_data`**: Stores downloaded models (~4-6GB)
- **`./data`**: Stores uploaded images and SQLite database (bind mount)

### Backing Up Data

```bash
# Backup images and database
cp -r ./data ./data_backup_$(date +%Y%m%d)

# Backup Ollama models
docker run --rm -v docAgent_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz -C /data .
```

### Restoring Data

```bash
# Restore images and database
cp -r ./data_backup_YYYYMMDD ./data

# Restore Ollama models
docker run --rm -v docAgent_ollama_data:/data -v $(pwd):/backup alpine tar xzf /backup/ollama_backup.tar.gz -C /data
```

## Troubleshooting

### Services Won't Start

**Check Docker is running:**
```bash
docker info
```

**Check service status:**
```bash
docker compose ps
```

**View error logs:**
```bash
docker compose logs backend
docker compose logs ollama
```

### "Connection Refused" Errors

**Ensure all services are healthy:**
```bash
docker compose ps

# Should show all services as "Up" or "healthy"
```

**Check network connectivity:**
```bash
# Test backend from frontend container
docker compose exec frontend curl http://backend:8000

# Test Ollama from backend container
docker compose exec backend curl http://ollama:11434
```

### Models Not Downloaded

**Check model-init logs:**
```bash
docker compose logs model-init
```

**Manually pull models:**
```bash
docker compose exec ollama ollama pull gemma3
docker compose exec ollama ollama pull mxbai-embed-large
```

**Verify models are available:**
```bash
docker compose exec ollama ollama list
```

### Out of Memory Errors

**Increase Docker memory limit:**
- Docker Desktop → Settings → Resources → Memory
- Allocate at least 8GB

**Use smaller models:**
```yaml
environment:
  - MODEL_NAME=gemma:2b  # Smaller variant
```

### Slow Performance

**Check CPU/Memory usage:**
```bash
docker stats
```

**Enable GPU (if available):**
- Ensure NVIDIA Container Toolkit is installed
- Uncomment GPU configuration in `compose.yaml`
- Restart services

### Port Already in Use

**Check what's using the port:**
```bash
# Linux/Mac
lsof -i :8000
lsof -i :8501
lsof -i :11434

# Windows
netstat -ano | findstr :8000
```

**Change ports in compose.yaml:**
```yaml
backend:
  ports:
    - "8001:8000"  # Change host port

frontend:
  ports:
    - "8502:8501"  # Change host port
```

### Database Locked Errors

**Stop all services:**
```bash
docker compose down
```

**Remove database lock:**
```bash
rm ./data/memory.db-shm
rm ./data/memory.db-wal
```

**Restart services:**
```bash
docker compose up -d
```

## Development Mode

### Live Code Reloading

The `compose.yaml` already includes volume mounts for live reloading:

```yaml
backend:
  volumes:
    - ./app:/app/app  # Backend code
    - ./config.py:/app/config.py
    - ./models.py:/app/models.py

frontend:
  volumes:
    - ./home.py:/app/home.py  # Frontend code
```

Changes to Python files will be reflected immediately (you may need to refresh the browser for frontend changes).

### Running Tests

```bash
# Enter backend container
docker compose exec backend bash

# Run tests
pytest tests/

# Exit container
exit
```

### Debugging

**Access container shell:**
```bash
# Backend
docker compose exec backend bash

# Frontend
docker compose exec frontend bash

# Ollama
docker compose exec ollama bash
```

**Check Python packages:**
```bash
docker compose exec backend pip list
docker compose exec frontend pip list
```

**Interactive Python shell:**
```bash
docker compose exec backend python
>>> from app.main import app
>>> # Test imports
```

## Performance Optimization

### Production Deployment

For production, consider:

1. **Use production WSGI server:**
   ```dockerfile
   CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
   ```

2. **Add health checks:**
   ```yaml
   backend:
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
       interval: 30s
       timeout: 10s
       retries: 3
   ```

3. **Use separate database:**
   - Replace SQLite with PostgreSQL
   - Add PostgreSQL service to `compose.yaml`

4. **Add Redis for caching:**
   ```yaml
   redis:
     image: redis:7-alpine
     ports:
       - "6379:6379"
   ```

5. **Set up reverse proxy (Nginx):**
   ```yaml
   nginx:
     image: nginx:alpine
     ports:
       - "80:80"
     volumes:
       - ./nginx.conf:/etc/nginx/nginx.conf
   ```

## Security Considerations

### For Production

1. **Don't expose Ollama port:**
   ```yaml
   ollama:
     # Remove ports section or use 127.0.0.1:11434:11434
   ```

2. **Use environment files:**
   ```bash
   # Create .env file
   echo "MODEL_NAME=gemma3" > .env
   echo "SECRET_KEY=your-secret-key" >> .env
   
   # Reference in compose.yaml
   env_file:
     - .env
   ```

3. **Set resource limits:**
   ```yaml
   backend:
     deploy:
       resources:
         limits:
           cpus: '2'
           memory: 4G
   ```

4. **Use read-only filesystems where possible:**
   ```yaml
   backend:
     read_only: true
     tmpfs:
       - /tmp
   ```

## Support

### Getting Help

- Check logs: `docker compose logs -f`
- Review this documentation
- Check Docker status: `docker compose ps`
- Verify Docker version: `docker --version`

### Common Issues

| Issue | Solution |
|-------|----------|
| Port conflict | Change ports in `compose.yaml` |
| Out of memory | Increase Docker memory allocation |
| Model not found | Run `docker compose exec ollama ollama pull gemma3` |
| Database locked | Stop services, remove `.db-shm` and `.db-wal` files |
| Network errors | Restart Docker: `docker compose down && docker compose up -d` |

## Cleanup

### Remove Everything

```bash
# Stop and remove containers, networks
docker compose down

# Remove volumes (WARNING: deletes all data including models)
docker compose down -v

# Remove images
docker compose down --rmi all

# Remove everything (nuclear option)
docker system prune -a --volumes
```

### Remove Only Application Data

```bash
# Stop services
docker compose down

# Remove only data directory
rm -rf ./data

# Restart (fresh database)
docker compose up -d
```

## License

[Your License Here]

## Contributors

[Your Contributors Here]