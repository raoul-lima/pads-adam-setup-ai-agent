from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import logging
from contextlib import asynccontextmanager
import asyncio

from utils.constants import USE_POSTGRES_STORAGE, POSTGRES_CONFIG
from utils.postgres_storage import PostgreSQLStorage

# Add backend root to Python path
backend_root = str(Path(__file__).parent.parent)
if backend_root not in sys.path:
    sys.path.append(backend_root)

from graph_system.initializer import graph_init
from config.configs import load_metadata_from_json
from agents.memory_agent import shutdown_memory_executor

# Import route modules
from routes import chat_router, feedback_router, data_router, health_router
import routes.chat as chat_routes
import routes.feedback as feedback_routes
import routes.health as health_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singletons for Cloud Run optimization
_compiled_graph = None
_metadata = None
_storage = None

def get_metadata():
    """Get or load metadata (lazy loading to avoid import-time GCS calls)"""
    global _metadata
    if _metadata is None:
        logger.info("📚 Loading metadata from GCS...")
        _metadata = load_metadata_from_json()
        logger.info("✅ Metadata loaded")
    return _metadata

def get_storage():
    """Get or create PostgreSQL storage (singleton pattern)"""
    global _storage
    if _storage is None and USE_POSTGRES_STORAGE:
        logger.info("🗄️  Initializing PostgreSQL storage...")
        _storage = PostgreSQLStorage(POSTGRES_CONFIG)
        logger.info("✅ PostgreSQL storage initialized")
    return _storage

def get_graph():
    """Get or create the compiled graph (singleton pattern)
    
    CRITICAL for Cloud Run: Compiling graph on every request causes:
    - Slow cold starts (2-3s per request)
    - High memory usage
    - Poor concurrency performance
    
    This singleton compiles ONCE and reuses across requests.
    """
    global _compiled_graph
    if _compiled_graph is None:
        logger.info("🔧 Compiling LangGraph (one-time operation)...")
        _compiled_graph = graph_init()
        logger.info("✅ Graph compiled and cached")
    return _compiled_graph

# Background warmup flag
_warmup_done = False

async def background_warmup():
    """Warm up in background after startup to avoid blocking health checks"""
    global _warmup_done
    try:
        logger.info("🔥 Starting background warmup...")
        
        # Load metadata first (required for graph compilation)
        _ = get_metadata()
        logger.info("✅ Metadata loaded")
        
        # Compile graph
        _ = get_graph()
        logger.info("✅ Graph compiled")
        
        # Warm up LLM (optional)
        try:
            from config.configs import llm_gemini_flash
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: llm_gemini_flash.invoke("ping")
            )
            logger.info("✅ LLM connection warmed")
        except Exception as e:
            logger.warning(f"⚠️ LLM warmup skipped: {e}")
        
        _warmup_done = True
        logger.info("✅ Background warmup complete")
    except Exception as e:
        logger.error(f"❌ Background warmup failed: {e}")
        _warmup_done = True  # Set to true anyway to not block

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - don't block on warmup!
    logger.info("🚀 Application startup (fast mode)")
    
    # Start warmup in background (non-blocking)
    # This will load metadata and compile graph
    asyncio.create_task(background_warmup())
    
    logger.info("✅ Application ready to serve requests (warmup in background)")
    yield
    
    # Shutdown
    shutdown_memory_executor()
    logger.info("🛑 Application shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Adam Setup Multi-Agent API",
    description="""
    ## Adam Setup Multi-Agent System API
    
    This API provides endpoints for interacting with the Adam Setup multi-agent system 
    designed for DV360 data analysis and setup automation.
    
    ### Key Features:
    - **Chat Interface**: Process messages through the multi-agent system
    - **Conversation Management**: Maintain conversation history and context
    - **Feedback System**: Collect user feedback for continuous improvement
    - **Health Monitoring**: System health and configuration endpoints
    
    ### Authentication:
    All endpoints require user email identification for conversation tracking and personalization.
    """,
    version="0.9.2",
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

# Initialize route dependencies
chat_routes.init_dependencies(get_graph, get_metadata)
feedback_routes.init_dependencies(get_storage)
health_routes.init_dependencies(_warmup_done)

# Include routers
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(data_router)
app.include_router(health_router)

logger.info("✅ All routes registered successfully")
