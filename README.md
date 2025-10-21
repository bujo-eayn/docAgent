# README.md
# docAgent

A document-based chat application that extracts and indexes information from images, enabling intelligent Q&A using RAG (Retrieval Augmented Generation) with pgvector.

## 🎥 Demo



## 🌟 Features

- **Chat-Based Interface**: Each document gets its own conversation thread
- **Comprehensive Information Extraction**: Extracts ALL text, data, and visual information from documents
- **Semantic Search**: pgvector with IVFFlat indexing for fast, accurate context retrieval
- **Streaming Responses**: Real-time AI responses with context transparency
- **Persistent Storage**: All chats and contexts saved in PostgreSQL
- **Multi-Document Support**: Manage multiple document conversations simultaneously

## 🏗️ Architecture

```
┌──────────────┐
│   Frontend   │  Streamlit Chat Interface
│  (Streamlit) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Backend    │  FastAPI REST API
│  (FastAPI)   │
└─┬─────┬──────┘
  │     │
  │     └─────────┐
  ▼               ▼
┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Ollama  │
│+pgvector │  │   LLM    │
└──────────┘  └──────────┘
```

## 📊 Workflow

### 1. Create New Chat
```
User uploads document image
         ↓
Backend creates chat session
         ↓
Extract ALL information from image (comprehensive)
         ↓
Chunk extracted text (500 chars, 50 char overlap)
         ↓
Create embeddings for each chunk
         ↓
Store chunks with embeddings in PostgreSQL
         ↓
Create IVFFlat index for fast search
         ↓
Chat ready for questions!
```

### 2. Ask Questions
```
User asks question in chat
         ↓
Convert question to embedding
         ↓
Search chat's contexts with pgvector (top 3)
         ↓
Retrieve relevant chunks (scoped to this chat only)
         ↓
Build context from retrieved chunks
         ↓
Send to LLM: context + question
         ↓
Stream response to user
         ↓
Save message with context used
```

## 🗄️ Database Schema

### Tables

**chats**
- `id`: Unique chat identifier
- `title`: Auto-generated chat title
- `document_filename`: Original uploaded file
- `document_path`: File system path
- `created_at`: Creation timestamp
- `updated_at`: Last activity timestamp
- `is_active`: Soft delete flag

**chat_contexts**
- `id`: Context chunk identifier
- `chat_id`: Foreign key to chat
- `content`: Extracted text chunk
- `embedding`: 768-dimensional vector (indexed with IVFFlat)
- `chunk_index`: Order of extraction
- `created_at`: Creation timestamp

**messages**
- `id`: Message identifier
- `chat_id`: Foreign key to chat
- `role`: 'user', 'assistant', or 'system'
- `content`: Message text
- `context_used`: Retrieved context for this message
- `created_at`: Creation timestamp

### Indexes

**IVFFlat Index on chat_contexts.embedding**
```sql
CREATE INDEX chat_contexts_embedding_idx 
ON chat_contexts 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

Benefits:
- 10-100x faster similarity search on large datasets
- Approximate nearest neighbor search
- Optimal for 10,000+ context chunks

## 🚀 Getting Started

### Prerequisites

- Docker Desktop
- Ollama installed on host (with gemma3 and mxbai-embed-large models)
- 8GB+ RAM
- 20GB+ disk space

### Installation

1. **Clone Repository**
```bash
git clone <repo-url>
cd docAgent
```

2. **Install Ollama Models**
```bash
ollama pull gemma3
ollama pull mxbai-embed-large
```

3. **Start Services**
```bash
docker compose up -d
```

4. **Access Application**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📖 Usage Guide

### Starting a New Chat

1. Click sidebar "Upload a document image"
2. Select image file (chart, graph, document, diagram)
3. Click "Create New Chat"
4. Wait for processing (extracts info, creates embeddings)
5. Start asking questions!

### Asking Questions

1. Select active chat from sidebar
2. Type question in chat input
3. View streaming response
4. Expand "Context Used" to see retrieved information
5. Continue conversation - context is automatically retrieved

### Managing Chats

- **Switch Chats**: Click chat in sidebar
- **Delete Chat**: Click 🗑️ button next to chat
- **Refresh List**: Click 🔄 Refresh Chats

## 🔧 API Endpoints

### Create Chat
```http
POST /chats/create
Content-Type: multipart/form-data

file: <image_file>
```

Response:
```json
{
  "success": true,
  "chat_id": 1,
  "message": "Chat created and document processed successfully",
  "document_filename": "chart.png",
  "chunks_created": 15
}
```

### Send Message
```http
POST /chats/{chat_id}/message
Content-Type: application/x-www-form-urlencoded

question=What is the trend in Q3?
```

Response: Server-Sent Events stream

### List Chats
```http
GET /chats
```

Response:
```json
[
  {
    "id": 1,
    "title": "Chat: production_chart.png",
    "document_filename": "production_chart.png",
    "created_at": "2025-10-16T10:30:00",
    "updated_at": "2025-10-16T11:45:00",
    "message_count": 12
  }
]
```

### Get Chat Details
```http
GET /chats/{chat_id}
```

### Delete Chat
```http
DELETE /chats/{chat_id}
```

## 🎯 Key Improvements Over Previous Version

| Feature | Old Version | New Version |
|---------|------------|-------------|
| Workflow | Single image analysis | Chat-based conversations |
| Context | Global (all images) | Scoped to chat |
| Information Extraction | Caption only | Comprehensive extraction |
| Context Storage | Single embedding | Multiple chunked embeddings |
| Search | FAISS (in-memory) | pgvector IVFFlat (persistent) |
| Interface | Single-shot | Conversational |
| History | Limited | Full chat history |
| Scalability | Limited | Production-ready |

## 🔍 Context Retrieval Example

**Document Uploaded**: Production chart with Q1-Q4 data

**Extracted and Chunked**:
- Chunk 1: "Chart Title: Production Analysis 2024. Shows quarterly data..."
- Chunk 2: "Q1 Production: 1200 units. Q2 Production: 1450 units..."
- Chunk 3: "Trend Analysis: Production increased 20% from Q1 to Q2..."
- ... (more chunks)

**User Question**: "What was the Q2 production?"

**Vector Search**:
1. Question → embedding
2. Find top 3 similar chunks
3. Results:
   - Chunk 2 (0.95 similarity): "Q1 Production: 1200 units. Q2 Production: 1450 units..."
   - Chunk 3 (0.82 similarity): "Trend Analysis: Production increased..."
   - Chunk 1 (0.71 similarity): "Chart Title: Production Analysis..."

**LLM Response**: "Based on the chart, Q2 production was 1450 units, which represents a 20% increase from Q1."

## 🛠️ Development

### Project Structure
```
docAgent/
├── app/
│   ├── main.py              # FastAPI application
│   └── faiss_indexer.py     # (Removed - using pgvector)
├── services/
│   ├── chat_service.py      # Chat management (NEW)
│   ├── document_processor.py # Document extraction (NEW)
│   ├── context_service.py   # Context retrieval
│   ├── ollama_service.py    # LLM interaction
│   ├── file_service.py      # File handling
│   └── database_service.py  # Database operations
├── config.py                # Configuration
├── models.py                # Database models (redesigned)
├── home.py                  # Streamlit frontend (redesigned)
├── compose.yaml             # Docker services
├── Dockerfile               # Backend container
├── Dockerfile.frontend      # Frontend container
└── requirements.txt         # Python dependencies
```

### Adding New Features

**Add Custom Document Processor**:
```python
# services/document_processor.py
class CustomProcessor(DocumentProcessor):
    def extract_information_from_image(self, image_b64: str) -> str:
        # Your custom extraction logic
        pass
```

**Customize Chunking Strategy**:
```python
def chunk_text(self, text: str, chunk_size: int = 1000):
    # Your custom chunking logic
    pass
```

## 📈 Performance Tuning

### IVFFlat Index Configuration

For different dataset sizes:

**Small (< 1,000 contexts)**:
```sql
-- No index needed, use flat search
```

**Medium (1,000 - 100,000)**:
```sql
CREATE INDEX ... WITH (lists = 100);
```

**Large (100,000 - 1M)**:
```sql
CREATE INDEX ... WITH (lists = 1000);
```

**Very Large (1M+)**:
```sql
CREATE INDEX ... WITH (lists = 10000);
```

### Chunking Optimization

Adjust based on document type:

**Dense Text** (papers, articles):
```python
chunk_size=1000, overlap=100
```

**Sparse Text** (charts, diagrams):
```python
chunk_size=500, overlap=50
```

**Mixed Content**:
```python
chunk_size=750, overlap=75
```

## 🐛 Troubleshooting

### Document Processing Takes Too Long

- Use smaller images (< 2MB)
- Adjust chunk_size to create fewer chunks
- Ensure Ollama is using GPU

### Search Returns Irrelevant Results

- Increase top_k for more context
- Check embedding quality
- Rebuild IVFFlat index with more lists

### Out of Memory

- Reduce chunk_size
- Process documents in batches
- Increase Docker memory allocation

## 🔒 Security Considerations

### Production Deployment

1. **Change Default Passwords**
```yaml
environment:
  - POSTGRES_PASSWORD=<strong-password>
```

2. **Enable Authentication**
```python
# Add JWT authentication to FastAPI
from fastapi.security import HTTPBearer
```

3. **Sanitize Inputs**
```python
# Already implemented: filename sanitization
# Add: SQL injection prevention (SQLAlchemy handles this)
```

4. **Rate Limiting**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
```

## 📊 Monitoring

### Database Metrics
```sql
-- Context count per chat
SELECT chat_id, COUNT(*) as context_count 
FROM chat_contexts 
GROUP BY chat_id;

-- Average similarity scores
SELECT AVG(distance) FROM (
  SELECT embedding <=> '[...]' as distance 
  FROM chat_contexts
) t;

-- Index usage
SELECT * FROM pg_stat_user_indexes 
WHERE indexrelname = 'chat_contexts_embedding_idx';
```

### Application Metrics
```bash
# API response times
docker compose logs backend | grep "POST /chats"

# Active chats
curl http://localhost:8000/chats | jq 'length'
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

[Your License]

## 🙏 Acknowledgments

- pgvector for PostgreSQL vector operations
- Ollama for local LLM inference
- Streamlit for rapid UI development
- FastAPI for modern Python APIs
"""