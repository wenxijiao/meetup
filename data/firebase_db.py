import math
import random
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
    active_participants = get_active_participants()
    total_count = len(active_participants)
    if total_count == 0:
        return

    # --- 1. 简单的桌数计算 ---
    # 比如 13人 / 4 = 4桌
    num_tables = math.ceil(total_count / target_per_table)
    
    # 修正：如果算出来的桌子导致平均人数太少 (比如 5人分2桌，平均2.5 < min 3)，就减一桌
    if num_tables > 1 and (total_count / num_tables) < min_per_table:
        num_tables -= 1
        
    num_tables = max(1, num_tables) # 保底 1 桌

    # --- 2. 随机打乱 (Shuffle) ---
    # 这一步保证了每次分桌结果都不一样
    random.shuffle(active_participants)

    # --- 3. 发牌分配 (Round-Robin) ---
    # 0, 1, 2, 0, 1, 2... 这样循环发
    for i, p in enumerate(active_participants):
        # 计算桌号 (从 1 开始)
        table_no = str((i % num_tables) + 1)
        
        # 更新内存中的对象状态
        p.table_number = table_no
        # (最简版暂时不更新 history，先只看桌号变化)

    # --- 4. 批量保存到数据库 ---
    # 这一步做完，用户手机上的界面就会自动刷新了
    batch_update_participants(active_participants)

def reset_event():
    participants = get_active_participants()
    for p in participants:
        p.table_number = None
        
    batch_update_participants(participants)
    