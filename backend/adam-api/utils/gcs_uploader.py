from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from datetime import timedelta, datetime
import os
import logging
import tempfile
import urllib.parse
import pandas as pd
from io import StringIO
import json

from utils.constants import GOOGLE_APPLICATION_CREDENTIALS

# Set up logging
logger = logging.getLogger(__name__)

# Set Google Cloud credentials from environment variable
GCS_ENABLED = True

if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS
    logger.info("Using local credentials - Using GCS")
elif GCS_ENABLED == False:
    logger.info("GCS is disabled - not using GCS")
else:
    logger.warning("Using default cloud credentials - Cloud Run - Using GCS")

def read_csv_from_gcs(bucket_name, gcs_path):
    """
    Reads a CSV file from GCS and returns a pandas DataFrame.
    """
    if not GCS_ENABLED:
        logger.error("GCS is not enabled. Cannot read from GCS.")
        raise Exception("GCS not configured, cannot read data.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)

        if not blob.exists():
            raise FileNotFoundError(f"File not found in GCS: gs://{bucket_name}/{gcs_path}")

        # Download the file contents as a string
        data = blob.download_as_string()
        
        # Use StringIO to wrap the string data and read it with pandas
        df = pd.read_csv(StringIO(data.decode('utf-8')))
        logger.info(f"Successfully read gs://{bucket_name}/{gcs_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to read CSV from GCS (gs://{bucket_name}/{gcs_path}): {e}")
        raise

def read_json_from_gcs(bucket_name, gcs_path):
    """
    Reads a JSON file from GCS and returns a dictionary.
    """
    if not GCS_ENABLED:
        logger.error("GCS is not enabled. Cannot read from GCS.")
        raise Exception("GCS not configured, cannot read data.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)

        if not blob.exists():
            raise FileNotFoundError(f"File not found in GCS: gs://{bucket_name}/{gcs_path}")

        # Force a reload of the blob's metadata to bypass any cache
        blob.reload()

        # Download the file contents as a string and parse as JSON
        data = blob.download_as_string()
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to read JSON from GCS (gs://{bucket_name}/{gcs_path}): {e}")
        raise

def upload_json_to_gcs(bucket_name, gcs_path, data):
    """
    Uploads a dictionary as a JSON file to GCS.
    """
    if not GCS_ENABLED:
        logger.error("GCS is not enabled. Cannot write to GCS.")
        raise Exception("GCS not configured, cannot write data.")

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)

        # Upload the JSON data
        blob.upload_from_string(
            json.dumps(data, indent=2),
            content_type='application/json'
        )
        logger.info(f"Successfully uploaded JSON to gs://{bucket_name}/{gcs_path}")
    except Exception as e:
        logger.error(f"Failed to upload JSON to GCS (gs://{bucket_name}/{gcs_path}): {e}")
        raise

def upload_to_gcs(df, bucket_name, folder="csv_outputs", label="query_result") -> str:
    """
    Uploads DataFrame to GCS and returns signed URL
    
    Args:
        df: pandas DataFrame to upload
        bucket_name: GCS bucket name
        folder: folder within bucket to store the file
        label: descriptive label for the file (default: "query_result")
        
    Returns:
        str: Signed URL for downloading the file or error message if GCS disabled
        
    Raises:
        Exception: If upload fails
    """
    if not GCS_ENABLED:
        logger.info("GCS upload skipped - credentials not configured")
        return "📊 Data generated successfully (GCS upload disabled - configure Google Cloud credentials to enable file downloads)"
    
    try:
        # Sanitize label for filename (replace spaces and special chars with underscores)
        safe_label = ''.join(c if c.isalnum() or c in '-_' else '_' for c in label.lower())
        safe_label = safe_label[:50]  # Limit length
        
        # Create timestamp with seconds precision for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename with folder structure, descriptive label, and timestamp
        filename = f"{folder}/{safe_label}_{timestamp}.csv"
        
        # Use temporary file with proper cleanup
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
            
        try:
            # Save DataFrame to CSV
            df.to_csv(tmp_file_path, index=False)
            logger.info(f"DataFrame saved to temporary file: {tmp_file_path}")
            
            # Initialize GCS client
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(filename)
            
            # Upload to GCS
            blob.upload_from_filename(tmp_file_path, content_type="text/csv")
            logger.info(f"File uploaded to GCS: gs://{bucket_name}/{filename}")
            
            # Generate signed URL with explicit parameters to avoid encoding issues
            # Using version 4 signing which is more robust
            try:
                signed_url = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(days=7),
                    method="GET",
                    version="v4"  # Use version 4 signing for better compatibility
                )
                logger.info(f"Signed URL (v4) generated successfully")
                
                # Validate the URL doesn't have double encoding issues
                if "%25" in signed_url:  # Check for double encoding (% encoded as %25)
                    logger.warning("Detected potential double encoding in signed URL, attempting to decode")
                    signed_url = urllib.parse.unquote(signed_url)
                
                return signed_url
                
            except Exception as signing_error:
                logger.warning(f"V4 signing failed: {signing_error}, trying V2 signing")
                # Fallback to version 2 signing
                signed_url = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(days=7),
                    method="GET"
                )
                logger.info(f"Signed URL (v2) generated successfully")
                return signed_url
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud error during upload: {e}")
            raise Exception(f"Failed to upload to Google Cloud Storage: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise Exception(f"Failed to upload file: {e}")
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    logger.debug(f"Temporary file cleaned up: {tmp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"Failed to upload DataFrame to GCS: {e}")
        # Re-raise with more context
        raise Exception(f"GCS upload failed: {str(e)}")


def upload_to_gcs_safe(df, bucket_name, folder="csv_outputs", label="query_result") -> str:
    """
    Safe wrapper for GCS upload that returns an error message instead of raising exceptions
    
    Args:
        df: pandas DataFrame to upload
        bucket_name: GCS bucket name
        folder: folder within bucket to store the file
        label: descriptive label for the file (default: "query_result")
        
    Returns:
        str: Either the signed URL or an error message
    """
    if not GCS_ENABLED:
        logger.info("GCS upload skipped - credentials not configured")
        return "📊 Data generated successfully (GCS upload disabled - configure Google Cloud credentials to enable file downloads)"
    
    try:
        return upload_to_gcs(df, bucket_name, folder, label)
    except Exception as e:
        error_msg = f"❌ Upload failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


def create_public_url(bucket_name: str, blob_name: str) -> str:
    """
    Alternative function to create a public URL (if bucket allows public access)
    This can be used as a fallback when signed URLs fail
    
    Args:
        bucket_name: GCS bucket name
        blob_name: Blob name (file path in bucket)
        
    Returns:
        str: Public URL
    """
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"


def upload_to_gcs_with_fallback(df, bucket_name, folder="csv_outputs", label="query_result") -> str:
    """
    Upload with multiple fallback strategies to ensure maximum compatibility
    
    Args:
        df: pandas DataFrame to upload
        bucket_name: GCS bucket name
        folder: folder within bucket to store the file
        label: descriptive label for the file (default: "query_result")
        
    Returns:
        str: URL for accessing the file (signed URL preferred, public URL as fallback)
    """
    if not GCS_ENABLED:
        logger.info("GCS upload skipped - credentials not configured")
        return "📊 Data generated successfully (GCS upload disabled - configure Google Cloud credentials to enable file downloads)"
    
    try:
        # Try the main upload function first
        signed_url = upload_to_gcs(df, bucket_name, folder, label)
        
        # Test if the signed URL is properly formatted
        if "Signature=" in signed_url and not "%25" in signed_url:
            return signed_url
        else:
            logger.warning("Signed URL appears to have encoding issues, trying alternative approach")
            raise Exception("Signed URL formatting issue")
            
    except Exception as e:
        logger.warning(f"Signed URL generation failed: {e}")
        
        # Fallback: Try to create a public URL
        try:
            # Sanitize label for filename (same as in upload_to_gcs)
            safe_label = ''.join(c if c.isalnum() or c in '-_' else '_' for c in label.lower())
            safe_label = safe_label[:50]  # Limit length
            
            # Create timestamp with seconds precision for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename with folder structure, descriptive label, and timestamp
            filename = f"{folder}/{safe_label}_{timestamp}.csv"
            
            # Use temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
                
            try:
                # Save DataFrame to CSV
                df.to_csv(tmp_file_path, index=False)
                
                # Initialize GCS client and upload
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(filename)
                
                # Upload to GCS
                blob.upload_from_filename(tmp_file_path, content_type="text/csv")
                
                # Try to make blob publicly accessible (if bucket policy allows)
                try:
                    blob.make_public()
                    public_url = create_public_url(bucket_name, filename)
                    logger.info(f"Public URL created as fallback: {public_url}")
                    return public_url
                except Exception as public_error:
                    logger.warning(f"Could not make blob public: {public_error}")
                    # Return the public URL anyway - it might work if bucket has public access
                    public_url = create_public_url(bucket_name, filename)
                    return f"⚠️ File uploaded but URL might require authentication: {public_url}"
                    
            finally:
                # Clean up
                try:
                    if os.path.exists(tmp_file_path):
                        os.remove(tmp_file_path)
                except Exception:
                    pass
                    
        except Exception as fallback_error:
            logger.error(f"All upload methods failed: {fallback_error}")
            return f"❌ Upload failed: {str(fallback_error)}"
