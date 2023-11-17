from utility.logger import logger
from typing import Dict, Any
import datetime
import mariadb

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
        self.__datbase_name = database_name
        self.__database_in_use = False

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
            Method to dynaically match the sensor name with the appropriate
            SQL generator method.
                *args -> str sensor name, dict data readings, datetime date time
        """
        return await getattr(self, sensor)(readings, dt)
    
    async def TDS_Meter(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for TDS Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO TDS_Meter "
        query += "(Node, DT, raw_value, raw_voltage, PPM) VALUES (?,?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                                readings["raw_value"], readings["raw_voltage"]) 
                        )
        
    async def Turbidity_Meter(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for Turbidity Sensor tabl
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO Turbidity_Meter "
        query += "(Node, DT, raw_value, raw_voltage) VALUES (?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                                readings["raw_value"], readings["raw_voltage"])
                         )
        
    async def PH_meter(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for pH Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO PH_Meter "
        query += "(Node, DT, raw_value, raw_voltage) VALUES (?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                                readings["raw_value"], readings["raw_voltage"])
                         )
        
    async def TEMP_AHT21(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for AHT21 Temperature Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO TEMP_AHT21 "
        query += "(Node, DT, temperature, relative_humidity) VALUES (?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                                readings["temperature"], readings["relative_humidity"])
                         )
        
    async def CO2_ENS160(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for ENS160 CO2 Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO CO2_ENS160 "
        query += "(Node, DT, AQI, TVOC, eCO2) VALUES (?,?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                                readings["AQI"], readings["TVOC"],
                                readings["eCO2"])
                        )
        
    async def RGB_TCS34725(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating an executing SQL for RGB Color Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO RGB_TCS34725 "
        query += "(Node, DT, color, color_temperature, lux) VALUES (?,?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                             readings["color"], readings["color_temperature"], 
                             readings["lux"])
                        )
        
    async def IR_MLX_90614(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for Infrared Temperature Sensor table
                *args -> dict data readings, datetime date time
        """
        query = "INSERT INTO IR_MLX90614 "
        query += "(Node, DT, ambient_temperature, object_temperature) VALUES (?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                             readings["ambient_temperature"], readings["object_temperature"])
                         )
        
    async def UV_LTR390(self, readings: Dict[str, Any], dt: datetime.datetime) -> None:
        """
            Method for generating and executing SQL for Ultra-Violet Sensor table
                *args -> dict date readings, datetime date time
        """
        query = "INSERT INTO UV_LTR390 "
        query += "(Node, DT, uvi, lux, light, uvs) VALUES (?,?,?,?,?,?)"
        self.cur.execute(query,
                            (readings["Node"], dt,
                             readings["uvi"], readings["lux"],
                             readings["light"], readings["uvs"])
                         )


    