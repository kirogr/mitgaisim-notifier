# Mitgaisim Notifier

Mitgiaisim Notifier is a simple script that connects to the Mitgaisim API (אפליקציית מתגייסים) and keeps track of changes in a malshab profile.

It automatically sends notifications when something in your profile changes.

# 🔹Features
- ✅ A new case is opened or closed.
- ✅ Status changes in an existing case.
- ✅ Updates in quality scores (דפ"ר, פרופיל רפואי, התרשמות מראיון, קה"ס, etc).
- ✅ Changes in personal details (phone, email, recruitment date, etc.).
- ✅ New summons (זימונים) added/removed.
- ✅ New messages in Inbox or updates in the CRM.
- ✅ Everything runs in the background and you receive a notification when there's a change.

# 📥 Installation

### 1️⃣ Clone the Repository
```sh
git clone https://github.com/kirogr/mitgaisim-notifier.git
cd mitgaisim-notifier
```

### 2️⃣ Install Dependencies
```sh
pip install -r requirements.txt
```

⚠️ You do NOT need to manually fill `BIOMETRIC_DATA` and `UUID` they will be generated when you run the script for the first time in the `.env` file.

# 🚀 Running the Script
```sh
python main.py
```

The script will:
- If it's your first time running, it would ask for your Malshab ID and password
- Register biometric authentication so you won't need to enter a password again.
- Start checking for updates every 5 minutes.
- Send notifications if any changes are detected.

# 📜 License
This project is licensed under the MIT License.