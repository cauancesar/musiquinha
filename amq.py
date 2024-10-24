import getpass
import json
import os
import time
import db
import threading
import queue

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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Load environment variables from .env file
load_dotenv('.env')

chrome_options = Options()
chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

URL = "https://animemusicquiz.com/"  # url of the website
USER = os.getenv("LOGIN")
PASS = os.getenv("PASSWORD")
VERBOSE = True  # whether to be verbose or not
HEADLESS, MUTED = False, False  # whether to run headless or muted
    
index_dict = 0
is_busy = False
pending_answers = queue.Queue()

if not USER or not PASS:
    # Prompt for information if environment variables are not set
    USER, PASS = input("Username: "), getpass.getpass()


def find_by_text(driver: webdriver.Chrome, text: str):
    """Finds an element by text."""
    return driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")

def get_driver() -> webdriver.Chrome:
    """Returns a Chrome driver with the specified options."""
    
    if HEADLESS:
        chrome_options.add_argument("--headless")
    if MUTED:
        chrome_options.add_argument("--mute-audio")
    
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(URL)
    return driver


def login() -> webdriver.Chrome:
    """Logs in and returns a webdriver object."""
    if HEADLESS:
        chrome_options.add_argument("--headless")
    if MUTED:
        chrome_options.add_argument("--mute-audio")
    
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(URL)
    print("Logging in...")
    driver.find_element(By.ID, "loginUsername").send_keys(USER)
    driver.find_element(By.ID, "loginPassword").send_keys(PASS)
    driver.find_element(By.ID, "loginButton").click()
    time.sleep(3)

    btn = driver.find_elements(By.XPATH, "//button[text()='Continue']")
    if len(btn) > 0:
        btn[0].click()
        print("Continuing...")

    time.sleep(10)
    return driver

def enter_game(
    driver: webdriver.Chrome
) -> None:
    """Enters a game from the home page."""
    try:
        rejoin_button = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.XPATH, "//button[text()='Rejoin']"))
        )
        if rejoin_button:
            print("Joining an existing game...")
            driver.find_element(By.XPATH, "//button[text()='Rejoin']").click()
            time.sleep(5)

    except TimeoutException:
        print("Creating a new game...")
        driver.find_element(By.ID, "mpPlayButton").click()
        time.sleep(3)
        driver.find_element(By.ID, "gmsSinglePlayer").click()

        time.sleep(3)
        actions = ActionChains(driver)

        sliderNumberSongs = driver.find_element(By.ID, "mhNumberOfSongsSlider")
        actions.click_and_hold(sliderNumberSongs).move_by_offset(150, 0).release().perform()


        sliderSongSelection = driver.find_element(By.ID, "mhSongPoolSlider")
        actions.click_and_hold(sliderSongSelection).move_by_offset(-100, 0).release().perform()


        driver.find_element(By.CSS_SELECTOR, "label[for='mhSongTypeInsert']").click()
        driver.find_element(By.CSS_SELECTOR, "label[for='mhSongDiffHard']").click()


        driver.find_element(By.ID, "mhHostButton").click()

        time.sleep(1)
        driver.find_element(By.ID, "lbStartButton").click()

def process_payload(payload):
    """Processes the payload to extract JSON data."""
    # Remover o prefixo numérico, se presente
    if payload.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
        if '[' in payload:
        # Encontrar o primeiro '[' e cortar a string até esse ponto
            index = payload.index('[')
            return json.loads(payload[index:])
    else:
        return json.loads(payload)


def capture_payloads(driver, payload_queue, stop_event):
    """Captura payloads de forma contínua e os adiciona a uma fila."""
    while not stop_event.is_set():
        try:
            logs = driver.get_log('performance')
            for log in logs:
                log_data = json.loads(log["message"])
                if log_data.get("message", {}).get("method") == "Network.webSocketFrameReceived":
                    payload = log_data["message"]["params"]["response"]["payloadData"]
                    payload_queue.put(payload)  # Adiciona o payload diretamente à fila
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error capturing logs: {e}")

def process_payloads(payload_queue, driver, stop_event):
    """Processes the payloads in the queue."""
    anime_dict = {}
    global index_dict, is_busy
    id_order = {}
    while not stop_event.is_set():
        try:
            if is_start_button_clickable(driver):
                print("Restarting game...")

            payload = payload_queue.get(timeout=1)
            payload_json = process_payload(payload)
            if isinstance(payload_json, list) and payload_json[0] == "command":
                command_data = payload_json[1]

                if command_data["command"] == "quiz next video info":
                    video_info = command_data["data"]["videoInfo"]["videoMap"]["catbox"]
                    anime_html_ids = [video_info.get("0"), video_info.get("720"), video_info.get("480")]
                    id_order[index_dict] = anime_html_ids

                    first_index = next(iter(id_order))
                    first_anime_ids = id_order[first_index]

                    anime_name = db.find_anime_by_id(first_anime_ids)

                    if anime_name:
                        time.sleep(4)
                        del id_order[first_index]

                        if not is_busy:
                            is_busy = True
                            answer(driver, anime_name)
                        else:
                            pending_answers.put(anime_name)

                    else:
                        print("Anime not found yet.")
                        index_dict += 1
                    
                elif command_data["command"] == "answer results":
                    process_answer_results(command_data, id_order)
                    
        except queue.Empty:
            continue

def process_answer_results(command_data, id_order):
    """Processes the 'answer results' command."""
    try:
        song_info = command_data['data']['songInfo']
        catbox = song_info['videoTargetMap']['catbox']
        anime_names = song_info['animeNames']
        anime_name_english = anime_names.get('english')

        for idx, ids in id_order.items():
            if (catbox.get("0") in ids or 
                catbox.get("720") in ids or 
                catbox.get("480") in ids):

                db.save_anime(ids, anime_name_english)
                del id_order[idx]
                break

    except Exception as e:
        print(f"Error processing 'answer results': {e}")

def monitor_network(driver: webdriver.Chrome):
    """Monitors network requests and captures anime opening requests."""
    payload_queue = Queue()
    threading.Thread(target=capture_payloads, args=(driver, payload_queue)).start()
    threading.Thread(target=process_next_answer, args=(driver,)).start()
    process_payloads(payload_queue, driver)
    print("teste")


def process_next_answer(driver, stop_event):
    """Processes the next answer in the queue, if available."""
    global is_busy
    while not stop_event.is_set():
        try:
            if not pending_answers.empty() and not is_busy:
                next_answer = pending_answers.get()
                is_busy = True
                answer(driver, next_answer)
        except Exception as e:
            print(f"An error occurred while processing the answer: {e}")
            is_busy = False  # Reset the busy state in case of an error

def answer(driver: webdriver.Chrome, ans: str) -> None:
    """Gives an answer."""
    global is_busy
    try:
        box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "qpAnswerInput"))
        )
        box.send_keys(ans)
        box.send_keys(Keys.RETURN)

        time.sleep(15)
    
    except TimeoutException:
        print("Timeout: the element did not become interactable in time.")
    
    except ElementNotInteractableException:
        print("Error: element found, but not interactable at the moment.")

    finally:
        is_busy = False

def is_start_button_clickable(driver):
    """Checks if the 'lbStartButton' is clickable and tries to click it."""
    try:
        # Espera até que o botão esteja presente, visível e clicável
        button = driver.find_element(By.ID, "lbStartButton")

        if button.is_displayed() and button.is_enabled():
            button.click()  # Clica no botão
            return True  # Retorna True se o botão foi clicado com sucesso
        else:
            return False

    except NoSuchElementException:
        return False
    except TimeoutException:
        return False
    except Exception as e:
        return False