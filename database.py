# database.py
from utility.logger import logger
from typing import Dict, Any
import datetime
import mariadb
import asyncio

# TODO - Implement asyncio lock to prevent race conditions on database

class Database(object):
    def __init__(
            self,
            user: str="admin",
            password: str="T@rleton123",
            host: str="localhost",
            database_name: str="AgCenter" ) -> None:
        self.__user = user
        self.__password = password
        self.__host = host
        self.__database_name = database_name
        #self.__database_in_use = False
        self.__database_lock = asyncio.Lock()

    @property
    def database_in_use(self) -> bool:
        """
            To determine if database is currently being used by an object
        """
        return self.__database_in_use
    
    @database_in_use.setter
    def database_in_use(self, value: bool) -> None:
        """
            For setting flag notifying other objects that database is in use
        """
        self.__database_in_use = value

    async def write(self, sensor: str, readings: Dict[str, Any]) -> None:
        """
            Method for establishing connection to database and
            writing data to tables.
                *args -> str sensor name, dict data readings
        """
        logger.info("Establishing connection to MariaDb")
        async with self.__database_lock:
            self.conn= mariadb.connect(
                user=self.__user,
                password=self.__password,
                host=self.__host,
                database=self.__database_name
            )

            try:
                self.cur = self.conn.cursor()
                logger.info(f"Writing {sensor} data to database...")
                dt = datetime.datetime.now()
                await self.insert(sensor, readings, dt)
                self.conn.commit()
                self.cur.close()
            except mariadb.Error as mariadb_error:
                logger.error(f"Error when trying to write {sensor} data to database: {mariadb_error}")
            finally:
                logger.info("MariaDb connection closed.")
                self.conn.close()

    async def insert(self, sensor: str, readings: Dict[str, Any], dt: datetime.datetime):
        """
            Method to dynaically generate an SQL query for the passed sensor
                *args -> str sensor name, dict data readings, datetime date time
        """
        query = f"INSERT INTO {sensor} (Node, DT "
        query += ", ".join(readings.keys())
        query += ") VALUES (?,?,"
        query += ",?".join(["" for _ in readings])
        query += ")"

        self.cur.execute(query, (readings["Node"], dt) + tuple(readings.values()))