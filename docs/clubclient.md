# ClubClient

ClubClient is the authenticated client for interacting the Adventures In Odyssey API. Login is necessary for use

Login example:

```python
from adventuresinodyssey import ClubClient

email="example@example.com" # Required
password="ExamplePassword" # Required

viewer_id="a3J..." # Optional. If using a viewer id, profile_username is ignored
profile_username="profile_username" # Optional. Name of a user profile, if not provided will pick the first profile with no pin
pin="1234" # Optional. Use if the profile has a pin enabled


print("Logging in")
# since no viewer_id or profile_username is provided, it will attempt to use the first profile with no pin
client = ClubClient(email=email, password=password, auto_relogin=True) # viewer_id=viewer_id, profile_username=profile_username, pin=pin
loggedInWithEpisode = client.fetch_random()
if loggedInWithEpisode:
    print(f"✅ Login successful!")
    print("Random Episode: " + loggedInWithEpisode["long_name"])
else:
    print("❌ Login failed")
```

`login()` doesnt need to be called since `ClubClient` automatically logs in if no session was cached. It also refreshes the session (or logs in again) on `401` response codes. If login fails an error will be thrown.
 This behavior can be changed by setting `auto_relogin=False`
 

 ```python
client = ClubClient(email=email, password=password, auto_relogin=False)
try:
    loggedIn = client.login()
except Exception as e:
    print("❌ Login failed")
    print("Error:", e)
else:
    if loggedIn:
        print("✅ Login successful!")
    else:
        print("❌ Login failed")
```
