import random
import time
import difflib
import sys
import select

import mpv
from adventuresinodyssey import AIOClient

client = AIOClient()

print("Caching episodes...")
all_episodes = client.cache_episodes()

if not all_episodes:
    print("Error: Failed to cache episodes.")
    exit()

# MPV player
player = mpv.MPV(ytdl=False, video="no")
player.http_header_fields = ["Sec-Fetch-Dest: audio"]

def is_close_enough(guess: str, answer: str, threshold: float = 0.70) -> bool:
    ratio = difflib.SequenceMatcher(None, guess.lower().strip(), answer.lower().strip()).ratio()
    return ratio >= threshold

# Non-blocking input helper
def input_with_timeout(timeout):
    """Wait for input up to 'timeout' seconds."""
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if r:
        return sys.stdin.readline().strip()
    return None

print("\nWelcome to the Adventures in Odyssey Trivia Game!")
print("You have **3 minutes** to guess as many episode titles as possible!\n")

start_time = time.time()
time_limit = 3 * 60 
score = 0
ROUND_LIMIT = 30 

while time.time() - start_time < time_limit:

    while True:
        episode = random.choice(all_episodes)
        fetch_episode = client.fetch_content(episode["id"])

        title = fetch_episode.get("short_name")
        url = fetch_episode.get("download_url")

        if url:
            break
        else:
            print("Episode has no promo audio, skipping...")

    print("\nNew Episode!")
    print("Playing audio...\n")

    player.play(url)
    player.wait_until_playing()

    tries = 3
    round_start = time.time()

    while tries > 0:
        elapsed = time.time() - round_start
        remaining = ROUND_LIMIT - elapsed

        # Time's up for this round
        if remaining <= 0:
            print(f"\nPromo's over!")
            print(f"The correct answer was: {title}")
            break

        print("Guess: ", end="", flush=True)

        guess = input_with_timeout(remaining)

        if guess is None:
            print(f"\nTime's up!")
            print(f"The correct answer was: {title}")
            break

        # User entered a guess
        if is_close_enough(guess, title):
            print("Correct!")
            print(f"Episode Title: {title}")
            score += 1
            break
        else:
            tries -= 1
            if tries > 0:
                print(f"Incorrect! {tries} tries left.")
            else:
                print(f"Out of tries! The correct answer was: {title}")

    print(f"Current Score: {score}")

    try:
        player.stop()
    except:
        pass

print("\nTime's up!")
print(f"Final Score: {score} correct in 3 minutes!")
print("Thanks for playing!")