import pandas as pd
from typing import Tuple, List, Dict
import numpy as np
import sys
import os
import json

# Add backend to path for importing configs
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

try:
    from config.configs import llm_gemini_flash
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    print("Warning: Could not import LLM configs. LLM-based checks will be disabled.")
    llm_gemini_flash = None
    ChatPromptTemplate = None


def detect_li_anomalies(line_items_df: pd.DataFrame,
                        campaigns_df: pd.DataFrame,
                        insertion_orders_df: pd.DataFrame,
                        naming_convention: str = None,
                        expected_markup: float = None) -> pd.DataFrame:
    """
    Main function that detects anomalies in line items dataframe.
    
    Checks performed:
    - Safeguards (brand safety, viewability, frequency capping, etc.)
    - Inventory consistency (premium IO vs public inventory)
    - Markup consistency (if expected_markup provided)
    - Naming convention format (LLM-based batch check)
    - Naming vs setup compliance (LLM-based validation that name matches actual config)
    
    Args:
        line_items_df: DataFrame containing line item data
        campaigns_df: DataFrame containing campaign data
        insertion_orders_df: DataFrame containing insertion order data
        naming_convention: Optional custom naming convention (defaults to partner default)
        expected_markup: Optional expected markup percentage for consistency check
        
    Returns:
        DataFrame containing only abnormal line items with anomalies_description column
    """
    
    # Create a copy to avoid modifying original
    df = line_items_df.copy()
    
    # Get default naming convention if not provided
    if naming_convention is None:
        partner_defaults = get_partner_defaults()
        naming_convention = partner_defaults.get('naming_convention', 'Country/Language - Targeting/Publisher - Device (Opt)')
    
    # List of check functions to apply
    check_functions = [
        check_li_safeguards,
        check_li_inventory_consistency,
        lambda li: check_li_markup_consistency(li, campaigns_df, insertion_orders_df, expected_markup) if expected_markup else (False, ""),
        # Note: Naming convention checks (format & setup compliance) are handled separately as batch operations
    ]
    
    # Perform LLM-based naming convention check (batch operation)
    naming_anomalies = {}
    if llm_gemini_flash is not None:
        try:
            naming_anomalies = check_li_naming_convention_batch(df, naming_convention)
        except Exception as e:
            print(f"Error in naming convention check: {str(e)}")
            naming_anomalies = {}
    
    # Perform LLM-based naming vs setup compliance check (batch operation)
    naming_setup_anomalies = {}
    if llm_gemini_flash is not None:
        try:
            naming_setup_anomalies = check_li_naming_vs_setup_batch(df, naming_convention)
        except Exception as e:
            print(f"Error in naming vs setup compliance check: {str(e)}")
            naming_setup_anomalies = {}
    
    # Initialize lists to store results
    is_abnormal_list = []
    anomalies_descriptions = []
    
    # Apply each check function to each row
    for idx, row in df.iterrows():
        row_anomalies = []
        row_is_abnormal = False
        
        # Run each check function
        for check_func in check_functions:
            try:
                is_abnormal, description = check_func(row, campaigns_df, insertion_orders_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                # Handle any errors in check functions gracefully
                print(f"Error in {check_func.__name__} for row {idx}: {str(e)}")
                continue
        
        # Add naming convention anomalies if present
        li_name = row.get('Name', '')
        if li_name in naming_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_anomalies[li_name])
        
        # Add naming vs setup compliance anomalies if present
        if li_name in naming_setup_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_setup_anomalies[li_name])
        
        is_abnormal_list.append(row_is_abnormal)
        # Join anomalies with semicolon for frontend rendering
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    # Add results to dataframe
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    # Filter to only abnormal line items
    abnormal_lis = df[df['is_abnormal']].copy()
    
    # Remove the temporary is_abnormal column
    abnormal_lis = abnormal_lis.drop('is_abnormal', axis=1)
    
    return abnormal_lis


def check_li_safeguards(li: pd.Series, campaigns_df: pd.DataFrame, insertion_orders_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if all required safeguards are present in line items (for active campaigns).
    
    Expected settings that must be present:
    - Brand safety exclusions (DCL/sensitive categories)
    - App URL exclusions (as applicable)
    - Environment targeting aligned with partner default
    - Viewability targeting appropriate to inventory type
    - Language settings (paid languages if applicable)
    - Device targeting configured
    - Frequency capping defined
    - Floodlight (conversion) attached where relevant
    - Channel and Keyword blacklist exclusions
    
    Args:
        li: Single line item row as pandas Series
        campaigns_df: DataFrame containing campaign data
        insertion_orders_df: DataFrame containing insertion order data
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    missing_safeguards = []
    
    # Only check active line items
    status = li.get('Status', '')
    if status != 'Active':
        return False, ""  # Skip inactive line items
    
    # 1. Check Brand Safety Exclusions
    dcl_exclusions = li.get('Digital Content Labels - Exclude', '')
    brand_safety_settings = li.get('Brand Safety Custom Settings', '')
    
    if pd.isna(dcl_exclusions) or dcl_exclusions == '':
        missing_safeguards.append("Digital Content Label exclusions")
    
    if pd.isna(brand_safety_settings) or brand_safety_settings == '':
        missing_safeguards.append("Brand Safety sensitive category exclusions")
    
    # 2. Check App URL Exclusions (if applicable - check if there's app inventory)
    app_targeting_include = li.get('App Targeting - Include', '')
    app_targeting_exclude = li.get('App Targeting - Exclude', '')
    
    # If app targeting is used for inclusion, should have exclusions too
    if not pd.isna(app_targeting_include) and app_targeting_include != '':
        if pd.isna(app_targeting_exclude) or app_targeting_exclude == '':
            missing_safeguards.append("App URL exclusions (app inventory detected)")
    
    # 3. Check Environment Targeting
    environment_targeting = li.get('Environment Targeting', '')
    
    if (pd.isna(environment_targeting) or environment_targeting == '') and li.get("Type", "") != "TrueView":
        missing_safeguards.append("Environment targeting")
    
    # 4. Check Viewability Targeting (for appropriate inventory types)
    viewability_targeting = li.get('Viewability Targeting Active View', '')
    inventory_source = li.get('Inventory Source Targeting - Include', '')
    private_deals = li.get('Private Deal Group Targeting Include', '')
    
    # Determine inventory type
    is_public_inventory = (not pd.isna(inventory_source) and inventory_source != '' and 
                          (pd.isna(private_deals) or private_deals == ''))
    
    # Public inventory should have viewability targeting
    if is_public_inventory:
        if pd.isna(viewability_targeting) or viewability_targeting == '' or viewability_targeting == 'All':
            missing_safeguards.append("Viewability targeting (required for public inventory)")
    
    # 5. Check Language Settings
    language_include = li.get('Language Targeting - Include', '')
    
    # Check if language targeting is configured (when applicable)
    # This is a basic check - you might want to add logic to determine when it's required
    if pd.isna(language_include) or language_include == '':
        missing_safeguards.append("Language targeting settings")
    
    # 6. Check Device Targeting
    device_targeting = li.get('Device Targeting - Include', '')
    
    if pd.isna(device_targeting) or device_targeting == '':
        missing_safeguards.append("Device targeting configuration")
    
    # 7. Check Frequency Capping
    freq_enabled = li.get('TrueView View Frequency Enabled') if li.get("Type", "") == "TrueView" else li.get('Frequency Enabled', False)
    freq_exposures = li.get('TrueView View Frequency Exposures') if li.get("Type", "") == "TrueView" else li.get('Frequency Exposures', 0)
    freq_amount = "Not applicable to TrueView line items" if li.get("Type", "") == "TrueView" else li.get('Frequency Amount', 0)
    freq_period = li.get('TrueView View Frequency Period') if li.get("Type", "") == "TrueView" else li.get('Frequency Period', '')
    
    # Convert to boolean if string
    if isinstance(freq_enabled, str):
        freq_enabled = freq_enabled.lower() == 'true'
    
    if not freq_enabled:
        missing_safeguards.append("Frequency capping (disabled)")
    elif pd.isna(freq_exposures) or freq_exposures == 0:
        missing_safeguards.append("Frequency exposures (not set or zero)")
    elif pd.isna(freq_amount) or freq_amount == 0 :
        missing_safeguards.append("Frequency amount (not set or zero)")
    elif pd.isna(freq_period) or freq_period == '':
        missing_safeguards.append("Frequency period (not set or zero)")

    # 8. Check Floodlight/Conversion Tracking (where relevant)
    # Check if this is a conversion-focused line item
    li_name = li.get('Name', '').lower()
    io_name = li.get('Io Name', '').lower()
    conversion_floodlight = li.get('Conversion Floodlight Activity Ids', '')
    
    # If name suggests conversion/performance focus, should have floodlight
    if any(keyword in li_name or keyword in io_name for keyword in ['conversion', 'convert', 'performance', 'cpa', 'acquisition']):
        if pd.isna(conversion_floodlight) or conversion_floodlight == '':
            missing_safeguards.append("Floodlight activity (required for conversion campaigns)")
    
    # 9. Check Channel and Keyword Blacklist Exclusions
    channel_exclude = li.get('Channel Targeting - Exclude', '')
    keyword_list_exclude = li.get('Keyword List Targeting - Exclude', '')
    
    if pd.isna(channel_exclude) or channel_exclude == '':
        missing_safeguards.append("Channel blacklist exclusions")
    
    if pd.isna(keyword_list_exclude) or keyword_list_exclude == '':
        missing_safeguards.append("Keyword blacklist exclusions")
    
    # Return results
    if missing_safeguards:
        return True, f"LI Missing Safeguards: {', '.join(missing_safeguards)};"
    
    return False, ""


def check_li_inventory_consistency(li: pd.Series, campaigns_df: pd.DataFrame, insertion_orders_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if inventory is consistent with IO naming (e.g., Premium IOs should use private inventory).
    
    Args:
        li: Single line item row as pandas Series
        campaigns_df: DataFrame containing campaign data
        insertion_orders_df: DataFrame containing insertion order data
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    io_name = li.get('Io Name', '')
    inventory_source = li.get('Inventory Source Targeting - Include', '')
    private_deals = li.get('Private Deal Group Targeting Include', '')
    
    # Check if IO is labeled as Premium
    if 'premium' in io_name.lower():
        # Check if using public inventory (no private deals)
        if (not pd.isna(inventory_source) and inventory_source != '' and 
            (pd.isna(private_deals) or private_deals == '')):
            return True, "Premium IO Uses Public Inventory: IO labeled as Premium but includes public inventory sources;"
    
    return False, ""


def check_li_markup_consistency(li: pd.Series, campaigns_df: pd.DataFrame, insertion_orders_df: pd.DataFrame, expected_markup: float = None) -> Tuple[bool, str]:
    """
    Check if revenue model/markup is consistent with expectations.
    
    Args:
        li: Single line item row as pandas Series
        campaigns_df: DataFrame containing campaign data
        insertion_orders_df: DataFrame containing insertion order data
        expected_markup: Expected markup percentage (if None, will skip check)
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    if expected_markup is None:
        return False, ""  # Skip if no expected markup provided
    
    partner_revenue = li.get('Partner Revenue Amount', np.nan)
    markup = li.get('Markup', np.nan)
    
    # Check if markup is present
    if pd.isna(partner_revenue) and pd.isna(markup):
        return True, "LI Markup Missing: No partner revenue amount or markup configured;"
    
    # Check markup value
    actual_markup = partner_revenue if not pd.isna(partner_revenue) else markup
    
    if not pd.isna(actual_markup):
        try:
            actual_markup = float(actual_markup)
            if abs(actual_markup - expected_markup) > 0.01:  # Allow small floating point differences
                return True, f"LI Markup Mismatch: Expected {expected_markup}% but found {actual_markup}%;"
        except (ValueError, TypeError):
            return True, f"LI Markup Invalid: Markup value '{actual_markup}' is not a valid number;"
    
    return False, ""


def check_li_naming_convention_batch(df: pd.DataFrame, 
                                     naming_convention: str = "Country/Language - Targeting/Publisher - Device (Opt)") -> Dict[str, str]:
    """
    Check line item naming convention using LLM for batch processing.
    Returns a dictionary mapping line item names to their anomaly descriptions.
    
    Args:
        df: DataFrame containing line items
        naming_convention: Expected naming convention pattern
        
    Returns:
        Dictionary mapping line item names to anomaly descriptions
    """
    if llm_gemini_flash is None or ChatPromptTemplate is None:
        print("LLM not available, skipping naming convention check")
        return {}
    
    # Extract unique line item names
    li_names = df['Name'].dropna().unique().tolist()
    
    if not li_names:
        return {}
    
    # Create prompt for LLM
    naming_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert in advertising campaign naming conventions.
        
        The expected naming convention for line items is like this: {naming_convention}
        
        Analyze the provided line item names and identify:
        1. NON-COMPLIANT: Names that don't follow the convention structure
        2. OUTLIERS: Names that are significantly different from the pattern of other names
        
        Return a JSON object with this structure:
        {{
            "non_compliant": [
                {{"name": "line_item_name", "reason": "specific reason why it's non-compliant"}}
            ],
            "outliers": [
                {{"name": "line_item_name", "reason": "why it's an outlier"}}
            ]
        }}
        
        Be strict about the convention but understand common variations:
        - Delimiters can be "-", "_", or spaces
        - Order might vary slightly
        - Additional metadata might be present
        
        Only return names that have clear issues. If a name is close enough to the convention, don't flag it.
        """), 
        ("human", "Analyze these line item names:\n{li_names_str}")
    ])
    
    # Format line item names for analysis
    li_names_str = "\n".join([f"- {name}" for name in li_names[:100]])  # Limit to 100 for token limits
    
    try:
        # Invoke LLM
        chain = naming_prompt | llm_gemini_flash
        response = chain.invoke({
            "naming_convention": naming_convention,
            "li_names_str": li_names_str
        })
        
        # Parse LLM response
        response_text = response.content
        
        # Extract JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "{" in response_text and "}" in response_text:
            # Find the JSON object in the response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
        else:
            print("Could not extract JSON from LLM response")
            return {}
        
        # Parse JSON
        result = json.loads(json_str)
        
        # Build anomaly dictionary
        anomaly_dict = {}
        
        # Process non-compliant names
        for item in result.get("non_compliant", []):
            name = item.get("name", "")
            reason = item.get("reason", "Non-compliant with naming convention")
            if name in li_names:
                anomaly_dict[name] = f"Naming Convention Non-Compliance: {reason};"
        
        # Process outlier names
        for item in result.get("outliers", []):
            name = item.get("name", "")
            reason = item.get("reason", "Outlier in naming pattern")
            if name in li_names:
                if name in anomaly_dict:
                    anomaly_dict[name] += f"; Naming Outlier: {reason};"
                else:
                    anomaly_dict[name] = f"Naming Outlier: {reason};"
        
        return anomaly_dict
        
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error in LLM naming convention check: {e}")
        return {}


def check_li_naming_vs_setup_batch(df: pd.DataFrame, 
                                    naming_convention: str = "Country/Language - Targeting/Publisher - Device (Opt)") -> Dict[str, str]:
    """
    Check if line item naming is compliant with actual setup/configuration using LLM.
    This validates that what's in the name matches what's actually configured.
    
    For example, if name says "Belgium - Mobile - Affinity" but the line item is configured for:
    - Geography: France (mismatch!)
    - Device: Desktop (mismatch!)
    - Audience: In-Market audiences (mismatch!)
    
    Returns a dictionary mapping line item names to their compliance anomaly descriptions.
    
    Args:
        df: DataFrame containing line items with all configuration columns
        naming_convention: Expected naming convention pattern
        
    Returns:
        Dictionary mapping line item names to compliance anomaly descriptions
    """
    if llm_gemini_flash is None or ChatPromptTemplate is None:
        print("LLM not available, skipping naming vs setup compliance check")
        return {}
    
    # Select relevant columns for comparison
    relevant_columns = [
        'Name', 
        'Geography Targeting - Include',
        'Geography Targeting - Exclude',
        'Device Targeting - Include',
        'Device Targeting - Exclude',
        'Language Targeting - Include',
        'Audience Targeting - Include',
        'Affinity & In Market Targeting - Include',
        'Combined Audience Targeting',
        'Channel Targeting - Include',
        'Site Targeting - Include',
        'Environment Targeting',
        'Demographic Targeting Age',
        'Demographic Targeting Gender',
        'Content Genre Targeting - Include',
        'Category Targeting - Include'
    ]
    
    # Filter to only existing columns
    available_columns = [col for col in relevant_columns if col in df.columns]
    df_subset = df[available_columns].copy()
    
    # Limit to first 50 line items to avoid token limits
    df_subset = df_subset.head(50)
    
    # Create prompt for LLM
    compliance_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert in advertising campaign setup validation.

Your task is to compare line item NAMES against their ACTUAL CONFIGURATION and identify mismatches.

The expected naming convention is: {naming_convention}

For each line item, analyze:
1. Parse the name to extract what SHOULD be configured (e.g., "Belgium - Mobile - Affinity" implies Belgium geo, Mobile device, Affinity audiences)
2. Check the actual configuration columns to see what IS configured
3. Identify mismatches between the name and actual setup

Common patterns to check:
- Geography: Name mentions country/region but different geo is targeted
- Device: Name mentions "Mobile"/"Desktop"/"Tablet" but different devices targeted
- Audience: Name mentions audience type but different audiences configured
- Language: Name has language code but different languages targeted
- Environment: Name implies "App" or "Web" but different environment set

Return a JSON object with this structure:
{{
    "mismatches": [
        {{
            "name": "line_item_name",
            "issues": [
                {{"aspect": "Geography", "name_implies": "Belgium", "actual_config": "France"}},
                {{"aspect": "Device", "name_implies": "Mobile", "actual_config": "Desktop"}}
            ]
        }}
    ]
}}

Only flag clear mismatches. If the name is generic or configuration seems aligned, don't flag it.
Be intelligent about variations (e.g., "BE" = "Belgium", "Mobile" = "DEVICE_TYPE_SMART_PHONE").
"""),
        ("human", "Analyze these line items:\n\n{line_items_data}")
    ])

    # Format data for LLM
    line_items_data = []
    for idx, row in df_subset.iterrows():
        item_str = f"Name: {row['Name']}\n"
        for col in available_columns[1:]:  # Skip 'Name' column
            val = row[col]
            if pd.notna(val) and val != '':
                item_str += f"  {col}: {val}\n"
        line_items_data.append(item_str)
    
    line_items_str = "\n---\n".join(line_items_data)
    
    try:
        # Invoke LLM
        chain = compliance_prompt | llm_gemini_flash
        response = chain.invoke({
            "naming_convention": naming_convention,
            "line_items_data": line_items_str
        })
        
        # Parse LLM response
        response_text = response.content
        
        # Extract JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
        else:
            print("Could not extract JSON from LLM response")
            return {}
        
        # Parse JSON
        result = json.loads(json_str)
        
        # Build anomaly dictionary
        anomaly_dict = {}
        
        # Process mismatches
        for item in result.get("mismatches", []):
            name = item.get("name", "")
            issues = item.get("issues", [])
            
            if name and issues:
                issue_descriptions = []
                for issue in issues:
                    aspect = issue.get("aspect", "")
                    name_implies = issue.get("name_implies", "")
                    actual_config = issue.get("actual_config", "")
                    issue_descriptions.append(f"{aspect}: name implies '{name_implies}' but actual is '{actual_config}'")
                
                if issue_descriptions:
                    anomaly_dict[name] = f"Naming vs Setup Mismatch: {'; '.join(issue_descriptions)};"
        
        return anomaly_dict
        
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error in LLM naming vs setup compliance check: {e}")
        return {}


def check_li_naming_convention(li: pd.Series, campaigns_df: pd.DataFrame, insertion_orders_df: pd.DataFrame, naming_convention: str = "Country/Language - Targeting/Publisher - Device (Opt)") -> Tuple[bool, str]:
    """
    Individual line item naming convention check (for single item processing).
    This is a simpler pattern-based check without LLM.
    
    Args:
        li: Single line item row as pandas Series
        campaigns_df: DataFrame containing campaign data
        insertion_orders_df: DataFrame containing insertion order data
        naming_convention: Expected naming convention
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    li_name = li.get('Name', '')
    
    if pd.isna(li_name) or li_name == '':
        return True, "Line item name is missing;"
    
    # Basic pattern check (can be enhanced based on specific requirements)
    # Check if name has at least 2 segments separated by common delimiters
    import re
    segments = re.split(r'[-_|/]', li_name)
    segments = [s.strip() for s in segments if s.strip()]
    
    if len(segments) < 2:
        return True, f"Naming Convention Issue: Name '{li_name}' doesn't follow expected pattern (too few segments);"
    
    # Additional basic checks can be added here
    # For example, check if first segment looks like country/language code
    # Check if common keywords are present, etc.
    
    return False, ""


# Configuration for partner defaults
PARTNER_DEFAULTS = {
    'default': {
        'environment': 'Web',
        'markup_percentage': None,  # Set to a value if you have a default
        'require_floodlight_for_conversion': True,
        'naming_convention': 'Country/Language - Targeting/Publisher - Device (Opt)'
    }
    # Add partner-specific defaults here
    # Example:
    # 'partner_x': {
    #     'environment': 'Web;App',
    #     'markup_percentage': 15.0,
    #     'naming_convention': 'Campaign - Audience - Creative - Platform'
    # }
}


def get_partner_defaults(partner_name: str = None) -> Dict:
    """
    Get default settings for a specific partner.
    
    Args:
        partner_name: Name of the partner
        
    Returns:
        Dictionary of partner default settings
    """
    if partner_name and partner_name in PARTNER_DEFAULTS:
        return PARTNER_DEFAULTS[partner_name]
    return PARTNER_DEFAULTS['default']


# Example usage
if __name__ == "__main__":
    from utils.constants import LOCAL_DATA_PATH
    
    # Load data from the local data path
    line_items_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'sample_sdf_data/line_items.csv'))
    campaigns_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'sample_sdf_data/campaigns.csv'))
    insertion_orders_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'sample_sdf_data/insertion_orders.csv'))
    
    # Detect anomalies (includes LLM-based naming convention check)
    abnormal_lis = detect_li_anomalies(line_items_df, campaigns_df, insertion_orders_df)
    
    # Save results to CSV
    abnormal_lis.to_csv(os.path.join(LOCAL_DATA_PATH, 'sample_sdf_data/abnormal_line_items.csv'), index=False)
    
    # Display results
    print(f"Found {len(abnormal_lis)} abnormal line items")
    for idx, row in abnormal_lis.iterrows():
        print(f"\nLine Item: {row['Name']}")
        print(f"Anomalies: {', '.join(row['anomalies_description'])}")
    
    # Example: Test naming convention check separately
    # if llm_gemini_flash is not None:
    #     sample_df = pd.DataFrame({
    #         'Name': [
    #             'BE-FR - Audience1 - Mobile',  # Compliant
    #             'NL - Publisher XYZ',           # Compliant (device optional)
    #             'Test Campaign 123',             # Non-compliant
    #             'x',                             # Outlier
    #             'US-EN - Remarketing - Desktop - Extra Info',  # Compliant with extra
    #         ]
    #     })
    #     naming_issues = check_li_naming_convention_batch(sample_df)
    #     print("\nNaming Convention Issues Found:")
    #     for name, issue in naming_issues.items():
    #         print(f"  {name}: {issue}")
