#!/usr/bin/env python3
"""
Migrate feedback from Google Cloud Storage to PostgreSQL Database

This script:
1. Reads feedback from GCS JSON file
2. Validates and transforms the data
3. Inserts into PostgreSQL database
4. Verifies data integrity
5. Generates migration report
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.constants import FEEDBACK_BUCKET_NAME, POSTGRES_CONFIG
from utils.gcs_uploader import read_json_from_gcs
from utils.postgres_storage import PostgreSQLStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_feedback_item(item):
    """Normalize feedback item by filling missing fields with 'Undefined'"""
    normalized = item.copy()
    
    # Required fields with defaults
    field_defaults = {
        'user_email': 'Undefined',
        'partner_name': 'Undefined',
        'user_query': 'Undefined',
        'ai_response': 'Undefined',
        'feedback': 'Undefined',
        'sentiment': 'neutral',  # Default to neutral if missing/invalid
        'agent_name': 'Adam Setup'
    }
    
    for field, default in field_defaults.items():
        if field not in normalized or not normalized[field]:
            if field == 'sentiment':
                logger.warning(f"Missing {field}, using default: {default}")
            else:
                logger.warning(f"Missing {field}, setting to: {default}")
            normalized[field] = default
    
    # Validate and fix sentiment
    if normalized['sentiment'] not in ['positive', 'negative', 'neutral']:
        logger.warning(f"Invalid sentiment '{normalized['sentiment']}', setting to: neutral")
        normalized['sentiment'] = 'neutral'
    
    return normalized


def migrate_feedback():
    """Main migration function"""
    
    print("=" * 60)
    print("FEEDBACK MIGRATION: GCS → PostgreSQL")
    print("=" * 60)
    print()
    
    # Check configuration
    if not FEEDBACK_BUCKET_NAME:
        logger.error("FEEDBACK_BUCKET_NAME is not configured")
        return False
    
    if not POSTGRES_CONFIG.get('user') or not POSTGRES_CONFIG.get('password'):
        logger.error("PostgreSQL credentials not configured")
        return False
    
    print(f"Source: gs://{FEEDBACK_BUCKET_NAME}/feedback_adam_security.json")
    print(f"Target: PostgreSQL - {POSTGRES_CONFIG['database']} @ {POSTGRES_CONFIG['host']}")
    print()
    
    try:
        # Initialize database storage
        logger.info("Connecting to PostgreSQL...")
        storage = PostgreSQLStorage(POSTGRES_CONFIG)
        
        # Check existing feedback count
        existing_count = storage.get_feedback_count()
        logger.info(f"Existing feedback in database: {existing_count}")
        
        if existing_count > 0:
            print()
            print(f"⚠️  WARNING: Database already contains {existing_count} feedback entries")
            response = input("Continue with migration? This will add more entries. (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled")
                return False
            print()
        
        # Read feedback from GCS
        logger.info("Reading feedback from GCS...")
        feedback_file_path = "feedback_adam_security.json"
        
        try:
            feedback_data = read_json_from_gcs(FEEDBACK_BUCKET_NAME, feedback_file_path)
            logger.info(f"✓ Read {len(feedback_data)} items from GCS")
        except FileNotFoundError:
            logger.error(f"Feedback file not found: gs://{FEEDBACK_BUCKET_NAME}/{feedback_file_path}")
            return False
        except Exception as e:
            logger.error(f"Error reading from GCS: {e}")
            return False
        
        if not feedback_data:
            logger.warning("No feedback data found in GCS")
            return True
        
        # Normalize feedback items (fill missing fields with "Undefined")
        logger.info("Normalizing feedback items...")
        normalized_feedback = []
        
        for i, item in enumerate(feedback_data):
            normalized = normalize_feedback_item(item)
            normalized_feedback.append(normalized)
        
        logger.info(f"✓ Normalized {len(normalized_feedback)} items")
        
        # Migrate feedback to database
        logger.info("Migrating feedback to database...")
        success_count = 0
        error_count = 0
        errors = []
        
        for i, item in enumerate(normalized_feedback):
            try:
                feedback_id = storage.save_feedback(
                    user_email=item['user_email'],
                    partner_name=item['partner_name'],
                    user_query=item['user_query'],
                    ai_response=item['ai_response'],
                    feedback=item['feedback'],
                    sentiment=item['sentiment'],
                    agent_name=item['agent_name'],
                    timestamp=item.get('timestamp')  # Preserve original timestamp if available
                )
                success_count += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"  Migrated {i + 1}/{len(normalized_feedback)} items...")
                    
            except Exception as e:
                error_count += 1
                error_msg = f"Error migrating item #{i} ({item.get('user_email', 'unknown')}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Verify migration
        logger.info("Verifying migration...")
        final_count = storage.get_feedback_count()
        expected_count = existing_count + success_count
        
        # Generate report
        print()
        print("=" * 60)
        print("MIGRATION REPORT")
        print("=" * 60)
        print(f"Source items (GCS):           {len(feedback_data)}")
        print(f"Items normalized:             {len(normalized_feedback)}")
        print(f"Successfully migrated:        {success_count}")
        print(f"Errors:                       {error_count}")
        print()
        print(f"Database count (before):      {existing_count}")
        print(f"Database count (after):       {final_count}")
        print(f"Expected count:               {expected_count}")
        print()
        
        if final_count == expected_count:
            print("✅ Migration verification: PASSED")
        else:
            print(f"⚠️  Migration verification: COUNT MISMATCH")
            print(f"   Difference: {abs(final_count - expected_count)}")
        
        print("=" * 60)
        
        if errors:
            print()
            print("ERRORS:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
        print()
        
        if error_count == 0 and final_count == expected_count:
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            return True
        elif success_count > 0:
            print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
            return True
        else:
            print("❌ MIGRATION FAILED")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    load_dotenv()
    
    success = migrate_feedback()
    
    if success:
        print()
        print("Next steps:")
        print("1. Verify feedback is accessible via API: GET /feedback/list")
        print("2. Check feedback statistics: GET /feedback/stats")
        print("3. Test admin dashboard with new database backend")
        print()
        sys.exit(0)
    else:
        print()
        print("Migration failed. Please check the logs and try again.")
        print()
        sys.exit(1)

