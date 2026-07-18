from google.cloud.firestore import FieldFilter
from data.data_structure import Participant
from data.firebase_db import db

def add_participant(name, language):
    user = Participant(name=name, language=language)
    db.collection("participants").add({"id": user.id,
                                      "name": user.name,
                                      "language": user.language,
                                      "table_number": user.table_number})
    return user.id, user.name

def get_participant(id):
    query = db.collection("participants").where(filter=FieldFilter("id", "==", id)).stream()
    return [ans.to_dict() for ans in query][0]

def list_all_participants():
    query = db.collection("participants").stream()
    return [ans.to_dict() for ans in query]

if __name__ == "__main__":
    # Example usage
    id1, name1 = add_participant("Haru", "English")
    id2, name2 = add_participant("Miku", "Japanese")

    print(get_participant(id2))
    print(list_all_participants())
