import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.mitgaisim.idf.il"
TOKEN_EXPIRY_BUFFER = 60
BIOMETRIC_DATA = os.getenv("BIOMETRIC_DATA")
MALSHAB_ID = os.getenv("MALSHAB_ID")
UUID = os.getenv("UUID")
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh")
