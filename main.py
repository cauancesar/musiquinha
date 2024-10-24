import db
import amq
import time
import threading
from queue import Queue

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

stop_event = threading.Event()

if __name__ == "__main__":
    driver = None
    threads = []
    try:
        if db.check_database() == False:
            db.create_database()

        user_input = input("Fazer login automaticamente? (Y/N) ")
        if user_input.lower() == "y":
            driver = amq.login()
            amq.enter_game(driver=driver)
            time.sleep(3)
        else:
            driver = amq.get_driver()
    
        payload_queue = Queue()
        t1 = threading.Thread(target=amq.capture_payloads, args=(driver, payload_queue, stop_event))
        t2 = threading.Thread(target=amq.process_next_answer, args=(driver, stop_event))
        threads.append(t1)
        threads.append(t2)

        t1.start()
        t2.start()

        amq.process_payloads(payload_queue, driver, stop_event)
    
    except KeyboardInterrupt:
        print("\nWaiting for threads to finish...")
        stop_event.set()
    finally:
        for thread in threads:
            thread.join()

        print("Stopping bot...")
        time.sleep(5)
        if driver is not None:  # Verifica se driver foi definido
            driver.quit()

        print("Bot stopped.")