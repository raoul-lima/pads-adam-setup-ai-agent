import os
import json
import logging
from googleapiclient.errors import HttpError
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(__file__))

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)
# Use credentials.json from the backend folder
API_SERVICE_ACCOUNT_CREDENTIALS = os.path.join(project_root, 'credentials.json')


class GoogleSheetWriter:
    """
    Class to write metadata to Google Sheets using service account authentication.
    """
    def __init__(self, google_sheet_url):
        self.google_sheet_url = google_sheet_url
        self.secret_service_path = API_SERVICE_ACCOUNT_CREDENTIALS
        self.sheet_id = self.google_sheet_url.split('/d/')[1].split('/')[0]
        self.credentials = service_account.Credentials.from_service_account_file(
            self.secret_service_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)

    def _get_sheet_headers(self, sheet_name):
        """Fetches the header row from a specific sheet."""
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A1:Z1"
            ).execute()
            
            values = result.get('values', [])
            return values[0] if values else []
            
        except HttpError as err:
            raise Exception(f"Failed to access Google Sheet: {err}")
        except Exception as e:
            raise Exception(f"Error reading sheet headers: {str(e)}")

    def _clear_sheet_data(self, sheet_name, start_row=2):
        """Clears data from a sheet starting from a specific row (keeps headers)."""
        try:
            # Clear from row 2 onwards (keeping headers in row 1)
            range_to_clear = f"{sheet_name}!A{start_row}:Z"
            
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=range_to_clear
            ).execute()
            
            print(f"   ✓ Cleared existing data from {sheet_name}")
            
        except HttpError as err:
            raise Exception(f"Failed to clear sheet data: {err}")

    def _write_sheet_data(self, sheet_name, data, start_cell="A2"):
        """Writes data to a specific sheet starting from a specific cell."""
        try:
            if not data:
                print(f"   ⚠ No data to write to {sheet_name}")
                return
            
            range_name = f"{sheet_name}!{start_cell}"
            body = {'values': data}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            print(f"   ✓ Wrote {len(data)} rows ({updated_cells} cells) to {sheet_name}")
            
        except HttpError as err:
            raise Exception(f"Failed to write to Google Sheet: {err}")

    def write_metadata_to_sheet(self, metadata, fields_key, sheet_name, field_column_name):
        """
        Writes metadata for a specific entity to its corresponding Google Sheet.
        
        Args:
            metadata: The general_metadata dictionary
            fields_key: Key for the fields (e.g., 'metadata_fields_Line_items')
            sheet_name: Name of the sheet in Google Sheets (e.g., 'Metadata : Line items')
            field_column_name: Name of the field column in the sheet
        """
        print(f"\n📝 Writing {fields_key} metadata to Google Sheet...")
        
        try:
            # Get headers from the sheet to understand the structure
            headers = self._get_sheet_headers(sheet_name)
            
            if not headers:
                print(f"   ❌ Could not read headers from sheet '{sheet_name}'")
                return False
            
            print(f"   📋 Found {len(headers)} columns in sheet: {headers}")
            
            # Get metadata fields for this entity
            entity_fields = metadata.get("metadata", {}).get(fields_key, {})
            
            if not entity_fields:
                print(f"   ❌ No fields found for {fields_key}")
                return False
            
            # Prepare data rows based on the headers
            rows = []
            field_names = list(entity_fields.keys())
            
            for field_name in field_names:
                row = [''] * len(headers)  # Initialize row with empty strings
                
                # Set field name in the appropriate column
                if field_column_name in headers:
                    field_col_idx = headers.index(field_column_name)
                    row[field_col_idx] = field_name
                
                # Get field details from metadata_fields
                field_details = entity_fields.get(field_name, {})
                
                # Set Type
                if 'Type' in headers:
                    type_idx = headers.index('Type')
                    row[type_idx] = field_details.get('type', 'string')
                
                # Set Description after transformation
                if 'Description after transformation' in headers:
                    desc_idx = headers.index('Description after transformation')
                    description = field_details.get('description', 'No description available.')
                    row[desc_idx] = description if description != 'No description available.' else ''
                
                # Set Definition DV360
                if 'Definition DV360' in headers:
                    dv360_idx = headers.index('Definition DV360')
                    dv360_def = field_details.get('dv360_definition', 'No DV360 definition available.')
                    row[dv360_idx] = dv360_def if dv360_def != 'No DV360 definition available.' else ''
                
                rows.append(row)
            
            # Clear existing data (keep headers)
            self._clear_sheet_data(sheet_name, start_row=2)
            
            # Write new data
            self._write_sheet_data(sheet_name, rows, start_cell="A2")
            
            print(f"   ✅ Successfully wrote {len(rows)} fields for {fields_key}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error writing {fields_key} metadata: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function to write metadata from general_metadata.json to Google Sheets."""
    data_dir = os.path.dirname(__file__)
    
    # Google Sheet URL
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit?gid=1009558974"
    
    print("🚀 Starting metadata write-back process...")
    print("="*80)
    
    try:
        # Step 1: Load metadata from JSON file
        metadata_file = os.path.join(data_dir, 'general_metadata.json')
        
        if not os.path.exists(metadata_file):
            print(f"❌ Error: Metadata file not found at {metadata_file}")
            return False
        
        print(f"📄 Loading metadata from {metadata_file}...")
        with open(metadata_file, 'r') as f:
            general_metadata = json.load(f)
        
        print(f"✅ Successfully loaded metadata")
        
        # Print summary of what will be written
        print("\n📊 Metadata Summary:")
        print("-" * 80)
        for fields_key, entity_data in general_metadata.get("metadata", {}).items():
            field_count = len(entity_data)
            print(f"  {fields_key:40} | {field_count} fields")
        print("-" * 80)
        
        # Step 2: Initialize Google Sheet writer
        print("\n📊 Connecting to Google Sheets...")
        sheet_writer = GoogleSheetWriter(google_sheet_url)
        print("✅ Successfully connected to Google Sheets")
        
        # Step 3: Write each entity to its corresponding sheet
        print("\n" + "="*80)
        print("📝 WRITING METADATA TO GOOGLE SHEETS")
        print("="*80)
        
        results = []
        
        # Write Line Items
        success = sheet_writer.write_metadata_to_sheet(
            general_metadata,
            'metadata_fields_Line_items',
            'Metadata : Line items',
            'Line item champs'
        )
        results.append(('Line Items', success))
        
        # Write Insertion Orders
        success = sheet_writer.write_metadata_to_sheet(
            general_metadata,
            'metadata_fields_Insertion_orders',
            'Metadata : Insertion orders',
            'Insertion Order champs'
        )
        results.append(('Insertion Orders', success))
        
        # Write Campaigns
        success = sheet_writer.write_metadata_to_sheet(
            general_metadata,
            'metadata_fields_Campaigns',
            'Metadata : Campaign',
            'Campaign champs'
        )
        results.append(('Campaigns', success))
        
        # Step 4: Summary
        print("\n" + "="*80)
        print("📊 WRITE SUMMARY")
        print("="*80)
        
        all_success = True
        for entity_name, success in results:
            status = "✅ Success" if success else "❌ Failed"
            print(f"  {entity_name:20} | {status}")
            if not success:
                all_success = False
        
        print("-" * 80)
        
        if all_success:
            print("\n🎉 All metadata successfully written to Google Sheets!")
        else:
            print("\n⚠️  Some entities failed to write. Please check the errors above.")
        
        print("="*80)
        
        return all_success
        
    except Exception as e:
        print(f"\n❌ Error during metadata write-back: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Please check your Google Sheets connection and try again.")
        return False


def preview_changes():
    """Preview what changes will be made without actually writing to sheets."""
    data_dir = os.path.dirname(__file__)
    metadata_file = os.path.join(data_dir, 'general_metadata.json')
    
    if not os.path.exists(metadata_file):
        print(f"❌ Error: Metadata file not found at {metadata_file}")
        return
    
    print("🔍 PREVIEW MODE - No changes will be made to Google Sheets")
    print("="*80)
    
    with open(metadata_file, 'r') as f:
        general_metadata = json.load(f)
    
    entities = [
        ('metadata_fields_Line_items', 'Metadata : Line items', 'Line item champs'),
        ('metadata_fields_Insertion_orders', 'Metadata : Insertion orders', 'Insertion Order champs'),
        ('metadata_fields_Campaigns', 'Metadata : Campaign', 'Campaign champs')
    ]
    
    for fields_key, sheet_name, field_column in entities:
        print(f"\n📋 {fields_key} (Sheet: {sheet_name})")
        print("-" * 80)
        
        entity_fields = general_metadata.get("metadata", {}).get(fields_key, {})
        
        field_names = list(entity_fields.keys())
        print(f"  Fields to write: {len(field_names)}")
        
        # Show first 5 fields as examples
        print(f"\n  Sample fields (first 5):")
        for i, field_name in enumerate(field_names[:5], 1):
            field_details = entity_fields.get(field_name, {})
            print(f"    {i}. {field_name}")
            print(f"       Type: {field_details.get('type', 'N/A')}")
            desc = field_details.get('description', 'N/A')
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"       Description: {desc}")
    
    print("\n" + "="*80)
    print("💡 To write these changes to Google Sheets, run without --preview flag")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        # Preview mode - show what will be written without making changes
        preview_changes()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python write_metadata_to_sheet.py           # Write metadata to Google Sheets")
        print("  python write_metadata_to_sheet.py --preview # Preview changes without writing")
        print("  python write_metadata_to_sheet.py --help    # Show this help message")
    else:
        # Run full write process
        success = main()
        if not success:
            sys.exit(1)

