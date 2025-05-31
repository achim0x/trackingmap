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
    """Establish a UTF-8 compatible connection to the SQLite database."""
    if not os.path.exists(db_path):
        error_msg = f"Database file '{db_path}' does not exist."
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA encoding = 'UTF-8';")
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
        tracker_id = request.args.get(
            'tracker_id', '').strip().replace("'", "").strip()
        age_hours = request.args.get(
            'age_hours', '').strip().replace("'", "").strip()
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

    except Exception as e:
        logging.error("Error fetching tracker data: %s", e)
        return f"<p>Error loading data: {str(e)}</p>"
    except Exception as e:
        logging.error("Error fetching tracker data: %s", e)
        return f"<p>Error loading data: {str(e)}</p>"

    try:
        with open('templates/data.html', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content, rows=rows)
    except FileNotFoundError:
        logging.error("Configuration HTML file not found.")
        return "<p>Configuration file not found.</p>", 404
    except Exception as e:
        logging.error("Error loading config page: %s", e)
        return f"<p>Error loading config page: {str(e)}</p>", 500


@app.route('/export')
def export_csv():
    """Export tracker data as a CSV file, with optional filters."""
    try:
        tracker_id = request.args.get('tracker_id', '').strip()
        age_hours = request.args.get('age_hours', '').strip()

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
        with open('templates/config.html', encoding='utf-8') as f:
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
