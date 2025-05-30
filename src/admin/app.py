"""Web Application to edit tracker config"""
import logging
import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

db_path = '../../tracker_data.db'


def get_db_connection():
    """Establish a connection to the SQLite database."""
    if not os.path.exists(db_path):
        error_msg = f"Database file '{db_path}' does not exist."
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Render the main HTML interface for managing tracker configuration."""
    return render_template_string('''<html><body><h2>Welcome</h2><ul>
        <li><a href="/config">Tracker Config Editor</a></li>
        <li><a href="/data">Tracker Data Viewer</a></li>
    </ul></body></html>''')


@app.route('/config')
def config():
    """Render the configuration page."""
    return render_template_string(open('templates/config.html').read())


@app.route('/data')
def data():
    """Render the data viewer page."""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            'SELECT * FROM tracker_data ORDER BY timestamp DESC LIMIT 100').fetchall()
        conn.close()
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Tracker Data</title>
            <style>
                table, th, td { border: 1px solid black; border-collapse: collapse; padding: 8px; }
            </style>
        </head>
        <body>
            <h2>Recent Tracker Data</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Tracker ID</th>
                        <th>Longitude</th>
                        <th>Latitude</th>
                        <th>Battery</th>
                        <th>Timestamp</th>
                        <th>GW RSSI</th>
                        <th>GW Name</th>
                        <th>GW Longitude</th>
                        <th>GW Latitude</th>
                    </tr>
                </thead>
                <tbody>
                {% for row in rows %}
                    <tr>
                        <td>{{ row['id'] }}</td>
                        <td>{{ row['tracker_id'] }}</td>
                        <td>{{ row['longitude'] }}</td>
                        <td>{{ row['latitude'] }}</td>
                        <td>{{ row['battery'] }}</td>
                        <td>{{ row['timestamp'] }}</td>
                        <td>{{ row['gw_rssi'] }}</td>
                        <td>{{ row['gw_name'] }}</td>
                        <td>{{ row['gw_longitude'] }}</td>
                        <td>{{ row['gw_latitude'] }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </body>
        </html>
        ''', rows=rows)
    except Exception as e:
        logging.error("Error fetching tracker data: %s", e)
        return f"<p>Error loading data: {str(e)}</p>"

# Existing API routes for tracker_config


@app.route('/api/trackers', methods=['GET'])
def get_trackers():
    """Return all tracker configurations as a JSON list."""
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM tracker_config').fetchall()
        conn.close()
        logging.info("Fetched all tracker configurations.")
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        logging.error("Error fetching tracker configurations: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trackers', methods=['POST'])
def add_tracker():
    """Add a new tracker configuration to the database."""
    try:
        data = request.get_json()
        conn = get_db_connection()
        conn.execute('''INSERT INTO tracker_config (tracker_id, tracker_name, tracker_symbol, tracker_symbol_color,
                        tracker_waypoint_max, tracker_waypoint_timeout, tracker_waypoint_color)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (data['tracker_id'], data['tracker_name'], data['tracker_symbol'],
                      data['tracker_symbol_color'], data['tracker_waypoint_max'],
                      data['tracker_waypoint_timeout'], data['tracker_waypoint_color']))
        conn.commit()
        conn.close()
        logging.info("Added new tracker configuration: %s", data)
        return '', 201
    except Exception as e:
        logging.error("Error adding tracker configuration: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trackers/<int:id>', methods=['PUT'])
def update_tracker(id):
    """Update an existing tracker configuration by ID."""
    try:
        data = request.get_json()
        conn = get_db_connection()
        conn.execute('''UPDATE tracker_config SET tracker_id = ?, tracker_name = ?, tracker_symbol = ?,
                        tracker_symbol_color = ?, tracker_waypoint_max = ?, tracker_waypoint_timeout = ?,
                        tracker_waypoint_color = ? WHERE id = ?''',
                     (data['tracker_id'], data['tracker_name'], data['tracker_symbol'],
                      data['tracker_symbol_color'], data['tracker_waypoint_max'],
                      data['tracker_waypoint_timeout'], data['tracker_waypoint_color'], id))
        conn.commit()
        conn.close()
        logging.info(
            "Updated tracker configuration ID %s with data: %s", id, data)
        return '', 204
    except Exception as e:
        logging.error("Error updating tracker ID %s: %s", id, e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trackers/<int:id>', methods=['DELETE'])
def delete_tracker(id):
    """Delete a tracker configuration by ID."""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM tracker_config WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        logging.info("Deleted tracker configuration ID %s", id)
        return '', 204
    except Exception as e:
        logging.error("Error deleting tracker ID %s: %s", id, e)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
