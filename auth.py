import base64
import json
import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()
import uuid
import secrets
from config import BASE_URL


class AuthClient:
    def __init__(self):
        self.token = None
        self.expiration = 0
        self.biometric_data = os.getenv("BIOMETRIC_DATA")
        self.malshab_id = os.getenv("MALSHAB_ID")
        self.uuid = os.getenv("UUID")

        if not self.biometric_data or not self.uuid:
            self.register_biometric()

    def register_biometric(self):
        print("🔐 Initial Setup: Registering Biometric Data and UUID")
        print("⚠️ Mitgaisim App would not work while this script is running!")

        generated_uuid = str(uuid.uuid4()).upper()
        
        biometric_data = secrets.token_hex(16)

        malshab_id = input("Enter your Malshab ID: ")
        password = input("Enter your password: ")

        login_url = f"{BASE_URL}/api/authenticate/userLogin"
        login_payload = {
            "biometricData": biometric_data,
            "malshabId": malshab_id,
            "password": password,
            "uuid": generated_uuid
        }

        login_response = requests.post(login_url, json=login_payload)

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return

        login_data = login_response.json()
        if login_data.get("statusCode") != 1:
            print(f"❌ Login error: {login_data.get('statusDescription')}")
            return

        otp_auth_cookie = login_data.get("otpAuthCookie")
        if not otp_auth_cookie:
            print("❌ OTP authentication failed.")
            return

        otp_url = f"{BASE_URL}/api/otp/sendOtp"
        headers = {"cookie": f"OtpAuthCookie={otp_auth_cookie}"}
        otp_payload = {"sendOtpMethod": 0}

        otp_response = requests.post(otp_url, headers=headers, json=otp_payload)
        otp_data = otp_response.json()

        if otp_data.get("statusCode") != 1:
            print(f"❌ OTP request failed: {otp_data.get('statusDescription')}")
            return

        otp_target = otp_data.get("otpTarget")
        print(f"📲 OTP sent to {otp_target}. Please enter the code.")

        otp_code = input("Enter the OTP you received: ")

        verify_otp_url = f"{BASE_URL}/api/otp/verifyOtp"
        verify_otp_payload = {"otp": otp_code}

        verify_otp_response = requests.post(verify_otp_url, headers=headers, json=verify_otp_payload)
        verify_otp_data = verify_otp_response.json()

        if verify_otp_data.get("statusCode") != 1:
            print(f"❌ OTP verification failed: {verify_otp_data.get('statusDescription')}")
            return

        self.token = verify_otp_data.get("accessToken")
        self.expiration = verify_otp_data.get("expiration")
        self.biometric_data = login_payload["biometricData"]
        self.uuid = login_payload["uuid"]

        self._save_to_env("BIOMETRIC_DATA", self.biometric_data)
        self._save_to_env("UUID", self.uuid)
        self._save_to_env("MALSHAB_ID", malshab_id)

        print("✅ Biometric data and UUID registered successfully!")
        print("ℹ️ Please restart the script to continue.")
        exit()

    def authenticate(self):
        url = f"{BASE_URL}/api/authenticate/biometricLogin"
        payload = {
            "biometricData": self.biometric_data,
            "malshabId": self.malshab_id,
            "uuid": self.uuid
        }

        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if data.get("statusCode") == 1:
                self.token = data.get("accessToken")
                self.expiration = self._extract_expiration(self.token)
                print("✅ Authentication successful!")
                return self.token
            else:
                raise Exception("❌ Authentication failed!")
        else:
            raise Exception(f"❌ Request failed: {response.status_code}")

    def get_token(self):
        if not self.token or time.time() > float(self.expiration):
            print("🔄 Refreshing token...")
            return self.authenticate()
        return self.token

    def _extract_expiration(self, token):
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")

            payload = parts[1]
            padding = "=" * (4 - len(payload) % 4)  # Fix padding issue
            decoded_bytes = base64.urlsafe_b64decode(payload + padding)
            decoded_json = json.loads(decoded_bytes.decode("utf-8"))

            return decoded_json.get("exp", time.time()) - 60
        except Exception as e:
            print(f"⚠️ Failed to decode token: {e}")
            return time.time()

    def _save_to_env(self, key, value):
        env_file = ".env"
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, "r") as file:
                for line in file:
                    key_value = line.strip().split("=", 1)
                    if len(key_value) == 2:
                        env_vars[key_value[0]] = key_value[1]

        env_vars[key] = value

        with open(env_file, "w") as file:
            for k, v in env_vars.items():
                file.write(f"{k}={v}\n")