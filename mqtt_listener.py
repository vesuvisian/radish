"""
MQTT Listener for Radish
Reads and prints MQTT messages from your broker
"""

import os
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from radish.frame import Frame


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker"""
    if rc == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to MQTT broker")
        # Subscribe to the configured topic
        topic = userdata.get("topic", "radish/#")
        client.subscribe(topic)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Subscribed to {topic} topic")
    else:
        print(f"Failed to connect, return code {rc}")


def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the broker"""
    if rc != 0:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected disconnection (code {rc})"
        )
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Disconnected from MQTT broker")


def on_message(client, userdata, msg):
    """Callback for when a message is received"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(
        f"[{timestamp}] {msg.topic}:\n{str(Frame.from_bytes(bytes.fromhex(msg.payload)))}\n"
    )
    # print(msg.topic, msg.payload)


def main():
    # Load environment variables from .env file
    load_dotenv()

    # MQTT broker configuration from .env
    broker_host = os.getenv("MQTT_HOST", "localhost")
    broker_port = int(os.getenv("MQTT_PORT", 1883))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    topic = os.getenv("MQTT_TOPIC", "radish/#")

    # Empty strings from .env are treated as None
    if username == "":
        username = None
    if password == "":
        password = None

    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, userdata={"topic": topic})

    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Set username and password if provided
    if username and password:
        client.username_pw_set(username, password)
        print(f"Connecting to {broker_host}:{broker_port} as {username}...")
    else:
        print(f"Connecting to {broker_host}:{broker_port}...")

    # Connect and start the loop
    try:
        client.connect(broker_host, broker_port, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
