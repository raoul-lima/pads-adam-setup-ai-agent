# ADAM API Service

FastAPI-based REST API for the ADAM multi-agent system, designed for DV360 data analysis and automated setup insights.

## 🏗️ Architecture

The API is built with:
- **FastAPI**: Modern, fast web framework for building APIs
- **LangGraph**: Stateful, multi-agent AI workflow orchestration
- **PostgreSQL**: Database for conversation history and user preferences
- **Google Cloud Storage**: Data storage for CSV files and metadata
- **Docker**: Containerized deployment
- **uv**: Fast Python package manager

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)
- Google Cloud credentials (for GCS access)

### 1. Start with Docker Compose

```bash
cd backend
docker-compose up adam-api
```

This will:
- Build the Docker image
- Start the service on port 8000
- Initialize PostgreSQL tables automatically
- Set up health checks

### 2. Access the API

- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Chat System
- `POST /chat/message` - Send message to multi-agent system
  - Requires: `content`, `user_email`, `partner`
  - Returns: AI response with conversation_id and download links

- `POST /chat/reset` - Reset conversation for a user-partner combination
  - Requires: `user_email`, `partner`
  - Clears conversation history

- `GET /chat/history` - Get conversation history
  - Query params: `user_email`, `partner`
  - Returns: Conversation messages and metadata

### Feedback System
- `GET /feedback` - Get user feedback with filters
  - Query params: `offset`, `limit`, `sentiment`, `status`, `partner_name`, `user_email`, `start_date`, `end_date`
  
- `POST /feedback` - Submit user feedback
  - Requires: `user_email`, `partner`, `user_query`, `ai_response`, `feedback`, `sentiment`

- `GET /feedback/stats` - Get feedback statistics
  - Query params: `partner_name`, `start_date`, `end_date`

- `PUT /feedback/{feedback_id}/status` - Update feedback status
- `PUT /feedback/{feedback_id}/notes` - Update feedback notes
- `DELETE /feedback/{feedback_id}` - Delete feedback

### Data Operations
- `GET /data/csv-preview` - Preview CSV files from GCS
  - Query params: `url` (GCS signed URL), `offset`, `limit`

### System
- `GET /health` - Health check endpoint
  - Returns: Service status, active users count, storage backend info

- `GET /config` - Get system configuration

## 🔐 Authentication & User Context

The API uses user email and partner name for conversation tracking:

```json
{
  "content": "How many line items do I have?",
  "user_email": "user@example.com",
  "partner": "partner_1"
}
```

Each user-partner combination maintains its own isolated conversation history.

## 🐳 Docker Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# PostgreSQL Configuration
POSTGRES_USER=adam_user
POSTGRES_PASSWORD=adam_password_2024
POSTGRES_DB=adam_security
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
USE_POSTGRES_STORAGE=true

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
GCS_BUCKET_NAME=your-gcs-bucket-name
DATA_BUCKET_NAME=your-data-bucket-name

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Gemini Configuration (for LLM judge)
GEMINI_API_KEY=your_gemini_api_key_here

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Docker Compose Service

```yaml
adam-api:
  build:
    context: ./adam-api
    dockerfile: Dockerfile
  ports:
    - "8000:8000"
  env_file:
    - .env
  volumes:
    - ./adam-api/local_data:/app/local_data
    - ./adam-api/logs:/app/logs
    - ./adam-api/credentials.json:/app/credentials.json:ro
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## 🛠️ Local Development

### Setup

```bash
# Install uv package manager
./install-uv.sh

# Or install manually
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd backend/adam-api
uv sync

# Set environment variables
export POSTGRES_USER=adam_user
export POSTGRES_PASSWORD=adam_password_2024
export POSTGRES_DB=adam_security
export POSTGRES_HOST=localhost
export USE_POSTGRES_STORAGE=true
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Run Locally

```bash
# Run with uvicorn
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or run directly
uv run python main.py
```

## 📊 Database Schema

### adam_conversations Table
- `conversation_id`: UUID primary key (auto-generated)
- `user_id`: VARCHAR(255) - Unique user identifier (hash of email)
- `user_email`: VARCHAR(255) - User's email address
- `partner_name`: VARCHAR(255) - Partner name for context isolation
- `created_at`: TIMESTAMP - Creation timestamp
- `updated_at`: TIMESTAMP - Last update timestamp
- Unique constraint on (`user_id`, `partner_name`)

### adam_messages Table
- `message_id`: UUID primary key (auto-generated)
- `conversation_id`: UUID - Foreign key to adam_conversations
- `message_type`: VARCHAR(50) - Message type (human, ai, system)
- `content`: TEXT - Message content
- `metadata`: JSONB - Message metadata
- `timestamp`: TIMESTAMP - Message timestamp
- `additional_kwargs`: JSONB - Additional message properties

### adam_user_preferences Table
- `user_id`: VARCHAR(255) - Primary key
- `user_email`: VARCHAR(255) - User's email
- `preferences`: JSONB - User preferences (long-term memory)
- `updated_at`: TIMESTAMP - Last update timestamp

### adam_feedback Table
- `feedback_id`: UUID primary key
- `user_email`: VARCHAR(255) - User email
- `partner_name`: VARCHAR(255) - Partner name
- `agent_name`: VARCHAR(100) - Agent name (default: "Adam Setup")
- `user_query`: TEXT - Original user query
- `ai_response`: TEXT - AI's response
- `feedback`: TEXT - User feedback text
- `sentiment`: VARCHAR(20) - positive, negative, or neutral
- `status`: VARCHAR(20) - To Consider, Considered, or Ignored
- `notes`: TEXT - Admin notes
- `created_at`: TIMESTAMP - Creation timestamp
- `metadata`: JSONB - Additional metadata

## 🔧 Management Commands

### View Logs
```bash
docker-compose logs -f adam-api
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart adam-api
```

### Database Access
```bash
# If using docker-compose with postgres service
docker-compose exec postgres psql -U adam_user -d adam_security

# Or connect directly
psql -h localhost -U adam_user -d adam_security
```

### Initialize Database Tables
```bash
# Tables are auto-initialized on first PostgreSQLStorage creation
# Or manually run:
uv run python utils/init_postgres_db.py
```

## 🧠 Multi-Agent System

The ADAM system uses a LangGraph-based multi-agent architecture:

1. **Language Detector**: Detects user's preferred language
2. **Intent Classifier**: Classifies user intent and fetches relevant context
3. **Analyser Agent**: Analyzes the request and determines required data
4. **Code Generator**: Generates Python code for data analysis
5. **Code Executor**: Executes generated code safely
6. **Final Response Agent**: Formats and presents the final response
7. **Memory Agent**: Manages conversation history and user preferences

## 🔒 Security Features

- **Input Validation**: Pydantic models for request/response validation
- **CORS**: Configurable cross-origin resource sharing
- **User Isolation**: Conversations isolated by user-partner combination
- **Safe Code Execution**: Sandboxed Python code execution
- **PostgreSQL Storage**: Secure database storage with connection pooling

## 📈 Monitoring

### Health Checks
- **API**: `GET /health` - Returns service status, active users, storage backend
- **Database**: Auto-initialized tables with health monitoring
- **Cloud Run**: Optimized for Cloud Run with singleton patterns

### Performance Optimizations
- **Singleton Graph**: Compiled once at startup (not per request)
- **Lazy Metadata Loading**: Metadata loaded on first use
- **PostgreSQL Connection Pooling**: Efficient database connections
- **Async Processing**: Non-blocking conversation history saving

## 🚀 Production Deployment

### Cloud Run Considerations

The service is optimized for Cloud Run:
- Singleton patterns prevent recompilation on each request
- Background warmup for faster cold starts
- Health checks configured for Cloud Run
- Efficient resource usage

### Environment Security
- Use strong database passwords
- Configure CORS origins properly
- Use environment-specific configurations
- Secure Google Cloud credentials

## 🐛 Troubleshooting

### Common Issues

1. **Database connection errors**: Check PostgreSQL is running and credentials are correct
2. **GCS access errors**: Verify `GOOGLE_APPLICATION_CREDENTIALS` path and permissions
3. **Graph compilation errors**: Check OpenAI API key and metadata availability
4. **Port conflicts**: Change port in docker-compose.yml

### Debug Commands

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs adam-api

# Access container shell
docker-compose exec adam-api bash

# Test database connection
docker-compose exec postgres pg_isready -U adam_user

# Check health endpoint
curl http://localhost:8000/health
```

## 📝 API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation powered by Swagger UI.

## 📄 License

This project is proprietary to Adam Setup.
