# Clients

* [AIOClient](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/aioclient.md): Use this for accessing any data that the public website can view **without logging in** (e.g., promotional content, general API structures).
* [ClubClient](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/clubclient.md): Use this for all private, user-specific, or club-subscriber content. It handles the complex authentication flow and token management necessary for all member-gated API endpoints. `ClubClient` inherits all functions from `AIOClient` .

# [Content](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/content.md)

# Logging

```python
from adventuresinodyssey import set_logging_level
set_logging_level('INFO')
```

# API Client Function Reference

Quick reference for the public methods available in the `AIOClient` (unauthenticated access) and `ClubClient` (authenticated access) classes.

| Function | `AIOClient` (Public) | `ClubClient` (Authenticated) | Description |
| :--- | :---: | :---: | :--- |
| **Content page** | | | |
| `fetch_content(content_id, page_type)` | ✅ | ✅ | Retrieves the detailed data for a specific content item by its ID. |
| `fetch_character(character_id)` | ✅ | ✅ | Retrieves the detailed data for a specific character by its ID. |
| `fetch_author(author_id)` | ✅ | ✅ | Retrieves the detailed data for a specific author by its ID (cast and crew). |
| `fetch_random()` | ❌ | ✅ | Fetches a random episode. |
| **Content group** | | | |
| `fetch_theme(theme_id)` | ✅ | ✅ | Retrieves the detailed data for a specific theme group item by its ID. |
| `fetch_content_group(group_id)` | ✅ | ✅ | Retrieves the detailed data for a specific content group item by its ID.|
| `fetch_badge(badge_id)`| ❌ | ✅ | Retrieves the detailed data for a specific badge by its ID. |
| **Content groupings** | | | |
| `fetch_home_playlists()`|  ✅ | ✅ | Retrieves a contentgroups on the home page |
| `fetch_cast_and_crew(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of cast and crew |
| `fetch_themes(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of themes |
| `fetch_characters(page_number, page_size)`|  ✅ | ✅ | Retrieves a paginated list of characters |
| `fetch_content_groupings(page_number, page_size, type)`| ✅ | ✅ | Retrieves a paginated list of content groupings by type (e.g., all **Albums** or **Collections**). |
| `fetch_radio(page_type, page_number, page_size)` | ✅ | ✅ | Fetches the schedule of aired or upcoming radio episodes. (aired or upcoming) |
| `fetch_bookmarks()`|  ✅ | ✅ | Retrieves a paginated list of bookmarks |
| `fetch_badges(page_number, page_size)`| ❌ | ✅ | Retrieves a paginated list of badges |
| **Search** | | | |
| `search_all(query)` | ✅ | ✅ | searches for everything |
| `search(query, search_objects)` | ✅ | ✅ | searches |
| **Upload content** | | | |
| `create_playlist(name, image_url, content_ids, playlist_json)` | ❌ | ✅ | Creates a playlist with the provided data.|
| `update_playlist(playlist, name, image_url, content_ids, add_ids, remove_ids)` | ❌ | ✅ | Updates a playlist with the provided data.|
| `send_progress(content_id, progress, status)`  | ❌ | ✅ | Sends content progress and state to the club |
| **Comments/Commenting** | | | |
| `post_comment(message, related_id)` | ❌ | ✅ | Posts a comment to a given page ID. |
| `post_reply(message, related_id)` | ❌ | ✅ | Posts a reply to a given comment ID. |
| `fetch_comment(comment_id, related_id)` | ❌ | ✅ | Fetches comment from given ID. Including the related_id includes replies. |
| `fetch_comments(related_id, page_number, page_size)` | ❌ | ✅ | Fetches comments from given ID. |
| `delete_comment(comment_id)` | ❌ | ✅ | Deletes comment by given ID. |
| **Other** | | | |
| `fetch_carousel()`|  ✅ | ✅ | Retrieves the carousel from home page |
| `bookmark(content_id)` | ❌ | ✅ | Bookmarks (favorites) given ID. |
| `fetch_profiles()` | ❌ | ✅ | Fetches the profiles for the account |
| `change_profile(viewer_id, pin)` | ❌ | ✅ | Changes the current profile to the provided one |
| `delete_playlist(playlist_id)` | ❌ | ✅ | Deletes playlist by given ID. |
| **Low-Level API Access** | | | |
| `get(endpoint, params, headers)` | ✅ | ✅ | Performs a general **GET** request to an API endpoint. The `ClubClient` version handles authentication and retry. |
| `post(endpoint, payload, headers)` | ✅ | ✅ | Performs a general **POST** request. The `ClubClient` version handles authentication and retry. |
| `put(endpoint, payload, headers)` | ❌ | ✅ | Performs a general **PUT** request |
| `delete(endpoint)` | ❌ | ✅ | Performs a general **DELETE** request |
| **Custom functions** | | | |
| `cache_episodes(grouping_type, include_bonus)` | ✅ | ✅ | Caches all episodes by fetching all albums and returns a flattened list. |
| `cache_albums(grouping_type, include_club_exclusive)` | ✅ | ✅ | Caches all albums and returns a flattened list. |
| `cache_content_groupings(generate_themes)` | ✅ | ✅ | Caches all content groupings and returns a flattened list. |
| `fetch_signed_cookie(type)` | ❌ | ✅ | Fetches a signed cookie. Either audio or video |
| `find_comment_pages()` | ❌ | ✅ | Fetches comments and returns comment pages (most active are top) |

---

## fetch_content(content_id, page_type)
```python
from adventuresinodyssey import AIOClient
client = AIOClient()
episode = client.fetch_content(content_id="a35Uh0000005suDIAQ", page_type="promo")
print(episode["short_name"])
```

## fetch_character(character_id)
```python
from adventuresinodyssey import AIOClient
client = AIOClient()
character = client.fetch_character(character_id="a2t4W000005cKTMQA2")
print(character["characters"][0]["first_name"])
```
## fetch_theme(theme_id)
```python
from adventuresinodyssey import AIOClient
client = AIOClient()
theme = client.fetch_theme(theme_id="a3H4W000004OhqnUAC")
print(theme["topics"][0]["name"])
```
