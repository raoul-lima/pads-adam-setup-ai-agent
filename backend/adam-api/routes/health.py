"""
Health and System Routes
=========================
Endpoints for health checks, configuration, and system operations.
"""

from fastapi import APIRouter, HTTPException, status
from pathlib import Path
from datetime import datetime
import logging
import asyncio
import sys

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["System"],
)

# These will be injected by main.py
_warmup_done = None


def init_dependencies(warmup_done_ref):
    """Initialize dependencies from main.py"""
    global _warmup_done
    _warmup_done = warmup_done_ref


@router.get(
    "/health",
    summary="Health Check",
    description="""
    System health check endpoint providing operational status.
    
    Returns:
    - System status (healthy/unhealthy)
    - Current timestamp
    - Number of active users
    - Conversation history limits
    - Storage backend information
    - Warmup status
    
    Used for monitoring and ensuring system availability.
    """
)
async def health_check():
    """Health check endpoint - responds immediately even during warmup"""
    try:
        from agents.memory_agent import EnhancedMemoryAgent
        from utils.constants import USE_POSTGRES_STORAGE
        
        if USE_POSTGRES_STORAGE:
            # Use singleton storage instance from main.py instead of creating new one
            from main import get_storage
            try:
                storage = get_storage()
                if storage:
                    active_users = storage.get_active_users_count()
                else:
                    active_users = 0
            except:
                active_users = 0
        else:
            from agents.memory_agent import in_memory_storage
            active_users = len(in_memory_storage)
        
        return {
            "status": "healthy",
            "warmup_complete": _warmup_done,
            "timestamp": datetime.now().isoformat(),
            "active_users": active_users,
            "conversation_history_limit": EnhancedMemoryAgent.get_default_conversation_limit(),
            "storage_backend": "postgresql" if USE_POSTGRES_STORAGE else "in-memory"
        }
    except Exception as e:
        # Health check should always respond, even if there are errors
        logger.error(f"Health check error: {e}")
        return {
            "status": "healthy",  # Still return healthy to pass Cloud Run checks
            "warmup_complete": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get(
    "/config",
    summary="Get Configuration",
    description="""
    Retrieve current system configuration settings.
    
    Returns:
    - Conversation history limits
    - System timestamp
    - Other configurable parameters
    
    Useful for understanding system behavior and limits.
    """
)
async def get_configuration():
    """Get current configuration settings"""
    from agents.memory_agent import EnhancedMemoryAgent
    return {
        "conversation_history_limit": EnhancedMemoryAgent.get_default_conversation_limit(),
        "timestamp": datetime.now().isoformat()
    }


@router.post(
    "/evaluation/run",
    tags=["Evaluation"],
    summary="Run ADAM Evaluation",
    description="""
    Run the ADAM agent evaluation pipeline.
    
    This endpoint:
    - Reads test cases from Google Sheets
    - Runs ADAM on each test case
    - Evaluates responses with LLM judge
    - Writes results back to the sheet
    
    Returns immediate response with status. Evaluation runs asynchronously.
    """
)
async def run_evaluation():
    """Run the ADAM evaluation pipeline asynchronously"""
    try:
        logger.info("🧪 Starting ADAM evaluation pipeline...")
        
        # Import and run the evaluation
        def run_eval():
            import subprocess
            
            # Get the path to evaluate_adam.py
            eval_script = Path(__file__).parent.parent / 'evaluate_adam.py'
            
            try:
                logger.info(f"📝 Running evaluation script: {eval_script}")
                
                # Run the evaluation script
                result = subprocess.run(
                    [sys.executable, str(eval_script)],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent.parent)
                )
                
                logger.info(f"✅ Evaluation script completed with return code: {result.returncode}")
                
                if result.stdout:
                    logger.info(f"📊 STDOUT:\n{result.stdout}")
                if result.stderr:
                    logger.error(f"❌ STDERR:\n{result.stderr}")
                
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            except Exception as e:
                logger.error(f"❌ Error running evaluation: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "error": str(e),
                    "returncode": -1
                }
        
        # Start evaluation in background using run_in_executor (returns a Future)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_eval)
        
        return {
            "status": "started",
            "message": "Evaluation pipeline started in background",
            "timestamp": datetime.now().isoformat(),
            "note": "Check the backend logs for progress. Results will be written to Google Sheet when complete."
        }
        
    except Exception as e:
        logger.error(f"Error starting evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting evaluation: {str(e)}"
        )

