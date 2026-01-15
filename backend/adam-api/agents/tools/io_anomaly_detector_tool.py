import pandas as pd
from typing import Tuple, List, Dict
import numpy as np
import re
import sys
import os
import json

# Add backend to path for importing configs if needed
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

# DV360 Campaign Mapping for compatibility validation
DV360_CAMPAIGN_MAPPING = {
    "brand_awareness": {
        "objective": "Brand awareness",
        "description": "Increase brand visibility and reach a broad audience",
        "kpis": [
            {
                "name": "CPCL",
                "description": "Cost Per Completed Listen",
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # Maximize completed in-view and audible
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "CPCV", 
                "description": "Cost Per Completed View",
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # Maximize completed in-view and audible
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "CPIAVC",
                "description": "Cost Per In-View Audible and Visible on Completion",
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # Maximize completed in-view and audible
                    "IVO_TEN",    # Maximize viewable for at least 10 seconds
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "CPM",
                "description": "Cost Per Mille (Thousand Impressions)",
                "compatible_bid_strategies": [
                    "CIVA",  # Maximize viewable impressions / Target viewable impressions
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "CPV",
                "description": "Cost Per View",
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # For video views
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "Audio CR",
                "description": "Audio Completion Rate",
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # Maximize completed in-view and audible
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "Video CR",
                "description": "Video Completion Rate", 
                "compatible_bid_strategies": [
                    "AV_VIEWED",  # Maximize completed in-view and audible
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "TOS10",
                "description": "Time On Screen 10 seconds",
                "compatible_bid_strategies": [
                    "IVO_TEN",  # Maximize viewable for at least 10 seconds
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "VCPM",
                "description": "Viewable Cost Per Mille",
                "compatible_bid_strategies": [
                    "CIVA",  # Maximize viewable impressions
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "VTR",
                "description": "View Through Rate",
                "compatible_bid_strategies": [
                    "CIVA"  # Maximize viewable impressions
                ]
            },
            {
                "name": "Custom impression value / cost",
                "description": "Value to Cost Ratio",
                "compatible_bid_strategies": [
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "% Viewability",
                "description": "Viewability Percentage",
                "compatible_bid_strategies": [
                    "CIVA",     # Maximize viewable impressions
                    "IVO_TEN"   # Maximize viewable for at least 10 seconds
                ]
            }
        ],
        "supported_line_item_types": [
            "Display",
            "Video", 
            "Mobile app install",
            "Ads in mobile apps",
            "YouTube & partners video",
            "YouTube & partners audio"
        ]
    },
    "clicks": {
        "objective": "Clicks",
        "description": "Maximize the number of clicks to your website or landing page",
        "kpis": [
            {
                "name": "CPC",
                "description": "Cost Per Click",
                "compatible_bid_strategies": [
                    "CPC",  # Target CPC / Maximize clicks
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "CTR",
                "description": "Click Through Rate",
                "compatible_bid_strategies": [
                    "CPC"  # Target CPC / Maximize clicks
                ]
            },
            {
                "name": "Custom impression value / cost",
                "description": "Value to Cost Ratio",
                "compatible_bid_strategies": [
                    "custom impr. value/cost"
                ]
            }
        ],
        "supported_line_item_types": [
            "Display",
            "Video",
            "Mobile app install", 
            "Ads in mobile apps",
            "Demand Gen"
        ]
    },
    "conversions": {
        "objective": "Conversions",
        "description": "Drive user actions such as sign-ups, sales, downloads etc.",
        "kpis": [
            {
                "name": "CPA",
                "description": "Cost Per Acquisition/Action",
                "compatible_bid_strategies": [
                    "CPA",  # Target CPA / Maximize conversions
                    "custom impr. value/cost"
                ]
            },
            {
                "name": "Click CVR",
                "description": "Click Conversion Rate",
                "compatible_bid_strategies": [
                    "CPA"  # Maximize conversions
                ]
            },
            {
                "name": "Impression CVR",
                "description": "Impression Conversion Rate",
                "compatible_bid_strategies": [
                    "CPA"  # Maximize conversions
                ]
            },
            {
                "name": "Custom impression value / cost",
                "description": "Value to Cost Ratio",
                "compatible_bid_strategies": [
                    "custom impr. value/cost"
                ]
            }
        ],
        "supported_line_item_types": [
            "Display",
            "Video",
            "Audio",
            "Mobile app install",
            "Ads in mobile apps", 
            "YouTube & partners video",
            "Demand Gen"
        ]
    }
}


def detect_io_anomalies(insertion_orders_df: pd.DataFrame,
                       campaigns_df: pd.DataFrame,
                       line_items_df: pd.DataFrame,
                       naming_convention: str = None,
                       default_cpm_cap: float = 5.0) -> pd.DataFrame:
    """
    Main function that detects anomalies in insertion orders dataframe.
    
    Args:
        insertion_orders_df: DataFrame containing insertion order data
        campaigns_df: DataFrame containing campaign data
        line_items_df: DataFrame containing line item data
        naming_convention: Optional custom naming convention (defaults to standard)
        default_cpm_cap: Default CPM cap value to check against
        
    Returns:
        DataFrame containing only abnormal IOs with anomalies_description column
    """
    
    # Create a copy to avoid modifying original
    df = insertion_orders_df.copy()
    
    # Get default naming convention if not provided
    if naming_convention is None:
        naming_convention = "Campaign Name - Funnel - Support - Country/Language (opt) Suffix"
    
    # List of check functions to apply
    check_functions = [
        check_naming_vs_kpi,
        check_kpi_vs_objective,
        check_kpi_vs_optimization,  # Placeholder for optimization check (to be implemented)
        lambda io, campaigns_df, line_items_df: check_cpm_capping(io, campaigns_df, line_items_df, default_cpm_cap),
    ]
    
    # Perform LLM-based naming convention check (batch operation)
    naming_anomalies = {}
    if llm_gemini_flash is not None:
        try:
            pass
            #naming_anomalies = check_io_naming_convention_batch(df, naming_convention)
        except Exception as e:
            print(f"Error in IO naming convention check: {str(e)}")
            naming_anomalies = {}
    
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
                is_abnormal, description = check_func(row, campaigns_df, line_items_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                # Handle any errors in check functions gracefully
                print(f"Error in check function for row {idx}: {str(e)}")
                continue
        
        # Add naming convention anomalies if present
        io_name = row.get('Name', '')
        if io_name in naming_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_anomalies[io_name])
        
        is_abnormal_list.append(row_is_abnormal)
        # Join anomalies with semicolon for frontend rendering
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    # Add results to dataframe
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    # Filter to only abnormal IOs
    abnormal_ios = df[df['is_abnormal']].copy()
    
    # Remove the temporary is_abnormal column
    abnormal_ios = abnormal_ios.drop('is_abnormal', axis=1)
    
    return abnormal_ios


def check_naming_vs_kpi(io: pd.Series, campaigns_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if IO naming-derived objective matches configured KPI.
    
    Mapping:
    - Awareness ↔ CPM (or CTR for reach+attention mixes)
    - Clicks/Consideration ↔ CTR target (e.g., 0.2–0.4%) or CPC proxy
    - Conversion ↔ CPA
    
    Args:
        io: Single IO row as pandas Series
        campaigns_df: DataFrame containing campaign data
        line_items_df: DataFrame containing line item data
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    io_name = io.get('Name', '')
    kpi_type = io.get('Kpi Type', '')
    kpi_value = io.get('Kpi Value', np.nan)
    
    if pd.isna(io_name) or io_name == '':
        return False, ""  # Skip if no name
    
    # Extract funnel stage from name (case-insensitive)
    name_lower = io_name.lower()
    
    # Determine inferred objective from naming
    inferred_objective = None
    expected_kpis = []
    
    # Check for Awareness keywords
    if any(keyword in name_lower for keyword in ['awareness', 'aware', 'branding', 'reach']):
        inferred_objective = 'Awareness'
        expected_kpis = ['CPM', 'CTR']  # CPM primary, CTR acceptable for reach+attention
    
    # Check for Consideration/Clicks keywords
    elif any(keyword in name_lower for keyword in ['consideration', 'consider', 'clicks', 'traffic', 'engagement']):
        inferred_objective = 'Consideration'
        expected_kpis = ['CTR', 'CPC']  # CTR primary, CPC as proxy
    
    # Check for Conversion keywords
    elif any(keyword in name_lower for keyword in ['conversion', 'convert', 'sales', 'acquisition', 'performance']):
        inferred_objective = 'Conversion'
        expected_kpis = ['CPA']
    
    # If objective was inferred, check against actual KPI
    if inferred_objective and expected_kpis:
        if pd.isna(kpi_type) or kpi_type == '':
            return True, f"IO Objective/KPI Mismatch: Name suggests {inferred_objective} but KPI type is missing;"
        
        if kpi_type not in expected_kpis:
            return True, f"IO Objective/KPI Mismatch: Name suggests {inferred_objective} (expects {'/'.join(expected_kpis)}) but KPI is {kpi_type};"
        
        # Additional check for CTR targets in Consideration campaigns
        if inferred_objective == 'Consideration' and kpi_type == 'CTR':
            if not pd.isna(kpi_value):
                # Check if CTR is within typical consideration range (0.2-0.4%)
                if kpi_value < 0.2 or kpi_value > 0.4:
                    return True, f"IO CTR target mismatch: Consideration campaign has CTR target {kpi_value}% outside typical range (0.2%-0.4%);"
    
    return False, ""


def check_kpi_vs_objective(io: pd.Series, campaigns_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if KPI matches well with selected IO Objective.
    
    Args:
        io: Single IO row as pandas Series
        campaigns_df: DataFrame containing campaign data
        line_items_df: DataFrame containing line item data
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    kpi_type = io.get('Kpi Type', '')
    io_objective = io.get('Io Objective', '')
    
    # Define acceptable objectives for each KPI
    kpi_objective_mapping = {
        'CPM': ['Reach', 'Brand awareness and reach', 'Viewable impressions', 'No Objective'],
        'CTR': ['Click', 'Clicks', 'Traffic', 'Engagement', 'No Objective'],
        'CPA': ['Conversion', 'Conversions', 'Sales', 'Lead', 'No Objective'],
        'CPC': ['Click', 'Clicks', 'Traffic', 'No Objective']
    }
    
    # Skip if no KPI type
    if pd.isna(kpi_type) or kpi_type == '':
        return False, ""
    
    # Check if IO objective is set
    if pd.isna(io_objective) or io_objective == '':
        return True, f"IO KPI/Objective Mismatch: KPI is {kpi_type} but IO Objective is not set;"
    
    # Check if objective matches KPI
    if kpi_type in kpi_objective_mapping:
        acceptable_objectives = kpi_objective_mapping[kpi_type]
        
        # Check if current objective is acceptable for this KPI
        objective_match = False
        for acceptable in acceptable_objectives:
            if acceptable.lower() in io_objective.lower():
                objective_match = True
                break
        
        if not objective_match and io_objective != 'No Objective':
            return True, f"IO KPI/Objective Mismatch: KPI is {kpi_type} but IO Objective is '{io_objective}' (expected: {'/'.join(acceptable_objectives)});"
    
    return False, ""


def check_kpi_vs_optimization(io: pd.Series, campaigns_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if KPI matches well with optimization/bid strategy settings using DV360 compatibility rules.
    
    This function validates the compatibility between:
    1. Campaign funnel (extracted from IO name) and KPI
    2. KPI and bid strategy (optimization)
    3. Line item types and funnel objective
    
    Funnel mapping:
    - "Awareness" → Brand awareness objective
    - "Consideration" → Clicks objective  
    - "Conversion" → Conversions objective
    
    Expected IO name format: "Campaign Name - Funnel - Type - Details"
    
    Note: This check only runs when 'Insertion Order Optimization' is True.
    
    Args:
        io: Single IO row as pandas Series
        campaigns_df: DataFrame containing campaign data
        line_items_df: DataFrame containing line item data
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    try:
        # Get IO details
        io_name = io.get('Name', '')
        io_kpi = io.get('Kpi Type', '')  # Updated column name
        io_bid_strategy = io.get('Bid Strategy Unit', '')  # Updated column name
        io_optimization = io.get('Insertion Order Optimization', '')
        
        # Skip if Insertion Order Optimization is not True
        if io_optimization != 'True':
            return False, ""
        
        # Skip if essential fields are missing
        if not io_kpi or not io_bid_strategy or not io_name:
            return False, ""
        
        # Extract funnel from IO name and map to objective
        objective_key = None
        io_funnel = ""
        
        # Parse funnel from name (expected format: "Campaign - Funnel - ...")
        name_parts = io_name.split(' - ')
        if len(name_parts) >= 2:
            io_funnel = name_parts[1].strip().lower()
            
            # Map funnel to objective keys
            if 'awareness' in io_funnel:
                objective_key = 'brand_awareness'
            elif 'consideration' in io_funnel:
                objective_key = 'clicks'  # Consideration maps to Clicks
            elif 'conversion' in io_funnel:
                objective_key = 'conversions'
        
        # If we can't map the objective, skip validation
        if not objective_key or objective_key not in DV360_CAMPAIGN_MAPPING:
            return False, ""
        
        objective_config = DV360_CAMPAIGN_MAPPING[objective_key]
        anomalies = []
        
        # Check 1: Objective-KPI compatibility
        kpi_found = False
        compatible_kpi = None
        for kpi_config in objective_config['kpis']:
            if kpi_config['name'].lower() in io_kpi.lower() or io_kpi.lower() in kpi_config['name'].lower():
                kpi_found = True
                compatible_kpi = kpi_config
                break
        
        if not kpi_found:
            available_kpis = [kpi['name'] for kpi in objective_config['kpis']]
            anomalies.append(f"KPI '{io_kpi}' is not compatible with funnel '{io_funnel}' (objective: {objective_config['objective']}). Compatible KPIs: {', '.join(available_kpis)};")
        
        # Check 2: KPI-Bid Strategy compatibility (only if KPI was found)
        if kpi_found and compatible_kpi:
            bid_strategy_compatible = False
            for strategy in compatible_kpi['compatible_bid_strategies']:
                if strategy.lower() in io_bid_strategy.lower() or io_bid_strategy.lower() in strategy.lower():
                    bid_strategy_compatible = True
                    break
            
            if not bid_strategy_compatible:
                anomalies.append(f"Bid strategy '{io_bid_strategy}' is not compatible with KPI '{io_kpi}'. Compatible strategies: {', '.join(compatible_kpi['compatible_bid_strategies'])};")
        
        # Check 3: Line item type compatibility (if we have line items for this IO)
        io_line_items = line_items_df[line_items_df['Insertion order'] == io_name] if 'Insertion order' in line_items_df.columns else pd.DataFrame()
        
        if not io_line_items.empty and 'Type' in io_line_items.columns:
            unsupported_types = []
            for _, li in io_line_items.iterrows():
                li_type = li.get('Type', '')
                if li_type:
                    type_supported = False
                    for supported_type in objective_config['supported_line_item_types']:
                        if supported_type.lower() in li_type.lower() or li_type.lower() in supported_type.lower():
                            type_supported = True
                            break
                    
                    if not type_supported and li_type not in unsupported_types:
                        unsupported_types.append(li_type)
            
            if unsupported_types:
                supported_types = ', '.join(objective_config['supported_line_item_types'])
                anomalies.append(f"Line item type(s) '{', '.join(unsupported_types)}' not supported for funnel '{io_funnel}' (objective: {objective_config['objective']}). Supported types: {supported_types};")
        
        # Check 4: Common misconfigurations
        # High severity checks
        if objective_key == 'brand_awareness' and any(term in io_kpi for term in ['CPA', 'Click CVR', 'Impression CVR']):
            anomalies.append(f"HIGH SEVERITY: Using conversion-focused KPI '{io_kpi}' with awareness funnel;")
        
        if objective_key == 'conversions' and any(term in io_kpi for term in ['CPM', '% Viewability', 'VTR', 'VCPM']):
            anomalies.append(f"HIGH SEVERITY: Using brand awareness KPI '{io_kpi}' with conversion funnel;")
        
        if io_bid_strategy == 'CPA' and io_kpi != 'CPA':
            anomalies.append(f"HIGH SEVERITY: CPA bid strategy without CPA KPI (current KPI: {io_kpi});")
        
        # Medium severity checks
        if io_bid_strategy == 'CPC' and objective_key == 'brand_awareness':
            anomalies.append(f"MEDIUM SEVERITY: CPC bid strategy with awareness funnel;")
        
        # Return results
        if anomalies:
            return True, f"Funnel-KPI-Optimization Compatibility Issues: {' | '.join(anomalies)};"
        
        return False, ""
    
    except Exception as e:
        # Handle any errors gracefully
        print(f"Error in funnel-KPI-optimization compatibility check: {str(e)}")
        return False, ""


def check_cpm_capping(io: pd.Series, campaigns_df: pd.DataFrame, line_items_df: pd.DataFrame, default_cpm_cap: float = 5.0) -> Tuple[bool, str]:
    """
    Check if CPM capping is properly configured when CPM is the KPI.
    
    Args:
        io: Single IO row as pandas Series
        campaigns_df: DataFrame containing campaign data
        line_items_df: DataFrame containing line item data
        default_cpm_cap: Default CPM cap value to check against
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    kpi_type = io.get('Kpi Type', '')
    kpi_value = io.get('Kpi Value', np.nan)
    
    # Only check if KPI is CPM
    if kpi_type != 'CPM':
        return False, ""
    
    # Check if CPM cap is set
    if pd.isna(kpi_value):
        return True, f"IO Missing/Invalid CPM Cap: KPI is CPM but no CPM cap is set;"
    
    # Convert to float if string
    try:
        if isinstance(kpi_value, str):
            kpi_value = float(kpi_value)
    except (ValueError, TypeError):
        return True, f"IO Missing/Invalid CPM Cap: CPM cap value '{kpi_value}' is invalid;"
    
    # Check if CPM cap is 0 (effectively no cap)
    if kpi_value == 0:
        return True, f"IO Missing/Invalid CPM Cap: KPI is CPM but CPM cap is set to 0 (no cap);"
    
    # Check if CPM cap exceeds the default ceiling
    if kpi_value > default_cpm_cap:
        return True, f"IO Missing/Invalid CPM Cap: CPM cap ({kpi_value}) exceeds agreed ceiling ({default_cpm_cap});"
    
    return False, ""


def check_io_naming_convention_batch(df: pd.DataFrame, 
                                    naming_convention: str = "Campaign Name - Funnel - Support - Country/Language (opt) Suffix") -> Dict[str, str]:
    """
    Check IO naming convention using LLM for batch processing.
    Returns a dictionary mapping IO names to their anomaly descriptions.
    
    Args:
        df: DataFrame containing insertion orders
        naming_convention: Expected naming convention pattern
        
    Returns:
        Dictionary mapping IO names to anomaly descriptions
    """
    if llm_gemini_flash is None or ChatPromptTemplate is None:
        print("LLM not available, skipping IO naming convention check")
        return {}
    
    # Extract unique IO names
    io_names = df['Name'].dropna().unique().tolist()
    
    if not io_names:
        return {}
    
    # Create prompt for LLM
    naming_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert in advertising campaign naming conventions for Insertion Orders.
        
        The expected naming convention for IOs is: {naming_convention}
        
        Where:
        - Campaign Name: The associated campaign name
        - Funnel: The funnel stage (Awareness, Consideration, Conversion, etc.)
        - Support: The media/support type
        - Country/Language: Geographic and language targeting (Optional - e.g., "BE-FR", "NL", "US-EN")
        - Suffix: Media type indicator
          * PAD: HTML5, Xtra Social, Native, Premium Display
          * PAV: Video, Youtube video, Demand Gen
          * PAR: Audio, Premium audio
          * PAOH: DOOH (Digital Out-Of-Home)
        
        Analyze the provided IO names and identify:
        1. NON-COMPLIANT: Names that don't follow the convention structure
        2. OUTLIERS: Names that are significantly different from the pattern of other names
        3. SUFFIX_ISSUES: Names with incorrect or missing suffix codes
        
        Return a JSON object with this structure:
        {{
            "non_compliant": [
                {{"name": "io_name", "reason": "specific reason why it's non-compliant"}}
            ],
            "outliers": [
                {{"name": "io_name", "reason": "why it's an outlier"}}
            ],
            "suffix_issues": [
                {{"name": "io_name", "reason": "suffix problem description"}}
            ]
        }}
        
        Be strict about the convention but understand common variations:
        - Delimiters can be "-", "_", "@", or spaces
        - Order might vary slightly
        - Additional metadata might be present
        - Check that media types match their suffix codes
        
        Only return names that have clear issues. If a name is close enough to the convention, don't flag it.
        """),
        ("human", "Analyze these IO names:\n{io_names_str}")
    ])
    
    # Format IO names for analysis
    io_names_str = "\n".join([f"- {name}" for name in io_names[:100]])  # Limit to 100 for token limits
    
    try:
        # Invoke LLM
        chain = naming_prompt | llm_gemini_flash
        response = chain.invoke({
            "naming_convention": naming_convention,
            "io_names_str": io_names_str
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
            if name in io_names:
                anomaly_dict[name] = f"IO Naming Convention Non-Compliance: {reason};"
        
        # Process outlier names
        for item in result.get("outliers", []):
            name = item.get("name", "")
            reason = item.get("reason", "Outlier in naming pattern")
            if name in io_names:
                if name in anomaly_dict:
                    anomaly_dict[name] += f"; IO Naming Outlier: {reason};"
                else:
                    anomaly_dict[name] = f"IO Naming Outlier: {reason};"
        
        # Process suffix issues
        for item in result.get("suffix_issues", []):
            name = item.get("name", "")
            reason = item.get("reason", "Suffix code issue")
            if name in io_names:
                if name in anomaly_dict:
                    anomaly_dict[name] += f"; IO Suffix Issue: {reason};"
                else:
                    anomaly_dict[name] = f"IO Suffix Issue: {reason};"
        
        return anomaly_dict
        
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response as JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error in LLM IO naming convention check: {e}")
        return {}


# Configuration function to update default CPM cap
def set_default_cpm_cap(new_cap: float):
    """
    Update the default CPM cap value used in checks.
    This would typically be called based on client/partner settings.
    """
    global DEFAULT_CPM_CAP
    DEFAULT_CPM_CAP = new_cap


# Partner-specific CPM caps (can be extended)
PARTNER_CPM_CAPS: Dict[str, float] = {
    'default': 5.0,
    # Add partner-specific caps here
    # 'partner_name': cap_value
}


def get_partner_cpm_cap(partner_name: str = None) -> float:
    """
    Get the CPM cap for a specific partner.
    
    Args:
        partner_name: Name of the partner
        
    Returns:
        CPM cap value for the partner
    """
    if partner_name and partner_name in PARTNER_CPM_CAPS:
        return PARTNER_CPM_CAPS[partner_name]
    return PARTNER_CPM_CAPS['default']


# Example usage
if __name__ == "__main__":
    from utils.constants import LOCAL_DATA_PATH
    
    # Load data from the local data path
    insertion_orders_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'insertion_orders.csv'))
    campaigns_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'campaigns.csv'))
    line_items_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'line_items.csv'))
    
    # Detect anomalies with custom naming convention
    abnormal_ios = detect_io_anomalies(
        insertion_orders_df,
        campaigns_df,
        line_items_df,
        naming_convention="Campaign Name - Funnel - Support - Country/Language (opt) Suffix"
    )
    
    # Save results to CSV
    abnormal_ios.to_csv(os.path.join(LOCAL_DATA_PATH, 'abnormal_ios.csv'), index=False)
    
    # Display results
    print(f"Found {len(abnormal_ios)} abnormal insertion orders")
    for idx, row in abnormal_ios.iterrows():
        print(f"\nIO: {row['Name']}")
        print(f"Anomalies: {', '.join(row['anomalies_description'])}")
    else:
        print("LLM not available for naming convention check.")
