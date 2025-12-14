"""
Adventures in Odyssey API Authentication Client
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlencode, urlparse, parse_qs
import requests
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

# Configure logging
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the common API prefix to be used for the new generalized methods
API_PREFIX = 'apexrest/v1/'

DEFAULT_FIELDS = {
    "Content__c": ["Name", "Thumbnail_Small__c", "Subtype__c", "Episode_Number__c"],
    "Content_Grouping__c": ["Name", "Image_URL__c", "Type__c"],
    "Topic__c": ["Name"],
    "Author__c": ["Name", "Profile_Image_URL__c"],
    "Character__c": ["Name", "Thumbnail_Small__c"],
    "Badge__c": ["Name", "Icon__c", "Type__c"]
}


class ClubClient:
    """
    Authentication client for Adventures in Odyssey API. 
    Handles login, token management, and authenticated API requests.
    """
    
    def __init__(self, email: str, password: str, viewer_id: Optional[str] = None, profile_username: Optional[str] = None, pin: Optional[str] = None, auto_relogin: bool = True, config_path: str = 'club_session.json'):
        """
        Initialize the AIO API client
        
        Args:
            email: User's account email address (used for web login).
            password: User's password.
            viewer_id: Optional. The specific Viewer ID (profile) to use. If provided, profile_username is ignored.
            profile_username: Optional. The username of the profile to select after account login. Required if viewer_id is not set.
            pin: Optional. The PIN for the selected profile. Defaults to '0000' if not provided.
        """
        # User credentials
        self.email = email
        self.password = password
        
        # Identity parameters
        self.viewer_id = viewer_id # User-provided ID, or None if derived from profile_username
        self.profile_username = profile_username
        self.pin = pin if pin is not None else "0000"
        
        # Session tokens
        self._refresh_token: Optional[str] = None
        self.session_token: Optional[str] = None
        
        # State tracking
        self.logging_in = False
        self.state = "loading"
        
        # Client configuration
        self.config = {
            'api_base': 'https://fotf.my.site.com/aio/services/', 
            'redirect_url': 'https://app.adventuresinodyssey.com/callback',
            'oauth_url': 'https://signin.auth.focusonthefamily.com',
            'api_version': 'v1',
            'client_id': '3MVG9l2zHsylwlpTFc1ZB3ryOQlpLYIqNo0UV4d0lBRjkbb6TXbw9UNhdcJfom2nnbB.AbNpkRbGoTfruF0gB',
            'client_secret': 'B25FC7FE3E4C155E77C73EA2AC72D410E0762C897798816FC257F0C8FA3618AD',
            'auto_relogin': auto_relogin
        }

        self.config_file = Path(config_path) 
        
        self._load_session_state()
        
        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'x-experience-name': 'Adventures In Odyssey',
            # These are set temporarily/initially. Will be finalized in _select_profile_and_set_headers
            'x-viewer-id': self.viewer_id if self.viewer_id else '',
            'x-pin': self.pin
        })
    
    def login(self) -> bool:
        """
        Login using Playwright to automate the OAuth flow and select the correct profile.
        
        Returns:
            bool: True if login successful and profile selected, False otherwise
        """
        if self.logging_in:
            logger.info("Login already in progress")
            return False
        
        self.logging_in = True
        self.state = "logging in"
        logger.info("Starting OAuth login...")
        
        try:
            # --- PHASE 1: OAuth Web Login (Get Session Token) ---
            
            auth_params = {
                'response_type': 'code',
                'client_id': self.config['client_id'],
                'redirect_uri': self.config['redirect_url'],
                'scope': 'api web refresh_token'
            }
            login_url = f"{self.config['api_base']}oauth2/authorize?{urlencode(auth_params)}"
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
                
                logger.info("Navigating to login page...")
                page.goto(login_url)
                
                # Fill login form
                # Ensure the selector is correct and fields are visible
                page.get_by_role("textbox", name="Email Address").wait_for(timeout=10000)
                page.get_by_role("textbox", name="Email Address").fill(self.email) # Use self.email now
                page.get_by_role("textbox", name="Password").fill(self.password)
                
                # Submit form and wait for navigation/redirect
                logger.info("Submitting login form and waiting for redirect...")
                with page.expect_navigation():
                    page.click('button[type="submit"]')
                
                # Wait for the final redirect to the callback URL
                page.wait_for_url(
                    lambda url: url.startswith(self.config['redirect_url']),
                    timeout=30000
                )
                callback_url = page.url
                browser.close()
            
            # Exchange authorization code for tokens
            parsed_url = urlparse(callback_url)
            auth_code = parse_qs(parsed_url.query).get('code', [None])[0]
            
            if not auth_code:
                raise ValueError("No authorization code ('code' parameter) in callback URL.")
            
            token_response = self._exchange_code_for_token(auth_code)
            
            # Store tokens and update session header
            self._refresh_token = token_response.get('refresh_token')
            self.session_token = token_response.get('access_token')
            self.session.headers['Authorization'] = f"Bearer {self.session_token}"
            
            logger.info("Account login successful.")
            
            # --- PHASE 2: Profile Selection (Get Viewer ID) ---
            if not self._select_profile_and_set_headers():
                self.state = "profile selection failed"
                self.session_token = None
                self._refresh_token = None
                self.logging_in = False
                return False
                
            self.logging_in = False
            self.state = "ready"
            logger.info("Login and profile selection successful!")
            self._save_session_state()
            
            return True
            
        except PlaywrightTimeout as e:
            self.state = "login failed"
            self.session_token = None
            self._refresh_token = None
            self.logging_in = False
            logger.error(f"Login failed (Playwright Timeout): {e}")
            raise RuntimeError(f"Failed to login: Playwright timed out. Check credentials or network.")
            
        except Exception as e:
            self.state = "login failed"
            self.session_token = None
            self._refresh_token = None
            self.logging_in = False
            logger.error(f"Login failed: {e}")
            # Raise RuntimeError to be caught by calling function
            raise RuntimeError(f"Failed to login: {e}")
        
    def _save_session_state(self):
        """Saves the essential session data to a local JSON file."""
        if not self._refresh_token or not self.viewer_id:
            logger.debug("Skipping save: Missing refresh token or viewer ID.")
            return

        state = {
            'refresh_token': self._refresh_token,
            'viewer_id': self.viewer_id,
            # Note: Storing the PIN is a security risk, but required for profile switching.
            'pin': self.pin 
        }
        
        try:
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
            logger.info(f"Session state saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def _load_session_state(self) -> bool:
        """Loads the essential session data from a local JSON file."""
        if not self.config_file.exists():
            return False
            
        try:
            with self.config_file.open('r', encoding='utf-8') as f:
                state = json.load(f)

            # 1. ALWAYS load the refresh token (this is the core of persistence)
            self._refresh_token = state.get('refresh_token')
            
            # 2. CONDITIONALLY load profile parameters
            
            # The viewer_id is only None if the user did NOT pass it to the constructor.
            # If the user supplied a viewer_id, we keep that new value.
            if self.viewer_id is None:
                self.viewer_id = state.get('viewer_id')
                
            # The pin defaults to "0000". If the user did NOT supply a pin 
            # (and it's currently "0000"), and the file has one, load the file's pin.
            # If the user supplied a custom pin (e.g., "1234"), we keep "1234".
            # This assumes the original value of self.pin is only "0000" if no pin was supplied.
            if self.pin == "0000" and state.get('pin'): 
                self.pin = state.get('pin')
            
            # Since the session token is short-lived, we *MUST* immediately try to refresh
            # to get a new access token before any API calls are made.
            # We don't call self.refresh_session() here because it depends on the 
            # self.session object and headers being set up, which happens *after* __init__.
            
            # The presence of the refresh_token is enough to signal that a saved session exists.
            if self._refresh_token:
                # Set state to ready, as we expect a refresh to follow
                self.state = "ready"
                logger.info("Loaded saved session state. Refresh required.")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
            return False
            
    def _fetch_viewer_profiles(self) -> List[Dict[str, Any]]:
        """GET /v1/viewer to retrieve all profiles associated with the account."""
        viewer_url = f"{self.config['api_base']}apexrest/{self.config['api_version']}/viewer"
        
        try:
            # Note: This API call needs the Authorization header set from Phase 1, 
            # but *before* the final x-viewer-id is set.
            response = self.session.get(viewer_url)
            response.raise_for_status()
            data = response.json()
            
            profiles = data.get("profiles", [])
            if not profiles:
                 logger.warning("Viewer endpoint returned no profiles.")
                 return []
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to fetch viewer profiles: {e}")
            return []

    def _select_profile_and_set_headers(self) -> bool:
        """
        Determines the Viewer ID, validates PIN if necessary, and sets the final 
        x-viewer-id and x-pin headers for subsequent API calls.
        
        The selection priority is:
        1. Explicit self.viewer_id
        2. Explicit self.profile_username (with PIN check)
        3. Automatic selection of the first profile without a PIN (if neither ID nor username is set)
        
        Returns:
            bool: True if profile selection succeeded, False otherwise.
        """
        # Case 1: Viewer ID was provided directly (highest priority)
        if self.viewer_id:
            logger.info(f"Using provided Viewer ID: {self.viewer_id}")
            self.session.headers['x-viewer-id'] = self.viewer_id
            self.session.headers['x-pin'] = self.pin
            return True

        # Need profiles for Case 2 and 3
        profiles = self._fetch_viewer_profiles()
        if not profiles:
            logger.error("Profile selection failed: Could not retrieve profile list.")
            return False

        selected_profile = None
        
        # Case 2: Profile username was provided
        if self.profile_username:
            logger.info(f"Searching for profile with username: '{self.profile_username}'")
            selected_profile = next(
                (p for p in profiles if p.get('username') == self.profile_username), 
                None
            )
            
            if not selected_profile:
                logger.error(f"Profile selection failed: Could not find profile with username '{self.profile_username}'.")
                return False
                
            has_pin = selected_profile.get('hasPIN', False)
            if has_pin and self.pin == "0000":
                # Pin is required but user did not provide one (using default "0000")
                logger.error(f"Profile '{self.profile_username}' requires a PIN, but the default PIN '{self.pin}' was used. Login aborted.")
                return False
        
        # Case 3: Automatic Selection (if neither Viewer ID nor Username was provided)
        elif not self.viewer_id and not self.profile_username: 
            logger.info("No Viewer ID or Username provided. Attempting to auto-select first profile with no PIN.")
            
            # Find the first profile that does not have a PIN
            selected_profile = next(
                (p for p in profiles if not p.get('hasPIN', False)),
                None
            )
            
            if not selected_profile:
                logger.error("Auto-selection failed: No profile found that does not require a PIN.")
                return False
            
            # For auto-selection of a no-PIN profile, ensure the pin header is '0000'
            self.pin = "0000"
            
        # If no profile was selected by any case, return False
        if not selected_profile:
            logger.error("Profile selection failed: Could not identify a profile to use.")
            return False

        # --- Final Header Setup ---
        self.viewer_id = selected_profile['viewer_id']
        self.session.headers['x-viewer-id'] = self.viewer_id
        # self.pin is already correctly set by Case 1, 2, or 3
        self.session.headers['x-pin'] = self.pin 
        
        log_name = selected_profile.get('username', 'N/A')
        logger.info(f"Profile selected: '{log_name}' (Viewer ID: {self.viewer_id}).")
        
        return True

    def _exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        token_url = f"{self.config['api_base']}oauth2/token"
        token_params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.config['redirect_url'],
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret']
        }
        
        response = self.session.post(token_url, params=token_params)
        response.raise_for_status()
        
        return response.json()
    
    def refresh_session(self) -> bool:
        """Refresh the session using the refresh token."""
        if not self._refresh_token:
            logger.info("Session refresh skipped: no refresh token available")
            return False
        
        try:
            token_url = f"{self.config['api_base']}oauth2/token"
            token_params = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret'],
            }
            
            response = self.session.post(token_url, params=token_params)
            
            if response.status_code == 200:
                token_data = response.json()
                self.session_token = token_data.get('access_token')
                if token_data.get('refresh_token'):
                    self._refresh_token = token_data.get('refresh_token')
                
                self.session.headers['Authorization'] = f"Bearer {self.session_token}"
                logger.info("Token refresh successful!")
                return True
            else:
                logger.warning(f"Token refresh failed with status {response.status_code}. Full login will be required.")
                self.session_token = None
                self._refresh_token = None
                return False
                
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            self.session_token = None
            self._refresh_token = None
            return False
    
    def check_session(self) -> bool:
        """Check if the current session token is valid and required headers are set."""
        if not self.session_token:
            return False
        
        # Check if the required headers are set (Viewer ID is essential for API calls)
        if not self.session.headers.get('x-viewer-id'):
            logger.debug("Session check failed: x-viewer-id is missing.")
            return False
        
        try:
            introspect_url = f"{self.config['api_base']}oauth2/introspect"
            introspect_params = {
                'token': self.session_token,
                'token_type_hint': 'access_token',
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret']
            }
            
            response = self.session.post(introspect_url, params=introspect_params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('active', False)
            
            return False
            
        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure the client is authenticated, attempting login/refresh as needed.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # 1. Check if current session is valid
        if self.check_session():
            logger.debug("Session is valid.")
            return True
        
        # 2. Try to refresh session
        logger.info("Session invalid, attempting refresh...")
        if self.refresh_session():
            return True
        
        # 3. Fall back to full login (Only if enabled)
        if self.config['auto_relogin']:
            logger.info("Refresh failed, attempting full login...")
            return self.login()
        else:
            logger.warning("Refresh failed. Automatic full login is disabled.")
            return False # Return False if we can't refresh and can't relogin
    
    def change_profile(self, viewer_id: str, pin: str) -> bool:
        """
        Switches the active profile (viewer) for authenticated requests without
        requiring a full web login, as long as the session token is still valid.
        
        This updates the 'x-viewer-id' and 'x-pin' headers for all subsequent API calls.
        
        Args:
            viewer_id: The ID of the profile to switch to.
            pin: The PIN associated with the new profile.
            
        Returns:
            bool: True if the profile was successfully switched and headers updated.
        """
        if self.state != "authenticated":
            logger.warning("Attempted to change profile on an unauthenticated client. Please login first.")
            return False
            
        logger.info(f"Switching active profile to ID: {viewer_id}...")
        
        self.viewer_id = viewer_id
        self.pin = pin
        self.session.headers['x-viewer-id'] = self.viewer_id
        self.session.headers['x-pin'] = self.pin
        
        logger.info("Profile successfully switched. Headers updated.")
        return True

    def fetch_content(self, content_id: str, page_type: str = 'full') -> Dict[str, Any]:
        """
        Fetches detailed content data for a given ID, based on page_type.
        
        Args:
            content_id: The ID of the content to fetch (e.g., 'a354W0000046U6OQAU').
            page_type: The type of content page: 'full' (default), 'radio', or 'promo'.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        # Determine authentication requirement and request parameters
        needs_auth = (page_type != 'promo')
        is_radio = (page_type == 'radio')
        
        # 1. Handle Authentication if required
        if needs_auth:
            if not self.ensure_authenticated():
                raise RuntimeError(f"Cannot fetch content for page_type '{page_type}': Failed to authenticate user.")
            
            session_to_use = self.session
            
        else:
            # Promo page type requires NO authentication/viewer/pin headers
            logger.info("Fetching content for 'promo' page type (unauthenticated request).")
            
            # Use a clean set of headers, keeping only the experience name if necessary
            headers = {'x-experience-name': 'Adventures In Odyssey'}
            # Temporarily remove default Authorization header for this request type
            session_to_use = requests.Session()
            session_to_use.headers.update(headers)
            
        # Base API URL structure for content details
        endpoint = f"apexrest/{self.config['api_version']}/content/{content_id}"
        url = f"{self.config['api_base']}{endpoint}"

        # Standard default parameters for 'full' and 'promo'
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

        def make_request():
            response = session_to_use.get(url, params=params)
            return response

        try:
            # 1. Initial attempt
            logger.info(f"Attempting to fetch content ID: {content_id} (Page Type: {page_type})")
            response = make_request()

            # 2. Handle Unauthorized (401) ONLY if authentication was required (needs_auth)
            if needs_auth and response.status_code == 401:
                logger.warning("Initial request failed with 401 Unauthorized. Attempting re-authentication...")
                
                # Try to refresh/re-login
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # 3. Retry attempt
                    response = make_request()
                else:
                    # If re-authentication failed, raise the initial 401 error
                    response.raise_for_status() 

            # Raise for any other non-2xx status codes (400, 403, 404, 500 etc.)
            response.raise_for_status()
            
            logger.info(f"Content fetch successful for ID: {content_id} (Page Type: {page_type})")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch content ID {content_id} (Page Type: {page_type}): {e}")
            raise
        
    def fetch_badge(self, badge_id: str) -> Dict[str, Any]:
        """
        Fetches detailed data for a badge (sometimes called an adventure).
        
        Args:
            badge_id: The ID of the badge to fetch (e.g., 'a2pUh0000008GXSIA2').
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get(f"badges/{badge_id}")
    
    def fetch_radio(self, content_type: str = 'aired', page_number: int = 1, page_size: int = 5) -> Dict[str, Any]:
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
        if content_type == 'aired':
            params['orderby'] = 'Recent_Air_Date__c DESC'
            params['radio_page_type'] = 'aired'
            log_info = "Aired Radio Episodes"
        elif content_type == 'upcoming':
            params['orderby'] = 'Recent_Air_Date__c ASC'
            params['radio_page_type'] = 'upcoming'
            log_info = "Upcoming Radio Episodes"
        else:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be 'aired' or 'upcoming'.")
            
        logger.info(f"Attempting to fetch {log_info} (Page {page_number}, Size {page_size})")

        # The endpoint is 'content/search', and the generalized get method handles the base URL.
        return self.get("content/search", params=params)
    
    def cache_episodes(self, grouping_type: str = "Album") -> List[Dict[str, Any]]:
        """
        Retrieves all available audio episodes from the specified content grouping type 
        (e.g., "Album", "Episode Home"), cleans the data, and returns a flattened list. 
        Excludes episodes starting with "BONUS!".

        This function automatically handles pagination across all pages for the grouping type.

        Args:
            grouping_type (str): The type of content grouping to fetch episodes from 
                                (e.g., "Album", "Episode Home"). Defaults to "Album".

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
                grouping_type=grouping_type,  # <<< CHANGED TO USE ARGUMENT
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
                    
                    # 1. Filter out episodes starting with "BONUS!"
                    if episode_name.startswith("BONUS!"):
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
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
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
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        
        # Construct the payload based on arguments
        if payload is not None:
            # Use custom payload provided by the user
            request_payload = payload
            log_info = "custom payload"
        else:
            # Use structured payload based on function arguments
            request_payload = {
                "type": grouping_type,
                "community": "Adventures in Odyssey",
                "pageNumber": page_number,
                "pageSize": page_size
            }
            log_info = f"Type: {grouping_type}, Page {page_number}, Size {page_size}"

        logger.info(f"Attempting to fetch content groupings ({log_info})")
        
        return self.post("contentgrouping/search", request_payload)
            
    def send_progress(self, content_id: str, progress: int, status: str) -> Dict[str, Any]:
        """
        Sends playback progress and status updates for a specific content ID.
        
        Sends a PUT request to /v1/content with a JSON body.
        
        Args:
            content_id: The ID of the content being updated.
            progress: The current playback position in seconds (integer).
            status: The playback status, typically 'In Progress' or 'Completed'.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API (usually success confirmation).
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        
        request_payload = {
            "content_id": content_id,
            "status": status,
            "current_progress": progress
        }
        
        log_info = f"ID: {content_id}, Status: {status}, Progress: {progress}s"
        logger.info(f"Attempting to send progress update: ({log_info})")

        return self.put("content", request_payload)


    def fetch_random(self) -> Dict[str, Any]:
        """
        Fetches a random piece of content (episode/media) from the API.
        
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get("content/random")
    
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

    def fetch_badges(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of available badges for the profile.
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        request_payload = {
            "type": "Badge",
            "pageNumber": page_number,
            "pageSize": page_size
        }
        
        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch badges ({log_info})")
        
        return self.post("badge/search", request_payload)
    
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
    
    def fetch_comments(self, related_id: str = None, page_number: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Fetches a paginated list of comments. Can fetch comments related to a 
        specific content item or fetch a general list of comments if no ID is provided.
        
        Args:
            related_id: The ID of the content item (e.g., episode, grouping) the comments 
                        belong to. Defaults to None, in which case the API should return 
                        a general list.
            page_number: The page number to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 10.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the comments.
        
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        
        json_data = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "orderBy": "CreatedDate DESC"
        }

        # Only include 'relatedToId' in the payload if a related_id was actually passed.
        if related_id is not None:
            json_data["relatedToId"] = related_id

        # POST to: apexrest/v1/comment/search
        return self.post("comment/search", payload=json_data)

    def post_comment(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a new comment to a content item (episode, grouping, etc.).
        
        This requires the client to be fully authenticated with a selected profile.
        
        Args:
            message: The comment text.
            related_id: The ID of the content item the comment is related to.
            
        Returns:
            Dict[str, Any]: The parsed JSON response (often status of the posted comment).
            
        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        # Ensure the viewer ID (profile ID) is available from the login process
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        comment_payload = {
            "comment": {
                # This ID links the comment to the content item
                "relatedToId": related_id, 
                # This ID identifies the profile posting the comment
                "viewerProfileId": self.viewer_id, 
                "message": message
            }
        }
        # POST to: apexrest/v1/comment
        # ClubClient's post method will handle authentication and retries
        return self.post("comment", payload=comment_payload)
    
    def post_reply(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a reply to a comment.
        
        This requires the client to be fully authenticated with a selected profile.
        
        Args:
            message: The reply text.
            related_id: The ID of the comment to reply to.
            
        Returns:
            Dict[str, Any]: The parsed JSON response (often status of the posted comment).
            
        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        # Ensure the viewer ID (profile ID) is available from the login process
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        reply_payload = {
                # This ID links the comment to the content item
                "relatedToId": related_id, 
                # This ID identifies the profile posting the comment
                "viewerProfileId": self.viewer_id, 
                "message": message
        }
        # POST to: apexrest/v1/comment
        # ClubClient's post method will handle authentication and retries
        return self.post("comment", payload=reply_payload)
    
    def fetch_bookmarks(self) -> Dict[str, Any]:
        """
        Retrieves all content bookmarked by the current club member.
        
        Returns:
            Dict[str, Any]: The search results containing bookmarked content.
        """
        # The API endpoint is a GET request with all necessary query parameters
        endpoint = (
            "content/search?community=Adventures+In+Odyssey"
            "&is_bookmarked=true"
            "&tag=true"
        )
        # Use the ClubClient's authenticated GET method
        return self.get(endpoint)

    def bookmark(self, content_id: str) -> Dict[str, Any]:
        """
        Creates a new bookmark for a given piece of content.
        
        Args:
            content_id: The ID of the content item to bookmark (e.g., an episode ID).
            
        Returns:
            Dict[str, Any]: The API response, typically confirming creation.
            
        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        if not self.viewer_id:
            raise ValueError("Cannot create bookmark: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        payload = {
            "subject_id": content_id,
            "bookmark_type": "Bookmark",
            "subject_type": "Content__c"
        }
        
        # POST to: apexrest/v1/bookmark
        # Use the ClubClient's authenticated POST method
        return self.post("bookmark", payload=payload)
    
    def create_playlist(self, json_payload: dict) -> str:
        """
        Creates a new content grouping (playlist) by directly posting the 
        provided JSON payload to the /v1/contentgrouping endpoint.

        This simplified version bypasses argument construction and requires
        the caller to provide the complete request body.

        Args:
            json_payload: A dictionary representing the full request body 
                        for the API call, e.g., {"contentGroupings": [ ... ]}.

        Returns:
            str: The ID of the newly created playlist (e.g., 'a31Up000007WmVJIA0').

        Raises:
            RuntimeError: If authentication fails.
            requests.exceptions.HTTPError: If the API request fails.
            KeyError: If the API response structure is unexpected.
            ValueError: If the required payload structure is not present.
        """
        
        # --- Validation and Logging ---
        try:
            # Attempt to extract the playlist name for logging purposes
            playlist_name = json_payload['contentGroupings'][0]['name']
            num_items = len(json_payload['contentGroupings'][0]['contentList'])
            log_info = f"Name: {playlist_name}, Items: {num_items}"
        except (KeyError, IndexError):
            # If structure is missing, just use a generic log and raise a clear error
            logger.warning("JSON payload does not conform to expected 'contentGroupings[0]['name']' structure.")
            log_info = "Malformed Payload (details missing)"
            
        if not json_payload.get('contentGroupings'):
            raise ValueError("JSON payload must contain the 'contentGroupings' key.")

        logger.info(f"Attempting to create new playlist with direct JSON payload: ({log_info})")

        # --- API Call ---
        # The base URL and API prefix are handled by self.post
        # POST to: apexrest/v1/contentgrouping
        response = self.post("contentgrouping", payload=json_payload)
        
        # --- Response Parsing ---
        # Expected response structure:
        # { "metadata": {}, "errors": [], "contentGroupings": [ { "id": "...", ... } ] }
        
        try:
            # Extract the ID of the first (and only) grouping in the response list
            playlist_id = response['contentGroupings'][0]['id']
            logger.info(f"Playlist successfully created with ID: {playlist_id}")
            return playlist_id
            
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse playlist ID from API response: {e}")
            logger.debug(f"Raw Response: {response}")
            raise KeyError("API response was missing the expected 'contentGroupings[0]['id']' field.")
        
    def fetch_signed_cookie(self, content_type: str = 'audio') -> str:
        """
        Fetches the content data for a known audio or video test ID, extracts the 
        signed cookie URL, and returns the query string portion *prefixed with '?'*.

        Args:
            content_type: The type of content to fetch: 'audio' or 'video'.

        Returns:
            str: The signed cookie URL query string, including the leading '?' (e.g., ?Policy=...&Signature=...&Key-Pair-Id=...).

        Raises:
            ValueError: If an invalid content_type is provided or the cookie URL is missing.
            requests.exceptions.HTTPError: If the underlying API request fails.
        """
        if content_type.lower() == 'audio':
            content_id = "a354W0000046V5fQAE"
            logger.info("Fetching signed cookie for known audio content ID.")
        elif content_type.lower() == 'video':
            content_id = "a354W0000046SHtQAM"
            logger.info("Fetching signed cookie for known video content ID.")
        else:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be 'audio' or 'video'.")

        # 1. Fetch the content data
        # Note: This uses the default 'full' page_type, which is authenticated.
        content_data = self.fetch_content(content_id)

        # 2. Extract the signed cookie URL
        # The key for the signed content URL is typically 'signed_cookie'
        # The API response structure varies, but often the signed URL is nested under 'media' or similar.
        signed_cookie_url = content_data.get('signed_cookie') 
        
        if not signed_cookie_url:
            logger.error("Signed cookie URL not found in API response.")
            raise ValueError("API response for content ID contains no 'signed_cookie' or similar URL.")

        # 3. Parse the URL to get only the query parameters
        # Example URL: https://media.adventuresinodyssey.com/.../*?Policy=...&Signature=...&Key-Pair-Id=...
        parsed_url = urlparse(signed_cookie_url)
        
        # The query component is the part after the '?'
        if not parsed_url.query:
            logger.error(f"URL contains no query parameters: {signed_cookie_url}")
            raise ValueError("The retrieved signed cookie URL did not contain a query string.")
            
        logger.info(f"Successfully extracted signed cookie query for ID: {content_id}")
        
        # *** MODIFICATION HERE ***
        # Prepend the '?' to the query string before returning.
        return '?' + parsed_url.query
        
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated GET request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/random').
            params: Optional dictionary of query parameters.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform GET request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        # 1. Start with the session's default headers
        request_headers = self.session.headers.copy()
        # 2. Update/Override with the provided headers
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            response = self.session.get(url, params=params, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting GET request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("GET request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # If re-auth succeeds, the session headers are updated, but we still need 
                    # to use the potentially overridden headers for the retry.
                    # Since session.headers updates 'Authorization', we re-copy it here.
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"GET request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"GET request failed for {full_endpoint}: {e}")
            raise

    def post(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated POST request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform POST request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            # Use json=payload to automatically set Content-Type: application/json
            response = self.session.post(url, json=payload, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting POST request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("POST request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # Update request headers after re-authentication
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"POST request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"POST request failed for {full_endpoint}: {e}")
            raise

    def put(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated PUT request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'content').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API, or a success dictionary if no content is returned.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform PUT request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            # Use json=payload to automatically set Content-Type: application/json
            response = self.session.put(url, json=payload, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting PUT request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("PUT request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # Update request headers after re-authentication
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"PUT request successful for: {full_endpoint}")
            # API might return no content for PUT (204 No Content), so check for content before parsing
            return response.json() if response.content else {"status": "success"}

        except requests.exceptions.HTTPError as e:
            logger.error(f"PUT request failed for {full_endpoint}: {e}")
            raise