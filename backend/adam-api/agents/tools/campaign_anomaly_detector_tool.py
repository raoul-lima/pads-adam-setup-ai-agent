import pandas as pd
from typing import Tuple
import numpy as np
import sys
import os

# Add backend to path for importing configs if needed
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)


def detect_campaign_anomalies(campaigns_df: pd.DataFrame, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> pd.DataFrame:
    """
    Main function that detects anomalies in campaigns dataframe.
    
    Args:
        campaigns_df: DataFrame containing campaign data
        
    Returns:
        DataFrame containing only abnormal campaigns with anomalies_description column
    """
    
    # List of check functions to apply
    check_functions = [
        check_campaign_goal,
        check_kpi_configuration,
        check_frequency_capping,
        # Add more check functions here as they are implemented
    ]
    
    # Create a copy to avoid modifying original
    df = campaigns_df.copy()
    
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
                is_abnormal, description = check_func(row, insertion_orders_df, line_items_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                # Handle any errors in check functions gracefully
                print(f"Error in {check_func.__name__} for row {idx}: {str(e)}")
                continue
        
        is_abnormal_list.append(row_is_abnormal)
        # Join anomalies with semicolon for frontend rendering
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    # Add results to dataframe
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    # Filter to only abnormal campaigns
    abnormal_campaigns = df[df['is_abnormal']].copy()
    
    # Remove the temporary is_abnormal column
    abnormal_campaigns = abnormal_campaigns.drop('is_abnormal', axis=1)
    
    return abnormal_campaigns


def check_campaign_goal(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if campaign goal is properly configured.
    Expected: Goal should be "Drive online action or visits" for most campaigns.
    
    Args:
        campaign: Single campaign row as pandas Series
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    expected_goal = "Drive online action or visits"
    
    campaign_goal = campaign.get('Campaign Goal', '')
    
    if pd.isna(campaign_goal) or campaign_goal == '':
        return True, "Campaign Goal is missing;"
    
    if campaign_goal != expected_goal:
        return True, f"Campaign Goal Mismatch: Expected '{expected_goal}' but found '{campaign_goal}';"
    
    return False, ""


def check_kpi_configuration(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if KPI is properly configured and aligned with campaign objectives.
    
    Args:
        campaign: Single campaign row as pandas Series
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    campaign_kpi = campaign.get('Campaign Goal KPI', '')
    kpi_value = campaign.get('Campaign Goal KPI Value', np.nan)
    campaign_name = campaign.get('Name', '')
    
    # Check if KPI is missing
    if pd.isna(campaign_kpi) or campaign_kpi == '':
        return True, "Campaign KPI type is missing;"
    
    # Check if KPI value is missing when KPI is set
    if campaign_kpi in ['CTR', 'CPA', 'CPM'] and (pd.isna(kpi_value) or kpi_value == 0):
        return True, f"Campaign KPI value is missing or zero for {campaign_kpi};"
    
    # Check naming convention alignment (if campaign name contains funnel stage keywords)
    name_lower = campaign_name.lower()
    
    # Awareness campaigns should typically use CPM
    if 'awareness' in name_lower and campaign_kpi not in ['CPM', 'CTR']:
        return True, f"Campaign name suggests Awareness but KPI is {campaign_kpi} (expected CPM or CTR);"
    
    # Consideration campaigns should typically use CTR
    if 'consideration' in name_lower and campaign_kpi != 'CTR':
        return True, f"Campaign name suggests Consideration but KPI is {campaign_kpi} (expected CTR);"
    
    # Conversion campaigns should typically use CPA
    if 'conversion' in name_lower and campaign_kpi != 'CPA':
        return True, f"Campaign name suggests Conversion but KPI is {campaign_kpi} (expected CPA);"
    
    # Check CTR targets are within reasonable range (0.1% - 0.5% typically)
    if campaign_kpi == 'CTR':
        if not pd.isna(kpi_value):
            if kpi_value < 0.1 or kpi_value > 0.5:
                return True, f"CTR target {kpi_value}% is outside typical range (0.1%-0.5%);"
    
    return False, ""


def check_frequency_capping(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if frequency capping is properly configured.
    
    Args:
        campaign: Single campaign row as pandas Series
        
    Returns:
        Tuple of (is_abnormal: bool, description: str)
    """
    freq_enabled = campaign.get('Frequency Enabled', False)
    freq_exposures = campaign.get('Frequency Exposures', 0)
    freq_amount = campaign.get('Frequency Amount', 0)
    freq_period = campaign.get('Frequency Period', '')
    
    # Convert to boolean if string
    if isinstance(freq_enabled, str):
        freq_enabled = freq_enabled.lower() == 'true'
    
    # Check if frequency capping is disabled
    if not freq_enabled:
        return True, "Frequency capping is disabled;"
    
    # Check if frequency exposures is 0 or missing
    if pd.isna(freq_exposures) or freq_exposures == 0:
        return True, "Frequency exposures is not set or is zero;"
    
    # Check if frequency amount is 0 when enabled
    if pd.isna(freq_amount) or freq_amount == 0:
        return True, "Frequency amount is not set or is zero;"
    
    # Check if frequency period is missing
    if pd.isna(freq_period) or freq_period == '':
        return True, "Frequency period is not specified;"
    
    # Check for unusually high frequency caps
    if freq_exposures > 20:
        return True, f"Frequency exposures ({freq_exposures}) is unusually high (>20);"
    
    return False, ""


# Placeholder functions for additional checks to be implemented
def check_budget_configuration(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if budget is properly configured.
    To be implemented based on specific requirements.
    """
    # Placeholder - to be implemented
    return False, ""


def check_targeting_configuration(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if targeting (geo, language, etc.) is properly configured.
    To be implemented based on specific requirements.
    """
    # Placeholder - to be implemented
    return False, ""


def check_brand_safety_configuration(campaign: pd.Series, insertion_orders_df: pd.DataFrame, line_items_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Check if brand safety settings are properly configured.
    To be implemented based on specific requirements.
    """
    # Placeholder - to be implemented
    return False, ""


# Example usage
if __name__ == "__main__":
    # Example of how to use the detector
    from utils.constants import LOCAL_DATA_PATH
        
    # Load campaigns data from the local data path
    campaigns_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'campaigns.csv'))
    insertion_orders_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'insertion_orders.csv'))
    line_items_df = pd.read_csv(os.path.join(LOCAL_DATA_PATH, 'line_items.csv'))
    
    # Detect anomalies
    abnormal_campaigns = detect_campaign_anomalies(campaigns_df, insertion_orders_df, line_items_df)

    # Save results to CSV
    abnormal_campaigns.to_csv(os.path.join(LOCAL_DATA_PATH, 'abnormal_campaigns.csv'), index=False)
    
    # Display results
    print(f"Found {len(abnormal_campaigns)} abnormal campaigns")
    for idx, row in abnormal_campaigns.iterrows():
        print(f"\nCampaign: {row['Name']}")
        print(f"Anomalies: {', '.join(row['anomalies_description'])}")
