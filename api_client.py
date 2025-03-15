import base64
import json

import requests
from auth import AuthClient
from config import BASE_URL

class MitgiaisimAPI:
    def __init__(self):
        self.auth = AuthClient()

    def _get_headers(self):
        token = self.auth.get_token()
        return {"Authorization": f"Bearer {token}"}

    # case types
    # 1 - פניות בטיפול
    # 2 - פניות שטופלו
    # 3 - כל הפניות

    def get_cases(self, case_type=3, page=1):
        url = f"{BASE_URL}/api/Inbox/GetCaseList?caseType={case_type}&page={page}"
        headers = {"cookie": f"MobileAuth={self.auth.get_token()}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_user_main_data(self):
        malshab_id = self._extract_malshab_id()
        url = f"{BASE_URL}/api/malshab/getUserMainData?malshabId={malshab_id}"
        response = requests.get(url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def get_user_quality_data(self):
        malshabId = self._extract_malshab_id()
        url = f"{BASE_URL}/api/malshabQualityData/getUserQualityData?malshabId={malshabId}"
        response = requests.get(url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    # def get_user_quality_data(self):
    #     with open("scores.json", "r", encoding="utf-8") as file:
    #         data = json.load(file)
    #     return data

    def _extract_malshab_id(self):
        try:
            token = self.auth.get_token()
            if not token:
                raise ValueError("No token available")

            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT token format")

            payload = parts[1]
            padding = "=" * (4 - len(payload) % 4)  # padding
            decoded_bytes = base64.urlsafe_b64decode(payload + padding)
            decoded_json = json.loads(decoded_bytes.decode("utf-8"))

            return decoded_json.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name", "") # malshab id from token
        except Exception as e:
            print(f"⚠️ Failed to extract Malshab ID: {e}")
            return None