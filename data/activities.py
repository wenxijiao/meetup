import hashlib


TASKS = [
    {
        "title": "Two Truths and a Lie / 本当のこと2つ＋うそ1つ",
        "steps": [
            "EN: Each person shares 3 statements (2 true, 1 false). Others guess the lie.",
            "JP: 一人ずつ3つ言います（本当2つ・うそ1つ）。他の人が嘘を当てます。",
        ],
    },
    {
        "title": "1-Minute Swap / 1分ずつ言語チェンジ",
        "steps": [
            "EN: 1 minute in English, then switch to Japanese for 1 minute.",
            "JP: 英語で1分→日本語で1分、話す人を回します。",
        ],
    },
    {
        "title": "Common Ground / 共通点さがし",
        "steps": [
            "EN: Find 3 things everyone at the table has in common.",
            "JP: テーブル全員の共通点を3つ見つけましょう。",
        ],
    },
    {
        "title": "Photo Story / 写真トーク",
        "steps": [
            "EN: Show a photo on your phone and tell a short story about it.",
            "JP: スマホの写真を1枚見せて、短いエピソードを話してください。",
        ],
    },
    {
        "title": "Teach Me a Phrase / 表現を教えて",
        "steps": [
            "EN: Teach a useful phrase or slang; everyone repeats it.",
            "JP: 便利な表現やスラングを教えて、全員で発音してみましょう。",
        ],
    },
    {
        "title": "Dream Trip Plan / 夢の旅行プラン",
        "steps": [
            "EN: Plan a 1-day trip together (where, what to eat, what to do).",
            "JP: みんなで1日旅行プランを作りましょう（場所・食事・やること）。",
        ],
    },
    {
        "title": "Mini Story Relay / 交互に物語",
        "steps": [
            "EN: Create a story, one sentence each. Alternate languages if possible.",
            "JP: 一人一文ずつで物語を作ります。できれば言語を交互に。",
        ],
    },
    {
        "title": "Question Jar / 質問トーク",
        "steps": [
            "EN: Each person asks one fun question; everyone answers briefly.",
            "JP: 一人ずつ面白い質問をして、みんなが短く答えます。",
        ],
    },
]


def default_task_index(date_str: str, round_no: int, table_no: str) -> int:
    seed = f"{date_str}|{round_no}|{table_no}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % len(TASKS)

