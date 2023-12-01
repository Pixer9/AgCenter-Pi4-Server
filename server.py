# server.py
import utility.config as config
from utility.logger import logger
from typing import Dict, Any
import datetime
import asyncio
import json

class Server(object):
    """
        Server handles all incoming TCP connection requests and processes the data
        that is transmitted.
            host: str --> IP of server
            port: int --> port for listening for connection requestions
            database --> database object used for storing data
    """

    SERVER_TIMEOUT = 10 # in seconds
    MAX_TCP_QUEUE = 10 # amount of connections to queue before refusing

    def __init__(self,
                 host: str=config.DEFAULT_SERVER_IP,
                 port: int=config.DEFAULT_SERVER_PORT,
                 database=None,
                 drive_writer=None,
                 local_writer=None,
                 store_database: bool=config.STORE_LOCAL_DATABASE,
                 store_local: bool=config.STORE_LOCAL_FILE,
                 store_drive: bool=config.STORE_DRIVE ) -> None:
        self.__host = host
        self.__port = port
        self.__database = database
        self.__GSWriter = drive_writer
        self.__XLSXWriter = local_writer
        self._store_database = store_database
        self._store_local = store_local
        self._store_drive = store_drive

    async def _handle_data(self, data: Dict[str, Any], timestamp: str) -> None:
        """
            Method for handling client connections asynchronously:
                writes to database
                writes to xlsx
                writes to Google sheet
        """
        try:
            if data and self._store_database and self.__database:
                for key in data.keys():
                    await self.__database.write(key, data[key])

            if data and self._store_local and self.__XLSXWriter:
                await self.__XLSXWriter.write_sensor_data(data)

            if data and self._store_drive and self.__GSWriter:
                await self.__GSWriter.writer_sensor_data(sesnsor_dict=data, timestamp_recv=timestamp)

        except Exception as e:
            logger.error(f"Error handling client data: {e}")

    async def open(self) -> None:
        """
            Open socket connection on specified port and begin listening for
            connection requests.
        """
        _server = await asyncio.start_server(
            self._process_client, self.__host, self.__port
        )

        async with _server:
            logger.info(f"Server is listening on port {self.__port}...")
            await _server.serve_forever()

    async def _process_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
            Method for handling client connections with asyncio.start_server
        """
        try:
            addr = writer.get_extra_info('peername')
            logger.info(f"Now serving... {addr}")

            # Send current datetime so that node is synced with server
            current_time = datetime.datetime.now().strftime("%m-%d-%Y@%H:%M:%S")
            current_time_bytes = json.dumps(current_time).encoe("utf-8")
            writer.write(current_time_bytes)
            await writer.drain()

            # Wait for data transmission from node
            data = await asyncio.wait_for(reader.read(config.PACKET_SIZE), timeout=Server.SERVER_TIMEOUT)
            json_data = json.loads(data.decode())
            logger.info(f"Data received from {addr} at {current_time}")

            await self._handle_data(data=json_data, timestamp=current_time)

        except asyncio.TimeoutError:
            logger.error(f"Connection timedout for {addr}")
        except json.JSONDecodeError as json_error:
            logger.error(f"Error decoding JSON: {json_error}")
        except Exception as e:
            logger.error(f"Error processing client connection {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()