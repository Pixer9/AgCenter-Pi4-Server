# client.py
from utility.logger import logger
import socket
import json

class Client(object):
    """
        Client handles TCP connection, data conversion to json packets, and transmission
            host --> IP address of server or board to connect to
            port --> target port number the server/board is listening to
    """

    CLIENT_TIMEOUT = 10 # in seconds

    def __init__( self, host: str="10.42.0.1", port: int=65432 ) -> None:
        self.__host = host
        self.__port = port

    async def _package_data(self, data: dict) -> bytes:
        """
            Method for converting data to json and encoding
                *args -> dict sensor data
        """
        packaged_data = json.dumps(data).encode("utf-8")
        return packaged_data
    
    async def transmit(self, data: dict) -> None:
        """
            Method for establishing TCP connection and transmitting data
                *args -> dict sensor data
        """
        packaged_data = await self._package_data(data)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(Client.CLIENT_TIMEOUT)
                sock.connect((self.__host, self.__port))
                sock.sendall(packaged_data)
        except socket.timeout:
            logger.error(f"Connection with {self.__host} on port {self.__port} timedout.")
        except RuntimeError as runtime_error:
            logger.error(f"Error occurred while establishing connection with {self.__host} on port {self.__port}: {runtime_error}")
            