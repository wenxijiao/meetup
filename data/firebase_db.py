from pathlib import Path
from datetime import date
from data.data_structure import Participant

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import FieldFilter

SERVICE_ACCOUNT_PATH = Path(__file__).parent / "meetup-table-assign-firebase-adminsdk-fbsvc-fda1739a4a.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred)
db = firestore.client()

ROOT_COLLECTION = "meetups"

def login_user(id, name, language):
    query = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        user = Participant(
            name=name,
            language=language,
            id=user_data["id"],
            table_number=user_data.get("table_number"),
            check_in_time=user_data.get("check_in_time"),
            status="Checked In",
            history=user_data.get("history", [])
        )
        db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").document(user.id).set(user.to_dict())
        return id, name
    else:
        return logup_user(name, language, id=id)

def logup_user(name, language, id=None):
    user = Participant(name=name, language=language, id=id)
    user.check_in()
    db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").document(user.id).set(user.to_dict())
    return user.id, user.name

def logout_user(id):
    query = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        user = Participant.from_dict(user_data)
        user.check_out()
        db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").document(user.id).set(user.to_dict())
    else:
        raise ValueError("Participant not found")

def get_my_status(id):
    query = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        return Participant.from_dict(user_data)
    else:
        raise ValueError("Participant not found")

def get_all_participants():
    query = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").stream()
    return [Participant.from_dict(ans.to_dict()) for ans in query]

def get_active_participants():
    query = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants").where(filter=FieldFilter("status", "==", "Checked In")).stream()
    return [Participant.from_dict(ans.to_dict()) for ans in query]

def batch_update_participants(participants):
    batch = db.batch()
    today_ref = db.collection(ROOT_COLLECTION).document(str(date.today())).collection("participants")
    for participant in participants:
        doc_ref = today_ref.document(participant.id)
        batch.set(doc_ref, participant.to_dict())
    batch.commit()

def start_next_round(target_per_table: int, min_per_table: int):
    pass

def reset_event():
    pass
