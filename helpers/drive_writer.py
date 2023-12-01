from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from collections import OrderedDict
from typing import Dict, Any
from utility.logger import logger
import utility.config as config
import datetime

"""
    PRIORITY:
        When writing to Google Spreadsheet, need to ensure that data is written
        to its correct corresponding column. Right now it is written simple as
        the ordering it is read.
"""

# TODO - In write_sensor_data, need to account for RGB list when writing to Google - [45, 135, 60]

class GSWriter(object):
    """
        GSWriter handles all Google API calls for writing to a Google Spreadsheet
            spreadsheet_id --> unique ID of sheet found in URL:
                https://docs.google.com/speradsheets/d/{SPREADSHEET_ID}/edit#grid=920914920
    """
    def __init__( self, spreadsheet_id: str=config.SPREADSHEET_ID ) -> None:
        self.__credentials = self._authenticate()
        self.__service = build("sheets", "v4", credentials=self.__credentials)
        self.__spreadsheet_id = spreadsheet_id
        self.__sheet_created = []
        self.__column_mappings = {}

    def _authenticate(self):
        """
            Verify credentials and establish permissions with API
        """
        creds = None
        
        creds = service_account.Credentials.from_service_account_file(
            config.CREDENTIALS_FILE,
            scopes=config.SCOPES
        )

        return creds
    
    async def _create_or_clear_sheet(self, sheet_name: str, headers: list) -> None:
        """
            For creating individual sheets within the Google Sheet. If sheet does not exist,
            create it and write the appropriate headers for the data.
        """
        try:
            sheets = self.__service.spreadsheets()
            spreadsheet = sheets.get(spreadsheetId=self.__spreadsheet_id).execute()
            sheet_properties = spreadsheet.get('sheets', [])

            sheet_exists = any(sheet['properties']['title'] == sheet_name for sheet in sheet_properties)

            if sheet_exists:
                logger.info(f"{sheet_name} exists... fetching column headers...")
                await self._fetch_headers_from_spreadsheet(sheet_name=sheet_name)
            else:
                logger.warning(f"{sheet_name} does not exist. Creating it...")
                body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }

                # Create missing sheet - sheet name is sensor name
                sheets.batchUpdate(spreadsheetId=self.__spreadsheet_id, body=body).execute()

                header_range = f"{sheet_name}!A1:{chr(65+len(headers)-1)}"
                header_values = [headers]

                self.__service.spreadsheets().values().update(
                    spreadsheetId=self.__spreadsheet_id,
                    range=header_range,
                    body={'values': header_values},
                    valueInputOption='RAW'
                ).execute()

                self.__column_mappings[sheet_name] = headers

        except HttpError as http_error:
            logger.error(f"Error occurred while trying to create/modify sheet: {http_error}")
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while working with Google Sheets.")

    async def write_sensor_data(self, sensor_dict: Dict[str, Any], timestamp_recv: str) -> None:
        """
            Method for processing data and writing it to specified Google Sheet
                *args -> dict sensor data, str datetime
        """
        # DT MUST be string as it is packaged as json for transmission to Google API
        for sensor in sensor_dict.keys():
            if 'DT' not in sensor_dict[sensor].keys():
                sensor_dict[sensor]['DT'] = timestamp_recv
            elif isinstance(sensor_dict[sensor]['DT'], datetime.datetime):
                sensor_dict[sensor]['DT'] = sensor_dict[sensor]['DT'].strftime("%m-%d-%Y@%H:%M:%S")
            else:
                sensor_dict[sensor]['DT'] = timestamp_recv

        for sensor_name, sensor_data in sensor_dict.items():
            sheet_name = sensor_name

            # Need to account for RGB values
            if sensor_name == "RGB_TCS34725":
                if "color_rgb_bytes" in sensor_data.keys():
                    del sensor_data["color_rgb_bytes"]
            
            # Sort data to match columns headers of sheet
            ordered_dict = await self._order_values_by_sheet(sheet_name, sensor_data)
            _values = list(ordered_dict.values())

            if sensor_name not in self.__sheets_created:
                await self._create_or_clear_sheet( sensor_name, list(sensor_data.keys()) )
                self.__sheet_created.append(sensor_name)

            range_to_append = (f"{sheet_name}!A1:{chr(65+len(list(ordered_dict.keys()))-1)}")

            try:
                logger.info("Writing to Google Spreadsheet...")
                self.__service.spreadsheets().values().append(
                    spreadsheetId=self.__spreadsheet_id,
                    range=range_to_append,
                    body={'values': [_values]},
                    valueInputoption='RAW'
                ).execute()

                logger.info("Write successful.")
            except HttpError as http_error:
                logger.error(f"Error occurred while trying to write to sheet: {http_error}")
            except RuntimeError as runtime_error:
                logger.error(f"Runtime Error: {runtime_error} while writing to sheet {self.__spreadsheet_id}")

    async def _order_values_by_sheet(self, sheet_name: str, sensor_dict: Dict[str, Any]) -> dict:
        """
            Order the dictionary keys/values by the order of the sheet column names
        """
        if sheet_name not in self.__column_mappings:
            return sensor_dict
        
        key_order = self.__column_mappings[sheet_name]
        ordered_dict = dict(OrderedDict((key, sensor_dict[key]) for key in key_order if key in sensor_dict))

        return ordered_dict
    
    async def _fetch_headers_from_spreadsheet(self, sheet_name: str) -> None:
        """
            Method for getting spreadsheet headers from Google Sheet
                *args -> str sheet name (should match sensor name)
        """
        _range = f"{sheet_name}!1:1"

        try:
            response = self.__service.spreadsheets().values().get(
                spreadsheetId=self.__spreadsheet_id,
                range=_range,
                majorDimension='ROWs'
            ).execute()

            headers = response.get('values', [])[0] if 'values' in response else []

            self.__column_mappings[sheet_name] = list(headers)

        except HttpError as http_error:
            logger.exception(f"HTTP request error occurred while fetching headers: {http_error}")
        except Exception as e:
            logger.exception(f"Error occurred while fetching headers: {e}")