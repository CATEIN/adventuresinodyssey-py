"""
Adventures in Odyssey API Unauthenticated Client
Used for accessing publicly available content (e.g., promo content, radio schedule).
"""

import re
import logging
from typing import Optional, Dict, Any, List, Union
import httpx

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


class AsyncAIOClient:
    """
    Unauthenticated async client for Adventures in Odyssey API.
    Does not handle login, profile selection, or token management.

    Usage:
        async with AsyncAIOClient() as client:
            data = await client.fetch_content("a354W0000046U6OQAU")

    Or manage the lifecycle manually:
        client = AsyncAIOClient()
        await client.open()
        ...
        await client.close()
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize the AIO API client configuration for unauthenticated access.
        """
        self.state = "ready"
        self.timeout = timeout

        # Client configuration (minimal set)
        self.config = {
            'api_base': 'https://fotf.my.site.com/aio/services/',
            'api_version': 'v1',
        }

        # The async httpx client is created lazily (or via open/context manager)
        self._client: Optional[httpx.AsyncClient] = None

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                'x-experience-name': 'Adventures In Odyssey',
                # NO x-viewer-id, x-pin, or Authorization header should be set
            },
            timeout=self.timeout,
        )

    async def open(self) -> None:
        """Explicitly open the underlying HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = self._make_client()

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncAIOClient":
        await self.open()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    @property
    def session(self) -> httpx.AsyncClient:
        """Return the active client, creating one on demand if needed."""
        if self._client is None or self._client.is_closed:
            self._client = self._make_client()
        return self._client

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def fetch_content(self, content_id: str, page_type: str = 'promo') -> Dict[str, Any]:
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
            httpx.HTTPStatusError: If the API request fails.
        """
        if page_type == 'full':
            raise ValueError("The 'full' page_type requires authentication and is not supported by AsyncAIOClient.")

        is_radio = (page_type == 'radio')

        endpoint = f"apexrest/{self.config['api_version']}/content/{content_id}"
        url = f"{self.config['api_base']}{endpoint}"

        params = {
            'tag': 'true',
            'series': 'true',
            'recommendations': 'true',
            'player': 'true',
            'parent': 'true'
        }

        if is_radio:
            params['radio_page_type'] = 'aired'
            logger.info("Fetching content for 'radio' page type, adding radio_page_type=aired.")

        logger.info(f"Attempting to fetch content ID: {content_id} (Page Type: {page_type})")

        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            logger.info(f"Content fetch successful for ID: {content_id} (Page Type: {page_type})")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch content ID {content_id} (Page Type: {page_type}): {e}")
            raise

    async def fetch_new_content(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches the latest published content for the community.

        Args:
            page_number (int): The page to retrieve (mapped to 'pagenum'). Defaults to 1.
            page_size (int): Number of items per page (mapped to 'pagecount'). Defaults to 25.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the newest content.
        """
        logger.info(f"Fetching new content: Page {page_number}, Size {page_size}")

        params = {
            "community": "Adventures In Odyssey",
            "orderby": "Last_Published_Date__c DESC NULLS LAST",
            "pagenum": page_number,
            "pagecount": page_size
        }

        return await self.get("content/search", params=params)

    async def fetch_radio(self, page_type: str = 'aired', page_number: int = 1, page_size: int = 5) -> Dict[str, Any]:
        """
        Fetches the schedule of aired or upcoming radio episodes.

        Args:
            page_type: The radio schedule type: 'aired' (default) or 'upcoming'.
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 5.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            ValueError: If an invalid page_type is provided.
            httpx.HTTPStatusError: If the API request fails.
        """
        params = {
            'content_type': 'Audio',
            'content_subtype': 'Episode',
            'community': 'Adventures In Odyssey',
            'pagenum': page_number,
            'pagecount': page_size,
        }

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

        return await self.get("content/search", params=params)

    async def cache_episodes(self, grouping_type: str = "Album", include_bonus: bool = False) -> List[Dict[str, Any]]:
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
        total_pages = 1

        while current_page <= total_pages:
            logger.debug(f"Fetching '{grouping_type}' page {current_page} of {total_pages}...")

            response = await self.fetch_content_groupings(
                grouping_type=grouping_type,
                page_number=current_page,
                page_size=200
            )

            if current_page == 1:
                try:
                    total_pages = response['metadata']['totalPageCount']
                    logger.info(f"Total '{grouping_type}' pages to retrieve: {total_pages}")
                except (KeyError, TypeError):
                    logger.warning("Could not determine totalPageCount from metadata. Assuming only one page.")

            content_groupings = response.get('contentGroupings', [])

            for content_grouping in content_groupings:
                grouping_id = content_grouping.get('id')
                grouping_name = content_grouping.get('name', f'UNKNOWN {grouping_type.upper()}')

                if not grouping_id:
                    logger.warning(f"Skipping {grouping_type} '{grouping_name}' due to missing ID.")
                    continue

                episode_list = content_grouping.get('contentList', [])

                for episode in episode_list:
                    episode_name = episode.get('name', 'Untitled Episode')

                    if episode.get('type') != 'Audio':
                        logger.debug(f"Skipping non-audio episode: {episode_name}")
                        continue

                    if not include_bonus and episode_name.startswith("BONUS"):
                        logger.debug(f"Skipping bonus episode: {episode_name}")
                        continue
                        
                    clean_episode = episode.copy()
                    clean_episode['album_id'] = grouping_id
                    all_episodes.append(clean_episode)

            current_page += 1

        logger.info(f"Successfully cached {len(all_episodes)} clean episodes across {total_pages} pages.")
        return all_episodes

    async def cache_albums(self, grouping_type: str = "Album", include_club_exclusive: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves all available content groupings from the specified type
        (e.g., "Album", "Episode Home") and returns them as a flattened list.

        Args:
            grouping_type (str): The type of content grouping to fetch. Defaults to "Album".
            include_club_exclusive (bool): If False, filters out "Club Season",
                                        "The Officer Harley Collection", and albums
                                        numbered #81 or higher. Defaults to True.

        Returns:
            List[Dict[str, Any]]: A flat list of content grouping dictionaries.
        """
        fetch_type = "Album" if grouping_type == "Themes" else grouping_type

        logger.info(f"Starting process to cache {grouping_type} (fetching {fetch_type} source).")

        all_groupings = []
        current_page = 1
        total_pages = 1
        club_num_pattern = re.compile(r'#(\d+)')

        while current_page <= total_pages:
            logger.debug(f"Fetching '{fetch_type}' page {current_page} of {total_pages}...")

            response = await self.fetch_content_groupings(
                grouping_type=fetch_type,
                page_number=current_page,
                page_size=100
            )

            if current_page == 1:
                try:
                    total_pages = response['metadata']['totalPageCount']
                except (KeyError, TypeError):
                    total_pages = 1

            content_groupings = response.get('contentGroupings', [])

            if not include_club_exclusive:
                filtered_batch = []
                for item in content_groupings:
                    name = item.get("name", "")
                    is_excluded = "Club Season" in name or "The Officer Harley Collection" in name

                    match = club_num_pattern.search(name)
                    if match and int(match.group(1)) >= 81:
                        is_excluded = True

                    if not is_excluded:
                        filtered_batch.append(item)
                all_groupings.extend(filtered_batch)
            else:
                all_groupings.extend(content_groupings)

            current_page += 1

        if grouping_type == "Themes":
            logger.info("Generating theme-based groupings from album episode tags...")
            themes_map = {}

            for grouping in all_groupings:
                for episode in grouping.get("contentList", []):
                    for tag in episode.get("tags", []):
                        topic_id = tag.get("topic_id")
                        if not topic_id:
                            continue

                        if topic_id not in themes_map:
                            themes_map[topic_id] = {
                                "type": "Theme",
                                "name": tag.get("name"),
                                "id": topic_id,
                                "topic_id": topic_id,
                                "contentList": [],
                                "description": f"Episodes related to {tag.get('name')}",
                                "total_runtime": 0, "tags": [], "rating_count": 0,
                                "is_editable": False, "is_bookmarked": False,
                                "imageURL": None, "product_links": []
                            }

                        if episode.get("id") not in {ep['id'] for ep in themes_map[topic_id]["contentList"]}:
                            themes_map[topic_id]["contentList"].append(episode)

            final_list = list(themes_map.values())
            logger.info(f"Successfully generated {len(final_list)} theme groupings.")
            return final_list

        logger.info(f"Successfully cached {len(all_groupings)} {grouping_type}s.")
        return all_groupings

    async def cache_content_groupings(self, generate_themes: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves all available content groupings and optionally generates
        "Theme" groupings based on episode tags.

        Args:
            generate_themes (bool): If True, parses all episodes within groupings to
                                create new groupings categorized by theme tags.
        """
        logger.info("Starting process to cache all content groupings.")

        all_groupings = []
        current_page = 1
        total_pages = 1

        while current_page <= total_pages:
            logger.debug(f"Fetching content groupings page {current_page} of {total_pages}...")

            payload = {
                "community": "Adventures in Odyssey",
                "pageNumber": current_page,
                "pageSize": 300
            }
            response = await self.post("contentgrouping/search", payload=payload)

            if current_page == 1:
                try:
                    total_pages = response['metadata']['totalPageCount']
                    logger.info(f"Total pages to retrieve: {total_pages}")
                except (KeyError, TypeError):
                    logger.warning("Could not determine totalPageCount. Assuming one page.")

            content_groupings = response.get('contentGroupings', [])
            all_groupings.extend(content_groupings)
            current_page += 1

        if generate_themes:
            logger.info("Generating theme-based groupings from episode tags...")
            themes_map = {}

            for grouping in all_groupings:
                content_list = grouping.get("contentList", [])
                for episode in content_list:
                    tags = episode.get("tags", [])
                    for tag in tags:
                        topic_id = tag.get("topic_id")
                        theme_name = tag.get("name")

                        if not topic_id:
                            continue

                        if topic_id not in themes_map:
                            themes_map[topic_id] = {
                                "type": "Theme",
                                "name": theme_name,
                                "id": topic_id,
                                "topic_id": topic_id,
                                "total_runtime": 0,
                                "tags": [],
                                "rating_count": 0,
                                "product_links": [],
                                "is_editable": False,
                                "is_bookmarked": False,
                                "imageURL": None,
                                "full_description": f"Episodes related to {theme_name}",
                                "enable_ratings": False,
                                "enable_commenting": False,
                                "disable_comment_posting": False,
                                "description": f"Episodes related to {theme_name}",
                                "contentList": [],
                                "content_for_parents": [],
                                "album_number": None,
                                "album_copyright_year": None
                            }

                        existing_ids = {ep['id'] for ep in themes_map[topic_id]["contentList"]}
                        if episode.get("id") not in existing_ids:
                            themes_map[topic_id]["contentList"].append(episode)

            generated_themes = list(themes_map.values())
            logger.info(f"Generated {len(generated_themes)} unique theme groupings.")
            all_groupings.extend(generated_themes)

        logger.info(f"Successfully cached {len(all_groupings)} total groupings.")
        return all_groupings

    async def fetch_content_group(self, group_id: str) -> Dict[str, Any]:
        """
        Fetches detailed data for a content grouping (e.g., an album or series).

        Args:
            group_id: The ID of the content grouping to fetch (e.g., 'a31Uh0000035T2rIAE').

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        return await self.get(f"contentgrouping/{group_id}")

    async def fetch_content_groupings(
        self,
        page_number: int = 1,
        page_size: int = 25,
        grouping_type: str = 'Album',
        order_by: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Searches for and fetches a paginated list of content groupings (e.g., albums/series).

        If 'payload' is provided, it is used directly as the POST body, overriding
        'page_number', 'page_size', and 'grouping_type'.

        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            grouping_type: The type of content grouping to search for.
            payload: Optional. A complete request body (dictionary) to send instead of
                     the default structured payload.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
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
            if order_by is not None:
                request_payload["orderBy"] = order_by
            log_info = f"Type: {grouping_type}, Page {page_number}, Size {page_size}"

        logger.info(f"Attempting to fetch content groupings ({log_info})")

        return await self.post("contentgrouping/search", request_payload)

    async def fetch_characters(self, page_number: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """
        Fetches a paginated list of characters (e.g., 'Whit', 'Connie', 'Eugene').

        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 200.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        request_payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }

        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch characters ({log_info})")

        return await self.post("character/search", request_payload)

    async def fetch_cast_and_crew(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of cast and crew (authors).

        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        request_payload = {
            "pageNumber": page_number,
            "pageSize": page_size
        }

        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch cast and crew ({log_info})")

        return await self.post("author/search", request_payload)

    async def fetch_themes(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
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

        return await self.post("topic/search", payload=themes_json)

    async def fetch_theme(self, theme_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific theme (Topic) by its ID.

        Args:
            theme_id: The unique ID of the theme (Topic) to retrieve.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the theme details.
        """
        endpoint = f"topic/{theme_id}?tag=true"
        return await self.get(endpoint)

    async def fetch_character(self, character_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific character by its ID.

        Args:
            character_id: The unique ID of the character to retrieve.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the character details.
        """
        return await self.get("character/" + character_id)

    async def fetch_author(self, author_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed information for a specific author by its ID.

        Args:
            author_id: The unique ID of the author to retrieve.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the character details.
        """
        return await self.get("author/" + author_id)

    async def fetch_home_playlists(self) -> Dict[str, Any]:
        """
        Fetches newish content groups from the API.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        return await self.get("viewer/home?personal_playlists=true&playlists=true")

    async def fetch_carousel(self) -> Dict[str, Any]:
        """
        Fetches the carousel.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        return await self.get("viewer/home?carousel=true&notifications=true")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _clean_search_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans and flattens the nested column structure of the search API response.

        The API returns results in 'column1', 'column2', etc. with redundant metadata.
        This function extracts and standardizes the key-value pairs.
        """
        cleaned_results = raw_results.copy()

        for obj_group in cleaned_results.get('resultObjects', []):
            cleaned_group_results = []

            for raw_result in obj_group.get('results', []):
                cleaned_result = {'id': raw_result.get('id')}

                for key, data in raw_result.items():
                    if key.startswith('column') and isinstance(data, dict):
                        api_name = data.get('name')
                        value = data.get('value')

                        if api_name:
                            if api_name.endswith('__c'):
                                python_name = api_name[:-3].lower().replace('__', '_')
                            else:
                                python_name = api_name.lower()

                            cleaned_result[python_name] = value

                cleaned_group_results.append(cleaned_result)

            obj_group['results'] = cleaned_group_results

            if 'metadata' in obj_group and 'fields' in obj_group['metadata']:
                del obj_group['metadata']['fields']

        return cleaned_results

    async def search_all(self, query: str) -> Dict[str, Any]:
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

        raw_response = await self.post("search", payload=search_payload)
        return self._clean_search_results(raw_response)

    async def search(
        self,
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

        if search_objects is None:
            config_list = [{"objectName": "Content", "pageNumber": 1, "pageSize": 10}]
        elif isinstance(search_objects, str):
            config_list = [{"objectName": search_objects, "pageNumber": 1, "pageSize": 10}]
        else:
            config_list = search_objects

        final_search_objects = []
        for cfg in config_list:
            obj_name_raw = cfg.get('objectName', 'Content')

            obj_name = obj_name_raw.lower().replace('__c', '')
            obj_name = obj_name.title()
            obj_name += '__c'

            page_num = cfg.get('pageNumber', 1)
            page_size = cfg.get('pageSize', 10)

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

        raw_response = await self.post("search", payload=search_payload)
        return self._clean_search_results(raw_response)

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Performs an unauthenticated GET request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/random').
            params: Optional dictionary of query parameters.
            timeout: Optional per-request timeout override.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.TimeoutException: If the request times out.
            httpx.HTTPStatusError: If the API request fails.
        """
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        request_timeout = timeout if timeout is not None else self.timeout

        try:
            logger.info(f"Attempting GET request to: {full_endpoint}")
            response = await self.session.get(url, params=params, timeout=request_timeout)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error(f"Request to {full_endpoint} timed out.")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"GET request failed: {e}")
            raise

    async def post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Performs an unauthenticated POST request to a generalized API endpoint with JSON data.

        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            timeout: Optional per-request timeout override.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.TimeoutException: If the request times out.
            httpx.HTTPStatusError: If the API request fails.
        """
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        request_timeout = timeout if timeout is not None else self.timeout

        try:
            logger.info(f"Attempting POST request to: {full_endpoint}")
            response = await self.session.post(url, json=payload, timeout=request_timeout)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error(f"POST request to {full_endpoint} timed out.")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"POST request failed: {e}")
            raise