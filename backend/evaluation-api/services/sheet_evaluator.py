"""
Google Sheets Evaluator
=======================
Handles reading from and writing to Google Sheets for evaluation.
"""

import logging
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import os

logger = logging.getLogger(__name__)

# Google Sheet configuration from environment
GOOGLE_SHEET_URL = os.getenv(
    "GOOGLE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit?gid=1009558974"
)
EVAL_SHEET_NAME = os.getenv("EVAL_SHEET_NAME", "GOLDEN SET - EVAL")


class GoogleSheetEvaluator:
    """Handles reading from and writing to Google Sheets for evaluation"""
    
    def __init__(self, google_sheet_url: str = None):
        """
        Initialize Google Sheets evaluator.
        
        Args:
            google_sheet_url: Google Sheet URL (defaults to GOOGLE_SHEET_URL env var)
        """
        self.google_sheet_url = google_sheet_url or GOOGLE_SHEET_URL
        self.sheet_id = self.google_sheet_url.split('/d/')[1].split('/')[0]
        
        # Initialize credentials using Application Default Credentials (ADC)
        # This works with:
        # - GOOGLE_APPLICATION_CREDENTIALS env var (local development)
        # - Attached service account (Cloud Run)
        # - gcloud auth application-default login (local dev alternative)
        credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        logger.info(f"📝 Using Google Sheets API with project: {project}")
        self.service = build('sheets', 'v4', credentials=credentials)
    
    def read_eval_dataset(self) -> pd.DataFrame:
        """
        Reads evaluation dataset from Google Sheet.
        
        Returns:
            DataFrame with evaluation test cases
        """
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.sheet_id,
                range=f"{EVAL_SHEET_NAME}!A:G"  # Adjust range as needed
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("No data found in evaluation sheet")
                return pd.DataFrame()
            
            # First row is headers
            headers = values[0]
            data = []
            
            for row_idx, row in enumerate(values[1:], start=2):  # Start at 2 for sheet row number
                # Pad row with empty strings if shorter than headers
                padded_row = row + [''] * (len(headers) - len(row))
                padded_row.append(row_idx)  # Add row number for updating later
                data.append(padded_row)
            
            df = pd.DataFrame(data, columns=headers + ['_row_number'])
            
            logger.info(f"📊 Loaded {len(df)} rows from evaluation sheet")
            return df
            
        except HttpError as err:
            logger.error(f"Failed to access Google Sheet: {err}")
            raise
        except Exception as e:
            logger.error(f"Error reading evaluation sheet: {str(e)}")
            raise
    
    def write_eval_results(
        self, 
        row_number: int, 
        current_response: str, 
        auto_score: int, 
        feedback: str
    ):
        """
        Writes evaluation results back to Google Sheet.
        
        Args:
            row_number: Row number in the sheet (1-indexed)
            current_response: ADAM's response to write
            auto_score: Score from LLM judge (0-100)
            feedback: Feedback from LLM judge
        """
        try:
            # Determine column letters (adjust based on your actual sheet structure)
            # Assuming: D=CURRENT ADAM RESPONSE, E=AUTO SCORE, F=FEEDBACK JUDGE LLM
            updates = [
                {
                    'range': f'{EVAL_SHEET_NAME}!D{row_number}',
                    'values': [[current_response]]
                },
                {
                    'range': f'{EVAL_SHEET_NAME}!E{row_number}',
                    'values': [[auto_score]]
                },
                {
                    'range': f'{EVAL_SHEET_NAME}!F{row_number}',
                    'values': [[feedback]]
                }
            ]
            
            body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=body
            ).execute()
            
            logger.debug(f"✓ Updated row {row_number}")
            return result
            
        except HttpError as err:
            logger.error(f"Failed to write to Google Sheet: {err}")
            raise

