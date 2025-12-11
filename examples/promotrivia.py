import random
import time
import difflib
import sys

import mpv
from adventuresinodyssey import AIOClient

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    WINDOWS = False

def input_with_timeout(timeout):
    start = time.time()
    buffer = ""

    if WINDOWS:
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwch()

                if char in ("\r", "\n"):
                    print() 
                    return buffer

                if char == "\b":
                    buffer = buffer[:-1]
                    print("\b \b", end="", flush=True)
                    continue

                buffer += char
                print(char, end="", flush=True)

            if time.time() - start > timeout:
                return None

            time.sleep(0.01)

    else:
        import select
        print("", end="", flush=True)
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if r:
            return sys.stdin.readline().strip()
        return None


client = AIOClient()

print("Caching episodes...")
all_episodes = client.cache_episodes()

if not all_episodes:
    print("Error: Failed to cache episodes.")
    exit()


player = mpv.MPV(ytdl=False, video="no")
player.http_header_fields = ["Sec-Fetch-Dest: audio"]


def is_close_enough(guess: str, answer: str, threshold: float = 0.70) -> bool:
    ratio = difflib.SequenceMatcher(None, guess.lower().strip(), answer.lower().strip()).ratio()
    return ratio >= threshold


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
    print("Playing promo...\n")

    player.play(url)
    player.wait_until_playing()

    tries = 3
    round_start = time.time()

    while tries > 0:
        elapsed = time.time() - round_start
        remaining = ROUND_LIMIT - elapsed

        if remaining <= 0:
            print("\nTime's up!")
            print(f"The correct answer was: {title}")
            break

        print("Guess: ", end="", flush=True)

        guess = input_with_timeout(remaining)

        if guess is None:
            print("\nTime's up!")
            print(f"The correct answer was: {title}")
            break

        if is_close_enough(guess, title):
            print("Correct!")
            print(f"Episode Title: {title}")
            score += 1
            break

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


print("\nTime’s up!")
print(f"Final Score: {score} correct in 3 minutes!")
print("Thanks for playing!")