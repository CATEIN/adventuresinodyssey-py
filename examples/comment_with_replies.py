import os
import textwrap
import time
from dotenv import load_dotenv
from adventuresinodyssey import ClubClient
load_dotenv()

# Load credentials from .env file
email = os.getenv("AIO_EMAIL")
password = os.getenv("AIO_PASSWORD")
viewer_id = os.getenv("AIO_VIEWER_ID")
comment_page = "a35Up000000Qn9xIAC"

full_message = """I really like this story from A member of the family part 1:
There was this little boy, see?
And for his birthday, his folks gave him the cutest puppy you ever saw.
He loved to run and play.
Couldn't sit still for a minute.
They also gave him a red leather leash for the puppy and told him to be sure and keep the
puppy on the leash whenever he took it out for a walk.
The boy promised he would, so off they went together to the park.
They ran and played and rolled in the grass and drank water out of the fountain.
Oh, they had a wonderful time.
But the boy felt sorry for the puppy because he was on a leash.
Then he began to think about it.
Wouldn't it be better to let him run free, he thought?
Then we wouldn't have to worry about getting tangled up in the leash when we run.
And I won't have to keep tugging him back when he heads in a different direction.
I'll bet that collar hurts his neck.
So the little boy thought himself right out of his promise to his parents.
And he let his new puppy run free.
Oh, did that puppy ever have a good time?
He ran in circles.
He chased his tail.
He chased a squirrel up a tree.
He scouted a flock of pigeons.
And then he ran into the street to chase a delivery truck.
Well, it happened so fast the boy couldn't stop him.
He heard a car honk and a screech of brakes.
And it was all over.
The little puppy, well, he didn't make it."""

# Wrap text into chunks of 255 characters
chunks = textwrap.wrap(full_message, width=255, break_long_words=False, replace_whitespace=False)

print("Logging in...")
client = ClubClient(email=email, password=password, viewer_id=viewer_id)

if chunks:
    # 1. Post the first chunk to establish the thread
    print("Posting initial comment...")
    parent_post = client.post_comment(message=chunks[0], related_id=comment_page)
    
    try:
        # Extract the ID immediately from the response
        parent_id = parent_post['comments'][0]['id']
        print(f"Initial comment posted! Parent ID: {parent_id}")

        # 2. Post all subsequent chunks as replies immediately
        for i, chunk in enumerate(chunks[1:], 1):
            time.sleep(1)
            
            print(f"Posting part {i+1} as a reply...")
            client.post_reply(message=chunk, related_id=parent_id)
            
        print("\nDone! The entire story has been threaded.")
        
    except (KeyError, IndexError) as e:
        print(f"Error: Could not retrieve the parent ID from the response. {e}")