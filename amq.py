import getpass
import json
import os
import time
import db
import threading
import queue
import random

from typing import Union
from queue import Queue
from threading import Event

from dotenv import load_dotenv
from queue import Queue
from collections import deque

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# Load environment variables from .env file
load_dotenv('.env')

chrome_options = Options()
chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

URL = "https://animemusicquiz.com/"  # url of the website
USER = os.getenv("LOGIN")
PASS = os.getenv("PASSWORD")
VERBOSE = True  # Verbose mode for debugging
HEADLESS, MUTED = False, False  # Configurations for headless or muted operation
    
index_dict = 0 # Counter for tracking order
answer_index = 0 # Index of current answer
is_busy = False # Flag to control answer processing
answered = False # Flag to indicate if answer has been processed
anime_order = {} # Order mapping of anime for processing
pending_answers = queue.Queue() # Queue for pending answers

# Prompt for credentials if not found in environment variables
if not USER or not PASS:
    USER, PASS = input("Username: "), getpass.getpass()

def get_driver() -> webdriver.Chrome:
    """Returns a Chrome driver with the specified options."""
    
    if HEADLESS:
        chrome_options.add_argument("--headless")
    if MUTED:
        chrome_options.add_argument("--mute-audio")
    
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(URL) # Navigate to the target URL
    return driver

def login() -> webdriver.Chrome:
    """Logs in and returns a webdriver object."""
    if HEADLESS:
        chrome_options.add_argument("--headless")
    if MUTED:
        chrome_options.add_argument("--mute-audio")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Access the login page
        driver.get(URL)
        print("Logging in...")

        # Enter login credentials and submit
        driver.find_element(By.ID, "loginUsername").send_keys(USER)
        driver.find_element(By.ID, "loginPassword").send_keys(PASS)
        driver.find_element(By.ID, "loginButton").click()
        time.sleep(3)

        # Press continue pop-up if exists
        btn = driver.find_elements(By.XPATH, "//button[text()='Continue']")
        if len(btn) > 0:
            btn[0].click()
            print("Continuing...")

        time.sleep(10)
        return driver

    except (NoSuchElementException, TimeoutException):
        print("\nError during login. Proceed manually.")
        return driver
    except Exception:
        return driver

def enter_game(
    driver: webdriver.Chrome
) -> None:
    """Enters a game from the home page."""
    try:
        # Attempt to rejoin an existing game if button is available
        rejoin_button = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.XPATH, "//button[text()='Rejoin']"))
        )
        if rejoin_button:
            print("Joining an existing game...")
            driver.find_element(By.XPATH, "//button[text()='Rejoin']").click()
            time.sleep(5)

    except TimeoutException:
        print("Creating a new game...")

        try:
            # Create a new game and configure settings if no game exists
            driver.find_element(By.ID, "mpPlayButton").click()
            time.sleep(3)
            driver.find_element(By.ID, "gmsSinglePlayer").click()

            time.sleep(3)
            actions = ActionChains(driver)

            # Adjust slider for the number of songs to 100
            sliderNumberSongs = driver.find_element(By.ID, "mhNumberOfSongsSlider")
            actions.click_and_hold(sliderNumberSongs).move_by_offset(150, 0).release().perform()

            # Adjust song selection slider to Random
            sliderSongSelection = driver.find_element(By.ID, "mhSongPoolSlider")
            actions.click_and_hold(sliderSongSelection).move_by_offset(-100, 0).release().perform()

            # Configure specific game options
            #driver.find_element(By.CSS_SELECTOR, "label[for='mhSongTypeInsert']").click()
            #driver.find_element(By.CSS_SELECTOR, "label[for='mhSongDiffHard']").click()

            # Host and start the game
            driver.find_element(By.ID, "mhHostButton").click()
            time.sleep(1)
            driver.find_element(By.ID, "lbStartButton").click()

        except Exception as e:
            print("Error creating a new game. Proceed manually.")
    
    except Exception:
        print("Error joining or creating a game. Proceed manually.")

def process_payload(
    payload: Union[dict, list]
) -> Union[dict, list]:
    """Processes the payload to extract JSON data."""
    if payload.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
        if '[' in payload:
            index = payload.index('[')
            return json.loads(payload[index:])
    else:
        return json.loads(payload)

def capture_payloads(
    driver: webdriver.Chrome, 
    payload_queue: Queue, 
    stop_event: Event
) -> None:
    """Continuously captures payloads and adds them to a queue."""
    while not stop_event.is_set():
        try:
            # Capture logs from the 'performance' log category
            logs = driver.get_log('performance')
            for log in logs:
                log_data = json.loads(log["message"])

                # Check if a WebSocket frame was received
                if log_data.get("message", {}).get("method") == "Network.webSocketFrameReceived":
                    payload = log_data["message"]["params"]["response"]["payloadData"]
                    payload_json = process_payload(payload)

                    # Check if it's a relevant command and add to queue
                    if isinstance(payload_json, list) and payload_json[0] == "command":
                        command_data = payload_json[1]
                        relevant_commands = ["quiz next video info", "answer results"]

                        if command_data["command"] in relevant_commands:
                            payload_queue.put(command_data)

            time.sleep(0.1)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            time.sleep(0.1)

        except Exception as e:
            print(f"Error capturing logs: {e}")
            time.sleep(0.1)

def process_payloads(
    payload_queue: Queue, 
    driver: webdriver.Chrome, 
    stop_event: Event
) -> None:
    """Processes the payloads in the queue."""
    global index_dict, is_busy, answer_index, answered, anime_order
    
    while not stop_event.is_set():
        try:
            # Check if the start button is clickable to restart game
            if is_start_button_clickable(driver):
                print("Restarting game...")

            # Process next command if available
            if not payload_queue.empty():
                command_data = payload_queue.get(timeout=1)

                if command_data["command"] == "quiz next video info":
                    process_quiz_next_video_info(command_data, driver)
                    
                elif command_data["command"] == "answer results":
                    if not answered:
                        process_answer_results(command_data, anime_order)
                    
                    answered = False
                    answer_index += 1

        except queue.Empty:
            continue
        except Exception as e:
            if "Unread result found" in str(e):
                print(f"Warning: {e}, skipping...")
                del anime_order[answer_index]
                index_dict += 1
                answered = False
                answer_index += 1
                continue

            print(f"Error processing payloads: {e}")

def process_quiz_next_video_info(
    command_data: Union[dict, list], 
    driver: webdriver.Chrome
) -> None:
    """Processes the 'quiz next video info' command data."""
    global index_dict, is_busy, answer_index, answered, anime_order

    try:
        # Extract anime video information and update order
        video_info = command_data["data"]["videoInfo"]["videoMap"]["catbox"]
        anime_html_id = video_info.get("0")
        anime_order[index_dict] = anime_html_id

        # Look up and answer if anime is identified
        if answer_index in anime_order:
            anime_name = db.find_anime_by_id(anime_order[answer_index])

            if anime_name:
                answered = True
                del anime_order[answer_index]
                if not is_busy:
                    is_busy = True
                    answer(driver, anime_name)
                else:
                    pending_answers.put(anime_name)

        index_dict += 1
        
    except Exception as e:
        print(f"Error processing 'quiz next video info': {e}")

def process_answer_results(
    command_data: Union[dict, list], 
    anime_order: dict
) -> None:
    """Processes the 'answer results' command."""
    try:
        # Extract song and anime details from answer results
        song_info = command_data['data']['songInfo']
        catbox = song_info['videoTargetMap']['catbox']
        anime_names = song_info['animeNames']
        anime_name_english = anime_names.get('english')

        print("\nAnime not found yet.")

        # Update database with correct anime details
        for idx, anime_html_id in anime_order.items():
            if catbox.get("0") == anime_html_id:
                db.save_anime(anime_html_id, anime_name_english)
                del anime_order[idx]
                break

    except Exception as e:
        print(f"Error processing 'answer results': {e}")

def process_next_answer(
    driver: webdriver.Chrome, 
    stop_event: Event
) -> None:
    """Processes the next answer in the queue, if available."""
    global is_busy
    while not stop_event.is_set():
        try:
            # Process next answer from pending queue if not busy
            if not pending_answers.empty() and not is_busy:
                next_answer = pending_answers.get()
                is_busy = True
                answer(driver, next_answer)
        except Exception as e:
            print(f"An error occurred while processing the answer: {e}")
            is_busy = False

def answer(
    driver: webdriver.Chrome, 
    ans: str
) -> None:
    """Gives an answer."""
    global is_busy
    try:
        # Locate the answer input box and submit the answer
        box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "qpAnswerInput"))
        )
        time.sleep(random.uniform(1, 9))
        box.send_keys(ans)
        box.send_keys(Keys.RETURN)
    
    except (TimeoutException, ElementNotInteractableException):
        print(f"Timeout or element not found: {e}. Retrying...")
        time.sleep(0.5)
        answer(driver, ans)

    except Exception as e:
        print(f"Error during answering: {e}")

    finally:
        is_busy = False

def is_start_button_clickable(
    driver: webdriver.Chrome
) -> bool:
    """Checks if the 'lbStartButton' is clickable and tries to click it."""
    global index_dict, is_busy, answer_index, answered, anime_order
    try:
        # Locate the start button and click if enabled
        button = driver.find_element(By.ID, "lbStartButton")

        if button.is_displayed() and button.is_enabled():
            reset_game_state()
            button.click()
            return True
        else:
            return False

    except (NoSuchElementException, TimeoutException):
        return False
    except Exception as e:
        return False
    
def reset_game_state() -> None:
    global index_dict, answer_index, is_busy, answered, anime_order, pending_answers
    index_dict = 0
    answer_index = 0
    is_busy = False
    answered = False
    anime_order.clear()
    while not pending_answers.empty(): # Clear pending answers queue
        pending_answers.get()