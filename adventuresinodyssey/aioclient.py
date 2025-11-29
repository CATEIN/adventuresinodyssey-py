"""
Adventures in Odyssey API Unauthenticated Client
Used for accessing publicly available content (e.g., promo content, radio schedule).
"""

import logging
from typing import Dict, Any, Optional
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the common API prefix
API_PREFIX = 'apexrest/v1/'


class AIOClient:
    """
    Unauthenticated client for Adventures in Odyssey API.
    Does not handle login, profile selection, or token management.
    """
    
    def __init__(self):
        """
        Initialize the AIO API client configuration for unauthenticated access.
        """
        
        self.state = "ready"
        
        # Client configuration (minimal set)
        self.config = {
            'api_base': 'https://fotf.my.site.com/aio/services/', 
            'api_version': 'v1',
        }
        
        # Setup HTTP session with unauthenticated header
        self.session = requests.Session()
        # The API requires the 'x-experience-name' header even for unauthenticated calls
        self.session.headers.update({
            'x-experience-name': 'Adventures In Odyssey',
            # NO x-viewer-id, x-pin, or Authorization header should be set
        })

    def fetch_content(self, content_id: str, page_type: str = 'promo') -> Dict[str, Any]:
        """
        Fetches detailed content data for a given ID.
        
        Supports 'promo' (default) and 'radio' page types, which do not require authentication.
        'full' page type is not supported as it requires login.
        
        Args:
            content_id: The ID of the content to fetch (e.g., 'a354W0000046U6OQAU').
            page_type: The type of content page: 'promo' (default) or 'radio'.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            ValueError: If the unsupported 'full' page_type is provided.
            requests.exceptions.HTTPError: If the API request fails.
        """
        if page_type == 'full':
            raise ValueError("The 'full' page_type requires authentication and is not supported by AIOClient.")
        
        is_radio = (page_type == 'radio')
        
        # Base API URL structure for content details
        endpoint = f"apexrest/{self.config['api_version']}/content/{content_id}"
        url = f"{self.config['api_base']}{endpoint}"

        # Standard default parameters for 'promo'
        params = {
            'tag': 'true',
            'series': 'true',
            'recommendations': 'true',
            'player': 'true',
            'parent': 'true'
        }

        if is_radio:
            # Add radio-specific parameter
            params['radio_page_type'] = 'aired'
            logger.info("Fetching content for 'radio' page type, adding radio_page_type=aired.")

        logger.info(f"Attempting to fetch content ID: {content_id} (Page Type: {page_type})")
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            logger.info(f"Content fetch successful for ID: {content_id} (Page Type: {page_type})")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch content ID {content_id} (Page Type: {page_type}): {e}")
            raise
    
    def fetch_content_group(self, group_id: str) -> Dict[str, Any]:
        """
        Fetches detailed data for a content grouping (e.g., an album or series).
        
        Args:
            group_id: The ID of the content grouping to fetch (e.g., 'a31Uh0000035T2rIAE').
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        # Uses the unauthenticated get helper
        return self.get(f"contentgrouping/{group_id}")

    def fetch_content_groupings(self, page_number: int = 1, page_size: int = 25, grouping_type: str = 'Album', payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches for and fetches a paginated list of content groupings (e.g., albums/series).
        
        If 'payload' is provided, it is used directly as the POST body, overriding 
        'page_number', 'page_size', and 'grouping_type'.
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            grouping_type: The type of content grouping to search for: 'Album' (default), 'Series', 'Collection', 'Episode Home', etc.
            payload: Optional. A complete request body (dictionary) to send instead of the default structured payload.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        
        # Construct the payload based on arguments
        if payload is not None:
            request_payload = payload
            log_info = "custom payload"
        else:
            request_payload = {
                "type": grouping_type,
                "community": "Adventures in Odyssey",
                "pageNumber": page_number,
                "pageSize": page_size
            }
            log_info = f"Type: {grouping_type}, Page {page_number}, Size {page_size}"

        logger.info(f"Attempting to fetch content groupings ({log_info})")
        
        # Uses the unauthenticated post helper
        return self.post("contentgrouping/search", request_payload)
            
    def fetch_characters(self, page_number: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """
        Fetches a paginated list of characters (e.g., 'Whit', 'Connie', 'Eugene').
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 200.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        request_payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        
        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch characters ({log_info})")
        
        return self.post("character/search", request_payload)

    def fetch_cast_and_crew(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of cast and crew (authors).
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        request_payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        
        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch cast and crew ({log_info})")
        
        return self.post("author/search", request_payload)
        
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Performs an unauthenticated GET request to a generalized API endpoint.
        
        Args:
            endpoint: The relative API path (e.g., 'content/random').
            params: Optional dictionary of query parameters.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        try:
            logger.info(f"Attempting unauthenticated GET request to: {full_endpoint}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            logger.info(f"GET request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"GET request failed for {full_endpoint}: {e}")
            raise

    def post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs an unauthenticated POST request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            json_data: The JSON dictionary to be sent in the request body.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        try:
            logger.info(f"Attempting unauthenticated POST request to: {full_endpoint}")
            # Use json=json_data to automatically set Content-Type: application/json
            response = self.session.post(url, json=json_data)
            response.raise_for_status()
            logger.info(f"POST request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"POST request failed for {full_endpoint}: {e}")
            raise