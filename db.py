import mysql.connector
import os

from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def create_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",  # ou o endereço do servidor MySQL
            user="root",       # seu usuário MySQL
            password=os.getenv("DB_PASSWORD")  # sua senha MySQL
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")

def create_database():
    db_name = "anime_db"
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
    for database in databases:
        if database[0] == db_name:
            print(f"Database '{db_name}' exists.")
            cursor.execute(f"USE {db_name}")
            break

    else:
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"Database '{db_name}' created.")
        cursor.execute(f"USE {db_name}")


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS animes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL
        )
        """
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS anime_ids (
            id INT AUTO_INCREMENT PRIMARY KEY,
            anime_id INT,
            anime_html_id VARCHAR(255) NOT NULL,
            FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
        )
        """
    )

    print("DB tables created.")
    conn.commit()
    cursor.close()
    conn.close()

def find_anime_by_id(anime_html_ids):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        for anime_html_id in anime_html_ids:
            cursor.execute("""
                SELECT a.nome 
                FROM anime_ids ai 
                JOIN animes a ON ai.anime_id = a.id 
                WHERE ai.anime_html_id = %s
            """, (anime_html_id,))

            result = cursor.fetchone()
            if result:
                anime_name = result[0]
                print(f"\nFound anime: {anime_name} for ID: {anime_html_id}\n")
                return anime_name
            else:
                return

    except Exception as e:
        print(f"Error searching for IDs in the database: {e}")
    finally:
        cursor.close()
        conn.close()

def find_anime_by_name(anime_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        cursor.execute("SELECT id FROM animes WHERE nome = %s", (anime_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

    except Exception as e:
        print(f"\nError searching for anime name in the database: {e}\n")
        return None

def save_anime(anime_html_ids, anime_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE anime_db")

    try:
        anime_id = find_anime_by_name(anime_name)
        if not anime_id:
            print("Saving new anime:", anime_name)
            cursor.execute("INSERT INTO animes (nome) VALUES (%s)", (anime_name,))
            anime_id = cursor.lastrowid
            print(f"Anime '{anime_name}' saved with ID: {anime_id}")

        print("Saving anime ids...")
        for anime_html_id in anime_html_ids:
            if anime_html_id:
                cursor.execute(
                    "INSERT INTO anime_ids (anime_id, anime_html_id) VALUES (%s, %s)",
                    (anime_id, anime_html_id)
                )

        conn.commit()
        print("Saved successfully!")
        print("Anime:", anime_name, " IDs:", anime_html_ids)

    except Exception as e:
        print(f"Error saving name or IDs to the database: {e}")
    finally:
        cursor.close()
        conn.close()