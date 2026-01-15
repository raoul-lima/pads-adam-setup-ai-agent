"""
ADAM API Client
===============
HTTP client for calling the ADAM API service.
"""

import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Get ADAM API URL from environment (defaults to docker service name)
ADAM_API_URL = os.getenv("ADAM_API_URL", "http://adam-api:8000")
ADAM_API_TIMEOUT = int(os.getenv("ADAM_API_TIMEOUT", "600"))  # 10 minutes default (for complex queries with code execution)


class AdamAPIClient:
    """Client for calling ADAM API service"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = ADAM_API_TIMEOUT):
        """
        Initialize ADAM API client.
        
        Args:
            base_url: Base URL for ADAM API (defaults to ADAM_API_URL env var)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or ADAM_API_URL).rstrip('/')
        self.timeout = timeout
        # Create httpx client with explicit timeout configuration
        # Use httpx.Timeout to set both connect and read timeouts
        httpx_timeout = httpx.Timeout(timeout, connect=30.0)  # 30s connect, timeout for read
        self.client = httpx.AsyncClient(timeout=httpx_timeout)
        logger.info(f"Initialized ADAM API client: {self.base_url} (timeout: {timeout}s)")
    
    async def send_message(
        self, 
        content: str, 
        user_email: str, 
        partner: str,
        use_memory: bool = True
    ) -> dict:
        """
        Send a message to ADAM API and get response.
        
        Args:
            content: Message content to send
            user_email: User email for conversation tracking
            partner: Partner name for context
            use_memory: Whether to use conversation history/memory
            
        Returns:
            Response dict with 'response', 'conversation_id', 'timestamp', 'download_links'
            
        Raises:
            httpx.HTTPError: If API call fails
        """
        url = f"{self.base_url}/chat/message"
        
        payload = {
            "content": content,
            "user_email": user_email,
            "partner": partner,
            "use_memory": use_memory
        }
        
        logger.info(f"Calling ADAM API: {url}")
        logger.debug(f"Payload: user_email={user_email}, partner={partner}, use_memory={use_memory}, content_length={len(content)}")
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ ADAM API response received (conversation_id: {result.get('conversation_id')})")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ ADAM API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ ADAM API request error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error calling ADAM API: {e}")
            raise
    
    async def reset_conversation(self, user_email: str, partner: str) -> dict:
        """
        Reset conversation for a user-partner combination.
        
        Args:
            user_email: User email
            partner: Partner name
            
        Returns:
            Response dict
        """
        url = f"{self.base_url}/chat/reset"
        
        payload = {
            "user_email": user_email,
            "partner": partner
        }
        
        logger.info(f"Resetting conversation: user_email={user_email}, partner={partner}")
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            raise
    
    async def health_check(self) -> dict:
        """
        Check ADAM API health.
        
        Returns:
            Health status dict
        """
        url = f"{self.base_url}/health"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ADAM API health check failed: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

