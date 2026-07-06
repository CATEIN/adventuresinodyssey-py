# ClubClient

> [!IMPORTANT]  
> Login on version `0.2.2` or older does not work on `ClubClient` . Ensure you are on the latest version.

ClubClient is the authenticated client for interacting the Adventures In Odyssey API. Login is necessary for use

Login example:

```python
from adventuresinodyssey import ClubClient

email="example@example.com" # Required
password="example_password" # Required

viewer_id="a3J..." # Optional. If using a viewer id, profile_username is ignored
profile_username="profile_username" # Optional. Name of a user profile, if not provided will pick the first profile with no pin
pin="1234" # Optional. Use if the profile has a pin enabled

# since no viewer_id or profile_username is provided, it will attempt to use the first profile with no pin
client = ClubClient(email=email, password=password, auto_relogin=True) # viewer_id=viewer_id, profile_username=profile_username, pin=pin
random_episode = ""
print("Logging In...")

try:
    random_episode = client.fetch_random()
except Exception as e:
    print(f"Login failed {e}")
    exit()
print("Logged In!")
print("Random episode: " + random_episode["short_name"])
```

`login()` doesnt need to be called since `ClubClient` automatically logs in if no session was cached. It also refreshes the session on `401` response codes.
 Full playwright login can be disabled by setting `auto_relogin=False`

 Upon successful login, ClubClient creates a json file and stores the `refresh_token`, `viewer_id` and `pin`.
