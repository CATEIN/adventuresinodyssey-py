# Clients

* **`AIOClient`**: Use this for accessing any data that the public website can view **without logging in** (e.g., promotional content, general API structures).
* **`ClubClient`**: Use this for all private, user-specific, or club-subscriber content. It handles the complex authentication flow and token management necessary for all member-gated API endpoints.

[AIOClient](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/aioclient.md)

[ClubClient](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/clubclient.md)

# Logging

```python
from adventuresinodyssey import set_logging_level
set_logging_level('INFO')
```

# API Client Function Reference

This document provides a quick reference for the public methods available in the `AIOClient` (unauthenticated access) and `ClubClient` (authenticated access) classes.

More functions and methods might be added

| Function/Method | `AIOClient` (Public) | `ClubClient` (Authenticated) | Description |
| :--- | :---: | :---: | :--- |
| **Content Retrieval** | | | |
| `fetch_content(id, type)` | ✅ | ✅ | Retrieves the detailed data for a specific content item by its ID. |
|`fetch_content_group(id)` | ✅ | ✅ | Retrieves the detailed data for a specific content group item by its ID.
| `fetch_radio(content_type, page_number, page_size)` | ✅ | ✅ | Fetches the schedule of aired or upcoming radio episodes. (aired or upcoming) |
| `fetch_content_groupings(page_number, page_size, type)`| ✅ | ✅ | Retrieves a paginated list of content groupings by type (e.g., all **Albums** or **Collections**). |
| `fetch_characters(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of characters |
| `fetch_cast_and_crew(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of cast and crew |
| `fetch_themes(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of themes |
| `fetch_theme(theme_id)` | ✅ | ✅ | Retrieves the detailed data for a specific theme group item by its ID. |
| `cache_episodes()` | ✅ | ✅ | Caches all episodes by fetching all albums and returns a flattened list. |
| `search_all(query)` | ✅ | ✅ | searches for everything |
| `search(query, search_objects)` | ✅ | ✅ | searches |
| `fetch_signed_cookie(type)` | ❌ | ✅ | Fetches a signed cookie. Either audio or video |
| `fetch_random()` | ❌ | ✅ | Fetches a random episode. |
| `fetch_badge(badge_id)`| ❌ | ✅ | Retrieves the detailed data for a specific badge by its ID. |
| `fetch_badges(page_number, page_size)`| ❌ | ✅ | Retrieves a paginated list of badges |
| `fetch_comments(related_id, page_number, page_size)` | ❌ | ✅ | Fetches comments from given ID. |
| `post_comment(related_id, page_number, page_size)` | ❌ | ✅ | Posts a comment to a given page ID. |
| `post_reply(related_id, page_number, page_size)` | ❌ | ✅ | Posts a reply to a given comment ID. |
| `send_progress(id, progress, status)`  | ❌ | ✅ | Sends content progress and state to the club |
| **Low-Level API Access** | | | |
| `get(endpoint, params, headers)` | ✅ | ✅ | Performs a general **GET** request to an API endpoint. The `ClubClient` version handles authentication and retry. |
| `post(endpoint, json_data, headers)` | ✅ | ✅ | Performs a general **POST** request. The `ClubClient` version handles authentication and retry. |
| `put(endpoint, json_data, headers)` | ❌ | ✅ | Performs a general **PUT** request |

---
