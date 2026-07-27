import pandas as pd
import sqlite3
import os

CSV_FILE = "Open_source_db2.csv"
DB_FILE = "projects_v2.db"

def import_chemicals():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found")
        return

    try:
        # Read CSV
        df = pd.read_csv(CSV_FILE)
        if 'Name' not in df.columns:
            print("Error: Column 'Name' not found in CSV")
            return

        # Extract unique chemical names
        chemicals = df['Name'].dropna().unique().tolist()
        print(f"Extracted {len(chemicals)} unique chemicals.")

        # Connect to SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create chemicals table if it doesn't exist
        cursor.execute("CREATE TABLE IF NOT EXISTS chemicals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
        
        # Insert chemicals
        inserted_count = 0
        for chem in chemicals:
            try:
                cursor.execute("INSERT INTO chemicals (name) VALUES (?)", (chem,))
                inserted_count += 1
            except sqlite3.IntegrityError:
                # Already exists, skip
                pass

        conn.commit()
        conn.close()
        print(f"Successfully imported {inserted_count} new chemicals into {DB_FILE}.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import_chemicals()
