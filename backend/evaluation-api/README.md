# ADAM Evaluation API Service

FastAPI service for running ADAM agent evaluations. This service calls the ADAM API service via HTTP instead of directly using the graph system, providing better separation of concerns and independent scaling.

## Features

- **HTTP-based**: Calls ADAM API service instead of direct graph access
- **Google Sheets Integration**: Reads test cases and writes results back
- **LLM Judge**: Evaluates ADAM responses using Gemini Flash
- **Environment Configuration**: Uses environment variables for user_email and partner
- **Async Evaluation**: Runs evaluations asynchronously in the background
- **Robust Timeouts**: 10-minute timeout for complex queries with code execution

## Architecture

```
evaluation-api (Port 8001)
    ↓ HTTP calls
adam-api (Port 8000)
    ↓ processes
ADAM Graph System
```

## Environment Variables

### Required Configuration

```bash
# ADAM API Configuration
ADAM_API_URL=http://adam-api:8000  # Default for docker-compose
ADAM_API_TIMEOUT=600                # Request timeout in seconds (10 minutes for complex queries)

# Evaluation Configuration
EVAL_USER_EMAIL=lorenzo@virtuology.com  # User email for evaluation sessions
EVAL_PARTNER_NAME=partner_1             # Partner name for evaluation context

# Google Sheets Configuration
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit
EVAL_SHEET_NAME=GOLDEN SET - EVAL

# Google Cloud Credentials
# Uses Application Default Credentials (ADC)
# For local development: Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# For Cloud Run: Attach service account with Sheets API access
```

### Configuration Priority

1. **Environment Variables** (highest priority)
2. **API Request Parameters** (overrides env vars for that request)
3. **Code Defaults** (fallback)

## API Endpoints

### POST `/evaluation/run`

Run the ADAM evaluation pipeline.

**Request Body:**
```json
{
  "preview_only": false,
  "dry_run": false,
  "user_email": "optional@email.com",  // Optional, defaults to EVAL_USER_EMAIL
  "partner": "optional_partner"          // Optional, defaults to EVAL_PARTNER_NAME
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Evaluation pipeline started in background",
  "timestamp": "2024-01-01T00:00:00",
  "user_email": "lorenzo@virtuology.com",
  "partner": "partner_1",
  "preview_only": false,
  "dry_run": false,
  "note": "Check the backend logs for progress. Results will be written to Google Sheet when complete."
}
```

**Notes:**
- Evaluation runs asynchronously in a background thread
- Check logs for real-time progress
- Results are written to Google Sheet as they complete
- Each test case is processed sequentially

### GET `/evaluation/status`

Check evaluation system status.

**Response:**
```json
{
  "adam_api_available": true,
  "credentials_configured": true,
  "ready": true,
  "timestamp": "2024-01-01T00:00:00"
}
```

**Status Fields:**
- `adam_api_available`: Whether ADAM API is reachable and healthy
- `credentials_configured`: Whether Google Application Default Credentials are available
- `ready`: Both ADAM API and credentials must be available
- `timestamp`: Current timestamp

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "evaluation-api",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Running Locally

### 1. Install Dependencies

```bash
cd backend/evaluation-api
uv sync
```

### 2. Set Environment Variables

```bash
export ADAM_API_URL=http://localhost:8000
export EVAL_USER_EMAIL=your@email.com
export EVAL_PARTNER_NAME=partner_1
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/...
export EVAL_SHEET_NAME=GOLDEN SET - EVAL
```

### 3. Run the Service

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Running with Docker Compose

The service is configured in `backend/docker-compose.yml`:

```bash
# Start both services
cd backend
docker-compose up

# Start only evaluation-api (requires adam-api to be running)
docker-compose up evaluation-api
```

The service will:
- Automatically connect to `adam-api` service via Docker network
- Wait for `adam-api` to be healthy before starting
- Use environment variables from `.env` file

### Docker Compose Configuration

```yaml
evaluation-api:
  build:
    context: ./evaluation-api
    dockerfile: Dockerfile
  ports:
    - "8001:8001"
  env_file:
    - .env
  environment:
    - ADAM_API_URL=http://adam-api:8000
  depends_on:
    adam-api:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Evaluation Flow

1. **Read Test Cases**: Reads from Google Sheet (`GOLDEN SET - EVAL` tab)
2. **Filter**: Only processes rows where `USE FOR EVALS` = "YES"
3. **Reset Conversation**: Resets ADAM conversation for clean slate (per user-partner)
4. **For Each Test Case**:
   - Call ADAM API with reference input
   - Get ADAM's response (with 10-minute timeout for complex queries)
   - Evaluate response using LLM judge (Gemini Flash)
   - Write results back to Google Sheet (unless `dry_run=true`)
5. **Summary**: Logs evaluation statistics including:
   - Total evaluations completed
   - Average score
   - Score range
   - Pass rate (≥70)
   - Score distribution

## Google Sheet Format

The evaluation sheet should have these columns:

### Input Columns
- `REFERENCE INPUT`: The question/input for ADAM
- `REFERENCE OUTPUT / EVALUATION INSTRUCTION`: Expected output or evaluation criteria
- `USE FOR EVALS`: "YES" to include in evaluation, "NO" to skip

### Output Columns (Written by Evaluation)
- `CURRENT ADAM RESPONSE`: ADAM's actual response
- `AUTO SCORE`: Score from 0-100 assigned by LLM judge
- `FEEDBACK JUDGE LLM`: Detailed feedback from the LLM judge

### Example Row

| REFERENCE INPUT | REFERENCE OUTPUT / EVALUATION INSTRUCTION | USE FOR EVALS | CURRENT ADAM RESPONSE | AUTO SCORE | FEEDBACK JUDGE LLM |
|----------------|-------------------------------------------|---------------|----------------------|------------|-------------------|
| How many line items do I have? | Should return a count of line items | YES | You have 15 active line items... | 95 | The response accurately answers the question... |

## Configuration

### User Email and Partner

Configure via environment variables in `.env` file:

```bash
EVAL_USER_EMAIL=your@email.com
EVAL_PARTNER_NAME=your_partner_name
```

Or override per request in the API call:

```json
{
  "user_email": "custom@email.com",
  "partner": "custom_partner"
}
```

### Timeout Configuration

Default timeout is 600 seconds (10 minutes) to handle complex queries that involve:
- Code generation
- Code execution
- Data processing
- Multiple agent interactions

To change the timeout:

```bash
export ADAM_API_TIMEOUT=900  # 15 minutes
```

## Differences from Direct Graph Access

**Before (Direct Import):**
- Imported graph system directly
- Used LangGraph invoke directly
- Required all ADAM dependencies
- Tight coupling between services

**Now (HTTP-based):**
- Calls ADAM API via HTTP
- No direct graph dependencies
- Lighter service, better separation of concerns
- Can scale independently
- Easier to test and maintain

## Error Handling

The service includes robust error handling:

- **ADAM API Timeouts**: 10-minute timeout with proper error messages
- **Connection Errors**: Retries and clear error reporting
- **Google Sheets Errors**: Graceful handling with detailed logs
- **LLM Judge Errors**: Fallback handling for evaluation failures

## Monitoring

### Logs

The service provides detailed logging:
- Evaluation start/completion
- Test case progress
- ADAM API calls
- LLM judge evaluations
- Google Sheets operations
- Errors and warnings

### Health Checks

- `/health`: Basic service health
- `/evaluation/status`: Detailed system status including ADAM API connectivity

## Troubleshooting

### Common Issues

1. **ADAM API not reachable**: 
   - Check `ADAM_API_URL` is correct
   - Verify `adam-api` service is running
   - Check Docker network connectivity

2. **Google Sheets access errors**:
   - Verify `GOOGLE_APPLICATION_CREDENTIALS` is set
   - Check service account has Sheets API access
   - Verify sheet URL and name are correct

3. **Evaluation stops unexpectedly**:
   - Check timeout settings (default 10 minutes)
   - Review logs for errors
   - Verify ADAM API is responding

4. **Results not written to sheet**:
   - Check `dry_run` is not set to `true`
   - Verify Google Sheets permissions
   - Check logs for write errors

### Debug Commands

```bash
# Check service logs
docker-compose logs -f evaluation-api

# Test health endpoint
curl http://localhost:8001/health

# Check evaluation status
curl http://localhost:8001/evaluation/status

# Test ADAM API connectivity
curl http://adam-api:8000/health
```

## API Documentation

Once running, visit http://localhost:8001/docs for interactive API documentation powered by Swagger UI.

## License

This project is proprietary to Adam Setup.
