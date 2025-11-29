# ClubClient

ClubClient is the authenticated client for interacting the Adventures In Odyssey API. Login is necessary for use

Login example:

```python
from adventuresinodyssey import ClubClient

email="example@example.com" # Required
password="example_password" # Required

viewer_id="a3J4W000003HSj6UAG" # Optional. If using a viewer id, profile_username is ignored
profile_username="name_of_a_profile_username" # Optional. Name of a user profile, if not provided will pick the first profile with no pin
pin=1234 # Optional. Use if the profile has a pin enabled


print("Logging in")
# since no viewer_id or profile_username is provided, it will attempt to use the first profile with no pin
client = ClubClient(email=email, password=password) # viewer_id=viewer_id, profile_username=profile_username, pin=pin
loggedIn = client.login()
if loggedIn:
    print(f"✅ Login successful!")
else:
    print("❌ Login failed")
```

