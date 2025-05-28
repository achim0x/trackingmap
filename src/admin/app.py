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
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tracker Config Editor</title>
        <style>
            table, th, td { border: 1px solid black; border-collapse: collapse; padding: 8px; }
            input { width: 100%; }
        </style>
    </head>
    <body>
        <h2>Tracker Config Editor</h2>
        <button onclick="loadData()">Reload</button>
        <table id="trackerTable">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Tracker ID</th>
                    <th>Name</th>
                    <th>Symbol</th>
                    <th>Symbol Color</th>
                    <th>Max Waypoints</th>
                    <th>Timeout</th>
                    <th>Waypoint Color</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
        <h3>Add New Tracker</h3>
        <form onsubmit="addTracker(); return false;">
            <input name="tracker_id" placeholder="Tracker ID">
            <input name="tracker_name" placeholder="Name">
            <input name="tracker_symbol" placeholder="Symbol">
            <input name="tracker_symbol_color" placeholder="Symbol Color">
            <input name="tracker_waypoint_max" type="number" placeholder="Max Waypoints">
            <input name="tracker_waypoint_timeout" type="number" placeholder="Timeout">
            <input name="tracker_waypoint_color" placeholder="Waypoint Color">
            <button type="submit">Add</button>
        </form>
        <script>
            async function loadData() {
                const res = await fetch('/api/trackers');
                const data = await res.json();
                const tbody = document.querySelector('#trackerTable tbody');
                tbody.innerHTML = '';
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${row.id}</td>
                        <td><input value="${row.tracker_id}"/></td>
                        <td><input value="${row.tracker_name}"/></td>
                        <td><input value="${row.tracker_symbol}"/></td>
                        <td><input value="${row.tracker_symbol_color}"/></td>
                        <td><input type="number" value="${row.tracker_waypoint_max}"/></td>
                        <td><input type="number" value="${row.tracker_waypoint_timeout}"/></td>
                        <td><input value="${row.tracker_waypoint_color}"/></td>
                        <td>
                            <button onclick="updateTracker(${row.id}, this.parentElement.parentElement)">Update</button>
                            <button onclick="deleteTracker(${row.id})">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            async function updateTracker(id, row) {
                const inputs = row.querySelectorAll('input');
                const body = {
                    tracker_id: inputs[0].value,
                    tracker_name: inputs[1].value,
                    tracker_symbol: inputs[2].value,
                    tracker_symbol_color: inputs[3].value,
                    tracker_waypoint_max: parseInt(inputs[4].value),
                    tracker_waypoint_timeout: parseInt(inputs[5].value),
                    tracker_waypoint_color: inputs[6].value
                };
                await fetch(`/api/trackers/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                loadData();
            }

            async function deleteTracker(id) {
                await fetch(`/api/trackers/${id}`, { method: 'DELETE' });
                loadData();
            }

            async function addTracker() {
                const form = document.querySelector('form');
                const formData = new FormData(form);
                const body = Object.fromEntries(formData.entries());
                body.tracker_waypoint_max = parseInt(body.tracker_waypoint_max);
                body.tracker_waypoint_timeout = parseInt(body.tracker_waypoint_timeout);
                await fetch('/api/trackers', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                form.reset();
                loadData();
            }

            loadData();
        </script>
    </body>
    </html>
    ''')


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
