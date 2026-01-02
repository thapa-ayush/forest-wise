# azure_client.py - Forest Guardian Hub
import os
import logging
from azure.iot.device import IoTHubDeviceClient, Message
from config import Config

class AzureIoTHubClient:
    def __init__(self):
        self.conn_str = Config.AZURE_IOTHUB_CONN_STR
        self.client = IoTHubDeviceClient.create_from_connection_string(self.conn_str)
        self.client.connect()

    def send_telemetry(self, data: dict):
        msg = Message(str(data))
        self.client.send_message(msg)
        logging.info(f"Sent telemetry: {data}")

    def receive_commands(self):
        # Placeholder for cloud-to-device commands
        pass

azure_iot = AzureIoTHubClient()
