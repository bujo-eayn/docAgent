# API Documentation - docAgent

Complete REST API documentation for the docAgent backend.

## Base URL

- **Development:** `http://localhost:8000`
- **Docker:** `http://backend:8000` (internal) or `http://localhost:8000` (external)

## Interactive Documentation

FastAPI provides automatic interactive documentation:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Endpoints Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chats/create` | POST | Upload document and create chat |
| `/chats/{chat_id}/message` | POST | Send message in chat |
| `/chats` | GET | List all chats |
| `/chats/{chat_id}` | GET | Get chat details |
| `/chats/{chat_id}` | DELETE | Delete chat |
| `/health` | GET | Health check |

---

## 1. Create Chat

Upload a document image and create a new chat session.

### Endpoint
```
POST /chats/create
```

### Request
**Content-Type:** `multipart/form-data`

**Parameters:**
- `file` (required): Image file to upload

**Supported Formats:**
- PNG (.png)
- JPEG (.jpg, .jpeg)
- WebP (.webp)

### Example Request
```bash
curl -X POST "http://localhost:8000/chats/create" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chart.png"
```

### Response
**Status:** 200 OK

```json
{
  "success": true,
  "chat_id": 1,
  "message": "Chat created and document processed successfully",
  "document_filename": "chart.png",
  "chunks_created": 15
}
```

### Process Flow
1. Document uploaded and saved with timestamp prefix
2. Chat record created in database
3. Document processed:
   - Information extracted using LLM
   - Text chunked into segments
   - Embeddings generated for each chunk
   - Chunks stored with embeddings
4. System message added to chat
5. Response returned with chat_id

### Error Responses

**400 Bad Request**
```json
{
  "detail": "No file provided"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Error processing document: [reason]"
}
```

---

## 2. Send Message

Send a question/message within a chat and receive streaming response.

### Endpoint
```
POST /chats/{chat_id}/message
```

### Request
**Content-Type:** `application/x-www-form-urlencoded`

**Path Parameters:**
- `chat_id` (integer): ID of the chat session

**Body Parameters:**
- `question` (string, required): User's question

### Example Request
```bash
curl -X POST "http://localhost:8000/chats/1/message" \
  -H "accept: text/event-stream" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "question=What are the key findings in this document?"
```

### Response
**Status:** 200 OK
**Content-Type:** `text/event-stream`

**Streaming Format:**
```
data: The
data:  key
data:  findings
data:  are
data: ...
data: {"final": "The key findings are...", "context": "[Relevance: 0.95]...", "chat_id": 1}
data: [DONE]
```

### Response Structure

**Token Stream:**
Each line contains a single token:
```
data: <token>

```

**Final Metadata:**
After all tokens, JSON metadata is sent:
```json
{
  "final": "Complete response text",
  "context": "Retrieved context chunks with relevance scores",
  "chat_id": 1
}
```

**End Marker:**
```
data: [DONE]

```

### Process Flow
1. User question saved as message
2. Question converted to embedding
3. Top-k relevant contexts retrieved (semantic search)
4. System prompt built with context
5. Response streamed from LLM
6. Complete response saved as assistant message
7. Metadata sent with context used

### Error Responses

**404 Not Found**
```json
{
  "detail": "Chat with ID 1 not found"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Error streaming response"
}
```

---

## 3. List All Chats

Retrieve all chat sessions, ordered by most recent.

### Endpoint
```
GET /chats
```

### Request
```bash
curl -X GET "http://localhost:8000/chats" \
  -H "accept: application/json"
```

### Response
**Status:** 200 OK

```json
[
  {
    "id": 2,
    "title": "Chat: sales_report.png",
    "document_filename": "sales_report.png",
    "created_at": "2025-11-06T10:30:00",
    "updated_at": "2025-11-06T11:45:00",
    "message_count": 8
  },
  {
    "id": 1,
    "title": "Chat: chart.png",
    "document_filename": "chart.png",
    "created_at": "2025-11-05T14:20:00",
    "updated_at": "2025-11-05T15:10:00",
    "message_count": 5
  }
]
```

### Response Fields
- `id`: Chat unique identifier
- `title`: Auto-generated title from filename
- `document_filename`: Original uploaded filename
- `created_at`: Chat creation timestamp (ISO 8601)
- `updated_at`: Last activity timestamp (ISO 8601)
- `message_count`: Number of messages in chat

### Notes
- Only active chats returned (soft-deleted excluded)
- Ordered by `updated_at` descending (most recent first)
- Empty array `[]` if no chats exist

---

## 4. Get Chat Details

Retrieve detailed information about a specific chat including all messages.

### Endpoint
```
GET /chats/{chat_id}
```

### Request
```bash
curl -X GET "http://localhost:8000/chats/1" \
  -H "accept: application/json"
```

### Response
**Status:** 200 OK

```json
{
  "id": 1,
  "title": "Chat: chart.png",
  "document_filename": "chart.png",
  "created_at": "2025-11-05T14:20:00",
  "updated_at": "2025-11-05T15:10:00",
  "message_count": 5,
  "messages": [
    {
      "id": 1,
      "role": "system",
      "content": "Document 'chart.png' uploaded and processed. Extracted 15 context chunks. Ready for questions!",
      "context_used": null,
      "created_at": "2025-11-05T14:20:15"
    },
    {
      "id": 2,
      "role": "user",
      "content": "What are the main trends shown?",
      "context_used": null,
      "created_at": "2025-11-05T14:21:00"
    },
    {
      "id": 3,
      "role": "assistant",
      "content": "The main trends shown in the document are...",
      "context_used": "[Relevance: 0.95]\nThe chart shows upward trend...\n\n---\n\n[Relevance: 0.87]\nKey metrics indicate...",
      "created_at": "2025-11-05T14:21:05"
    }
  ]
}
```

### Message Roles
- `system`: System notifications (document processing status)
- `user`: User questions
- `assistant`: AI responses

### Error Responses

**404 Not Found**
```json
{
  "detail": "Chat with ID 999 not found"
}
```

---

## 5. Delete Chat

Delete a chat session (soft delete).

### Endpoint
```
DELETE /chats/{chat_id}
```

### Request
```bash
curl -X DELETE "http://localhost:8000/chats/1" \
  -H "accept: application/json"
```

### Response
**Status:** 200 OK

```json
{
  "success": true,
  "message": "Chat deleted"
}
```

### Notes
- Soft delete: Sets `is_active=False`
- Associated messages and contexts preserved in database
- Chat won't appear in list or be accessible
- Can be recovered by database administrator if needed

### Error Responses

**404 Not Found**
```json
{
  "detail": "Chat with ID 999 not found"
}
```

---

## 6. Health Check

Check if the API is running and healthy.

### Endpoint
```
GET /health
```

### Request
```bash
curl -X GET "http://localhost:8000/health" \
  -H "accept: application/json"
```

### Response
**Status:** 200 OK

```json
{
  "status": "healthy"
}
```

### Use Cases
- Container orchestration health checks
- Load balancer health probes
- Monitoring systems
- Smoke tests

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input (missing file, invalid parameters) |
| 404 | Not Found | Chat ID doesn't exist |
| 500 | Internal Server Error | Server-side processing error |

### Custom Exception Details
Some exceptions include additional details:

```json
{
  "detail": "Chat with ID 1 not found",
  "chat_id": 1
}
```

```json
{
  "detail": "Failed to process document 'chart.png': Extraction failed",
  "filename": "chart.png",
  "reason": "Extraction failed"
}
```

---

## Rate Limiting

**Current Status:** No rate limiting implemented

**Production Recommendations:**
- Implement rate limiting per IP/user
- Suggested limits:
  - Document upload: 5 per minute
  - Messages: 20 per minute
  - List operations: 60 per minute

---

## Authentication

**Current Status:** No authentication required

**Production Recommendations:**
- Implement JWT or OAuth2 authentication
- Add API key support for programmatic access
- Role-based access control for multi-tenant scenarios

---

## Data Models

### Chat Object
```typescript
{
  id: integer,
  title: string,
  document_filename: string,
  created_at: string (ISO 8601),
  updated_at: string (ISO 8601),
  message_count: integer
}
```

### Message Object
```typescript
{
  id: integer,
  role: "system" | "user" | "assistant",
  content: string,
  context_used: string | null,
  created_at: string (ISO 8601)
}
```

### Context Chunk (Internal)
```typescript
{
  id: integer,
  chat_id: integer,
  content: string,
  embedding: float[1024],
  chunk_index: integer,
  created_at: string (ISO 8601)
}
```

---

## Streaming Response Details

### Server-Sent Events (SSE)
The `/chats/{chat_id}/message` endpoint uses SSE format:

**Format:**
```
data: <content>

```

**Key Points:**
- Each event starts with `data:`
- Followed by content
- Ended with double newline `\n\n`
- Final event is `data: [DONE]\n\n`

### Example Client (JavaScript)
```javascript
const eventSource = new EventSource(
  `http://localhost:8000/chats/1/message?question=${encodeURIComponent(question)}`
);

eventSource.onmessage = (event) => {
  if (event.data === "[DONE]") {
    eventSource.close();
  } else {
    console.log(event.data);
  }
};
```

### Example Client (Python)
```python
import requests

url = "http://localhost:8000/chats/1/message"
data = {"question": "What are the key findings?"}

with requests.post(url, data=data, stream=True) as response:
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('data:'):
                content = decoded[5:].strip()
                if content == "[DONE]":
                    break
                print(content, end='', flush=True)
```

---

## Configuration

### Timeouts
- Document extraction: 360 seconds
- Chat streaming: 300 seconds
- Embedding generation: 30 seconds

### Limits
- Chunk size: 500 characters
- Chunk overlap: 50 characters
- Top-k contexts: 3 per query
- Embedding dimensions: 1024

### Models
- Chat model: `gemma3`
- Embedding model: `mxbai-embed-large`

---

## Testing the API

### Using curl
```bash
# Create chat
curl -X POST http://localhost:8000/chats/create \
  -F "file=@document.png"

# Send message
curl -X POST "http://localhost:8000/chats/1/message" \
  -d "question=Summarize this document"

# List chats
curl http://localhost:8000/chats

# Get chat details
curl http://localhost:8000/chats/1

# Delete chat
curl -X DELETE http://localhost:8000/chats/1
```

### Using Python requests
```python
import requests

# Create chat
with open('document.png', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/chats/create',
        files=files
    )
    chat_id = response.json()['chat_id']

# Send message
data = {'question': 'What does this show?'}
response = requests.post(
    f'http://localhost:8000/chats/{chat_id}/message',
    data=data,
    stream=True
)
for line in response.iter_lines():
    print(line.decode('utf-8'))
```

---

## Next Steps

- [Setup Guide](setup.md) - Installation instructions
- [Docker Guide](docker.md) - Docker deployment
- [README](../README.md) - Project overview
