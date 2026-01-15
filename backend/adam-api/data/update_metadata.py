import os
import pandas as pd
import logging
from googleapiclient.errors import HttpError
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# Add the parent directory to the path to import from metadata_generator
sys.path.insert(0, os.path.dirname(__file__))


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


logger = logging.getLogger(__name__)
# Use credentials.json from the backend folder
API_SERVICE_ACCOUNT_CREDENTIALS = os.path.join(project_root, 'credentials.json')

class GoogleSheetOperator:
    """
    Class to operate data from multiple sheets in a Google Sheet using service account authentication.
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

    def _get_sheet_data(self, sheet_name):
        """
        Fetches and returns data from a specific sheet as a pandas DataFrame.
        """
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame()
                
            headers = values[0]
            data = []
            for row in values[1:]:
                # Pad row with empty strings if shorter than headers
                padded_row = row + [''] * (len(headers) - len(row))
                data.append(padded_row)
            
            return pd.DataFrame(data, columns=headers)
            
        except HttpError as err:
            raise Exception(f"Failed to access Google Sheet: {err}")
        except Exception as e:
            raise Exception(f"Error processing Google Sheet: {str(e)}")

    def get_general_metadata(self):
        """Returns combined metadata for Line Items, Insertion Orders and Campaigns"""
        line_items_df, line_items_fields = self.get_metadata_line_items()
        insertion_orders_df, insertion_orders_fields = self.get_metadata_insertion_orders()
        campaigns_df, campaigns_fields = self.get_metadata_campaigns()
        
        # Combine all metadata
        combined_metadata = {
            "metadata": {
                **line_items_fields,
                **insertion_orders_fields,
                **campaigns_fields
            }
        }
        
        return combined_metadata

    def get_metadata_line_items(self):
        """Returns Line Items metadata as DataFrame and JSON format"""
        df = self._get_sheet_data("Metadata : Line items")

        # Create fields metadata
        fields_metadata = {
            "metadata_fields_Line_items": {
                field: {
                    "type": str(df[df["Line item champs"] == field]["Type"].iloc[0]),
                    "description": str(df[df["Line item champs"] == field]["Description after transformation"].iloc[0]),
                    "dv360_definition": str(df[df["Line item champs"] == field]["Definition DV360"].iloc[0]) if "Definition DV360" in df.columns else "No DV360 definition available.",
                    "sample_data": []
                }
                for field in df["Line item champs"].tolist()
            }
        }
        
        return df, fields_metadata

    def get_metadata_insertion_orders(self):
        """Returns Insertion Orders metadata"""
        df = self._get_sheet_data("Metadata : Insertion orders")

        # Create fields metadata
        fields_metadata = {
            "metadata_fields_Insertion_orders": {
                field: {
                    "type": str(df[df["Insertion Order champs"] == field]["Type"].iloc[0]),
                    "description": str(df[df["Insertion Order champs"] == field]["Description after transformation"].iloc[0]),
                    "dv360_definition": str(df[df["Insertion Order champs"] == field]["Definition DV360"].iloc[0]) if "Definition DV360" in df.columns else "No DV360 definition available.",
                    "sample_data": []
                }
                for field in df["Insertion Order champs"].tolist()
            }
        }

        return df, fields_metadata
    
    def get_metadata_campaigns(self):
        """Returns Campaign metadata"""
        df = self._get_sheet_data("Metadata : Campaign")

        # Create fields metadata
        fields_metadata = {
            "metadata_fields_Campaigns": {
                field: {
                    "type": str(df[df["Campaign champs"] == field]["Type"].iloc[0]),
                    "description": str(df[df["Campaign champs"] == field]["Description after transformation"].iloc[0]),
                    "dv360_definition": str(df[df["Campaign champs"] == field]["Definition DV360"].iloc[0]) if "Definition DV360" in df.columns else "No DV360 definition available.",
                    "sample_data": []
                }
                for field in df["Campaign champs"].tolist()
            }
        }

        return df, fields_metadata



def get_user_friendly_type(dtype):
    """Converts pandas dtype to a more user-friendly type string."""
    if 'int' in dtype:
        return 'integer'
    if 'float' in dtype:
        return 'float'
    if 'bool' in dtype:
        return 'boolean'
    return 'string'

def get_descriptions_from_google_sheet(google_sheet_url):
    """
    Fetches field descriptions from Google Sheets for all entities.
    Returns a dictionary with descriptions for each field.
    """
    descriptions = {}
    
    try:
        sheet_operator = GoogleSheetOperator(google_sheet_url)
        
        # Get descriptions for Line Items
        try:
            line_items_df = sheet_operator._get_sheet_data("Metadata : Line items")
            if not line_items_df.empty and "Line item champs" in line_items_df.columns and "Description after transformation" in line_items_df.columns:
                for _, row in line_items_df.iterrows():
                    field_name = str(row["Line item champs"]).strip()
                    description = str(row["Description after transformation"]).strip()
                    if field_name and field_name != 'nan':
                        # Only update if we have a meaningful description
                        if description and description != 'nan' and description.strip():
                            descriptions[field_name] = description
        except Exception as e:
            print(f"Warning: Could not fetch Line Items descriptions from Google Sheet: {e}")
        
        # Get descriptions for Insertion Orders
        try:
            insertion_orders_df = sheet_operator._get_sheet_data("Metadata : Insertion orders")
            if not insertion_orders_df.empty and "Insertion Order champs" in insertion_orders_df.columns and "Description after transformation" in insertion_orders_df.columns:
                for _, row in insertion_orders_df.iterrows():
                    field_name = str(row["Insertion Order champs"]).strip()
                    description = str(row["Description after transformation"]).strip()
                    if field_name and field_name != 'nan':
                        # Only update if we have a meaningful description AND field doesn't already have one
                        if description and description != 'nan' and description.strip() and field_name not in descriptions:
                            descriptions[field_name] = description
        except Exception as e:
            print(f"Warning: Could not fetch Insertion Orders descriptions from Google Sheet: {e}")
        
        # Get descriptions for Campaigns
        try:
            campaigns_df = sheet_operator._get_sheet_data("Metadata : Campaign")
            if not campaigns_df.empty and "Campaign champs" in campaigns_df.columns and "Description after transformation" in campaigns_df.columns:
                for _, row in campaigns_df.iterrows():
                    field_name = str(row["Campaign champs"]).strip()
                    description = str(row["Description after transformation"]).strip()
                    if field_name and field_name != 'nan':
                        # Only update if we have a meaningful description AND field doesn't already have one
                        if description and description != 'nan' and description.strip() and field_name not in descriptions:
                            descriptions[field_name] = description
        except Exception as e:
            print(f"Warning: Could not fetch Campaigns descriptions from Google Sheet: {e}")
            
    except Exception as e:
        print(f"Error: Could not connect to Google Sheets: {e}")
        print("Falling back to existing descriptions...")
    
    return descriptions

def detect_field_discrepancies(google_sheet_url):
    """
    Detects discrepancies between Google Sheets fields and sample CSV data fields.
    Returns a detailed report of missing and extra fields for each entity.
    """
    print("\n" + "="*80)
    print("🔍 FIELD DISCREPANCY DETECTION")
    print("="*80)
    
    discrepancies = {
        "Line_Items": {"missing_in_sheets": [], "extra_in_sheets": [], "csv_fields": [], "sheet_fields": []},
        "Insertion_Orders": {"missing_in_sheets": [], "extra_in_sheets": [], "csv_fields": [], "sheet_fields": []},
        "Campaigns": {"missing_in_sheets": [], "extra_in_sheets": [], "csv_fields": [], "sheet_fields": []}
    }
    
    try:
        # Get Google Sheets data
        sheet_operator = GoogleSheetOperator(google_sheet_url)
        
        # Get sample CSV data directory
        data_dir = os.path.dirname(__file__)
        sample_data_dir = os.path.join(data_dir, 'sample_sdf_data')
        
        # Define mappings between sample CSV files and Google Sheets
        entity_mappings = [
            {
                "entity": "Line_Items",
                "csv_file": "line_items.csv",
                "sheet_name": "Metadata : Line items",
                "field_column": "Line item champs"
            },
            {
                "entity": "Insertion_Orders", 
                "csv_file": "insertion_orders.csv",
                "sheet_name": "Metadata : Insertion orders",
                "field_column": "Insertion Order champs"
            },
            {
                "entity": "Campaigns",
                "csv_file": "campaigns.csv", 
                "sheet_name": "Metadata : Campaign",
                "field_column": "Campaign champs"
            }
        ]
        
        for mapping in entity_mappings:
            entity = mapping["entity"]
            print(f"\n📋 Analyzing {entity}...")
            
            # Get sample CSV fields
            csv_path = os.path.join(sample_data_dir, mapping["csv_file"])
            try:
                df_csv = pd.read_csv(csv_path)
                csv_fields = set(df_csv.columns.tolist())
                discrepancies[entity]["csv_fields"] = sorted(list(csv_fields))
                print(f"   📄 Sample CSV fields: {len(csv_fields)} found")
            except Exception as e:
                print(f"   ❌ Error reading sample CSV {mapping['csv_file']}: {e}")
                csv_fields = set()
            
            # Get Google Sheets fields
            try:
                df_sheet = sheet_operator._get_sheet_data(mapping["sheet_name"])
                if not df_sheet.empty and mapping["field_column"] in df_sheet.columns:
                    sheet_fields = set()
                    for field in df_sheet[mapping["field_column"]].tolist():
                        field_clean = str(field).strip()
                        if field_clean and field_clean != 'nan':
                            sheet_fields.add(field_clean)
                    
                    discrepancies[entity]["sheet_fields"] = sorted(list(sheet_fields))
                    print(f"   📊 Google Sheets fields: {len(sheet_fields)} found")
                    
                    # Find discrepancies
                    missing_in_sheets = csv_fields - sheet_fields
                    extra_in_sheets = sheet_fields - csv_fields
                    
                    discrepancies[entity]["missing_in_sheets"] = sorted(list(missing_in_sheets))
                    discrepancies[entity]["extra_in_sheets"] = sorted(list(extra_in_sheets))
                    
                    # Report findings
                    if missing_in_sheets:
                        print(f"   ⚠️  Missing in Google Sheets: {len(missing_in_sheets)} fields")
                        for field in sorted(missing_in_sheets):
                            print(f"      - {field}")
                    
                    if extra_in_sheets:
                        print(f"   ⚠️  Extra in Google Sheets: {len(extra_in_sheets)} fields")
                        for field in sorted(extra_in_sheets):
                            print(f"      - {field}")
                    
                    if not missing_in_sheets and not extra_in_sheets:
                        print(f"   ✅ Perfect match! All fields align between sample CSV and Google Sheets")
                        
                else:
                    print(f"   ❌ Error: Could not find column '{mapping['field_column']}' in sheet '{mapping['sheet_name']}'")
                    
            except Exception as e:
                print(f"   ❌ Error reading Google Sheet '{mapping['sheet_name']}': {e}")
    
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
    
    # Print summary
    print(f"\n" + "="*80)
    print("📊 DISCREPANCY SUMMARY")
    print("="*80)
    
    total_missing = 0
    total_extra = 0
    
    for entity, data in discrepancies.items():
        missing_count = len(data["missing_in_sheets"])
        extra_count = len(data["extra_in_sheets"])
        total_missing += missing_count
        total_extra += extra_count
        
        status = "✅ Perfect" if missing_count == 0 and extra_count == 0 else "⚠️  Issues"
        print(f"{entity:20} | Missing: {missing_count:3d} | Extra: {extra_count:3d} | {status}")
    
    print("-" * 80)
    print(f"{'TOTAL':20} | Missing: {total_missing:3d} | Extra: {total_extra:3d}")
    
    if total_missing == 0 and total_extra == 0:
        print("\n🎉 Excellent! All fields are perfectly aligned between sample CSV files and Google Sheets!")
    else:
        print(f"\n💡 Recommendation: Review and update Google Sheets to align with sample CSV schema")
    
    print("="*80)
    
    return discrepancies

def update_metadata_from_google_sheet(old_metadata, sheet_operator, entity_name, sheet_name, field_column, type_column, description_column, fields_key, data_dir):
    """Updates a specific entity's metadata based solely on Google Sheet data."""
    
    print(f"\n📊 Updating {entity_name} metadata from Google Sheet...")
    
    try:
        # Get data from Google Sheet
        df = sheet_operator._get_sheet_data(sheet_name)
        
        if df.empty:
            print(f"❌ No data found in Google Sheet '{sheet_name}'")
            return old_metadata
            
        if field_column not in df.columns:
            print(f"❌ Column '{field_column}' not found in Google Sheet '{sheet_name}'")
            return old_metadata
            
        # Extract old descriptions as fallback
        old_descriptions = {}
        old_dv360_defs = {}
        if fields_key in old_metadata.get("metadata", {}):
            old_descriptions = {
                field: details.get('description', 'No description available.')
                for field, details in old_metadata["metadata"][fields_key].items()
            }
            old_dv360_defs = {
                field: details.get('dv360_definition', 'No DV360 definition available.')
                for field, details in old_metadata["metadata"][fields_key].items()
            }
        
        # Get field information from Google Sheet
        fields = df[field_column].dropna().tolist()
        field_types = {}
        field_descriptions = {}
        
        # Get DV360 definitions
        field_dv360_definitions = {}
        dv360_column = 'Definition DV360'
        
        # Process each field
        for _, row in df.iterrows():
            field_name = str(row[field_column]).strip()
            if field_name and field_name != 'nan':
                # Get type information
                if type_column in df.columns and not pd.isna(row[type_column]):
                    field_types[field_name] = str(row[type_column]).strip()
                else:
                    field_types[field_name] = 'string'  # Default type
                
                # Get description
                if description_column in df.columns and not pd.isna(row[description_column]):
                    description = str(row[description_column]).strip()
                    if description and description != 'nan':
                        field_descriptions[field_name] = description
                    else:
                        field_descriptions[field_name] = old_descriptions.get(field_name, 'No description available.')
                else:
                    field_descriptions[field_name] = old_descriptions.get(field_name, 'No description available.')
                
                # Get DV360 definition
                if dv360_column in df.columns and not pd.isna(row[dv360_column]):
                    dv360_definition = str(row[dv360_column]).strip()
                    if dv360_definition and dv360_definition != 'nan':
                        field_dv360_definitions[field_name] = dv360_definition
                    else:
                        field_dv360_definitions[field_name] = old_dv360_defs.get(field_name, 'No DV360 definition available.')
                else:
                    field_dv360_definitions[field_name] = old_dv360_defs.get(field_name, 'No DV360 definition available.')
        
        # Update metadata_fields with new structure
        updated_fields = {}
        for field in fields:
            description = field_descriptions.get(field, old_descriptions.get(field, 'No description available.'))
            field_type = field_types.get(field, 'string')
            dv360_definition = field_dv360_definitions.get(field, old_dv360_defs.get(field, 'No DV360 definition available.'))
            
            # Try to get sample data from sample CSV if available
            sample_data = []
            csv_file_mapping = {
                'Line_Items': 'line_items.csv',
                'Insertion_orders': 'insertion_orders.csv', 
                'Campaigns': 'campaigns.csv'
            }
            
            if entity_name in csv_file_mapping:
                sample_data_dir = os.path.join(data_dir, 'sample_sdf_data')
                csv_path = os.path.join(sample_data_dir, csv_file_mapping[entity_name])
                try:
                    df_csv = pd.read_csv(csv_path)
                    if not df_csv.empty and field in df_csv.columns:
                        samples = df_csv[field].dropna().unique()
                        # Filter samples to only include those with less than 500 characters
                        filtered_samples = [str(s) for s in samples if len(str(s)) < 500]
                        sample_data = filtered_samples[:3]
                except (FileNotFoundError, KeyError):
                    pass  # Sample CSV not available or field not found
            
            updated_fields[field] = {
                "type": field_type,
                "description": description,
                "dv360_definition": dv360_definition,
                "sample_data": sample_data
            }
            
            # Print status
            if field in field_descriptions and field_descriptions[field] != 'No description available.':
                print(f"✓ Updated '{field}' with Google Sheet description")
            elif field in old_descriptions:
                print(f"⚠ Using existing description for '{field}' (not found in Google Sheet)")
            else:
                print(f"⚠ No description found for '{field}'")
            
            # Print DV360 definition status
            if field in field_dv360_definitions and field_dv360_definitions[field] != 'No DV360 definition available.':
                print(f"✓ Updated '{field}' with DV360 definition")
            else:
                print(f"⚠ No DV360 definition found for '{field}'")
        
        old_metadata["metadata"][fields_key] = updated_fields
        print(f"✅ Successfully updated {len(fields)} fields for {entity_name}")
        
    except Exception as e:
        print(f"❌ Error updating {entity_name} metadata: {str(e)}")
    
    return old_metadata


def main():
    """Main function to update the general metadata file based solely on Google Sheet data."""
    data_dir = os.path.dirname(__file__)
    
    # Google Sheet URL
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit?gid=1009558974"
    
    print("🚀 Starting metadata update process...")
    print("="*80)
    
    try:
        # Initialize Google Sheet operator
        print("📊 Connecting to Google Sheets...")
        sheet_operator = GoogleSheetOperator(google_sheet_url)
        print("✅ Successfully connected to Google Sheets")
        
        # Step 1: Detect field discrepancies between sample CSV files and Google Sheets
        print("\n🔍 Checking for field discrepancies between sample CSV files and Google Sheets...")
        discrepancies = detect_field_discrepancies(google_sheet_url)
        
        # Step 2: Load existing metadata or create new structure
        metadata_file = os.path.join(data_dir, 'general_metadata.json')
        if os.path.exists(metadata_file):
            print(f"\n📄 Loading existing metadata from {metadata_file}...")
            with open(metadata_file, 'r') as f:
                general_metadata = json.load(f)
        else:
            print(f"\n📄 Creating new metadata structure...")
            general_metadata = {
                "metadata": {
                    "metadata_fields_Line_items": {},
                    "metadata_fields_Insertion_orders": {},
                    "metadata_fields_Campaigns": {}
                }
            }
        
        # Step 3: Update each entity from Google Sheets
        print("\n" + "="*80)
        print("📝 UPDATING METADATA FROM GOOGLE SHEETS")
        print("="*80)
        
        # Update Line Items
        general_metadata = update_metadata_from_google_sheet(
            general_metadata, sheet_operator,
            'Line_Items', 'Metadata : Line items', 
            'Line item champs', 'Type', 'Description after transformation',
            'metadata_fields_Line_items', data_dir
        )
        
        # Update Insertion Orders
        general_metadata = update_metadata_from_google_sheet(
            general_metadata, sheet_operator,
            'Insertion_orders', 'Metadata : Insertion orders',
            'Insertion Order champs', 'Type', 'Description after transformation', 
            'metadata_fields_Insertion_orders', data_dir
        )
        
        # Update Campaigns
        general_metadata = update_metadata_from_google_sheet(
            general_metadata, sheet_operator,
            'Campaigns', 'Metadata : Campaign',
            'Campaign champs', 'Type', 'Description after transformation',
            'metadata_fields_Campaigns', data_dir
        )
        
        # Step 4: Save the updated metadata
        print("\n" + "="*80)
        print("💾 SAVING UPDATED METADATA")
        print("="*80)
        
        with open(metadata_file, 'w') as f:
            json.dump(general_metadata, f, indent=4)
        
        print(f"✅ Successfully saved updated metadata to {metadata_file}")
        
        # Step 5: Summary
        print("\n" + "="*80)
        print("📊 UPDATE SUMMARY")
        print("="*80)
        
        for entity_name, entity_data in general_metadata["metadata"].items():
            field_count = len(entity_data)
            print(f"{entity_name:40} | Fields: {field_count:3d}")
        
        print("\n🎉 Metadata update completed successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error during metadata update: {str(e)}")
        print("Please check your Google Sheets connection and try again.")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--check-discrepancies":
        # Only run discrepancy detection
        google_sheet_url = "https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit?gid=1009558974"
        print("🔍 Running discrepancy detection only...")
        discrepancies = detect_field_discrepancies(google_sheet_url)
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python update_metadata.py                    # Run full metadata update")
        print("  python update_metadata.py --check-discrepancies  # Only check field discrepancies")
        print("  python update_metadata.py --help             # Show this help message")
    else:
        # Run full update process
        success = main()
        if not success:
            sys.exit(1)