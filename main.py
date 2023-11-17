# !/usr/bin/env python3
from helpers.drive_writer import GSWriter
from utility.utils import Controller
from database import Database
from server import Server
import asyncio
import busio
import board


async def main():
    # Optional Datbase for storing data locally
    AgDatabase = Database()

    # Optional Google Drive Spreadsheet writer
    writer = GSWriter()

    sensor_list = ["Camera", "TDS_Meter", "Turbidity_Meter", "PH_Meter"]
    i2c = busio.I2C(board.SCL, board.SDA)

    server = Server(host="10.42.0.1", port=65432, database=AgDatabase, writer=writer)

    control = Controller(sensor_list=sensor_list, i2c_bus=i2c, databse=AgDatabase, writer=writer)

    task_sensor_data = asyncio.create_task(control.gather_sensor_data())
    task_server = asyncio.create_task(server.open())

    await asyncio.gather(task_sensor_data, task_server)

if __name__ == "__main__":
    asyncio.run(main())