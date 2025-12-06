from datetime import datetime
import pytz
import uuid

tz = pytz.timezone("Pacific/Auckland")

class Participant:
    def __init__(self, name, language, id=None, table_number=None, check_in_time=None, check_out_time=None, status="Not Checked In", history=None):
        self.id = id or str(uuid.uuid4())
        self.name = name.strip().title()
        self.language = language
        self.table_number = table_number
        self.check_in_time = check_in_time
        self.check_out_time = check_out_time
        self.status = status
        self.history = history or []

    def check_in(self):
        now_str = str(datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"))
        self.check_in_time = now_str
        self.status = "Checked In"

    def check_out(self):
        now_str = str(datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"))
        self.check_out_time = now_str
        self.status = "Not Checked In"
        self.table_number = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "table_number": self.table_number,
            "check_in_time": self.check_in_time,
            "status": self.status,
            "history": self.history
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            language=data["language"],
            id=data["id"],
            table_number=data.get("table_number"),
            check_in_time=data.get("check_in_time"),
            status=data.get("status", "Not Checked In"),
            history=data.get("history", [])
        )