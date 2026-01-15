"""
Database-backed Evaluation State Manager
========================================
PostgreSQL-based state manager for tracking evaluation status and progress.
Works across multiple instances/replicas in production.
"""

import logging
import os
from typing import Optional, Dict, Any
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class EvaluationStatus(str, Enum):
    """Evaluation status enum"""
    IDLE = "idle"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationStateManagerDB:
    """
    Database-backed state manager for evaluation state.
    
    Uses PostgreSQL to store state, allowing it to work across multiple instances.
    Only one evaluation can run at a time (enforced by database).
    """
    
    def __init__(self):
        """Initialize database connection configuration"""
        self.connection_config = {
            "host": os.getenv("POSTGRES_HOST", "35.205.161.122"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "adsecura_testing"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD")
        }
        self._init_database()
    
    @staticmethod
    def _get_default_state() -> Dict[str, Any]:
        """Get default evaluation state dictionary"""
        return {
            "status": "idle",
            "current_test_case": 0,
            "total_test_cases": 0,
            "percentage": 0.0,
            "current_step": "",
            "start_time": None,
            "end_time": None,
            "elapsed_seconds": None,
            "error_message": None,
            "user_email": None,
            "partner": None,
            "preview_only": False,
            "dry_run": False,
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.connection_config['host'],
                port=self.connection_config.get('port', 5432),
                database=self.connection_config['database'],
                user=self.connection_config['user'],
                password=self.connection_config['password']
            )
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize evaluation_state table if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS evaluation_state (
                            id INTEGER PRIMARY KEY DEFAULT 1,
                            status VARCHAR(20) NOT NULL DEFAULT 'idle',
                            current_test_case INTEGER NOT NULL DEFAULT 0,
                            total_test_cases INTEGER NOT NULL DEFAULT 0,
                            percentage DECIMAL(5,2) NOT NULL DEFAULT 0,
                            current_step TEXT DEFAULT '',
                            start_time TIMESTAMP,
                            end_time TIMESTAMP,
                            error_message TEXT,
                            user_email VARCHAR(255),
                            partner VARCHAR(255),
                            preview_only BOOLEAN DEFAULT FALSE,
                            dry_run BOOLEAN DEFAULT FALSE,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT single_evaluation CHECK (id = 1)
                        )
                    """)
                    
                    # Create index for faster lookups
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_evaluation_state_status 
                        ON evaluation_state(status)
                    """)
                    
                    # Ensure there's exactly one row (singleton pattern in database)
                    cursor.execute("""
                        INSERT INTO evaluation_state (id, status) 
                        VALUES (1, 'idle')
                        ON CONFLICT (id) DO NOTHING
                    """)
                    
                    logger.info("✅ Evaluation state table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize evaluation state table: {e}")
            raise
    
    def start_evaluation(
        self,
        total_test_cases: int,
        user_email: str,
        partner: str,
        preview_only: bool = False,
        dry_run: bool = False
    ) -> bool:
        """
        Start a new evaluation.
        
        Args:
            total_test_cases: Total number of test cases to evaluate
            user_email: User email for evaluation
            partner: Partner name for evaluation
            preview_only: Whether this is a preview-only run
            dry_run: Whether this is a dry run
            
        Returns:
            True if evaluation started, False if one is already ongoing
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if evaluation is already ongoing
                    cursor.execute("""
                        SELECT status FROM evaluation_state WHERE id = 1
                    """)
                    result = cursor.fetchone()
                    if result and result[0] == 'ongoing':
                        logger.warning("Cannot start evaluation: one is already ongoing")
                        return False
                    
                    # Start evaluation
                    cursor.execute("""
                        UPDATE evaluation_state SET
                            status = 'ongoing',
                            current_test_case = 0,
                            total_test_cases = %s,
                            percentage = 0,
                            current_step = 'Initializing evaluation...',
                            start_time = CURRENT_TIMESTAMP,
                            end_time = NULL,
                            error_message = NULL,
                            user_email = %s,
                            partner = %s,
                            preview_only = %s,
                            dry_run = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """, (total_test_cases, user_email, partner, preview_only, dry_run))
                    
                    logger.info(f"✅ Evaluation started: {total_test_cases} test cases")
                    return True
        except Exception as e:
            logger.error(f"Error starting evaluation: {e}")
            return False
    
    def update_progress(
        self,
        current_test_case: int,
        step_description: str = ""
    ):
        """
        Update evaluation progress.
        
        Args:
            current_test_case: Current test case number (1-indexed, represents completed cases)
            step_description: Description of current step
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get current total_test_cases
                    cursor.execute("""
                        SELECT total_test_cases FROM evaluation_state WHERE id = 1
                    """)
                    result = cursor.fetchone()
                    total_test_cases = result[0] if result else 0
                    
                    # Ensure current_test_case doesn't exceed total
                    current_test_case = min(current_test_case, total_test_cases)
                    
                    # Calculate percentage
                    percentage = (current_test_case / total_test_cases * 100) if total_test_cases > 0 else 0
                    
                    # Update progress
                    cursor.execute("""
                        UPDATE evaluation_state SET
                            current_test_case = %s,
                            percentage = %s,
                            current_step = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1 AND status = 'ongoing'
                    """, (current_test_case, percentage, step_description))
                    
                    logger.info(f"📊 Progress: {current_test_case}/{total_test_cases} ({percentage:.1f}%) - {step_description}")
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def complete_evaluation(self, success: bool = True, error_message: Optional[str] = None):
        """
        Mark evaluation as completed or failed.
        
        Args:
            success: True if completed successfully, False if failed
            error_message: Error message if failed
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    status = 'completed' if success else 'failed'
                    cursor.execute("""
                        UPDATE evaluation_state SET
                            status = %s,
                            end_time = CURRENT_TIMESTAMP,
                            error_message = %s,
                            current_step = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """, (
                        status,
                        error_message,
                        f"Evaluation {'completed successfully' if success else f'failed: {error_message}'}"
                    ))
                    
                    if success:
                        logger.info("✅ Evaluation completed successfully")
                    else:
                        logger.error(f"❌ Evaluation failed: {error_message}")
        except Exception as e:
            logger.error(f"Error completing evaluation: {e}")
    
    def reset(self):
        """Reset evaluation state to idle"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE evaluation_state SET
                            status = 'idle',
                            current_test_case = 0,
                            total_test_cases = 0,
                            percentage = 0,
                            current_step = '',
                            start_time = NULL,
                            end_time = NULL,
                            error_message = NULL,
                            user_email = NULL,
                            partner = NULL,
                            preview_only = FALSE,
                            dry_run = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """)
                    logger.info("🔄 Evaluation state reset")
        except Exception as e:
            logger.error(f"Error resetting evaluation state: {e}")
    
    def reset_stale_evaluations(self, stale_threshold_hours: int = 24):
        """
        Reset evaluations that appear to be stuck (stale).
        
        An evaluation is considered stale if:
        - Status is 'ongoing' but hasn't been updated in more than threshold hours
        - This can happen if the container was stopped while evaluation was running
        
        Args:
            stale_threshold_hours: Hours after which an ongoing evaluation is considered stale
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for stale ongoing evaluations
                    cursor.execute("""
                        SELECT updated_at
                        FROM evaluation_state
                        WHERE id = 1 AND status = 'ongoing'
                    """)
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.debug("No ongoing evaluation found")
                        return False
                    
                    updated_at = result[0]
                    if not updated_at:
                        # No updated_at timestamp, reset to be safe
                        logger.warning("⚠️ Found ongoing evaluation without updated_at timestamp. Resetting.")
                        self.reset()
                        return True
                    
                    # Calculate hours since last update
                    cursor.execute("""
                        SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - %s)) / 3600 as hours_ago
                    """, (updated_at,))
                    hours_ago = cursor.fetchone()[0]
                    
                    if hours_ago > stale_threshold_hours:
                        logger.warning(
                            f"⚠️ Found stale evaluation (last updated {hours_ago:.1f} hours ago). "
                            f"Resetting to idle state."
                        )
                        self.reset()
                        return True
                    else:
                        logger.info(
                            f"✅ Found ongoing evaluation (last updated {hours_ago:.1f} hours ago). "
                            f"Keeping state as-is."
                        )
                        return False
        except Exception as e:
            logger.error(f"Error checking for stale evaluations: {e}")
            # On error, reset to be safe
            try:
                self.reset()
            except Exception as reset_error:
                logger.error(f"Error resetting state: {reset_error}")
            return False
    
    def reset_on_startup(self):
        """
        Reset evaluation state on service startup.
        This ensures that if a container was stopped while evaluation was running,
        the state is reset so new evaluations can start.
        """
        try:
            logger.info("🔄 Checking evaluation state on startup...")
            state = self.get_state()
            current_status = state['status']
            
            if current_status == 'ongoing':
                logger.warning(
                    f"⚠️ Found ongoing evaluation from previous session. "
                    f"This likely means the container was stopped while evaluation was running. "
                    f"Resetting state to allow new evaluations."
                )
                self.reset()
                logger.info("✅ Evaluation state reset on startup")
            elif current_status in ['completed', 'failed']:
                # Reset completed/failed evaluations on startup to start fresh
                logger.info(f"🔄 Resetting {current_status} evaluation state on startup")
                self.reset()
            else:
                logger.info("✅ Evaluation state is idle, no reset needed")
        except Exception as e:
            logger.error(f"Error resetting evaluation state on startup: {e}")
            # Try to reset anyway to ensure clean state
            try:
                self.reset()
                logger.info("✅ Forced reset completed on startup")
            except Exception as reset_error:
                logger.error(f"Failed to force reset on startup: {reset_error}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current evaluation state.
        
        Returns:
            Dictionary with current state information
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            status,
                            current_test_case,
                            total_test_cases,
                            percentage,
                            current_step,
                            start_time,
                            end_time,
                            error_message,
                            user_email,
                            partner,
                            preview_only,
                            dry_run,
                            EXTRACT(EPOCH FROM (COALESCE(end_time, CURRENT_TIMESTAMP) - start_time)) as elapsed_seconds
                        FROM evaluation_state
                        WHERE id = 1
                    """)
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            "status": result['status'],
                            "current_test_case": result['current_test_case'] or 0,
                            "total_test_cases": result['total_test_cases'] or 0,
                            "percentage": float(result['percentage']) if result['percentage'] else 0.0,
                            "current_step": result['current_step'] or "",
                            "start_time": result['start_time'].isoformat() if result['start_time'] else None,
                            "end_time": result['end_time'].isoformat() if result['end_time'] else None,
                            "elapsed_seconds": round(float(result['elapsed_seconds']), 1) if result['elapsed_seconds'] else None,
                            "error_message": result['error_message'],
                            "user_email": result['user_email'],
                            "partner": result['partner'],
                            "preview_only": result['preview_only'] or False,
                            "dry_run": result['dry_run'] or False,
                        }
                    else:
                        # Return default state if no row exists
                        return self._get_default_state()
        except Exception as e:
            logger.error(f"Error getting evaluation state: {e}")
            # Return default state on error
            return self._get_default_state()
    
    def is_ongoing(self) -> bool:
        """Check if evaluation is currently ongoing"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT status FROM evaluation_state WHERE id = 1
                    """)
                    result = cursor.fetchone()
                    return result and result[0] == 'ongoing'
        except Exception as e:
            logger.error(f"Error checking if evaluation is ongoing: {e}")
            return False
    
    def get_status(self) -> EvaluationStatus:
        """Get current evaluation status"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT status FROM evaluation_state WHERE id = 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        return EvaluationStatus(result[0])
                    return EvaluationStatus.IDLE
        except Exception as e:
            logger.error(f"Error getting evaluation status: {e}")
            return EvaluationStatus.IDLE

