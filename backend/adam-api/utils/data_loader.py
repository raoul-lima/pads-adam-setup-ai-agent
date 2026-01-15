import pandas as pd
import os
from utils.constants import DATA_BUCKET_NAME
from utils.gcs_uploader import read_csv_from_gcs

def load_data(user_email: str, partner_name: str) -> tuple:
    """
    Loads data for a given user and partner from GCS.
    """
    if not DATA_BUCKET_NAME:
        raise ValueError("DATA_BUCKET_NAME environment variable is not set.")

    base_path = f"adam_agent_users/{user_email}/{partner_name}"

    # GCS file paths
    line_items_path = f"{base_path}/line_items.csv"
    campaigns_path = f"{base_path}/campaigns.csv"
    insertion_orders_path = f"{base_path}/insertion_orders.csv"

    try:
        Line_Items = read_csv_from_gcs(DATA_BUCKET_NAME, line_items_path)
        Campaigns = read_csv_from_gcs(DATA_BUCKET_NAME, campaigns_path)
        Insertion_orders = read_csv_from_gcs(DATA_BUCKET_NAME, insertion_orders_path)

        return Line_Items, Campaigns, Insertion_orders
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Data file not found in GCS for user {user_email} and partner {partner_name}: {e}")