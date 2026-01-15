"""
Advertiser Cache Module
Provides partner-specific in-memory cache with daily TTL for advertiser data.
Each user-partner combination has its own cache entry.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import logging
import pandas as pd
from utils.gcs_uploader import read_csv_from_gcs
from utils.constants import DATA_BUCKET_NAME

logger = logging.getLogger(__name__)


class AdvertiserCache:
    """
    Partner-specific cache for advertiser data with automatic daily refresh.
    Each user-partner combination maintains its own cache entry.
    Thread-safe singleton pattern for process-level caching.
    """
    # Dictionary keyed by (user_email, partner_name) tuple
    _caches: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    _last_fetches: Dict[Tuple[str, str], datetime] = {}
    _ttl_hours: int = 24  # Cache expires after 24 hours
    
    @classmethod
    def _get_cache_key(cls, user_email: str, partner_name: str) -> Tuple[str, str]:
        """Generate cache key from user email and partner name."""
        return (user_email.lower().strip(), partner_name.lower().strip())
    
    @classmethod
    async def get_advertisers(cls, user_email: str, partner_name: str, force_refresh: bool = False) -> List[Dict[str, str]]:
        """
        Get cached advertiser list with automatic refresh for the specific partner.
        
        Args:
            user_email: User's email for GCS path
            partner_name: Partner name for GCS path (used as cache key)
            force_refresh: Force cache refresh regardless of TTL
            
        Returns:
            List of dicts with 'advertiser_id' and 'advertiser_name'
        """
        cache_key = cls._get_cache_key(user_email, partner_name)
        now = datetime.now()
        
        # Get cache for this specific partner
        cached_data = cls._caches.get(cache_key)
        last_fetch = cls._last_fetches.get(cache_key)
        
        cache_expired = (
            cached_data is None or 
            last_fetch is None or 
            (now - last_fetch) > timedelta(hours=cls._ttl_hours)
        )
        
        if cache_expired or force_refresh:
            logger.info(f"Advertiser cache for partner '{partner_name}' {'expired' if cache_expired else 'force refreshing'}, fetching from GCS...")
            try:
                advertiser_list = await cls._fetch_advertisers_from_gcs(user_email, partner_name)
                cls._caches[cache_key] = advertiser_list
                cls._last_fetches[cache_key] = now
                logger.info(f"Advertiser cache refreshed successfully for partner '{partner_name}'. Found {len(advertiser_list)} unique advertisers.")
                return advertiser_list
            except Exception as e:
                logger.error(f"Failed to refresh advertiser cache for partner '{partner_name}': {e}")
                # If cache exists but refresh failed, return stale cache
                if cached_data is not None:
                    logger.warning(f"Returning stale cache for partner '{partner_name}' due to refresh failure")
                    return cached_data
                # If no cache exists and fetch fails, return empty list
                logger.error(f"No cache available for partner '{partner_name}' and fetch failed, returning empty list")
                return []
        else:
            cache_age = (now - last_fetch).total_seconds() / 3600
            logger.debug(f"Using cached advertiser data for partner '{partner_name}' (age: {cache_age:.1f} hours)")
            
        return cached_data or []
    
    @classmethod
    async def _fetch_advertisers_from_gcs(cls, user_email: str, partner_name: str) -> List[Dict[str, str]]:
        """
        Fetch unique advertisers from all CSV files in GCS.
        
        Args:
            user_email: User's email for GCS path
            partner_name: Partner name for GCS path
            
        Returns:
            List of unique advertisers with id and name
        """
        if not DATA_BUCKET_NAME:
            raise ValueError("DATA_BUCKET_NAME environment variable is not set.")
        
        base_path = f"adam_agent_users/{user_email}/{partner_name}"
        
        # GCS file paths
        csv_files = [
            f"{base_path}/line_items.csv",
            f"{base_path}/campaigns.csv", 
            f"{base_path}/insertion_orders.csv"
        ]
        
        all_advertisers = set()
        advertiser_map = {}
        
        for csv_path in csv_files:
            try:
                df = read_csv_from_gcs(DATA_BUCKET_NAME, csv_path)
                
                # Extract advertiser info if columns exist
                if 'Advertiser Id' in df.columns and 'Advertiser Name' in df.columns:
                    for _, row in df[['Advertiser Id', 'Advertiser Name']].drop_duplicates().iterrows():
                        adv_id = str(row['Advertiser Id']).strip()
                        adv_name = str(row['Advertiser Name']).strip()
                        
                        # Skip NaN or empty values
                        if adv_id and adv_id != 'nan' and adv_name and adv_name != 'nan':
                            advertiser_map[adv_id] = adv_name
                            all_advertisers.add(adv_id)
                            
            except FileNotFoundError:
                logger.warning(f"CSV file not found: {csv_path}, skipping...")
            except Exception as e:
                logger.error(f"Error reading {csv_path}: {e}")
        
        # Convert to list of dicts sorted by name
        advertiser_list = [
            {"advertiser_id": adv_id, "advertiser_name": advertiser_map[adv_id]}
            for adv_id in sorted(all_advertisers, key=lambda x: advertiser_map[x])
        ]
        
        return advertiser_list
    
    @classmethod
    def get_cache_info(cls, user_email: Optional[str] = None, partner_name: Optional[str] = None) -> Dict[str, any]:
        """
        Get information about current cache state for a specific partner or all partners.
        Useful for debugging and monitoring.
        
        Args:
            user_email: Optional user email to get info for specific partner
            partner_name: Optional partner name to get info for specific partner
            
        Returns:
            Cache info dict. If user_email and partner_name provided, returns info for that partner.
            Otherwise returns summary of all cached partners.
        """
        if user_email and partner_name:
            # Return info for specific partner
            cache_key = cls._get_cache_key(user_email, partner_name)
            cached_data = cls._caches.get(cache_key)
            last_fetch = cls._last_fetches.get(cache_key)
            
            if cached_data is None or last_fetch is None:
                return {
                    "cached": False,
                    "user_email": user_email,
                    "partner_name": partner_name,
                    "count": 0,
                    "age_hours": None,
                    "expires_in_hours": None
                }
            
            now = datetime.now()
            age = (now - last_fetch).total_seconds() / 3600
            expires_in = cls._ttl_hours - age
            
            return {
                "cached": True,
                "user_email": user_email,
                "partner_name": partner_name,
                "count": len(cached_data),
                "age_hours": round(age, 2),
                "expires_in_hours": round(expires_in, 2),
                "last_fetch": last_fetch.isoformat()
            }
        else:
            # Return summary of all cached partners
            return {
                "total_partners_cached": len(cls._caches),
                "partners": [
                    {
                        "user_email": key[0],
                        "partner_name": key[1],
                        "count": len(cache),
                        "age_hours": round((datetime.now() - cls._last_fetches[key]).total_seconds() / 3600, 2) if key in cls._last_fetches else None,
                        "last_fetch": cls._last_fetches[key].isoformat() if key in cls._last_fetches else None
                    }
                    for key, cache in cls._caches.items()
                ]
            }
    
    @classmethod
    def clear_cache(cls, user_email: Optional[str] = None, partner_name: Optional[str] = None):
        """
        Manually clear the cache for a specific partner or all partners.
        Useful for testing or forcing a refresh.
        
        Args:
            user_email: Optional user email to clear cache for specific partner
            partner_name: Optional partner name to clear cache for specific partner
            If both are None, clears all caches.
        """
        if user_email and partner_name:
            cache_key = cls._get_cache_key(user_email, partner_name)
            if cache_key in cls._caches:
                del cls._caches[cache_key]
            if cache_key in cls._last_fetches:
                del cls._last_fetches[cache_key]
            logger.info(f"Advertiser cache cleared manually for partner '{partner_name}'")
        else:
            cls._caches.clear()
            cls._last_fetches.clear()
            logger.info("All advertiser caches cleared manually")


# Synchronous wrapper for backward compatibility
def get_advertisers_sync(user_email: str, partner_name: str, force_refresh: bool = False) -> List[Dict[str, str]]:
    """
    Synchronous wrapper for get_advertisers.
    Uses asyncio to run the async function.
    """
    import asyncio
    
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            # This is useful when called from async context
            return asyncio.create_task(AdvertiserCache.get_advertisers(user_email, partner_name, force_refresh))
        else:
            # If no loop is running, use run_until_complete
            return loop.run_until_complete(AdvertiserCache.get_advertisers(user_email, partner_name, force_refresh))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(AdvertiserCache.get_advertisers(user_email, partner_name, force_refresh))

