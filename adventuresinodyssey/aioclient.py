"""
Adventures in Odyssey API Unauthenticated Client
Used for accessing publicly available content (e.g., promo content, radio schedule).
"""

import logging
from typing import Optional, Dict, Any, List, Union
import requests

# Configure logging
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the common API prefix
API_PREFIX = 'apexrest/v1/'

DEFAULT_FIELDS = {
    "Content__c": ["Name", "Thumbnail_Small__c", "Subtype__c", "Episode_Number__c"],
    "Content_Grouping__c": ["Name", "Image_URL__c", "Type__c"],
    "Topic__c": ["Name"],
    "Author__c": ["Name", "Profile_Image_URL__c"],
    "Character__c": ["Name", "Thumbnail_Small__c"],
    "Badge__c": ["Name", "Icon__c", "Type__c"]
}


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
        
    def fetch_radio(self, page_type: str = 'aired', page_number: int = 1, page_size: int = 5) -> Dict[str, Any]:
        """
        Fetches the schedule of aired or upcoming radio episodes.
        
        Args:
            content_type: The radio schedule type: 'aired' (default) or 'upcoming'.
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 5.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            ValueError: If an invalid content_type is provided.
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        
        # Base query parameters common to both aired and upcoming searches
        params = {
            'content_type': 'Audio',
            'content_subtype': 'Episode',
            'community': 'Adventures In Odyssey',
            'pagenum': page_number,
            'pagecount': page_size,
        }
        
        # Set type-specific parameters
        if page_type == 'aired':
            params['orderby'] = 'Recent_Air_Date__c DESC'
            params['radio_page_type'] = 'aired'
            log_info = "Aired Radio Episodes"
        elif page_type == 'upcoming':
            params['orderby'] = 'Recent_Air_Date__c ASC'
            params['radio_page_type'] = 'upcoming'
            log_info = "Upcoming Radio Episodes"
        else:
            raise ValueError(f"Invalid content_type '{page_type}'. Must be 'aired' or 'upcoming'.")
            
        logger.info(f"Attempting to fetch {log_info} (Page {page_number}, Size {page_size})")

        # The endpoint is 'content/search', and the generalized get method handles the base URL.
        return self.get("content/search", params=params)
    
    def cache_episodes(self, grouping_type: str = "Album", include_bonus: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves all available audio episodes from the specified content grouping type 
        (e.g., "Album", "Episode Home"), cleans the data, and returns a flattened list.

        This function automatically handles pagination across all pages for the grouping type.

        Args:
            grouping_type (str): The type of content grouping to fetch episodes from 
                                (e.g., "Album", "Episode Home"). Defaults to "Album".
        include_bonus (bool): If True, episodes starting with "BONUS" will be included.
                               Defaults to False.

        Returns:
            List[Dict[str, Any]]: A flat list of cleaned episode dictionaries.
        """

        logger.info(f"Starting process to cache all episodes (fetching all '{grouping_type}' pages).")
        
        all_episodes = []
        current_page = 1
        total_pages = 1  # Will be updated after the first API call

        # Loop until the current page exceeds the total number of pages
        while current_page <= total_pages:
            logger.debug(f"Fetching '{grouping_type}' page {current_page} of {total_pages}...")
            
            # Fetch content groupings (e.g., Albums or Episode Home)
            # Use a large page size (100) to minimize the number of API calls
            response = self.fetch_content_groupings(
                grouping_type=grouping_type,
                page_number=current_page, 
                page_size=100
            )
            
            # Update total pages on the first request
            if current_page == 1:
                try:
                    total_pages = response['metadata']['totalPageCount']
                    logger.info(f"Total '{grouping_type}' pages to retrieve: {total_pages}")
                except (KeyError, TypeError):
                    logger.warning("Could not determine totalPageCount from metadata. Assuming only one page.")
            
            # Process the content groupings on the current page
            content_groupings = response.get('contentGroupings', [])
            
            for content_grouping in content_groupings: # <<< RENAMED FROM 'album' for generality
                # Use a generic name for the grouping ID and Name
                grouping_id = content_grouping.get('id')
                grouping_name = content_grouping.get('name', f'UNKNOWN {grouping_type.upper()}')
                
                if not grouping_id:
                    logger.warning(f"Skipping {grouping_type} '{grouping_name}' due to missing ID.")
                    continue

                episode_list = content_grouping.get('contentList', [])
                
                for episode in episode_list:
                    episode_name = episode.get('name', 'Untitled Episode')
                    
                    # 1. Filter out episodes starting with "BONUS"
                    if not include_bonus and episode_name.startswith("BONUS"):
                        logger.debug(f"Skipping bonus episode: {episode_name}")
                        continue

                    # 2. Add the grouping ID to the episode dictionary
                    # Note: Keeping the key as 'album_id' for consistency with previous usage
                    clean_episode = episode.copy() 
                    clean_episode['album_id'] = grouping_id # Still using 'album_id' key
                    
                    all_episodes.append(clean_episode)
                    
            current_page += 1

        logger.info(f"Successfully cached {len(all_episodes)} clean episodes across {total_pages} pages.")
        return all_episodes
    
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
    
    def fetch_themes(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of themes (Topics) via a POST request.
        
        Args:
            page_number: The page number to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the list of themes.
        """
        themes_json = {
            "pageNumber": page_number,
            "pageSize": page_size
        }
        
        # POST to: apexrest/v1/topic/search
        return self.post("topic/search", payload=themes_json)

    def fetch_theme(self, theme_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific theme (Topic) by its ID.
        
        Args:
            theme_id: The unique ID of the theme (Topic) to retrieve.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the theme details.
        """
        # GET to: apexrest/v1/topic/{id}?tag=true
        endpoint = f"topic/{theme_id}?tag=true"
        return self.get(endpoint)
    
    def fetch_character(self, character_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific character by its ID.
        
        Args:
            character_id: The unique ID of the character to retrieve.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the character details.
        """
        endpoint = "character/" + character_id
        return self.get(endpoint)
    
    def fetch_author(self, author_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific author by its ID.
        
        Args:
            author_id: The unique ID of the author to retrieve.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the character details.
        """
        endpoint = "author/" + author_id
        return self.get(endpoint)
    
    def fetch_home_playlists(self) -> Dict[str, Any]:
        """
        Fetches newish content groups from the API.
        
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get("viewer/home?personal_playlists=true&playlists=true")
    
    def fetch_carousel(self) -> Dict[str, Any]:
        """
        Fetches the carousel.
        
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get("viewer/home?carousel=true&notifications=true")
    
    def _clean_search_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans and flattens the nested column structure of the search API response.
        
        The API returns results in 'column1', 'column2', etc. with redundant metadata.
        This function extracts and standardizes the key-value pairs.
        """
        cleaned_results = raw_results.copy()
        
        # Iterate through each object type (e.g., Content__c, Content_Grouping__c)
        for obj_group in cleaned_results.get('resultObjects', []):
            cleaned_group_results = []
            
            # Iterate through each individual search result within the group
            for raw_result in obj_group.get('results', []):
                cleaned_result = {'id': raw_result.get('id')}
                
                # Iterate through all 'column' keys (column1, column2, etc.)
                for key, data in raw_result.items():
                    if key.startswith('column') and isinstance(data, dict):
                        # Use the API field name (e.g., 'Name', 'Subtype__c')
                        api_name = data.get('name')
                        value = data.get('value')
                        
                        if api_name:
                            # Standardize field names for easier Python use (snake_case)
                            # Example: 'Thumbnail_Small__c' -> 'thumbnail_small'
                            if api_name.endswith('__c'):
                                python_name = api_name[:-3].lower().replace('__', '_')
                            else:
                                python_name = api_name.lower()
                                
                            cleaned_result[python_name] = value

                cleaned_group_results.append(cleaned_result)
                
            # Replace the old nested results with the new flat list
            obj_group['results'] = cleaned_group_results
            
            # Remove redundant column metadata from the object group metadata
            if 'metadata' in obj_group and 'fields' in obj_group['metadata']:
                del obj_group['metadata']['fields']
                
        return cleaned_results


    def search_all(self, query: str) -> Dict[str, Any]:
        """
        Performs a comprehensive, multi-object search across the API for a given query,
        and cleans the results into a flat, readable dictionary format.
        
        Args:
            query: The search term (e.g., "Whit's End").
            
        Returns:
            Dict[str, Any]: The parsed, cleaned JSON response containing results.
        """
        if not query:
            logger.warning("Search query is empty. Returning empty result.")
            return {"searchTerm": "", "resultObjects": []}

        search_payload = {
            "searchTerm": query,
            "searchObjects": [
                {"objectName": "Content__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name", "Thumbnail_Small__c", "Subtype__c", "Episode_Number__c"]},
                {"objectName": "Content_Grouping__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name", "Image_URL__c", "Type__c"]},
                {"objectName": "Topic__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name"]},
                {"objectName": "Author__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name", "Profile_Image_URL__c"]},
                {"objectName": "Character__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name", "Thumbnail_Small__c"]},
                {"objectName": "Badge__c", "pageNumber": 1, "pageSize": 9, 
                 "fields": ["Name", "Icon__c", "Type__c"]}
            ]
        }
        
        # 1. Perform the raw POST request
        raw_response = self.post("search", payload=search_payload)
        
        # 2. Clean the raw response before returning
        return self._clean_search_results(raw_response)
    
    def search(self, 
               query: str, 
               search_objects: Union[str, List[Dict[str, Any]], None] = None
               ) -> Dict[str, Any]:
        """
        Performs a flexible search across the API, allowing specification of object types,
        pagination, and automatically correcting object names with '__c'.
        
        Args:
            query: The search term (e.g., "whits flop").
            search_objects: 
                - str: Single object name (e.g., 'content'). Defaults to page 1, size 10.
                - List[Dict]: List of object configurations.
                - None: Defaults to searching only 'Content'.
            
        Returns:
            Dict[str, Any]: The parsed, cleaned JSON response containing results.
        """
        if not query:
            logger.warning("Search query is empty. Returning empty result.")
            return {"searchTerm": "", "resultObjects": []}

        # 1. Normalize and structure the object configurations
        if search_objects is None:
            config_list = [{"objectName": "Content", "pageNumber": 1, "pageSize": 10}]
        elif isinstance(search_objects, str):
            config_list = [{"objectName": search_objects, "pageNumber": 1, "pageSize": 10}]
        else:
            config_list = search_objects

        final_search_objects = []
        for config in config_list:
            obj_name_raw = config.get('objectName', 'Content')

            # --- FIX APPLIED HERE ---
            # 1. Strip '__c' and make lowercase
            # 2. Capitalize the main word (TitleCase)
            # 3. Append the correct lowercase suffix '__c'
            obj_name = obj_name_raw.lower().replace('__c', '')
            obj_name = obj_name.title()
            obj_name += '__c'
            # --- END FIX ---

            # Get pagination details
            page_num = config.get('pageNumber', 1)
            page_size = config.get('pageSize', 10)
            
            # Use predefined fields based on the correctly normalized object name
            fields = DEFAULT_FIELDS.get(obj_name, ["Name"])

            final_search_objects.append({
                "objectName": obj_name,
                "pageNumber": page_num,
                "pageSize": page_size,
                "fields": fields
            })
            
        search_payload = {
            "searchTerm": query,
            "searchObjects": final_search_objects
        }

        # 2. Perform the raw POST request
        raw_response = self.post("search", payload=search_payload)
        
        # 3. Clean the raw response before returning
        return self._clean_search_results(raw_response)
        
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

    def post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs an unauthenticated POST request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            
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
            # Use json=payload to automatically set Content-Type: application/json
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"POST request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"POST request failed for {full_endpoint}: {e}")
            raise