"""
Evaluation API Service
======================
FastAPI service for running ADAM agent evaluations.
Calls the ADAM API service via HTTP instead of directly using the graph.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from routes.evaluation import router as evaluation_router
from routes.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Evaluation API Service starting up...")
    
    # Reset evaluation state on startup to handle cases where container was stopped
    # while evaluation was running
    try:
        from services.evaluation_state_db import EvaluationStateManagerDB
        state_manager = EvaluationStateManagerDB()
        state_manager.reset_on_startup()
    except Exception as e:
        logger.warning(f"⚠️ Could not reset evaluation state on startup: {e}")
    
    yield
    logger.info("🛑 Evaluation API Service shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="ADAM Evaluation API",
    description="""
    ## ADAM Evaluation API Service
    
    This service evaluates the ADAM agent using test cases from Google Sheets.
    It calls the ADAM API service via HTTP and evaluates responses using an LLM-as-a-judge.
    
    ### Key Features:
    - **Evaluation Pipeline**: Run evaluations on test cases from Google Sheets
    - **LLM Judge**: Evaluates ADAM responses using Gemini Flash
    - **Google Sheets Integration**: Reads test cases and writes results back
    - **HTTP-based**: Calls ADAM API service instead of direct graph access
    """,
    version="0.1.0",
    lifespan=lifespan,
    contact={
        "name": "Adam Setup Team",
        "email": "support@adamsetup.com"
    },
    license_info={
        "name": "Proprietary",
        "identifier": "Proprietary"
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(evaluation_router)
app.include_router(health_router)

logger.info("✅ Evaluation API Service initialized successfully")
