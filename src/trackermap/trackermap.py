"""The main module with the program entry point.

This modul handle the mqtt connection and uses submodules for database handling and user interface
"""

# ******************************************************************************
# Copyright (c) 2024, Achim Brunner
# License: BSD 3 Clause
# ******************************************************************************

# Imports **********************************************************************

import sys
import logging
import os
import argparse
import json
import ssl
import csv
from zoneinfo import ZoneInfo
from datetime import datetime
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import trackermap.tracker_db

try:
    from trackermap.version import __version__, __author__, __email__, __repository__, __license__
except ModuleNotFoundError:
    # provide dummy information when not installed as package but called directly
    # also necessary to get sphinx running without error
    __version__ = 'dev'
    __author__ = 'development'
    __email__ = 'none'
    __repository__ = 'none'
    __license__ = 'none'

# Variables ********************************************************************

LOG: logging.Logger = logging.getLogger(__name__)

# Classes **********************************************************************

# Functions ********************************************************************


def on_connect(cl, userdata, flags, rc, _):
    """
    Callback function triggered upon successful connection to the MQTT broker.
    Subscribes to the specified topic for device uplinks.

    Args:
        cl: The MQTT client instance.
        userdata: User-defined data of any type (not used).
        flags: Response flags sent by the broker.
        rc: The connection result (0 indicates success).
        _: Deprecated or unused parameter (kept for compatibility).
    """

    if rc == 0:
        LOG.info("Connected RC = %s", rc)
        cl.subscribe(TOPIC)
        LOG.info("Subscribed: %s", TOPIC)
    else:
        LOG.error("Connection failed: %s", rc)


def on_message(cl, userdata, msg):
    """
    Callback function triggered when a message is received on a subscribed topic.
    Parses the JSON payload and prints device ID and decoded payload.

    Args:
        cl: The MQTT client instance.
        userdata: User-defined data of any type (not used).
        msg: The received MQTT message object.
    """

    tracker_info = {
        "tracker_id": "",
        "latitude": 0.0,
        "longitude": 0.0,
        "battery": 0,  # Percenct
        "timestamp": "",
        "gw-rssi": -70,    # Signalstrength in dBm
        "gw-name": "",
        "gw-latitude": 0.0,
        "gw-longitude": 0.0

    }

    try:
        LOG.debug("Payload: %s", msg.payload)
        data = json.loads(msg.payload)
    except (json.JSONDecodeError) as e:
        LOG.error("Json Decoding error: %s", e)

    try:
        dev = data["end_device_ids"]["device_id"]
    except (KeyError) as e:
        LOG.error("Error in message processing: %s for device id", e)
        LOG.debug("Payload Data: %s", data)

    try:
        payl = data["uplink_message"]["decoded_payload"]["messages"][0]
        rx_metadata = data["uplink_message"]["rx_metadata"][0]
        LOG.debug("Device: [%s] %s", dev, payl)
        LOG.debug("Metadata: %s", rx_metadata)

        tracker_info["tracker_id"] = dev
        tracker_info["gw-name"] = rx_metadata["gateway_ids"]["gateway_id"]
        tracker_info["gw-rssi"] = rx_metadata["rssi"]
        tracker_info["gw-latitude"] = rx_metadata["location"]["latitude"]
        tracker_info["gw-longitude"] = rx_metadata["location"]["longitude"]

        for measurement in payl:
            if measurement["measurementId"] == "4197":
                tracker_info["longitude"] = measurement["measurementValue"]
                utc_dt = datetime.fromtimestamp(
                    int(measurement["timestamp"])/1000, tz=ZoneInfo("Europe/Berlin"))
                tracker_info["timestamp"] = utc_dt.strftime('%Y-%m-%d %H:%M')
            if measurement["measurementId"] == "4198":
                tracker_info["latitude"] = measurement["measurementValue"]
            if measurement["measurementId"] == "3000":
                tracker_info["battery"] = measurement["measurementValue"]
        LOG.info(tracker_info)
        if tracker_info["latitude"] != 0.0 and tracker_info["longitude"] != 0.0:
            trackermap.tracker_db.insert_tracker_info(db_conn, tracker_info)
            csv_writer.writerow(tracker_info)
    except (KeyError) as e:
        LOG.error("Error in message processing: %s for device: %s", e, dev)
        LOG.debug("Payload Data: %s", data)


def init_csv_writer(file_path, fieldnames):
    """
    Initialize CSV output of received tracker data

    Args:
        file_path (str): File name and path
        fieldnames (dict): Dictionary with field names

    Returns:
        handle: Handler to writer object
    """
    file_exists = os.path.isfile(file_path)
    file = open(file_path, mode='a', newline='', encoding='utf-8', buffering=1)
    writer = csv.DictWriter(file, fieldnames=fieldnames)

    if not file_exists:
        writer.writeheader()

    return writer


def main() -> int:
    """ The program entry point function.

    .. uml::

        Alice -> Bob: Hi!
        Alice <- Bob: How are you?

    Returns:
        int: System exit status.
    """
    logging.basicConfig(level=logging.INFO)

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="A simple example of parsing command-line arguments.")

    # Add arguments
    parser.add_argument('--verbose', action='store_true',
                        help='Increase output verbosity')
    parser.add_argument('--version', action='version',
                        version='%(prog)s' + __version__)

    args = parser.parse_args()  # Parse the arguments

    if args.verbose:
        print("Verbose mode is enabled.")
        LOG.setLevel(logging.DEBUG)

    LOG.info("Application started")
    LOG.debug("Client ID: %s", CLIENT_ID)
    LOG.debug("Credentials: %s - %s", USERNAME, PASSWORD)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         CLIENT_ID, protocol=mqtt.MQTTv311)
    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)         # TLS, Port 8883
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, port=8883)
    # client.connect(mqtt_host, port=8883, keepalive=120)
    # client.connect(mqtt_host, port=1883, keepalive=60)
    client.loop_forever()

    return 0  # return without errors

# Main *************************************************************************


load_dotenv()                                       # liest .env ein

try:
    app_id = os.environ["TTN_APP_ID"]
    tenant = os.getenv("TTN_TENANT", "ttn")
    region = os.getenv("TTN_REGION", "eu1")
    api_key = os.environ["TTN_API_KEY"]
except KeyError as e:
    raise RuntimeError(f"Missing required environment variable: {e}")

MQTT_HOST = f"{region}.cloud.thethings.network"
CLIENT_ID = app_id
USERNAME = app_id
PASSWORD = api_key
TOPIC = "v3/+/devices/+/up"    # all uplinks of all devices

# For CSV File init only
tracker_info = {
    "tracker_id": "",
    "latitude": 0.0,
    "longitude": 0.0,
    "battery": 0,
    "timestamp": "",
    "gw-rssi": -1,
    "gw-name": "",
    "gw-latitude": 0.0,
    "gw-longitude": 0.0
}

csv_writer = init_csv_writer("./tracker_data.csv", tracker_info.keys())

db_conn = trackermap.tracker_db.init_db()

if __name__ == "__main__":
    sys.exit(main())
