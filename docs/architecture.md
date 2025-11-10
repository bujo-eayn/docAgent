# Architecture Documentation - docAgent

Technical architecture and design decisions for the docAgent application.

## System Overview

docAgent is a **RAG (Retrieval-Augmented Generation)** system that enables conversational Q&A about uploaded documents using:
- **Document Processing:** Extract all information from images
- **Semantic Search:** pgvector for similarity-based context retrieval
- **Chat Interface:** Multi-session conversation management
- **LLM Integration:** Ollama for embeddings and chat completion

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│                     (Streamlit Frontend)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Endpoints                                               │   │
│  │  • POST /chats/create                                    │   │
│  │  • POST /chats/{id}/message (SSE)                        │   │
│  │  • GET /chats, GET /chats/{id}, DELETE /chats/{id}      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │               Service Layer                               │   │
│  │  • ChatService - Chat/Message CRUD                        │   │
│  │  • DocumentProcessor - Extract, Chunk, Embed             │   │
│  │  • ContextService - Query Processing                     │   │
│  │  • OllamaService - LLM Integration                        │   │
│  │  • FileService - File Management                          │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
            ↓                                 ↓
┌───────────────────────┐         ┌──────────────────────┐
│  PostgreSQL + pgvector│         │   Ollama LLM         │
│  • Chats              │         │   • gemma3           │
│  • Chat Contexts      │         │   • mxbai-embed-large│
│  • Messages           │         │   (Host Service)     │
│  • IVFFlat Index      │         └──────────────────────┘
└───────────────────────┘
```

---

## Core Components

### 1. Frontend (Streamlit)

**File:** `home.py`

**Responsibilities:**
- User interface for document upload
- Chat session management
- Message streaming display
- Session state management

**Key Features:**
- Single-page application
- Sidebar with chat list
- Real-time message streaming
- Document upload interface

**Technology:**
- Streamlit
- Python Requests for API calls
- Server-Sent Events (SSE) streaming

---

### 2. Backend (FastAPI)

**File:** `app/main.py`

**Responsibilities:**
- RESTful API endpoints
- Request validation
- Response streaming
- Exception handling

**Architecture Pattern:** Service-oriented

**Key Features:**
- Automatic API documentation (Swagger/ReDoc)
- Async request handling
- SSE streaming for chat responses
- Custom exception handlers

**Technology:**
- FastAPI
- Uvicorn ASGI server
- Pydantic for validation

---

### 3. Service Layer

#### ChatService (`services/chat_service.py`)
**Purpose:** Database operations for chats, contexts, and messages

**Methods:**
- `create_chat()` - Create chat session
- `get_chat()` - Retrieve chat by ID
- `get_all_chats()` - List all chats
- `delete_chat()` - Soft delete chat
- `add_context_chunk()` - Store document chunks
- `search_context()` - pgvector similarity search
- `add_message()` - Save messages
- `get_chat_messages()` - Retrieve conversation history

**Database Interaction:** Direct SQLAlchemy + raw SQL for pgvector

---

#### DocumentProcessor (`services/document_processor.py`)
**Purpose:** Complete document processing pipeline

**Pipeline:**
```
Image Upload
    ↓
Extract Info (LLM)
    ↓
Chunk Text (500 chars, 50 overlap)
    ↓
Generate Embeddings (1024-dim)
    ↓
Store in Database
    ↓
Return chunk count
```

**Methods:**
- `extract_information_from_image()` - LLM-based extraction
- `chunk_text()` - Split into overlapping segments
- `process_document()` - Orchestrate full pipeline

**Configuration:**
- Chunk size: 500 characters (configurable)
- Overlap: 50 characters (configurable)
- Sentence-based chunking for coherence

---

#### ContextService (`services/context_service.py`)
**Purpose:** Query processing and context retrieval

**Process Flow:**
```
User Question
    ↓
Convert to Embedding
    ↓
Search Top-K Contexts (cosine similarity)
    ↓
Format with Relevance Scores
    ↓
Return Context String
```

**Key Algorithm:** Semantic search with pgvector cosine distance

---

#### OllamaService (`services/ollama_service.py`)
**Purpose:** LLM and embedding API integration

**Methods:**
- `call_ollama_embed()` - Generate embeddings
- `stream_ollama_chat()` - Stream chat responses
- `stream_ollama_chat_with_image()` - Chat with image input
- `_stream_ollama_response()` - Shared streaming logic (DRY)

**Models:**
- Chat: `gemma3`
- Embeddings: `mxbai-embed-large` (1024 dimensions)

**Error Handling:** Tries multiple endpoints for compatibility

---

#### FileService (`services/file_service.py`)
**Purpose:** File upload and storage management

**Features:**
- Timestamp-prefixed filenames (collision prevention)
- Configurable storage directory
- Simple file save operation

---

### 4. Data Layer

#### Database Schema

```sql
-- Chat Sessions
CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    document_filename VARCHAR(255) NOT NULL,
    document_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Document Context Chunks
CREATE TABLE chat_contexts (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1024),  -- pgvector type
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversation Messages
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    context_used TEXT,  -- Context provided to LLM
    created_at TIMESTAMP DEFAULT NOW()
);

-- IVFFlat Index for Fast Similarity Search
CREATE INDEX chat_contexts_embedding_idx
ON chat_contexts
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## Design Patterns

### 1. Service Layer Pattern
**Why:** Separation of business logic from HTTP handling
- Services contain business logic
- Controllers (endpoints) handle HTTP concerns
- Easy to test and maintain

### 2. Repository Pattern (Partial)
**Current:** Service classes handle data access
**Future:** Can extract to dedicated repositories

### 3. Dependency Injection
**Implementation:** FastAPI dependencies
**Usage:** Database sessions, configuration

### 4. Factory Pattern
**Usage:** Logger creation, service initialization

---

## Data Flow

### Document Upload Flow

```
1. User uploads image (Frontend)
        ↓
2. POST /chats/create (Backend)
        ↓
3. FileService.save_uploaded_file()
        ↓
4. ChatService.create_chat() → Database
        ↓
5. OllamaService.image_to_base64()
        ↓
6. DocumentProcessor.process_document()
        ├─→ extract_information_from_image()
        │   └─→ Ollama: Extract all info
        ├─→ chunk_text()
        │   └─→ Split into 500-char chunks
        └─→ For each chunk:
            ├─→ OllamaService.call_ollama_embed()
            │   └─→ Generate 1024-dim embedding
            └─→ ChatService.add_context_chunk()
                └─→ Store in database
        ↓
7. ChatService.add_message() → System message
        ↓
8. Return: {chat_id, chunks_created}
```

### Question Answering Flow

```
1. User asks question (Frontend)
        ↓
2. POST /chats/{chat_id}/message (Backend)
        ↓
3. ChatService.add_message() → Save user question
        ↓
4. ContextService.build_context_from_query()
        ├─→ OllamaService.call_ollama_embed(question)
        │   └─→ Convert question to embedding
        ├─→ ChatService.search_context()
        │   └─→ pgvector: SELECT ... ORDER BY embedding <=> query
        │       └─→ Returns top-3 similar chunks
        └─→ Format contexts with relevance scores
        ↓
5. Build system prompt with context
        ↓
6. OllamaService.stream_ollama_chat()
        ├─→ POST /api/chat (Ollama)
        └─→ Stream tokens via SSE
        ↓
7. Collect and save complete response
        ↓
8. ChatService.add_message() → Save assistant response
        ↓
9. Return: Streamed tokens + final metadata
```

---

## Key Algorithms

### 1. Text Chunking
```python
def chunk_text(text, chunk_size=500, overlap=50):
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) > chunk_size:
            # Save chunk
            chunks.append(' '.join(current_chunk))
            # Start new chunk with overlap (last 2 sentences)
            current_chunk = current_chunk[-2:] + [sentence]
        else:
            current_chunk.append(sentence)
            current_length += len(sentence)

    return chunks
```

**Benefits:**
- Maintains sentence coherence
- Overlap ensures context continuity
- Configurable sizes

### 2. Semantic Search (pgvector)
```python
# Cosine distance search
query = """
    SELECT id, content, embedding <=> :query_embedding AS distance
    FROM chat_contexts
    WHERE chat_id = :chat_id AND embedding IS NOT NULL
    ORDER BY distance
    LIMIT :top_k
"""
# Lower distance = more similar
# Similarity = 1 - distance
```

**Why pgvector:**
- Native PostgreSQL extension
- Persistent storage
- IVFFlat index for fast search
- Cosine distance operator `<=>`

### 3. Streaming Response
```python
def stream_ollama_chat():
    with requests.post(url, json=payload, stream=True) as response:
        for line in response.iter_lines():
            parsed = json.loads(line)
            if parsed.get("done"):
                yield "data: [DONE]\n\n"
                break
            content = parsed["message"]["content"]
            yield f"data: {content}\n\n"
```

**SSE Format:**
- Prefix: `data:`
- Content: token or message
- Suffix: `\n\n` (double newline)

---

## Configuration Management

### Pydantic Settings
```python
class Settings(BaseSettings):
    ollama_url: str = "http://host.docker.internal:11434"
    model_name: str = "gemma3"
    chunk_size: int = 500
    top_k_contexts: int = 3
    # ... etc

    @field_validator("chunk_size")
    def validate_chunk_size(cls, v):
        if v < 100 or v > 5000:
            raise ValueError("Invalid chunk size")
        return v

    class Config:
        env_file = ".env"
```

**Benefits:**
- Type safety
- Validation
- Environment variable support
- .env file loading

---

## Error Handling

### Exception Hierarchy
```
DocAgentException (base)
├── ChatNotFoundException
├── DocumentProcessingException
├── OllamaServiceException
│   └── EmbeddingException
├── DatabaseException
└── FileUploadException
    └── InvalidFileTypeException
```

### FastAPI Handlers
```python
@app.exception_handler(ChatNotFoundException)
async def chat_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, **exc.details}
    )
```

---

## Logging Strategy

### Centralized Logger
```python
# utils/logger.py
logger = setup_logger(__name__)

# Usage in services
logger.info("Processing document for chat {chat_id}")
logger.error("Extraction failed", exc_info=True)
logger.debug("Stored chunk {idx}/{total}")
```

**Log Levels:**
- `DEBUG`: Detailed processing steps
- `INFO`: Key operations (upload, search)
- `WARNING`: Recoverable issues
- `ERROR`: Failures with stack traces

---

## Performance Considerations

### Database
1. **Indexes:**
   - IVFFlat index on embeddings (100 lists)
   - Primary keys on all tables
   - Foreign keys for referential integrity

2. **Queries:**
   - Scoped searches (chat_id filter)
   - Limited result sets (top_k)
   - Prepared statements via SQLAlchemy

### Caching Opportunities
- Embedding cache (future enhancement)
- Query result cache (Redis)
- Static response cache

### Streaming
- Reduces memory usage
- Improves perceived performance
- Better UX for long responses

---

## Security Considerations

### Current Status
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ No input sanitization
- ⚠️ Default database credentials

### Production Requirements
1. **Authentication:**
   - JWT tokens
   - OAuth2 integration
   - API keys

2. **Authorization:**
   - User-scoped chats
   - Role-based access
   - Resource ownership

3. **Input Validation:**
   - File size limits
   - File type verification
   - Request rate limiting

4. **Data Protection:**
   - Encrypted storage
   - Secure credentials
   - HTTPS only

---

## Scalability

### Current Limitations
- Single backend instance
- No horizontal scaling
- No load balancing
- Session affinity required (streaming)

### Scaling Strategy
1. **Horizontal Scaling:**
   - Stateless backend (database-backed sessions)
   - Load balancer with sticky sessions (SSE)
   - Shared file storage (S3/NFS)

2. **Database Scaling:**
   - Connection pooling
   - Read replicas
   - Partitioning by chat_id

3. **Caching Layer:**
   - Redis for embeddings
   - CDN for static assets

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Streamlit | Web UI |
| Backend | FastAPI | REST API |
| Database | PostgreSQL 14+ | Data storage |
| Vector Search | pgvector | Similarity search |
| LLM | Ollama (gemma3) | Chat completion |
| Embeddings | mxbai-embed-large | Text embeddings |
| Containerization | Docker Compose | Deployment |
| ORM | SQLAlchemy | Database access |
| Validation | Pydantic | Config & validation |

---

## Future Enhancements

### Near-Term
1. Input validation with Pydantic models
2. Enhanced health checks
3. Database connection pooling
4. Embedding cache

### Long-Term
1. Multi-user support with authentication
2. Document versioning
3. Multi-document chats
4. Export conversations
5. Advanced analytics
6. Mobile application

---

## Development Principles

1. **Code Quality:**
   - PEP 8 compliance
   - Type hints throughout
   - Comprehensive docstrings

2. **Maintainability:**
   - Clear separation of concerns
   - DRY principle
   - Consistent patterns

3. **Documentation:**
   - Inline comments for complex logic
   - API documentation
   - Architecture documentation

4. **Testing (Future):**
   - Unit tests for services
   - Integration tests for API
   - End-to-end tests

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Ollama Documentation](https://ollama.ai/docs)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Last Updated:** 2025-11-06
**Version:** 2.0.0
**Status:** Production-Ready (with security enhancements needed)
