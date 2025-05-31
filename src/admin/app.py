"""Tracker Management Web Application """

import logging
import os
import sqlite3
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, Response


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
    """Render the main HTML interface for navigation."""
    return render_template_string('''<html><body><h2>Welcome</h2><ul>
        <li><a href="/config">Tracker Config Editor</a></li>
        <li><a href="/data">Tracker Data Viewer</a></li>
    </ul></body></html>''')


@app.route('/data')
def data():
    """Render the data viewer page with filters and pagination."""
    try:
        tracker_id = request.args.get('tracker_id', '')
        age_hours = request.args.get('age_hours', '')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        query = 'SELECT * FROM tracker_data'
        filters = []
        params = []

        if tracker_id:
            filters.append('tracker_id = ?')
            params.append(tracker_id)

        if age_hours:
            try:
                age_dt = datetime.utcnow() - timedelta(hours=int(age_hours))
                filters.append('timestamp >= ?')
                params.append(age_dt.isoformat(sep=' '))
            except ValueError:
                pass

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        conn = get_db_connection()
        rows = conn.execute(query, params).fetchall()
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
            <h2>Tracker Data</h2>
            <form method="get">
                <label>Tracker ID: <input name="tracker_id" value="{{ request.args.get('tracker_id', '') }}"></label>
                <label>Max Age (hrs): <input type="number" name="age_hours" value="{{ request.args.get('age_hours', '') }}"></label>
                <label>Limit: <input type="number" name="limit" value="{{ request.args.get('limit', 50) }}"></label>
                <label>Offset: <input type="number" name="offset" value="{{ request.args.get('offset', 0) }}"></label>
                <button type="submit">Apply</button>
                <a href="/export?tracker_id={{ request.args.get('tracker_id', '') }}&age_hours={{ request.args.get('age_hours', '') }}">Export CSV</a>
            </form>
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


@app.route('/export')
def export_csv():
    """Export tracker data as a CSV file, with optional filters."""
    try:
        tracker_id = request.args.get('tracker_id', '')
        age_hours = request.args.get('age_hours', '')

        query = 'SELECT * FROM tracker_data'
        filters = []
        params = []

        if tracker_id:
            filters.append('tracker_id = ?')
            params.append(tracker_id)

        if age_hours:
            try:
                age_dt = datetime.utcnow() - timedelta(hours=int(age_hours))
                filters.append('timestamp >= ?')
                params.append(age_dt.isoformat(sep=' '))
            except ValueError:
                pass

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

        query += ' ORDER BY timestamp DESC'

        conn = get_db_connection()
        rows = conn.execute(query, params).fetchall()
        conn.close()

        output = StringIO()
        writer = csv.writer(output)
        headers = rows[0].keys() if rows else []
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[h] for h in headers])

        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=tracker_data.csv"})
    except Exception as e:
        logging.error("Error exporting CSV: %s", e)
        return f"<p>Error exporting data: {str(e)}</p>"


@app.route('/config')
def config():
    """Render the configuration editor page from the HTML file."""
    try:
        with open('templates/config.html') as f:
            html_content = f.read()
        return render_template_string(html_content)
    except FileNotFoundError:
        logging.error("Configuration HTML file not found.")
        return "<p>Configuration file not found.</p>", 404
    except Exception as e:
        logging.error("Error loading config page: %s", e)
        return f"<p>Error loading config page: {str(e)}</p>", 500


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
        tracker_data = request.get_json()
        conn = get_db_connection()
        conn.execute('''INSERT INTO tracker_config (tracker_id, tracker_name, tracker_symbol, tracker_symbol_color,
                        tracker_waypoint_max, tracker_waypoint_timeout, tracker_waypoint_color)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (tracker_data['tracker_id'], tracker_data['tracker_name'], tracker_data['tracker_symbol'],
                      tracker_data['tracker_symbol_color'], tracker_data['tracker_waypoint_max'],
                      tracker_data['tracker_waypoint_timeout'], tracker_data['tracker_waypoint_color']))
        conn.commit()
        conn.close()
        logging.info("Added new tracker configuration: %s", tracker_data)
        return '', 201
    except Exception as e:
        logging.error("Error adding tracker configuration: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trackers/<int:id>', methods=['PUT'])
def update_tracker(id):
    """Update an existing tracker configuration by ID."""
    try:
        tracker_data = request.get_json()
        conn = get_db_connection()
        conn.execute('''UPDATE tracker_config SET tracker_id = ?, tracker_name = ?, tracker_symbol = ?,
                        tracker_symbol_color = ?, tracker_waypoint_max = ?, tracker_waypoint_timeout = ?,
                        tracker_waypoint_color = ? WHERE id = ?''',
                     (tracker_data['tracker_id'], tracker_data['tracker_name'], tracker_data['tracker_symbol'],
                      tracker_data['tracker_symbol_color'], tracker_data['tracker_waypoint_max'],
                      tracker_data['tracker_waypoint_timeout'], tracker_data['tracker_waypoint_color'], id))
        conn.commit()
        conn.close()
        logging.info(
            "Updated tracker configuration ID %s with data: %s", id, tracker_data)
        return '', 204
    except Exception as e:
        logging.error("Error updating tracker ID %s: %s", id, e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trackers/<int:id>', methods=['DELETE'])
def delete_tracker(tracker_id):
    """Delete a tracker configuration by ID."""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM tracker_config WHERE id = ?', (tracker_id,))
        conn.commit()
        conn.close()
        logging.info("Deleted tracker configuration ID %s", tracker_id)
        return '', 204
    except Exception as e:
        logging.error("Error deleting tracker ID %s: %s", tracker_id, e)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
