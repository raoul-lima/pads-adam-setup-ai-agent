"""
Evaluation Routes
=================
Endpoints for running ADAM agent evaluations.
"""

import os
import asyncio
import logging
import threading
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from services.adam_client import AdamAPIClient
from services.sheet_evaluator import GoogleSheetEvaluator
from services.llm_judge import ADAMEvaluator

logger = logging.getLogger(__name__)

# Use database-backed state manager for production (works across multiple instances)
# Falls back to in-memory singleton if database is not available
from services.evaluation_state_db import EvaluationStateManagerDB
EvaluationStateManager = EvaluationStateManagerDB
logger.info("✅ Using database-backed evaluation state manager")

router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation"],
)

# Get configuration from environment
EVAL_USER_EMAIL = os.getenv("EVAL_USER_EMAIL")
EVAL_PARTNER_NAME = os.getenv("EVAL_PARTNER_NAME")

# Batch size configuration with validation
try:
    _batch_size = int(os.getenv("EVAL_BATCH_SIZE", "20"))
    # Validate batch size: between 1 and 100
    if _batch_size < 1:
        logger.warning(f"EVAL_BATCH_SIZE ({_batch_size}) is less than 1, using default: 20")
        EVAL_BATCH_SIZE = 20
    elif _batch_size > 100:
        logger.warning(f"EVAL_BATCH_SIZE ({_batch_size}) is greater than 100, capping at 100")
        EVAL_BATCH_SIZE = 100
    else:
        EVAL_BATCH_SIZE = _batch_size
except (ValueError, TypeError):
    logger.warning(f"Invalid EVAL_BATCH_SIZE value, using default: 20")
    EVAL_BATCH_SIZE = 20

logger.info(f"⚙️  Evaluation batch size configured: {EVAL_BATCH_SIZE}")


class EvaluationRunRequest(BaseModel):
    """Request to run evaluation"""
    preview_only: bool = Field(
        default=False,
        description="If True, only preview test cases without running evaluation"
    )
    dry_run: bool = Field(
        default=False,
        description="If True, runs evaluation but doesn't write results to sheet"
    )
    user_email: Optional[str] = Field(
        default=None,
        description="User email for evaluation (defaults to EVAL_USER_EMAIL env var)"
    )
    partner: Optional[str] = Field(
        default=None,
        description="Partner name for evaluation (defaults to EVAL_PARTNER_NAME env var)"
    )


class EvaluationStatusResponse(BaseModel):
    """Evaluation system status"""
    adam_api_available: bool
    credentials_configured: bool
    ready: bool
    timestamp: str


class EvaluationProgressResponse(BaseModel):
    """Evaluation progress information"""
    status: str  # idle, ongoing, completed, failed
    current_test_case: int
    total_test_cases: int
    percentage: float
    current_step: str
    start_time: Optional[str]
    end_time: Optional[str]
    elapsed_seconds: Optional[float]
    error_message: Optional[str]
    user_email: Optional[str]
    partner: Optional[str]
    preview_only: bool
    dry_run: bool


# Constants
USE_FOR_EVALS_COLUMN = 'USE FOR EVALS'
REFERENCE_INPUT_COLUMN = 'REFERENCE INPUT'
REFERENCE_OUTPUT_COLUMN = 'REFERENCE OUTPUT / EVALUATION INSTRUCTION'
ROW_NUMBER_COLUMN = '_row_number'

# Singleton instances
_adam_client: Optional[AdamAPIClient] = None
_sheet_evaluator: Optional[GoogleSheetEvaluator] = None
_state_manager: Optional[EvaluationStateManager] = None


def get_state_manager() -> EvaluationStateManager:
    """Get or create evaluation state manager singleton"""
    global _state_manager
    if _state_manager is None:
        _state_manager = EvaluationStateManager()
    return _state_manager


def get_adam_client() -> AdamAPIClient:
    """Get or create ADAM API client singleton"""
    global _adam_client
    if _adam_client is None:
        _adam_client = AdamAPIClient()
    return _adam_client


def get_sheet_evaluator() -> GoogleSheetEvaluator:
    """Get or create Google Sheets evaluator singleton"""
    global _sheet_evaluator
    if _sheet_evaluator is None:
        _sheet_evaluator = GoogleSheetEvaluator()
    return _sheet_evaluator


def _run_evaluation_in_thread(
    preview_only: bool,
    dry_run: bool,
    user_email: Optional[str],
    partner: Optional[str]
):
    """
    Run evaluation pipeline in a background thread with proper event loop management.
    
    This function creates a new event loop for the thread and ensures proper cleanup.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("🔄 Starting evaluation in background thread...")
        loop.run_until_complete(
            run_evaluation_pipeline(
                preview_only=preview_only,
                dry_run=dry_run,
                user_email=user_email,
                partner=partner
            )
        )
        logger.info("✅ Evaluation pipeline completed successfully")
    except Exception as e:
        logger.error(f"❌ Evaluation pipeline failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Give time for any pending tasks to complete
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.info(f"Waiting for {len(pending)} pending tasks to complete...")
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            logger.warning(f"Error waiting for pending tasks: {e}")
        finally:
            loop.close()
            logger.info("🔄 Background thread event loop closed")


async def run_adam_via_api(
    user_query: str,
    user_email: str,
    partner: str,
    test_case_num: int = 0,
    client: Optional[AdamAPIClient] = None,
    use_memory: bool = True
) -> str:
    """
    Run ADAM agent via API call.
    
    Args:
        user_query: The user's question/input
        user_email: User email for conversation tracking
        partner: Partner name for context
        test_case_num: Test case number (for logging)
        client: Optional ADAM API client (if None, creates new one)
        use_memory: Whether to use conversation history/memory (default: True)
        
    Returns:
        ADAM's response as a string
    """
    if client is None:
        from services.adam_client import AdamAPIClient
        client = AdamAPIClient()
        should_close = True
    else:
        should_close = False
    
    try:
        logger.info(f"🤖 Calling ADAM API for test case {test_case_num}: {user_query[:100]}...")
        
        result = await client.send_message(
            content=user_query,
            user_email=user_email,
            partner=partner,
            use_memory=use_memory
        )
        
        response = result.get("response", "No response generated")
        logger.info(f"✅ ADAM API response received ({len(response)} chars)")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error calling ADAM API: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if should_close:
            try:
                await client.close()
            except Exception:
                pass


async def process_test_case_batch(
    batch: list,
    batch_num: int,
    total_batches: int,
    user_email: str,
    partner: str,
    client: AdamAPIClient,
    evaluator: ADAMEvaluator,
    state_manager: EvaluationStateManager,
    total_cases: int
) -> list:
    """
    Process a batch of test cases in parallel.
    
    Args:
        batch: List of test case dictionaries with keys: case_index, row_number, reference_input, reference_output
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
        user_email: User email for evaluation
        partner: Partner name for evaluation
        client: ADAM API client instance
        evaluator: LLM evaluator instance
        state_manager: Evaluation state manager
        total_cases: Total number of test cases
        
    Returns:
        List of result dictionaries with keys: test_case, row_number, reference_input, adam_response, score, feedback, error
    """
    batch_start_idx = batch[0]['case_index']
    batch_end_idx = batch[-1]['case_index']
    
    logger.info(f"\n🔄 Processing Batch {batch_num}/{total_batches} (test cases {batch_start_idx}-{batch_end_idx})")
    state_manager.update_progress(
        batch_start_idx - 1,
        f"Processing batch {batch_num}/{total_batches} (test cases {batch_start_idx}-{batch_end_idx})..."
    )
    
    # Step 1: Call ADAM API in parallel for all test cases in batch
    logger.info(f"📡 Calling ADAM API for {len(batch)} test cases in parallel...")
    state_manager.update_progress(
        batch_start_idx - 1,
        f"Batch {batch_num}/{total_batches}: Calling ADAM API for {len(batch)} test cases..."
    )
    
    async def call_adam_api(test_case_data: dict) -> tuple:
        """Helper function to call ADAM API for a single test case"""
        try:
            response = await run_adam_via_api(
                user_query=test_case_data['reference_input'],
                user_email=user_email,
                partner=partner,
                test_case_num=test_case_data['case_index'],
                client=client,
                use_memory=False  # Disable memory for evaluations
            )
            return test_case_data['case_index'], response, None
        except Exception as e:
            logger.error(f"❌ Error calling ADAM API for test case {test_case_data['case_index']}: {e}")
            return test_case_data['case_index'], None, str(e)
    
    # Execute all ADAM API calls in parallel
    adam_tasks = [call_adam_api(tc) for tc in batch]
    adam_results = await asyncio.gather(*adam_tasks, return_exceptions=True)
    
    # Process ADAM API results and prepare for LLM evaluation
    adam_responses = {}
    failed_cases = []
    
    for result in adam_results:
        if isinstance(result, Exception):
            logger.error(f"❌ Unexpected error in ADAM API call: {result}")
            continue
        
        case_index, response, error = result
        if error:
            failed_cases.append(case_index)
            adam_responses[case_index] = None
        else:
            adam_responses[case_index] = response
    
    logger.info(f"✅ ADAM API calls completed: {len(adam_responses) - len(failed_cases)}/{len(batch)} successful")
    
    # Step 2: Evaluate responses with LLM judge in parallel
    logger.info(f"⚖️  Evaluating {len(adam_responses) - len(failed_cases)} responses with LLM Judge in parallel...")
    state_manager.update_progress(
        batch_start_idx - 1,
        f"Batch {batch_num}/{total_batches}: Evaluating responses with LLM Judge..."
    )
    
    async def evaluate_response(test_case_data: dict, adam_response: str) -> tuple:
        """Helper function to evaluate a single response"""
        if adam_response is None:
            return test_case_data['case_index'], None, None, "ADAM API call failed"
        
        try:
            eval_result = await evaluator.evaluate_response_async(
                reference_input=test_case_data['reference_input'],
                reference_output=test_case_data['reference_output'],
                adam_response=adam_response
            )
            return test_case_data['case_index'], eval_result['score'], eval_result['feedback'], None
        except Exception as e:
            logger.error(f"❌ Error evaluating response for test case {test_case_data['case_index']}: {e}")
            return test_case_data['case_index'], None, None, str(e)
    
    # Execute all LLM evaluations in parallel
    eval_tasks = [
        evaluate_response(tc, adam_responses.get(tc['case_index']))
        for tc in batch
        if tc['case_index'] not in failed_cases
    ]
    eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)
    
    # Step 3: Combine results maintaining order
    batch_results = []
    eval_dict = {}
    
    for result in eval_results:
        if isinstance(result, Exception):
            logger.error(f"❌ Unexpected error in LLM evaluation: {result}")
            continue
        
        case_index, score, feedback, error = result
        eval_dict[case_index] = {'score': score, 'feedback': feedback, 'error': error}
    
    # Build results list maintaining original batch order
    for test_case_data in batch:
        case_index = test_case_data['case_index']
        adam_response = adam_responses.get(case_index)
        
        if case_index in failed_cases:
            # ADAM API failed
            batch_results.append({
                'test_case': case_index,
                'row_number': test_case_data['row_number'],
                'reference_input': test_case_data['reference_input'],
                'adam_response': None,
                'score': 0,
                'feedback': 'ADAM API call failed',
                'error': True
            })
        elif case_index in eval_dict:
            eval_data = eval_dict[case_index]
            if eval_data['error']:
                # LLM evaluation failed
                batch_results.append({
                    'test_case': case_index,
                    'row_number': test_case_data['row_number'],
                    'reference_input': test_case_data['reference_input'],
                    'adam_response': adam_response,
                    'score': 0,
                    'feedback': f"LLM evaluation failed: {eval_data['error']}",
                    'error': True
                })
            else:
                # Success
                batch_results.append({
                    'test_case': case_index,
                    'row_number': test_case_data['row_number'],
                    'reference_input': test_case_data['reference_input'],
                    'adam_response': adam_response,
                    'score': eval_data['score'],
                    'feedback': eval_data['feedback'],
                    'error': False
                })
        else:
            # Should not happen, but handle gracefully
            batch_results.append({
                'test_case': case_index,
                'row_number': test_case_data['row_number'],
                'reference_input': test_case_data['reference_input'],
                'adam_response': adam_response,
                'score': 0,
                'feedback': 'Unknown error during evaluation',
                'error': True
            })
    
    logger.info(f"✅ Batch {batch_num}/{total_batches} completed: {sum(1 for r in batch_results if not r.get('error', False))}/{len(batch_results)} successful")
    
    return batch_results


async def run_evaluation_pipeline(
    preview_only: bool = False,
    dry_run: bool = False,
    user_email: str = None,
    partner: str = None
):
    """
    Run the evaluation pipeline.
    
    Args:
        preview_only: If True, only preview test cases
        dry_run: If True, don't write results to sheet
        user_email: User email (defaults to env var)
        partner: Partner name (defaults to env var)
    """
    user_email = user_email or EVAL_USER_EMAIL
    partner = partner or EVAL_PARTNER_NAME
    
    # Get state manager instance
    state_manager = get_state_manager()
    
    logger.info("🚀 Starting ADAM Evaluation Pipeline")
    logger.info(f"📧 User: {user_email}")
    logger.info(f"🏢 Partner: {partner}")
    logger.info(f"🔍 Preview only: {preview_only}")
    logger.info(f"🧪 Dry run: {dry_run}")
    
    # Initialize components
    sheet_eval = get_sheet_evaluator()
    # Create a new client instance for this evaluation run (don't use singleton in background thread)
    from services.adam_client import AdamAPIClient
    client = AdamAPIClient()
    
    try:
        # Read evaluation dataset first (before starting evaluation tracking)
        logger.info("📖 Reading evaluation dataset from Google Sheet...")
        df = sheet_eval.read_eval_dataset()
        
        if df.empty:
            logger.error("❌ No evaluation data found!")
            state_manager.complete_evaluation(success=False, error_message="No evaluation data found")
            return
        
        # Filter to rows marked for evaluation
        eval_df = df[df[USE_FOR_EVALS_COLUMN].str.upper() == 'YES'].copy()
        
        logger.info(f"✅ Found {len(eval_df)} test cases marked for evaluation")
        
        if preview_only:
            logger.info("\n📋 EVALUATION DATASET PREVIEW")
            logger.info(f"✅ Total rows marked for evaluation: {len(eval_df)}")
            logger.info(f"⏭️  Skipped rows: {len(df) - len(eval_df)}")
            state_manager.complete_evaluation(success=True)
            return
        
        # Start evaluation tracking (already checked in endpoint, but double-check here)
        if not state_manager.start_evaluation(
            total_test_cases=len(eval_df),
            user_email=user_email,
            partner=partner,
            preview_only=preview_only,
            dry_run=dry_run
        ):
            logger.error("❌ Failed to start evaluation: one is already ongoing")
            return
        
        # Now we can update progress
        state_manager.update_progress(0, "Reading evaluation dataset from Google Sheet...")
        
        # Reset conversation before evaluation starts (clean slate)
        state_manager.update_progress(0, "Resetting conversation...")
        logger.info("🧹 Resetting evaluation user conversation...")
        try:
            await client.reset_conversation(user_email, partner)
            logger.info("✅ Conversation reset - starting with clean slate")
        except Exception as e:
            logger.warning(f"⚠️ Could not reset conversation: {e}")
        
        # Initialize evaluator
        state_manager.update_progress(0, "Initializing LLM Judge...")
        logger.info("🤖 Initializing LLM Judge (Gemini Flash)...")
        evaluator = ADAMEvaluator(model_name="gemini-flash-latest")
        
        # Prepare test cases for batch processing
        total_cases = len(eval_df)
        test_cases = []
        
        # Use enumerate to get sequential counter (not DataFrame index)
        for case_index, (idx, row) in enumerate(eval_df.iterrows(), start=1):
            test_cases.append({
                'case_index': case_index,
                'row_number': int(row[ROW_NUMBER_COLUMN]),
                'reference_input': row[REFERENCE_INPUT_COLUMN],
                'reference_output': row[REFERENCE_OUTPUT_COLUMN]
            })
        
        # Calculate batch configuration
        batch_size = max(1, EVAL_BATCH_SIZE)  # Ensure at least 1
        total_batches = (total_cases + batch_size - 1) // batch_size  # Ceiling division
        
        logger.info("\n🧪 RUNNING EVALUATIONS WITH BATCH PROCESSING")
        logger.info(f"📊 Total test cases to process: {total_cases}")
        logger.info(f"⚡ Batch size: {batch_size}")
        logger.info(f"📦 Total batches: {total_batches}")
        
        # Process test cases in batches
        all_results = []
        completed_cases = 0
        
        for batch_num in range(1, total_batches + 1):
            # Get batch of test cases
            start_idx = (batch_num - 1) * batch_size
            end_idx = min(start_idx + batch_size, total_cases)
            batch = test_cases[start_idx:end_idx]
            
            try:
                # Process batch in parallel (ADAM API + LLM evaluation)
                batch_results = await process_test_case_batch(
                    batch=batch,
                    batch_num=batch_num,
                    total_batches=total_batches,
                    user_email=user_email,
                    partner=partner,
                    client=client,
                    evaluator=evaluator,
                    state_manager=state_manager,
                    total_cases=total_cases
                )
                
                # Write results to Google Sheets SEQUENTIALLY (maintaining order)
                if not dry_run:
                    logger.info(f"💾 Writing batch {batch_num}/{total_batches} results to Google Sheet sequentially...")
                    
                    if batch_results:
                        state_manager.update_progress(
                            batch_results[0]['test_case'] - 1,
                            f"Writing batch {batch_num}/{total_batches} results to Google Sheet..."
                        )
                    
                    for result in batch_results:
                        if result.get('error'):
                            logger.warning(f"⚠️  Skipping write for failed test case {result['test_case']}")
                            continue
                        
                        try:
                            sheet_eval.write_eval_results(
                                row_number=result['row_number'],
                                current_response=result['adam_response'],
                                auto_score=result['score'],
                                feedback=result['feedback']
                            )
                            completed_cases += 1
                            logger.debug(f"✅ Written results for test case {result['test_case']} (row {result['row_number']})")
                        except Exception as e:
                            logger.error(f"❌ Error writing results for test case {result['test_case']}: {e}")
                            result['write_error'] = str(e)
                    
                    logger.info(f"✅ Batch {batch_num}/{total_batches} results written to sheet")
                    if batch_results:
                        state_manager.update_progress(
                            batch_results[-1]['test_case'],
                            f"Completed batch {batch_num}/{total_batches} - {completed_cases}/{total_cases} test cases written"
                        )
                else:
                    logger.info(f"⏭️  Skipped writing batch {batch_num}/{total_batches} (dry run mode)")
                    completed_cases += len([r for r in batch_results if not r.get('error', False)])
                    if batch_results:
                        state_manager.update_progress(
                            batch_results[-1]['test_case'],
                            f"Completed batch {batch_num}/{total_batches} (dry run) - {completed_cases}/{total_cases} test cases processed"
                        )
                
                # Add batch results to all results
                all_results.extend(batch_results)
                
            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_num}/{total_batches}: {e}")
                import traceback
                traceback.print_exc()
                
                # Mark all test cases in this batch as failed
                for test_case_data in batch:
                    all_results.append({
                        'test_case': test_case_data['case_index'],
                        'row_number': test_case_data['row_number'],
                        'reference_input': test_case_data['reference_input'],
                        'adam_response': None,
                        'score': 0,
                        'feedback': f"Batch processing failed: {str(e)}",
                        'error': True
                    })
        
        # Use all_results for summary
        results = all_results
        
        # Summary - mark as complete (all test cases processed)
        state_manager.update_progress(total_cases, "Generating evaluation summary...")
        logger.info("\n📊 EVALUATION SUMMARY")
        
        if results:
            # Filter out failed test cases for score statistics
            successful_results = [r for r in results if not r.get('error', False)]
            failed_results = [r for r in results if r.get('error', False)]
            
            logger.info(f"✅ Completed {len(results)} test cases")
            logger.info(f"   ✓ Successful: {len(successful_results)}")
            if failed_results:
                logger.warning(f"   ✗ Failed: {len(failed_results)}")
                for failed in failed_results:
                    logger.warning(f"      - Test case {failed['test_case']}: {failed.get('feedback', 'Unknown error')}")
            
            if successful_results:
                scores = [r['score'] for r in successful_results]
                avg_score = sum(scores) / len(scores)
                
                logger.info(f"\n📈 Average Score: {avg_score:.1f}/100")
                logger.info(f"📊 Score Range: {min(scores)} - {max(scores)}")
                pass_rate = sum(1 for s in scores if s >= 70) / len(scores) * 100 if scores else 0
                logger.info(f"🎯 Pass Rate (≥70): {sum(1 for s in scores if s >= 70)}/{len(scores)} ({pass_rate:.1f}%)")
                
                # Score distribution
                logger.info("\n📊 Score Distribution:")
                logger.info(f"  90-100 (Excellent): {sum(1 for s in scores if s >= 90)}")
                logger.info(f"  70-89  (Good):      {sum(1 for s in scores if 70 <= s < 90)}")
                logger.info(f"  50-69  (Adequate):  {sum(1 for s in scores if 50 <= s < 70)}")
                logger.info(f"  30-49  (Poor):      {sum(1 for s in scores if 30 <= s < 50)}")
                logger.info(f"  0-29   (Very Poor): {sum(1 for s in scores if s < 30)}")
            else:
                logger.error("❌ No successful evaluations to summarize")
        
        logger.info("\n✅ Evaluation Complete!")
        state_manager.complete_evaluation(success=True)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Evaluation pipeline failed: {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            state_manager.complete_evaluation(success=False, error_message=error_msg)
        except Exception as state_error:
            logger.error(f"Error updating evaluation state on failure: {state_error}")
            # If we can't update state, reset it to allow future evaluations
            try:
                state_manager.reset()
                logger.info("✅ Reset evaluation state after error")
            except Exception as reset_error:
                logger.error(f"Error resetting evaluation state: {reset_error}")
    finally:
        # Clean up HTTP client
        try:
            await client.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")


@router.post(
    "/run",
    summary="Run ADAM Evaluation",
    description="""
    Run the ADAM agent evaluation pipeline.
    
    This endpoint:
    - Reads test cases from Google Sheets
    - Calls ADAM API for each test case
    - Evaluates responses with LLM judge
    - Writes results back to the sheet
    
    Returns immediate response with status. Evaluation runs asynchronously.
    Cannot start if an evaluation is already ongoing.
    """
)
async def run_evaluation(request: EvaluationRunRequest = EvaluationRunRequest()):
    """Run the ADAM evaluation pipeline asynchronously"""
    try:
        # Check if evaluation is already ongoing
        state_manager = get_state_manager()
        if state_manager.is_ongoing():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An evaluation is already in progress. Please wait for it to complete."
            )
        
        logger.info("🧪 Starting ADAM evaluation pipeline...")
        
        # Start evaluation in background (fire and forget)
        thread = threading.Thread(
            target=_run_evaluation_in_thread,
            args=(request.preview_only, request.dry_run, request.user_email, request.partner),
            daemon=False
        )
        thread.start()
        logger.info(f"✅ Evaluation thread started (thread_id: {thread.ident})")
        
        return {
            "status": "started",
            "message": "Evaluation pipeline started in background",
            "timestamp": datetime.now().isoformat(),
            "user_email": request.user_email or EVAL_USER_EMAIL,
            "partner": request.partner or EVAL_PARTNER_NAME,
            "preview_only": request.preview_only,
            "dry_run": request.dry_run,
            "note": "Use /evaluation/progress endpoint to track progress. Results will be written to Google Sheet when complete."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting evaluation: {str(e)}"
        )


@router.get(
    "/status",
    response_model=EvaluationStatusResponse,
    summary="Get Evaluation System Status",
    description="""
    Check the status of the evaluation system.
    
    Returns status information about the evaluation system including
    ADAM API availability and credentials configuration.
    """
)
async def evaluation_status():
    """Get evaluation system status"""
    try:
        # Check ADAM API availability
        adam_api_available = False
        try:
            client = get_adam_client()
            await client.health_check()
            adam_api_available = True
        except Exception as e:
            logger.warning(f"ADAM API health check failed: {e}")
        
        # Check Google credentials
        import google.auth
        try:
            credentials, project = google.auth.default(
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            credentials_configured = True
        except Exception:
            credentials_configured = False
        
        return EvaluationStatusResponse(
            adam_api_available=adam_api_available,
            credentials_configured=credentials_configured,
            ready=adam_api_available and credentials_configured,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error checking evaluation status: {str(e)}")
        return EvaluationStatusResponse(
            adam_api_available=False,
            credentials_configured=False,
            ready=False,
            timestamp=datetime.now().isoformat()
        )


@router.get(
    "/progress",
    response_model=EvaluationProgressResponse,
    summary="Get Evaluation Progress",
    description="""
    Get the current progress of an ongoing evaluation.
    
    Returns detailed progress information including:
    - Current status (idle, ongoing, completed, failed)
    - Current test case number and total test cases
    - Progress percentage
    - Current step description
    - Start/end times and elapsed time
    - Error message (if failed)
    """
)
async def evaluation_progress():
    """Get current evaluation progress"""
    try:
        state_manager = get_state_manager()
        state = state_manager.get_state()
        return EvaluationProgressResponse(**state)
    except Exception as e:
        logger.error(f"Error getting evaluation progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting evaluation progress: {str(e)}"
        )

