# adventuresinodyssey documentation

Unofficial Python clients for the Adventures in Odyssey Club API. New here? Read the [README](../README.md) for installation and a quick start, then come back.

## Contents

**Clients**
* [AIOClient](aioclient.md): public data, no login
* [ClubClient](clubclient.md): login, profiles and sessions
* [Async clients](async.md): `AsyncAIOClient` and `AsyncClubClient`

**Guides**
* [Content](content.md): episodes, videos and other content pages, media URLs, listening progress
* [Groupings](groupings.md): albums, series, collections, themes and badges
* [Browsing](browsing.md): radio schedule, new releases, characters, cast and crew, home page
* [Search](search.md)
* [Playlists and bookmarks](playlists.md)
* [Comments](comments.md)
* [Cache functions](cachefunctions.md): download whole catalogs in one call

**Reference**
* [Function reference](#function-reference)
* [Low-level requests](#low-level-requests)
* [Logging](#logging)
* [Errors](#errors)

---

## Key concepts

### IDs

Everything on the Club has an 18-character ID. You'll find it at the end of the URL on the website:

| Website URL | What the ID is |
| --- | --- |
| `app.adventuresinodyssey.com/content/a354W0000046U7kQAE` | Content (episode, video, article...) |
| `app.adventuresinodyssey.com/playlists/a31...` | Playlist (a kind of content group) |

The first three characters tell you what kind of object it is:

| Prefix | Object | Fetch it with |
| --- | --- | --- |
| `a35` | Content | `fetch_content()` |
| `a31` | Content group | `fetch_content_group()` |
| `a2t` | Character | `fetch_character()` |
| `a2m` | Author (cast and crew) | `fetch_author()` |
| `a3H` | Theme (topic) | `fetch_theme()` |
| `a2p` | Badge | `fetch_badge()` (ClubClient) |
| `a2w` | Comment | `fetch_comment()` (ClubClient) |

### Responses are plain dictionaries

Every method returns the API's JSON as a Python `dict` (or a `list` for the cache functions). Nothing is wrapped in custom classes, so `print()` or `json.dumps(result, indent=2)` is the quickest way to see what's available.

Responses come in a few shapes, depending on the endpoint:

| Shape | Returned by | Items are in |
| --- | --- | --- |
| Single object | `fetch_content()` | the top level |
| Grouping list | `fetch_content_group()`, `fetch_content_groupings()`, `fetch_playlists()`, `create_playlist()` | `["contentGroupings"]` |
| Content search | `fetch_radio()`, `fetch_new_content()`, `fetch_bookmarks()` | `["results"]` |
| Other lists | `fetch_characters()` / `fetch_character()`, `fetch_cast_and_crew()` / `fetch_author()`, `fetch_themes()` / `fetch_theme()`, `fetch_badges()` / `fetch_badge()`, `fetch_comments()` | `["characters"]`, `["authors"]`, `["topics"]`, `["badges"]`, `["comments"]` |
| Search | `search()`, `search_all()` | `["resultObjects"][n]["results"]` |

Note that fetching a *single* character, author, theme, badge or group still returns a list with one item, for example `client.fetch_character(id)["characters"][0]`.

### Pagination

Methods that return lists take `page_number` (starting at 1) and `page_size`. How you find the total depends on the shape:

```python
# Grouping-style and "other" lists
page = client.fetch_content_groupings(page_number=1, page_size=25)
page["metadata"]["totalPageCount"]
page["metadata"]["totalRecordCount"]

# Content-search lists
page = client.fetch_radio(page_number=1, page_size=25)
page["total_pages"]
page["total_count"]
```

If you want *everything*, the [cache functions](cachefunctions.md) handle pagination for you.

### Page types

Content can be fetched as a `promo`, `radio` or `full` page. They differ mainly in which audio/video you get back. See [Content](content.md#page-types).

---

## Function reference

✅ = available. All four clients have the same methods; the async ones just need `await`.

### Content

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `fetch_content(content_id, page_type)` | ✅ | ✅ | One content page. `page_type` is `"promo"`, `"radio"` or `"full"` (Club only). Defaults: `"promo"` on AIOClient, `"full"` on ClubClient. [Docs](content.md) |
| `fetch_random()` | | ✅ | A random episode. |
| `update_content_status(content_id, progress, status, devotional_complete, timestamp)` | | ✅ | Save listening progress (ms), status or devotional completion. Check the result: the server can skip updates. [Docs](content.md#saving-listening-progress) |
| `fetch_signed_cookie(content_type)` | | ✅ | The current media signature, as a `?Policy=...` query string. `content_type` is `"audio"` or `"video"`. |

### Groupings

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `fetch_content_group(group_id)` | ✅ | ✅ | One album, collection, series, etc. with its `contentList`. [Docs](groupings.md#a-single-group) |
| `fetch_content_groupings(page_number, page_size, grouping_type, order_by, payload)` | ✅ | ✅ | A page of groupings of one type, e.g. `"Album"`. [Docs](groupings.md) |
| `fetch_themes(page_number, page_size)` | ✅ | ✅ | A page of top-level themes with their sub-themes. |
| `fetch_theme(theme_id)` | ✅ | ✅ | One theme with recommended content. |
| `fetch_badges(page_number, page_size)` | | ✅ | A page of badges (adventures). [Docs](groupings.md#badges) |
| `fetch_badge(badge_id)` | | ✅ | One badge and its requirements. |

### Browsing

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `fetch_radio(page_type, page_number, page_size)` | ✅ | ✅ | Radio schedule. `page_type` is `"aired"` (newest first) or `"upcoming"`. [Docs](browsing.md#radio-schedule) |
| `fetch_new_content(page_number, page_size)` | ✅ | ✅ | Most recently published content. |
| `fetch_characters(page_number, page_size)` | ✅ | ✅ | A page of characters. |
| `fetch_character(character_id)` | ✅ | ✅ | One character with bio, voice actor and appearances. |
| `fetch_cast_and_crew(page_number, page_size)` | ✅ | ✅ | A page of cast and crew. |
| `fetch_author(author_id)` | ✅ | ✅ | One cast or crew member with bio. |
| `fetch_home_playlists()` | ✅ | ✅ | The groupings shown on the home page. |
| `fetch_carousel()` | ✅ | ✅ | The home page banner carousel. |

### Search

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `search(query, search_objects)` | ✅ | ✅ | Search one or more object types (content by default). [Docs](search.md) |
| `search_all(query)` | ✅ | ✅ | Search every object type, 9 results each. |

### Playlists and bookmarks

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `fetch_playlists(page_number, page_size)` | | ✅ | Playlists made by the current profile. [Docs](playlists.md) |
| `create_playlist(name, image_url, content_ids, playlist_json)` | | ✅ | Create a playlist. |
| `update_playlist(playlist, name, image_url, add_ids, content_ids, remove_ids)` | | ✅ | Rename, add to, remove from or replace a playlist. |
| `delete_playlist(playlist_id)` | | ✅ | Delete a playlist. |
| `fetch_bookmarks()` | | ✅ | Everything the current profile has bookmarked. |
| `bookmark(content_id)` | | ✅ | Bookmark a content item. |

### Comments

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `fetch_comments(related_id, page_number, page_size, order_by)` | | ✅ | Comments on a page or comment (or the latest site-wide if no ID). [Docs](comments.md) |
| `fetch_comment(comment_id, related_id)` | | ✅ | One comment, with replies if `related_id` is given. |
| `post_comment(message, related_id)` | | ✅ | Comment on a page. |
| `post_reply(message, related_id)` | | ✅ | Reply to a comment. |
| `delete_comment(comment_id)` | | ✅ | Delete your comment. |
| `find_comment_pages()` | | ✅ | Pages with the most recent comment activity. |

### Cache functions

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `cache_episodes(grouping_type, include_bonus)` | ✅ | ✅ | Every audio episode, as one flat list. [Docs](cachefunctions.md) |
| `cache_albums(grouping_type, include_club_exclusive)` | ✅ | ✅ | Every album (or other grouping type), as one list. |
| `cache_audiobooks()` | ✅ | ✅ | Every audiobook. |
| `cache_content_groupings(generate_themes)` | ✅ | ✅ | Every grouping of every type. |

### Account and session (ClubClient only)

| Method | Description |
| --- | --- |
| `login()` | Log in through a headless browser. Called for you automatically. [Docs](clubclient.md) |
| `ensure_authenticated()` | Check the session, refreshing it or logging in again if needed. |
| `refresh_session()` | Get a new access token using the saved refresh token. |
| `check_session()` | `True` if the current access token is still valid. |
| `fetch_profiles()` | The profiles on the account. |
| `change_profile(viewer_id, pin)` | Switch to another profile. `pin` is only needed if it has one. [Docs](clubclient.md#switching-profiles) |
| `check_pin(viewer_id, pin)` | `True` if the PIN is correct for a profile (defaults to the current one). [Docs](clubclient.md#checking-a-pin) |
| `logout(timeout)` | Revoke the session, visit the logout page and delete the session file. [Docs](clubclient.md#logging-out) |

### Low-level requests

| Method | AIO | Club | Description |
| --- | :---: | :---: | --- |
| `get(endpoint, params)` | ✅ | ✅ | GET request |
| `post(endpoint, payload)` | ✅ | ✅ | POST request with a JSON body |
| `put(endpoint, payload)` | | ✅ | PUT request with a JSON body |
| `patch(endpoint, payload)` | | ✅ | PATCH request with a JSON body |
| `delete(endpoint, params)` | | ✅ | DELETE request |

---

## Low-level requests

If the library doesn't have a method for something the website does, you can call the endpoint directly. `endpoint` is the path after `https://fotf.my.site.com/aio/services/apexrest/v1/`. Open your browser's developer tools on the website (Network tab) to find endpoints and payloads.

```python
from adventuresinodyssey import AIOClient

client = AIOClient()

# Same as client.fetch_radio(), written by hand
data = client.get("content/search", params={
    "content_type": "Audio",
    "content_subtype": "Episode",
    "community": "Adventures In Odyssey",
    "orderby": "Recent_Air_Date__c DESC",
    "radio_page_type": "aired",
    "pagenum": 1,
    "pagecount": 5,
})
```

On `ClubClient`, these methods add your login headers, and if the server answers `401 Unauthorized` they refresh the session and retry once. They also accept `headers=` to add or override headers for one request. All of them accept `timeout=` (seconds) to override the client's default of 10.

## Logging

The library is silent by default. To see what it's doing (requests, logins, token refreshes):

```python
from adventuresinodyssey import set_logging_level

set_logging_level("INFO")   # or "DEBUG", "WARNING", "ERROR", "CRITICAL"
```

## Errors

| Exception | When |
| --- | --- |
| `requests.exceptions.HTTPError` | The API returned an error status. A malformed ID gives `400`; an ID that doesn't exist (or that you can't access) usually gives `500`. Async clients raise `httpx.HTTPStatusError` instead. |
| `requests.exceptions.Timeout` | The request took longer than `timeout` seconds (`httpx.TimeoutException` on async clients). |
| `RuntimeError` | `ClubClient` couldn't log in (wrong password, no matching profile, Playwright timed out). |
| `ValueError` | Invalid arguments, e.g. `page_type="full"` on `AIOClient`, or missing email/password. |

```python
import requests
from adventuresinodyssey import AIOClient

client = AIOClient()
try:
    content = client.fetch_content("not-a-real-id")
except requests.exceptions.HTTPError as e:
    print("Request failed:", e.response.status_code, e.response.text)
```
