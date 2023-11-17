from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from typing import Dict, Any, Optional
from utility.logger import logger
import os.path

"""
    PRIORITY:
        When writing to Google Spreadsheet, need to ensure that data is written
        to its correct corresponding column. Right now it is written simple as
        the ordering it is read.
"""

# TODO - In write_sensor_data, need to account for RGB list when writing to Google - [45, 135, 60]

CREDENTIALS_FILE = "./helpers/credentials.json" # for authenticating and generating token
SPREADSHEET_ID = "1Ffsrae8gBJSGfGUf9ubA3sehmHv77zW0ysqKY-EYkeQ" # unique ID for accessing specific spreadsheet

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class GSWriter(object):
    """
        GSWriter handles all Google API calls for writing to a Google Spreadsheet
            spreadsheet_id --> unique ID of sheet found in URL:
                https://docs.google.com/speradsheets/d/{SPREADSHEET_ID}/edit#grid=920914920
    """
    def __init__( self, spreadsheet_id: str=SPREADSHEET_ID ) -> None:
        self.__credentials = self._generate_token()
        self.__service = build("sheets", "v4", credentials=self.__credentials)
        self.__spreadsheet_id = spreadsheet_id
        self.__sheet_created = []

    def _generate_token(self):
        """
            Check if credentials have been verified and token has been generated. If not,
            create a token and store it locally.
        """
        creds = None
        if os.path.exists("./helpers/token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )

        # Store fresh token locally
        with open("token.json", "w") as token:
            token.write(creds.to_json())

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

            if not sheet_exists:
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
        except HttpError as http_error:
            logger.error(f"Error occurred while trying to create/modify sheet: {http_error}")
        except RuntimeError as runtime_error:
            logger.error(f"Error: {runtime_error} while working with Google Sheets.")

    async def write_sensor_data(self, sensor_data: Dict[str, Any]) -> None:
        """
            Method for processing data and writing it to specified Google Sheet
                *args -> dict sensor data
        """
        for sensor_name, sensor_data in sensor_data.items():
            sheet_name = sensor_name

            # Need to account for RGB values
            if sensor_name == "RGB_TCS34725":
                del sensor_data["color_rgb_bytes"]
            
            values = list(sensor_data.values())
            headers = list(sensor_data.keys())

            if sensor_name not in self.__sheets_created:
                await self._create_or_clear_sheet( sensor_name, headers )
                self.__sheets_create.append(sensor_name)

            range_to_append = (f"{sheet_name}!A1:{chr(65+len(headers)-1)}")

            try:
                logger.info("Writing to Google Spreadsheet...")
                self.__service.spreadsheets().values().append(
                    spreadsheetId=self.__spreadsheet_id,
                    range=range_to_append,
                    body={'values': [values]},
                    valueInputoption='RAW'
                ).execute()

                logger.info("Write successful.")
            except HttpError as http_error:
                logger.error(f"Error occurred while trying to write to sheet: {http_error}")
            except RuntimeError as runtime_error:
                logger.error(f"Runtime Error: {runtime_error} while writing to sheet {self.__spreadsheet_id}")

# Remove after thorough testing
if __name__ == "__main__":
    test_sensor_data = {
        "TDS_Meter": {'Node': 183, 'DT': '11-12-2023@17:00:36', 'raw_value': 13, 'raw_voltage': 0.2356236, 'PPM': 0},
        "Turbidity_Meter": {'Node': 183, 'DT': '11-12-2023@17:00:36', 'raw_value': 24981, 'raw_voltage': 3.1351365}
    }

    spreadsheet_id = SPREADSHEET_ID
    spreadsheet_writer = GSWriter(spreadsheet_id)
    spreadsheet_writer.write_sensor_data(test_sensor_data)
