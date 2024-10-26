import mysql.connector
import os

from typing import Optional
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def create_connection() -> Optional[mysql.connector.connection.MySQLConnection]:
    """Establishes a connection to the MySQL database."""
    try:
         # Attempt to connect to the MySQL server with the provided credentials
        conn = mysql.connector.connect(
            host="localhost", # The host where the MySQL server is located (usually 'localhost')
            user="root",      # The MySQL username (default is often 'root')
            password=os.getenv("DB_PASSWORD") # Retrieves the MySQL password from environment variables
        )
        # Check if the connection was successful
        if conn.is_connected():
            return conn # Return the connection object if successful
    except Error as e:
        print(f"Error connecting to MySQL: {e}")

def create_database() -> None:
    """Creates a database and tables for storing anime information."""

    db_name = "anime_db" # Define the name of the database to be created
    conn = create_connection()
    cursor = conn.cursor() # Create a cursor object to interact with the database

    try:
        # Execute a query to show all existing databases
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall() # Fetch all the results of the executed query

        # Check if the specified database already exists
        for database in databases:
            if database[0] == db_name:
                print(f"Database '{db_name}' exists.")
                cursor.execute(f"USE {db_name}") # Select the existing database for use
                break

        else: # If the loop completes without finding the database
            cursor.execute(f"CREATE DATABASE {db_name}") # Create the database
            print(f"Database '{db_name}' created.")
            cursor.execute(f"USE {db_name}") # Select the newly created database for use

        # Create a table for storing anime names if it does not already exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS animes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(255) NOT NULL UNIQUE
            )
            """
            )
        # Create a table for storing anime IDs with a foreign key reference to the animes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS anime_ids (
                id INT AUTO_INCREMENT PRIMARY KEY,
                anime_id INT,
                anime_html_id VARCHAR(255) NOT NULL UNIQUE,
                FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
            )
            """
        )

        print("DB tables created or alredy exists.")
        conn.commit() # Commit the changes to the database
    except Exception as e:
        print(f"Error creating database or tables: {e}")

    finally:
        cursor.close() # Close the cursor
        conn.close() # Close the database connection

def find_anime_by_id(
    anime_html_id: str
) -> Optional[str]:
    """Finds an anime name based on its HTML IDs."""

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        # Execute a query to find the anime name associated with the given HTML ID
        cursor.execute("""
            SELECT a.nome 
            FROM anime_ids ai 
            JOIN animes a ON ai.anime_id = a.id 
            WHERE ai.anime_html_id = %s
        """, (anime_html_id,))

        result = cursor.fetchone() # Fetch the first matching result
        if result: # If a result is found
            anime_name = result[0]
            print(f"\nFound anime: {anime_name} for ID: {anime_html_id}\n")
            return anime_name # Return the found anime name
        else:
            return # Return None if no result is found

    except Exception as e:
        print(f"Error searching for IDs in the database: {e}")
    finally:
        cursor.close() # Close the cursor
        conn.close() # Close the database connection

def find_anime_by_name(
    anime_name: str
) -> Optional[int]:
    """Finds an anime ID based on its name."""

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        # Execute a query to find the ID of the anime by its name
        cursor.execute("SELECT id FROM animes WHERE nome = %s", (anime_name,))
        result = cursor.fetchone() # Fetch the first matching result
        if result: # If a result is found return the anime ID
            return result[0]
        else:
            return None # Return None if no result is found

    except Exception as e:
        print(f"\nError searching for anime name in the database: {e}\n")
        return None

def save_anime(
    anime_html_id: str, 
    anime_name: str
) -> None:
    """Saves an anime name and its associated HTML IDs in the database."""

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        # Find the anime ID based on the provided anime name
        anime_id = find_anime_by_name(anime_name)
        if not anime_id: # If the anime does not exist in the database
            print("Saving new anime:", anime_name)
            cursor.execute("INSERT INTO animes (nome) VALUES (%s)", (anime_name,)) # Insert the new anime into the database
            anime_id = cursor.lastrowid
            print(f"Anime '{anime_name}' saved with ID: {anime_id}")

        print("Saving anime ids...")
        if anime_html_id: # Check if the HTML ID is not empty
            cursor.execute(
                "INSERT INTO anime_ids (anime_id, anime_html_id) VALUES (%s, %s)",
                (anime_id, anime_html_id)
            ) # Insert the anime ID and HTML ID

        conn.commit()
        print("Saved successfully!")
        print("Anime:", anime_name, " IDs:", anime_html_id)

    except Exception as e:
        print(f"Error saving name or IDs to the database: {e}")
    finally:
        cursor.close()
        conn.close()