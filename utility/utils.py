# utils.py
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS
import utility.config as config
#from libcamera import Transform
from typing import Optional, Dict, Any
from .logger import logger
from busio import I2C
import picamera2
import datetime
import inspect
import asyncio
import time
import sys
import os


class Controller(object):
    """
        Controller handles sensor object creation, management, and data collection
            sensor_dict --> key is str sensor name, value is Analog Pin object
    """

    STAGGER_INTERVAL = 20 # in minutes

    def __init__(self,
                 sensor_list: list,
                 i2c_bus: I2C,
                 store_locally: bool=config.STORE_LOCAL_FILE,
                 store_database: bool=config.STORE_LOCAL_DATABASE,
                 store_drive: bool=config.STORE_DRIVE,
                 database=None,
                 drive_writer=None,
                 local_writer = None ) -> None:
        self.__sensor_list = sensor_list
        self.__i2c_bus = i2c_bus
        self.__store_locally = store_locally
        self.__store_database = store_database
        self.__store_drive = store_drive
        self.__database = database
        self.__GSWriter = drive_writer
        self.__XLSXWriter = local_writer
        self.__object_map = self._create_object_map()
        self.__current_objects = self._create_objects()

    def _create_object_map(self) -> dict:
        """
            Method for generating str -> class map
        """
        logger.info("Mapping existing classes...")
        object_map = {}

        for name, obj in inspect.getmemebers(sys.modules[__name__]):
            if inspect.isclass(obj):
                object_map[name] = obj

        logger.info("Mapping complete.")
        return object_map
    
    def _create_objects(self) -> list:
        """
            Method for creating objects based on passed dict of sensors
        """
        logger.info("Generating Objects...")
        objects = []

        for name in self.__sensor_list:
            if name in self.__object_map:
                try:
                    object_class = self.__object_map[name]
                    if name == "Camera":
                        obj = object_class()
                    else:
                        obj = object_class(self.__i2c_bus)
                    objects.append(obj)

                except RuntimeError as runtime_error:
                    logger.exception(f"Runtime Error: {runtime_error} when creating object {name}.")
                except Exception as e:
                    logger.exception(f"Error occurred while creating object {name}: {e}")

        logger.info("Generation complete.")
        return objects
    
    async def gather_sensor_data(self) -> None:
        """
            Method for collecting all sensor object data
        """
        while True:
            current_time = datetime.datetime.now().strftime("%m-%d-%Y@%H:%M:%S")
            sensor_data = {}
            logger.info("Collecting data...")

            for sensor in self.__current_objects:
                data = None
                if isinstance(sensor, Camera):
                    image_path = await sensor.capture_image()
                    if image_path is not None and config.SCP_COPY:
                        await self._ssh_copy_to_hub(image_path)
                else:
                    data = await sensor.package(current_time)
                if data is not None:
                    sensor_data.update(data)
                    await asyncio.sleep(1.0)
            logger.info("Collection complete.")

            if sensor_data:
                await self._write_to_database(sensor_data)
                await self._write_to_file(data=sensor_data, timestamp=current_time)

            next_reading = await self._calc_next_reading()
            logger.info(f"Next reading in {next_reading} seconds.")

            await asyncio.sleep(next_reading)

    async def _ssh_copy_to_hub(self, image_path: str) -> None:
        """
            Optional method for copying images to Pi 4 using SSH/SCP
                *args -> str image path
        """
        logger.info("Copying image to hub...")
        
        if os.path.exists(image_path):
            copy_command = f"scp {image_path} {config.USERNAME}@{config.IP_ADDR}:{config.DESTINATION_COPY_PATH}"
            os.system(copy_command)

            # Remove image from local directory if not wanting to store locally (saves storage space)
            if not self.__store_locally:
                del_command = f"rm {image_path}"
                os.system(del_command)

    async def _write_to_file(self, data: Dict[str, Any], timestamp: str) -> None:
        """
            Optional method for storing data locally
                *args -> dict sensor data
        """
        if self.__store_locally and self.__XLSXWriter:
            await self.__XLSXWriter.write_sensor_data(data)
        if self.__store_drive and self.__GSWriter:
            await self.__GSWriter.write_sensor_data(sensor_dict=data, timestamp_recv=timestamp)

    async def _write_to_database(self, data: dict) -> None:
        """
            Method for acquiring database lock and writing to database
                *args -> dict sensor data
        """
        if self.__database:
            for key in data.keys():
                await self.__database.write(key, data[key])
        else:
            logger.warning(f"No database was established. Current database is {self.__database}")

    async def _calc_next_readings(self) -> int:
        """
            Method for determing how long to wait until next readings
        """
        logger.info("Calculating next reading...")

        current_time = datetime.datetime.now()
        minutes_next = Controller.STAGGER_INTERVAL - int(current_time.minute % Controller.STAGGER_INTERVAL)
        next_reading = (minutes_next * 60) + current_time.second

        return next_reading
    
class Camera(picamera2.Picamera2):
    """
        Camera handles all image/video creation
            local_store --> Specify whether you want images/videos stored locally or just on hub
    """
    # Set log level to error to remove unneccessary data from logs
    picamera2.Picamera2.set_logging(picamera2.Picamera2.ERROR)

    def __init__(self,
                 dimensions: tuple=config.IMAGE_DIMENSIONS,
                 file_format: str=config.IMAGE_FORMAT,
                 use_timestamp: bool=config.USE_TIMESTAMP_AS_NAME ) -> None:
        super().__init__()
        self.__dimensions = dimensions
        self.__file_format = file_format
        self.__use_timestamp = use_timestamp

    @property
    def _image_name(self) -> str:
        """
            Property method for generating image names
        """
        if self.__use_timestamp:
            return datetime.datetime.now().strftime("%m-%d-%Y@%H:%M:%S")
        return "test1"
    
    async def capture_image(self) -> Optional(str, None):
        """
            Method for capturing image and returning absolute path to that image
        """
        try:
            config = self.create_still_configuration(
                main={"size": self.__dimensions},
                #transform=Transform(vflip=1, hflip=1),
                raw=self.sensor_modes[3]
            )

            self.configure(config)
            self.start(show_preview=False)

            asyncio.sleep(2.0)
            
            full_image_path = config.IMAGE_STORE_PATH+self._image_name+f".{self.__file_format}"
            self.capture_file(
                file_output=full_image_path,
                name="main",
                format=self.__file_format,
                wait=True
            )

            self.stop()
            return full_image_path
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while trying to capture image.")
            return None
        
class ADC_Analog(object):
    """
        Helper Class for ADS1115/Sensor Integration
            i2c_bus --> I2C object/bus that the ADS1115 uses
            address --> Default I2C address for ADS1115 is 0x48
            channel --> Adafruit Analog Pin Type (e.g., ADS.P1)
    """
    def __init__(self, i2c_bus: I2C, address: int, channel) -> None:
        self.ADC = AnalogIn(ADS.ADS1115(i2c_bus, address=address), channel)

"""
    https://mm.digikey.com/Column-/opasdata/d220001/medias/docus/2309/SEN0244_Web.pdf

        Output Voltage: 0 ~ 2.3v
        TDS Measurement Range: 0 ~ 1000ppm
"""
class TDS_Meter(ADC_Analog):
    def __init__( self, i2c_bus: I2C, address: int=config.ADC_ADDR, channel=config.TDS_CHAN ) -> None:
        super().__int__( i2c_bus, address, channel )
        self.__max_voltage = 2.3
        self.__max_ppm = 1000
        self.__ratio = self.__max_voltage / self.__max_ppm

    async def _convert_to_ppm(self, voltage: float) -> int:
        """
            Method for converting raw voltage readings to parts per million readings
        """
        return int(voltage * self.__ratio)
    
    @property
    async def _read_analog(self) -> bool:
        """
            Property method for retreiving analog readings for ADS1115
        """
        try:
            self.__TDS_Dict = {
                "Node": config.NODE,
                "DT": None,
                "raw_value": None,
                "raw_voltage": None,
                "PPM": None
            }

            value = self.ADC.value
            voltage = self.ADC.voltage

            self.__TDS_dict["raw_value"] = value
            self.__TDS_dict["raw_voltage"] = voltage
            self.__TDS_dict["PPPM"] = await self._convert_to_ppm(voltage)
            #ppms = list(map(self._convert_to_ppm, voltages))

            return True
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while reading TDS analog.")
            return False
        
    async def package(self, date_time: datetime.dattime) -> Optional(dict, None):
        """
            Method for packaging data into dictionary with sensor name as key
                *args --> datetime date time
        """
        if await self._read_analog:
            self.__TDS_dict["DT"] = date_time
            data = {"TDS_Meter": self.__TDS_Dict}
            return data
        return None
    
"""
    https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2555/SEN0189_Web.pdf

        My interpretation of this is that the higher the read voltage from the sensor,
        the more pure the substance. As the voltage decreases, the particulates increase
        as the light is scattered by the increased solids.
"""
class Turbidity_Meter(ADC_Analog):
    def __init__( self, i2c_bus: I2C, address: int=config.ADC_ADDR, channel=config.TURBIDITY_CHAN ) -> None:
        super().__init__( i2c_bus, address, channel )
        self.__min = None
        self.__max = None

    @property
    async def _read_analog(self) -> bool:
        """
            Property method for retreiving analog readings for ADS1115
        """
        try:
            self.__TB_dict = {
                "Node": config.NODE,
                "DT": None,
                "raw_value": None,
                "raw_voltage": None
            }

            value = self.ADC.value
            voltage = self.ADC.voltage

            self.__TB_dict["raw_value"] = value
            self.__TB_dict["raw_voltage"] = voltage

            return True
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while reading Turbidity analog.")
            return False
        
    async def package(self, date_time: datetime.datetime) -> Optional(dict, None):
        """
            Method for packaging data into dictionary with sensor name as key
                *args --> datetime date time
        """
        if await self._read_analog:
            self.__TB_dict["DT"] = date_time
            data = {"Turbidity_Meter": self.__TB_dict}
            return data
        return None
    
"""
    https://www.e-gizmo.net/oc/kits%20documents/PH%20Sensors%20E-201-C/PH%20Sensor%20E-201-C.pdf

        Reference pH Value and Output Voltage:
            pHValue         Output
                4               3.071
                7               2.535
                10              2.066
"""
class PH_Meter(ADC_Analog):
    def __init__( self, i2c_bus: I2C, address: int=config.ADC_ADDR, channel=config.PH_CHAN ) -> None:
        super().__init__( i2c_bus, address, channel )
        self.__min = None
        self.__max = None

    @property
    async def _read_analog(self) -> bool:
        """
            Property method for retreiving analog readings for ADS1115
        """
        try:
            self.__PH_dict = {
                "Node": config.NODE,
                "DT": None,
                "raw_value": None,
                "raw_voltage": None
            }

            value = self.ADC.value
            voltage = self.ADC.voltage

            self.__PH_dict["raw_value"] = value
            self.__PH_dict["raw_voltage"] = voltage

            return True
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while reading PH analog.")
            return False
        
    async def package(self, date_time: datetime.datetime) -> Optional(dict, None):
        """
            Method for packaging data into dictionary with sensor name as key
        """
        if await self._read_analog:
            self.__PH_dict["DT"] = date_time
            data = {"PH_Meter": self.__PH_dict}
            return data
        return None