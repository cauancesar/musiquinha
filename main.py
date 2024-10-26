import db
import amq
import time
import threading
from queue import Queue

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

stop_event = threading.Event() # Event to signal threads to stop

if __name__ == "__main__":
    driver = None
    threads = [] # List to keep track of threads

    try:
        db.create_database() # Create the database

        user_input = input("Would you like to login automatically? (Y/N) ")
        if user_input.lower() == "y":
            driver = amq.login() # Login automatically
            amq.enter_game(driver=driver) # Create and enter the game
            time.sleep(3) # Wait for the game to load
        else:
            driver = amq.get_driver() # Get a new web driver instance
    
        payload_queue = Queue() # Queue for storing payloads
        t1 = threading.Thread(target=amq.capture_payloads, args=(driver, payload_queue, stop_event))
        t2 = threading.Thread(target=amq.process_next_answer, args=(driver, stop_event))
        threads.append(t1) # Add thread for capturing payloads
        threads.append(t2) # Add thread for processing answers

        # Start the threads
        t1.start()
        t2.start()

        amq.process_payloads(payload_queue, driver, stop_event) # Process payloads from the queue
    
    except KeyboardInterrupt:
        print("\nWaiting for threads to finish...")
        stop_event.set() # Signal threads to stop
    finally:
        for thread in threads:
            thread.join() # Wait for all threads to finish

        print("Stopping bot...")
        if driver is not None:
            driver.quit() # Close the web driver

        print("Bot stopped.")