# AIOClient

AIOClient is the non-authenticated client for interacting the Adventures In Odyssey API.

Example:
```python
from adventuresinodyssey import AIOClient

client = AIOClient()

res = client.fetch_content(content_id="a354W0000046UqfQAE")
print(res["short_name"])
```
