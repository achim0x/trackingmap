""" Database handler for a sqlite database

This module manages a sqlite database for storing tracker information
"""

import sqlite3
import os
from datetime import datetime

# --- Configuration ---
DB_PATH = "tracker_data.db"

# --- Tracker info structure (for reference) ---
tracker_info = {
    "tracker_id": "",
    "longitude": 0.0,
    "latitude": 0.0,
    "battery": 0,
    "timestamp": "",
    "gw-rssi": -70,
    "gw-name": "",
    "gw-longitude": 0.0,
    "gw-latitude": 0.0
}


def init_db(db_path=DB_PATH):
    """
    Initialize the SQLite database.

    If the database file does not exist, it creates a new one and
    defines the schema for the 'tracker_data' table.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        sqlite3.Connection: SQLite connection object or None on failure.
    """
    try:
        db_exists = os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not db_exists:
            # Create data table if the DB is new
            cursor.execute("""
                CREATE TABLE tracker_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracker_id TEXT,
                    longitude REAL,
                    latitude REAL,
                    battery INTEGER,
                    timestamp DATETIME,
                    gw_rssi INTEGER,
                    gw_name TEXT,
                    gw_longitude REAL,
                    gw_latitude REAL
                )
            """)
            conn.commit()

            # Create config table if the DB is new
            cursor.execute("""
                CREATE TABLE tracker_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracker_id TEXT,
                    tracker_name TEXT,
                    tracker_symbol TEXT,
                    tracker_symbol_color TEXT,
                    tracker_waypoint_max INTEGER,
                    tracker_waypoint_timeout INTEGER,
                    tracker_waypoint_color TEXT
                )
            """)
            conn.commit()

        return conn  # Return connection for reuse
    except sqlite3.Error as e:
        print(f"SQLite error during init: {e}")
        return None


def insert_tracker_info(conn, data):
    """
    Insert a row of tracker data into the 'tracker_data' table.

    Args:
        conn (sqlite3.Connection): An active SQLite connection.
        data (dict): A dictionary containing tracker info with keys:
            'tracker_id', 'latitude', 'longitude', 'battery',
            'timestamp', 'gw-rssi', 'gw-name', 'gw-latitude', 'gw-longitude'
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tracker_data (
                tracker_id, latitude, longitude, battery, timestamp,
                gw_rssi, gw_name, gw_latitude, gw_longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["tracker_id"],
            data["latitude"],
            data["longitude"],
            data["battery"],
            data["timestamp"],
            data["gw-rssi"],
            data["gw-name"],
            data["gw-latitude"],
            data["gw-longitude"]
        ))
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error during insert: {e}")
