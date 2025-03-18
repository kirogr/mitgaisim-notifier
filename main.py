import time
import logging
from api_client import MitgiaisimAPI
from notifier import Notifier

class MitgiaisimMonitor:
    def __init__(self, check_interval=300): # 5 minutes
        self.api = MitgiaisimAPI()
        self.notifier = Notifier()
        self.tracked_cases = {}
        self.tracked_summons = {}
        self.tracked_scores = {}
        self.tracked_user_data = {}
        self.tracked_questionnaires = {}
        self.tracked_crm = {}
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
        self._check_summon_updates()
        self._check_quality_updates()
        self._check_user_data_updates()
        self._check_questionaire_updates()
        self._check_crm_updates()

    def _check_crm_updates(self):
        has_update = self.api.get_has_crm_update()

        if not has_update or "isUpdated" not in has_update:
            self.logger.warning("⚠️ Failed to retrieve CRM update status")
            return

        if not self.tracked_crm:
            self.tracked_crm = has_update["isUpdated"]
            return

        if not self.tracked_crm and has_update["isUpdated"]:
            title = "📢 CRM Update"
            message = "A new CRM message is available!" # a crm message in inbox , or any other updates in crm.
            self.notifier.send_notification(title, message)

        self.tracked_crm = has_update["isUpdated"]


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
                # New case detected
                title = f"New Case Opened: {case_number}"
                message = f"📌 Subject: {case['subject']}\n📅 Created: {case['creationDate']}\n📞 Contact: {case['channel']}\n🔍 Status: {case['statusDescription']}"
                self.notifier.send_notification(title, message)

            self.tracked_cases[case_number] = case # store case data

        previous_case_numbers = set(self.tracked_cases.keys())
        deleted_cases = previous_case_numbers - current_case_numbers

        for case_number in deleted_cases:
            if self.tracked_cases[case_number].get("checkedForRemoval", 0) < 2:
                self.tracked_cases[case_number]["checkedForRemoval"] = self.tracked_cases[case_number].get(
                    "checkedForRemoval", 0) + 1
            else:
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
            "status",
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

    def _check_summon_updates(self):
        summons = self.api.get_all_summons()
        if not summons or "allSummons" not in summons:
            self.logger.warning("⚠️ Failed to retrieve summons data")
            return

        new_summons = {s["summonId"]: s for s in summons["allSummons"]}

        if not self.tracked_summons:
            self.tracked_summons = new_summons
            return

        for summon_id, summon_details in new_summons.items():
            if summon_id not in self.tracked_summons:
                title = f"📌 New Summon: {summon_details['summonSubject']}"
                message = (
                    f"📅 Date: {summon_details['startDate']}\n"
                    f"📍 Location: {summon_details['locationName']}"
                )
                self.notifier.send_notification(title, message)

        for summon_id in self.tracked_summons:
            if summon_id not in new_summons:
                old_details = self.tracked_summons[summon_id]
                title = f"🗑️ Summon Removed: {old_details['summonSubject']}"
                message = (
                    f"📅 Date: {old_details['startDate']}\n"
                    f"📍 Location: {old_details['locationName']}"
                )
                self.notifier.send_notification(title, message)

        for summon_id, new_details in new_summons.items():
            if summon_id in self.tracked_summons:
                old_details = self.tracked_summons[summon_id]
                summon_updates = []

                for field in ["startDate", "endDate", "summonSubject", "locationAddress", "locationName", "approved", "read"]:
                    if old_details.get(field) != new_details.get(field):
                        summon_updates.append(f"{field} changed: {old_details.get(field)} → {new_details.get(field)}")

                if summon_updates:
                    title = f"🔄 Summon Updated: {new_details['summonSubject']}"
                    message = "\n".join(summon_updates)
                    self.notifier.send_notification(title, message)

        self.tracked_summons = new_summons

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

    def _check_questionaire_updates(self):
        questionaire = self.api.get_questionaire_data()
        if not questionaire:
            self.logger.warning("⚠️ Failed to retrieve questionaire data")
            return

        self._detect_questionaire_changes(questionaire)

    def _detect_questionaire_changes(self, new_questionnaire):
        updates = []
        new_questionnaires = {q["name"]: q for q in new_questionnaire.get("questionnaire", [])}

        if not self.tracked_questionnaires:
            self.tracked_questionnaires = new_questionnaires
            return

        old_questionnaires = self.tracked_questionnaires

        for name, details in new_questionnaires.items():
            if name not in old_questionnaires:
                updates.append(f"📌 New Questionnaire Added: {name}")

        for name in old_questionnaires:
            if name not in new_questionnaires:
                updates.append(f"🗑️ Questionnaire Removed: {name}")

        for name, new_details in new_questionnaires.items():
            if name in old_questionnaires:
                old_details = old_questionnaires[name]
                for field in ["endDate", "isFinished", "isStarted"]:
                    if old_details.get(field) != new_details.get(field):
                        updates.append(f"🔄 {name} {field} changed: {old_details.get(field)} → {new_details.get(field)}")

        if updates:
            title = "📋 Questionnaire Update"
            message = "\n".join(updates)
            self.notifier.send_notification(title, message)
            self.logger.info(f"📋 Questionnaire update detected: {len(updates)} changes")

        # Update stored state
        self.tracked_questionnaires = new_questionnaires

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
