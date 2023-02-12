import os
from dotenv import load_dotenv

load_dotenv()


def get_local_secret(name, default=None):
    return os.getenv(name, default)


GSHEET_CREDENTIALS_PATH = get_local_secret("GSHEET_CREDENTIALS_PATH")
URL_FOR_GSHEET = get_local_secret("URL_FOR_GSHEET")
SHEET = get_local_secret("SHEET")
