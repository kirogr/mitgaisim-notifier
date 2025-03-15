import subprocess
import os
import sys

class Notifier:
    def __init__(self):
        self.ntfy_url = os.getenv("NTFY_URL")

    # you can modify this function to send notifications to other services :)
    # for example, you can use the Telegram API to send notifications to a bot
    # for this script, i used ntfy.sh to send notifications to my phone (push)

    def send_notification(self, title, message, priority="default", tags="loudspeaker"):
        try:
            curl_command = [
                "curl",
                "-H", f"Title: {title}",
                "-H", f"Priority: {priority}",
                "-H", f"Tags: {tags}",
                "-d", message,
                self.ntfy_url
            ]
            result = subprocess.run(curl_command, capture_output=True, text=True, encoding="utf-8")  # Fix encoding
            if result.returncode == 0:
                print("✅ Notification sent!")
            else:
                print(f"❌ Failed to send notification: {result.stderr.encode(sys.stdout.encoding, errors='replace').decode()}")
        except Exception as e:
            print(f"⚠️ Error sending notification: {e}")