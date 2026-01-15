"""
Feedback Routes
===============
Endpoints for managing user feedback on AI responses.
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, Literal
import logging

from .models import Feedback

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)

# This will be injected by main.py
_get_storage = None


def init_dependencies(get_storage_func):
    """Initialize dependencies from main.py"""
    global _get_storage
    _get_storage = get_storage_func


@router.post(
    "",
    summary="Submit User Feedback",
    description="""
    Submit user feedback about AI responses for continuous improvement.
    
    This endpoint:
    - Stores user feedback with sentiment analysis
    - Links feedback to specific AI responses
    - Helps improve the multi-agent system performance
    - Supports positive, negative, and neutral feedback
    
    Feedback is stored in PostgreSQL database for analysis.
    """
)
async def save_feedback(feedback: Feedback):
    """Save user feedback to database"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        # Save to database
        feedback_id = storage.save_feedback(
            user_email=feedback.user_email,
            partner_name=feedback.partner_name,
            user_query=feedback.user_query,
            ai_response=feedback.ai_response,
            feedback=feedback.feedback,
            sentiment=feedback.sentiment
        )
        
        return {
            "message": "Feedback received successfully",
            "feedback_id": feedback_id
        }
        
    except Exception as e:
        logger.error(f"Error saving feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving feedback: {str(e)}"
        )


@router.get(
    "/list",
    summary="Get Feedback List",
    description="""
    Retrieve feedback with pagination and filters.
    
    Supports filtering by:
    - sentiment (positive/negative/neutral)
    - status (To Consider/Considered/Ignored)
    - partner_name
    - user_email
    - date range (start_date, end_date)
    
    Results are paginated and sorted.
    """
)
async def list_feedback(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Number of results (max 100)"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    feedback_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    partner_name: Optional[str] = Query(None, description="Filter by partner"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    start_date: Optional[str] = Query(None, description="Filter from date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter to date (ISO 8601)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """Get paginated feedback with filters"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        result = storage.get_feedback(
            offset=offset,
            limit=limit,
            sentiment=sentiment,
            status=feedback_status,
            partner_name=partner_name,
            user_email=user_email,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving feedback: {str(e)}"
        )


@router.get(
    "/stats",
    summary="Get Feedback Statistics",
    description="""
    Get aggregated feedback statistics.
    
    Returns:
    - Total feedback count
    - Counts by sentiment (positive/negative/neutral)
    - Counts by status (To Consider/Considered/Ignored)
    - Breakdown by partner
    
    Can be filtered by partner and date range.
    """
)
async def get_feedback_statistics(
    partner_name: Optional[str] = Query(None, description="Filter by partner"),
    start_date: Optional[str] = Query(None, description="Filter from date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Filter to date (ISO 8601)")
):
    """Get feedback statistics"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        stats = storage.get_feedback_stats(
            partner_name=partner_name,
            start_date=start_date,
            end_date=end_date
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving feedback stats: {str(e)}"
        )


@router.patch(
    "/{feedback_id}/status",
    summary="Update Feedback Status",
    description="""
    Update the review status of feedback.
    
    Valid statuses:
    - To Consider (default for new feedback)
    - Considered (reviewed and acted upon)
    - Ignored (reviewed but not relevant)
    
    Admin operation for managing feedback review workflow.
    """
)
async def update_feedback_status(
    feedback_id: str,
    status: Literal['To Consider', 'Considered', 'Ignored'] = Query(..., description="New status")
):
    """Update feedback status"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        updated = storage.update_feedback_status(feedback_id, status)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID {feedback_id} not found"
            )
        
        return {
            "message": "Feedback status updated successfully",
            "feedback_id": feedback_id,
            "new_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating feedback status: {str(e)}"
        )


@router.patch(
    "/{feedback_id}/notes",
    summary="Update Feedback Notes",
    description="""
    Update the admin notes for feedback.
    
    Notes field allows admins to add their observations and considerations
    about how the feedback was addressed or why it was ignored.
    
    Admin operation for managing feedback review workflow.
    """
)
async def update_feedback_notes(
    feedback_id: str,
    notes: str = Query(..., description="Admin notes about the feedback")
):
    """Update feedback notes"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        updated = storage.update_feedback_notes(feedback_id, notes)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID {feedback_id} not found"
            )
        
        return {
            "message": "Feedback notes updated successfully",
            "feedback_id": feedback_id,
            "notes": notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating feedback notes: {str(e)}"
        )


@router.delete(
    "/{feedback_id}",
    summary="Delete Feedback",
    description="""
    Delete a feedback entry.
    
    This is a permanent operation and cannot be undone.
    Admin operation for managing feedback data.
    """
)
async def delete_feedback_endpoint(feedback_id: str):
    """Delete feedback"""
    try:
        storage = _get_storage()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database storage is not configured."
            )
        
        deleted = storage.delete_feedback(feedback_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID {feedback_id} not found"
            )
        
        return {
            "message": "Feedback deleted successfully",
            "feedback_id": feedback_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting feedback: {str(e)}"
        )

