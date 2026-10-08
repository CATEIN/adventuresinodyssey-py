# ClubClient

`ClubClient` is the logged-in client. It needs an Adventures in Odyssey Club account and can do everything [`AIOClient`](aioclient.md) can, plus:

* full-length episodes and videos (`fetch_content()` defaults to the `"full"` page type)
* [playlists and bookmarks](playlists.md)
* [comments](comments.md)
* [badges](groupings.md#badges)
* [saving listening progress](content.md#saving-listening-progress)
* `fetch_random()`, `fetch_profiles()` and other account features

> [!IMPORTANT]
> Login on version `0.2.2` and older no longer works. Make sure you're on the latest version: `pip install -U adventuresinodyssey`

## Setup

Login runs a headless Chromium browser through Playwright, so install it once:

```bash
playwright install chromium
```

## Logging in

```python
import os
from dotenv import load_dotenv
from adventuresinodyssey import ClubClient

load_dotenv()  # reads AIO_EMAIL etc. from a .env file

client = ClubClient(
    email=os.getenv("AIO_EMAIL"),
    password=os.getenv("AIO_PASSWORD"),
    viewer_id=os.getenv("AIO_VIEWER_ID"),  # optional
    pin=os.getenv("AIO_PIN"),              # optional
)

episode = client.fetch_random()  # logs in automatically on the first request
print("Random episode:", episode["short_name"])
```

You don't have to call `login()` yourself. Here's what happens on each request:

1. If the current access token is valid, the request goes ahead.
2. Otherwise the client tries to get a new token with the saved refresh token (fast, no browser).
3. If that fails, it does a full browser login (a few seconds), unless `auto_relogin=False`.
4. If a request comes back `401 Unauthorized`, it repeats steps 1–3 and retries once.

If login fails, the request raises a `RuntimeError` explaining why.

### Constructor options

| Parameter | Default | Description |
| --- | --- | --- |
| `email` | *required* | Account email. |
| `password` | *required* | Account password. |
| `viewer_id` | `None` | ID of the profile to use. Takes priority over `profile_username`. |
| `profile_username` | `None` | Username of the profile to use. |
| `pin` | `None` | The profile's 4-digit PIN, as a string. Only needed if the profile has one. |
| `auto_relogin` | `True` | Allow automatic browser logins. If `False`, the client only uses the saved session and you call `login()` yourself. |
| `config_path` | `"club_session.json"` | Where the session is saved. |
| `timeout` | `10` | Request timeout in seconds. |
| `browser_executable` | `None` | Path to a Chromium/Chrome executable to use instead of Playwright's. |
| `browser_args` | `None` | Extra Chromium command-line arguments, e.g. `["--no-sandbox"]` in Docker. |

## Choosing a profile

A Club account can have several profiles, and comments, playlists, bookmarks, badges and progress all belong to a profile. The client picks one like this:

1. **`viewer_id` given:** use that profile. Fastest and most reliable.
2. **`profile_username` given:** find the profile with that username. If it has a PIN, you must pass `pin` too.
3. **Neither given:** use the first profile *without* a PIN. If every profile has a PIN, login fails.

### Finding your viewer ID

```python
for profile in client.fetch_profiles()["profiles"]:
    print(profile["username"], profile["viewer_id"], "PIN" if profile["hasPIN"] else "")
```

Copy the ID into your `.env` file as `AIO_VIEWER_ID` so the client doesn't have to look it up again.

### Switching profiles

`change_profile(viewer_id, pin=None)` switches to another profile on the same account, without logging in again:

```python
if client.change_profile("a3J...", pin="1234"):   # pin only if that profile has one
    print("Now using", client.profile_username)
```

It returns `False` (and keeps the current profile) if the ID isn't a profile on this account, or if the profile needs a PIN and you didn't pass one. The new profile is saved to the session file, so it's still selected next time.

`change_profile()` doesn't check that the PIN is *correct*. Use `check_pin()` for that.

### Checking a PIN

`check_pin(viewer_id=None, pin=None)` asks the server whether a PIN is correct. With no arguments, it checks the current profile and PIN:

```python
if not client.check_pin():
    print("The PIN in your .env is wrong")

client.check_pin("a3J...", "1234")   # check another profile without switching to it
```

It returns `True` or `False`, and doesn't change the active profile. Login doesn't check the PIN (that would make every login slower), so call this yourself if you want to confirm it, for example when a user types one in.

The server only really checks profiles that have a PIN. For a profile without one, any PIN counts as correct, and so does a viewer ID that doesn't exist.

## Logging out

```python
client.logout()
```

`logout()`:

1. revokes the saved refresh token, so it can't be used again,
2. opens the Club's logout page in the headless browser and waits for it to redirect,
3. forgets the tokens and selected profile, and deletes the session file.

The local state is cleared even if steps 1 or 2 fail (for example, with no internet). It returns `True` if everything succeeded. Your other sessions, like the Club app on your phone, stay logged in.

After `logout()` the client goes back to the profile settings you created it with. If `auto_relogin` is on, the next request logs in again.

## The session file

After a successful login the client writes `club_session.json` (or your `config_path`) containing:

* `email`: which account the session belongs to
* `refresh_token`: lets later runs log in without the browser
* `viewer_id`, `profile_username`: the profile that was selected
* `pin`: that profile's PIN

> [!CAUTION]
> The refresh token gives access to your account. Add `club_session.json` to your `.gitignore` and never share it.

The saved session is loaded when you create a client, as long as it matches what you asked for:

* **Different `email`:** the saved session is ignored and you're logged in fresh.
* **`viewer_id` given:** that profile is used. The saved PIN is only reused for the same profile.
* **`profile_username` given:** the saved profile is reused only if it was selected with the same username. Otherwise the profile is looked up again (no browser login needed).

The refresh token is saved again whenever it's renewed. Use a different `config_path` for each account or bot if you run several at once.

## Manual session control

You usually won't need these:

| Method | Description |
| --- | --- |
| `login()` | Do a full browser login now. Returns `True`, or raises `RuntimeError`. |
| `ensure_authenticated()` | Steps 1–3 above. Returns `True` if the client is ready. |
| `refresh_session()` | Get a new access token from the refresh token. Returns `True`/`False`. |
| `check_session()` | `True` if the current access token is still valid. |
| `logout()` | Log out and clear the session. See [Logging out](#logging-out). |

```python
# Log in up front instead of on the first request
client = ClubClient(email=..., password=..., auto_relogin=False)
if not client.ensure_authenticated():
    client.login()
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Executable doesn't exist` / browser not found | Run `playwright install chromium`. |
| `Failed to login: Playwright timed out` | Check your email and password, and your connection. Try logging in on the website. |
| `Could not find profile with username` | Check the spelling, or use `viewer_id` instead. |
| `requires a PIN, but the default PIN '0000' was used` | Pass `pin=` for that profile. |
| `No profile found that does not require a PIN` | Pass `viewer_id`/`profile_username` and `pin`. |
| Logged into the wrong account or profile | Call `logout()`, or delete `club_session.json`. See [The session file](#the-session-file). |
| Login fails inside Docker or on a server | Try `browser_args=["--no-sandbox"]`. |
