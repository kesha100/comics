import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse
load_dotenv()
from stability_ai import text_to_image 
from add_text import add_text_to_panel

DATABASE_URL = os.getenv('DATABASE_URL')
result = urlparse(DATABASE_URL)
DB_HOST = result.hostname
DB_NAME = result.path.lstrip('/')
DB_USER = result.username
DB_PASSWORD = result.password

def connect_to_database():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


def save_panel_to_db(text, image_url):
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO "Panel" (text, image_url) VALUES (%s, %s)',
            (text if text else '', image_url)
        )
        connection.commit()
    except Exception as e:
        print(f"Error saving panel to database: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()