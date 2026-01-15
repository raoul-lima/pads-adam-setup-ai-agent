"""
Data Routes
===========
Endpoints for data operations like CSV preview.
"""

from fastapi import APIRouter, HTTPException, status, Query
from urllib.parse import urlparse
import logging

from .models import CsvDataResponse
from utils.gcs_uploader import read_csv_from_gcs

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/csv",
    tags=["Data"],
)


@router.get(
    "/preview",
    response_model=CsvDataResponse,
    summary="Get CSV Data Preview",
    description="""
    Fetch CSV data from Google Cloud Storage with pagination support for lazy loading.
    
    This endpoint:
    - Accepts a GCS signed URL or gs:// path
    - Reads the CSV file using pandas
    - Returns paginated data in JSON format
    - Supports lazy loading with offset and limit parameters
    
    Perfect for previewing large CSV files without downloading them entirely.
    """
)
async def get_csv_preview(
    url: str = Query(..., description="GCS signed URL or gs:// path to the CSV file"),
    offset: int = Query(0, ge=0, description="Starting row offset (0-based)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of rows to return (max 1000)")
):
    """
    Get paginated CSV data from Google Cloud Storage
    """
    try:
        # Parse the URL to extract bucket and path
        if url.startswith("gs://"):
            # Handle gs:// format
            parts = url[5:].split("/", 1)
            bucket_name = parts[0]
            gcs_path = parts[1] if len(parts) > 1 else ""
        elif "storage.googleapis.com" in url:
            # Handle https://storage.googleapis.com/bucket/path format
            parsed = urlparse(url)
            path_parts = parsed.path.lstrip("/").split("/", 1)
            bucket_name = path_parts[0]
            gcs_path = path_parts[1] if len(path_parts) > 1 else ""
        else:
            # Try to extract from signed URL
            parsed = urlparse(url)
            # Signed URLs have format: https://storage.googleapis.com/bucket_name/path?...
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) >= 2:
                bucket_name = path_parts[0]
                gcs_path = path_parts[1]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid GCS URL format. Please provide a valid GCS URL or gs:// path."
                )
        
        logger.info(f"Reading CSV from gs://{bucket_name}/{gcs_path} (offset={offset}, limit={limit})")
        
        # Read the entire CSV file from GCS using pandas
        df = read_csv_from_gcs(bucket_name, gcs_path)
        
        # Get total row count
        total_rows = len(df)
        
        # Handle empty dataframe
        if total_rows == 0:
            return CsvDataResponse(
                headers=[],
                rows=[],
                total_rows=0,
                offset=0,
                limit=limit,
                has_more=False
            )
        
        # Get headers
        headers = df.columns.tolist()
        
        # Apply pagination
        start_idx = offset
        end_idx = min(offset + limit, total_rows)
        
        # Get paginated data and convert to list of lists
        # Replace NaN values with empty strings
        paginated_df = df.iloc[start_idx:end_idx].fillna("")
        rows = paginated_df.values.tolist()
        
        # Convert all values to strings for consistent JSON serialization
        rows = [[str(cell) for cell in row] for row in rows]
        
        # Check if there are more rows
        has_more = end_idx < total_rows
        
        logger.info(f"Returning {len(rows)} rows (total: {total_rows}, has_more: {has_more})")
        
        return CsvDataResponse(
            headers=headers,
            rows=rows,
            total_rows=total_rows,
            offset=offset,
            limit=len(rows),
            has_more=has_more
        )
        
    except FileNotFoundError as e:
        logger.error(f"CSV file not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading CSV file: {str(e)}"
        )

