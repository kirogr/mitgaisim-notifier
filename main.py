import time
import logging
from api_client import MitgiaisimAPI
from notifier import Notifier

class MitgiaisimMonitor:
    def __init__(self, check_interval=300): # 5 minutes
        self.api = MitgiaisimAPI()
        self.notifier = Notifier()
        self.tracked_cases = {}
        self.tracked_scores = {}
        self.tracked_user_data = {}
        self.check_interval = check_interval
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def fetch_initial_data(self):
        self.logger.info("🔄 Initializing data...")

        cases = self.api.get_cases()
        if cases and "caseList" in cases:
            self.tracked_cases = {case["caseNumber"]: case for case in cases["caseList"]}

        quality_data = self.api.get_user_quality_data()
        if quality_data and "scoreList" in quality_data:
            self.tracked_scores = {item["name"]: item for item in quality_data["scoreList"]}

        user_data = self.api.get_user_main_data()
        if user_data:
            self.tracked_user_data = user_data

        self.logger.info(f"✅ Loaded {len(self.tracked_cases)} cases, {len(self.tracked_scores)} quality scores")

    def check_for_updates(self):
        self.logger.info("🔍 Checking for updates...")

        self._check_case_updates()
        self._check_quality_updates()
        self._check_user_data_updates()

    def _check_case_updates(self):
        cases = self.api.get_cases()
        if not cases or "caseList" not in cases:
            self.logger.warning("⚠️ Failed to retrieve case data")
            return

        current_case_numbers = set()

        for case in cases["caseList"]:
            case_number = case["caseNumber"]
            current_case_numbers.add(case_number)

            if case_number in self.tracked_cases:
                self._detect_case_changes(self.tracked_cases[case_number], case)
            else:
                title = f"New Case Opened: {case_number}"
                message = f"📌 Subject: {case['subject']}\n📅 Created: {case['creationDate']}\n📞 Contact: {case['channel']}\n🔍 Status: {case['statusDescription']}"
                self.notifier.send_notification(title, message)

            self.tracked_cases[case_number] = case



        previous_case_numbers = set(self.tracked_cases.keys())
        deleted_cases = previous_case_numbers - current_case_numbers

        for case_number in deleted_cases:
            title = f"Case Deleted: {case_number} | {self.tracked_cases[case_number]['mainSubject']}"
            message = f"The case with number {case_number} has been removed from the system."
            self.notifier.send_notification(title, message)
            del self.tracked_cases[case_number]  # remove from tracked cases


    def _detect_case_changes(self, old_case, new_case):
        updates = []
        fields = [ # fields to monitor
            "creationDate",
            "channel",
            "subject",
            "mainSubject",
            "statusDescription",
            "lastUpdateDate",
            "answer",
            "slaDate"
        ]

        for field in fields:
            if old_case.get(field) != new_case.get(field):
                updates.append(f"🔄 {field} changed: {old_case.get(field, 'N/A')} → {new_case.get(field, 'N/A')}")

        if new_case.get("status") == 1:
            old_answer = old_case.get("answer", "No answer")
            new_answer = new_case.get("answer", "No answer")

            if old_answer != new_answer:
                updates.append(f"📝 Answer updated: {new_answer}")

        if updates:
            title = f"Case Updated: {new_case['caseNumber']} | {new_case['mainSubject']}"
            message = "\n".join(updates)
            self.notifier.send_notification(title, message)


    def _check_quality_updates(self):
        quality_data = self.api.get_user_quality_data()
        if not quality_data or "scoreList" not in quality_data:
            self.logger.warning("⚠️ Failed to retrieve quality data")
            return
            
        for score in quality_data["scoreList"]:
            score_name = score["name"]
            if score_name in self.tracked_scores:
                self._detect_quality_changes(self.tracked_scores[score_name], score)
            self.tracked_scores[score_name] = score

    def _check_user_data_updates(self):
        user_data = self.api.get_user_main_data()
        if not user_data:
            self.logger.warning("⚠️ Failed to retrieve user data")
            return
            
        self._detect_user_data_changes(self.tracked_user_data, user_data)
        self.tracked_user_data = user_data

    def _detect_case_changes(self, old_case, new_case):
        updates = []

        if old_case["status"] != new_case["status"]:
            updates.append(f"Status changed: {old_case['statusDescription']} → {new_case['statusDescription']}")

        if old_case["lastUpdateDate"] != new_case["lastUpdateDate"]:
            updates.append(f"Last update changed: {old_case['lastUpdateDate']} → {new_case['lastUpdateDate']}")

        if updates:
            title = f"📋 Case Update: {new_case['caseNumber']} | {new_case['mainSubject']}"
            message = "\n".join(updates)
            self.notifier.send_notification(title, message)
            self.logger.info(f"📝 Case {new_case['caseNumber']} updated: {len(updates)} changes")

    def _detect_quality_changes(self, old_score, new_score):
        updates = []

        if old_score["score"] != new_score["score"]:
            updates.append(f"{old_score['title']} score changed: {old_score['score']} → {new_score['score']}")

        old_internal = {item["indicatorName"]: item["indicatorValue"] 
                        for item in old_score.get("internalScoreList", [])}
        new_internal = {item["indicatorName"]: item["indicatorValue"] 
                        for item in new_score.get("internalScoreList", [])}

        for name, value in new_internal.items():
            if name not in old_internal:
                updates.append(f"New internal score added: {name} ({value})")
            elif old_internal[name] != value:
                updates.append(f"Internal score changed: {name}: {old_internal[name]} → {value}")

        for name in old_internal:
            if name not in new_internal:
                updates.append(f"Internal score removed: {name} ({old_internal[name]})")

        if updates:
            title = "📊 Quality Score Update"
            message = "\n".join(updates)
            self.notifier.send_notification(title, message)
            self.logger.info(f"📈 Quality score updated: {len(updates)} changes")

    def _detect_user_data_changes(self, old_data, new_data):
        updates = []

        for key in new_data.keys():
            if key in old_data and old_data[key] != new_data[key]:
                updates.append(f"{key} changed: {old_data[key]} → {new_data[key]}")

        if updates:
            title = "👤 User Data Update"
            message = "\n".join(updates)
            self.notifier.send_notification(title, message)
            self.logger.info(f"👤 User data updated: {len(updates)} changes")

    def run_monitoring(self):
        self.fetch_initial_data()

        try:
            while True:
                self.check_for_updates()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Error in monitoring loop: {str(e)}", exc_info=True)

if __name__ == "__main__":
    monitor = MitgiaisimMonitor()
    monitor.run_monitoring()
