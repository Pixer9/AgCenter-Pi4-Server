# server.py
from utility.logger import logger
from typing import Dict, Any
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
                 host: str="10.42.0.1",
                 port: int=65432,
                 database=None,
                 writer=None,
                 store_local: bool=True,
                 store_drive: bool=True) -> None:
        self.__host = host
        self.__port = port
        self._db = database
        self._GSWriter = writer
        self._store_local = store_local
        self._store_drive = store_drive

    async def _handle_data(self, data: Dict[str, Any]) -> None:
        """
            Method for handling client connections asynchronously:
        """
        try:
            if data and self._db:
                while self._db.database_in_use:
                    await asyncio.sleep(0.1)
                self._db.database_in_use = True
                for key in data.keys():
                    await self._db.write(key, data[key])
                self._db.database_in_use = False

            if data and self._store_local:
                # implement XLSWriter from xlsx_writer.py once complete
                pass

            if data and self._store_drive and self._GSWriter:
                await self._GSWriter.writer_sensor_data(data)

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

    async def _process_client(self, reader, writer) -> None:
        """
            Method for handling client connections with asyncio.start_server
        """
        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=Server.SERVER_TIMEOUT)
            data_str = data.decode()
            logger.info(f"Data received from {writer.get_extra_info('peername')}")

            json_data = json.loads(data_str)
            await self._handle_data(json_data)
        except asyncio.TimeoutError:
            logger.error(f"Connection timedout for {writer.get_extra_info('peername')}")
        except json.JSONDecodeError as json_error:
            logger.error(f"Error decoding JSON: {json_error}")
        except Exception as e:
            logger.error(f"Error processing client connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()