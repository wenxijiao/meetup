from __future__ import annotations

import random
from typing import Dict, List

import streamlit as st

from .registry import ActivityMeta, ACTIVITY_UNDERCOVER, register_activity
from .ui import register_participant_renderer


META = ActivityMeta(
    id=ACTIVITY_UNDERCOVER,
    title="Who is the Undercover? / 誰がウソつき？",
    description=(
        "EN: Everyone gets a word. One person gets a similar-but-different word. "
        "Describe your word without saying it; find the undercover.\n"
        "JP: 全員に単語が配られます。1人だけ似ているけど違う単語です。"
        "単語を言わずに説明して、ウソつきを見つけよう。"
    ),
)


# Similar-but-different word pairs for Undercover (common_word, undercover_word)
UNDERCOVER_WORD_PAIRS = [
    # Food / Drinks / 食べ物・飲み物
    ("Coffee / コーヒー", "Americano / アメリカーノ"),
    ("Tea / お茶", "Milk Tea / ミルクティー"),
    ("Sushi / 寿司", "Sashimi / 刺身"),
    ("Ramen / ラーメン", "Udon / うどん"),
    ("Pizza / ピザ", "Calzone / カルツォーネ"),
    ("Burger / ハンバーガー", "Sandwich / サンドイッチ"),
    ("Ice Cream / アイスクリーム", "Gelato / ジェラート"),
    ("Beer / ビール", "Highball / ハイボール"),

    # Daily habits / 日常の習慣
    ("Wake up early / 早起き", "Stay up late / 夜更かし"),
    ("Shower in the morning / 朝シャワー", "Shower at night / 夜シャワー"),
    ("Eat alone / 一人で食べる", "Eat together / みんなで食べる"),
    ("Listen to music / 音楽を聴く", "Listen to podcasts / ポッドキャストを聴く"),

    # Feelings / 状態
    ("Relaxing / リラックス", "Chill / まったり"),
    ("Lonely / 寂しい", "Quiet / 静か"),
    ("Excited / ワクワク", "Nervous / ドキドキ"),
    ("Tired / 疲れた", "Sleepy / 眠い"),

    # Scenes / 場面
    ("Rainy night / 雨の夜", "Cloudy evening / 曇りの夕方"),
    ("Empty café / 空いているカフェ", "Quiet library / 静かな図書館"),
    ("Late train / 終電", "Early train / 始発"),
    ("Small town / 小さな町", "Suburb / 郊外"),

    # Social / Modern life / 現代生活
    ("Text message / メッセージ", "Voice message / ボイスメッセージ"),
    ("Call / 電話", "Video call / ビデオ通話"),
    ("Instagram / インスタ", "Stories / ストーリー"),
    ("YouTube / YouTube", "Short videos / ショート動画"),

    # Personality / 性格
    ("Introvert / 内向的", "Shy / 人見知り"),
    ("Careful / 慎重", "Overthinking / 考えすぎ"),
    ("Spontaneous / 思いつき", "Impulsive / 衝動的"),
    ("Independent / 自立", "Lonely but fine / 一人でも平気"),

    # Slightly darker / ちょっと重め
    ("Overthinking at night / 夜に考えすぎる", "Suddenly sad at night / 夜に急に落ち込む"),
    ("Pretending to be fine / 大丈夫なふり", "Not explaining feelings / 気持ちを説明しない"),
    ("Missing someone / 誰かを思い出す", "Thinking about the past / 過去を考える"),

    # ☕ Coffee details
    ("Latte / ラテ", "Cappuccino / カプチーノ"),
    ("Black coffee / ブラックコーヒー", "No sugar coffee / 無糖コーヒー"),
    ("Fried chicken / フライドチキン", "Karaage / 唐揚げ"),
    ("Hot pot / 火鍋", "Shabu-shabu / しゃぶしゃぶ"),
    ("Street food / 屋台", "Food truck / フードトラック"),
    ("Convenience store / コンビニ", "Supermarket / スーパー"),

    # 🍺 Night life
    ("After work drink / 仕事後の一杯", "Weekend drink / 週末の一杯"),
    ("Last train / 終電", "Missed last train / 終電逃す"),
    ("Quiet bar / 静かなバー", "Crowded izakaya / 賑やかな居酒屋"),
    ("Beer garden / ビアガーデン", "Rooftop bar / ルーフトップバー"),

    # 🛋️ Lifestyle
    ("Stay home / 家にこもる", "Go out alone / 一人で外出"),
    ("Watching series / 一気見", "Watching clips / 切り抜き見る"),
    ("Cooking at home / 自炊", "Ordering delivery / デリバリー"),
    ("Clean room / きれいな部屋", "Messy but cozy / 散らかってるけど落ち着く"),

    # 🧠 Mindset
    ("Overthinking / 考えすぎ", "Being realistic / 現実的"),
    ("Low energy / 元気ない", "Calm mood / 落ち着いてる"),
    ("Motivated at night / 夜にやる気", "Motivated in morning / 朝にやる気"),
    ("Emotionally tired / 心が疲れた", "Physically tired / 体が疲れた"),

    # 📱 现代人日常（笑点密集）
    ("Scrolling endlessly / 無限スクロール", "Just checking one thing / ちょっと見るだけ"),
    ("Saved posts / 保存した投稿", "Liked but forgotten / いいねして忘れる"),
    ("Reply immediately / 即レス", "Reply later / 後で返す"),
    ("Seen but no reply / 既読スルー", "Forgot to reply / 返信忘れ"),

    # 🎮 娱乐 & 沉迷
    ("Casual game / カジュアルゲーム", "Addictive game / 中毒性あるゲーム"),
    ("Story game / ストーリー重視", "Multiplayer game / 対戦ゲーム"),
    ("Watching streams / 配信見る", "Watching highlights / 切り抜き見る"),

    # 🌃 场景感拉满
    ("Late night walk / 夜散歩", "Early morning walk / 朝散歩"),
    ("Rain after midnight / 深夜の雨", "Rain before dawn / 明け方の雨"),
    ("City lights / 夜景", "Street lights / 街灯"),
    ("Empty station / 無人駅", "Quiet platform / 静かなホーム"),

    # 😈 社交潜规则（非常好笑）
    ("Pretending to listen / 聞いてるふり", "Actually listening / ちゃんと聞いてる"),
    ("Nodding politely / とりあえずうなずく", "Asking follow-up / ちゃんと質問する"),
    ("Laughing politely / 愛想笑い", "Laughing too hard / 笑いすぎ"),
    ("Remembering names / 名前覚えてる", "Forgetting names / 名前忘れる"),

    # 📱 消息 & 社交地狱（核爆区）
    ("Reply immediately / 即レス", "Reply when free / 手が空いたら返す"),
    ("Seen but no reply / 既読スルー", "Read but forgot / 読んだけど忘れた"),
    ("Typing then stop / 入力中やめる", "Thinking what to say / 返事考えてる"),
    ("Short reply / 短文返信", "Emoji reply / スタンプ返信"),
    ("Reply with sticker / スタンプだけ", "Reply with haha / 笑だけ返す"),

    # 🕰️ 时间感 & 拖延症
    ("Do it later / あとでやる", "Do it tomorrow / 明日やる"),
    ("Almost on time / ほぼ時間通り", "Slightly late / ちょい遅れ"),
    ("Leaving now / 今出る", "Leaving soon / そろそろ出る"),
    ("Five more minutes / あと5分", "Just one more thing / もう一個だけ"),

    # 🧠 内心活动（开始精神裸奔）
    ("Overthinking replies / 返信考えすぎ", "Rewriting replies / 書き直しすぎ"),
    ("Pretending not to care / 気にしてないふり", "Actually caring a lot / めっちゃ気にする"),
    ("Want to say something / 言いたいことある", "Decide not to say / 言わない選択"),
    ("Waiting for reply / 返信待ってる", "Pretending not waiting / 待ってないふり"),

    # 😶 社交场面（全员共鸣）
    ("Listening quietly / 静かに聞く", "Thinking what to say / 次何言うか考える"),
    ("Nodding a lot / めっちゃうなずく", "Saying 'yeah' a lot / そうだね多用"),
    ("Laughing at wrong timing / 笑うタイミング間違える", "Laughing too late / 笑うの遅れる"),
    ("Joining late conversation / 話題途中参加", "Missing the context / 文脈わからん"),

    # 🛌 生活废度（真实到不行）
    ("Going to bed early / 早く寝るつもり", "Scrolling in bed / ベッドでスマホ"),
    ("Just resting / 休んでるだけ", "Doing nothing / 何もしてない"),
    ("Busy but unproductive / 忙しいけど何もしてない", "Free but tired / 暇だけど疲れてる"),
    ("Too lazy to cook / 作るのだるい", "Too lazy to order / 頼むのもだるい"),

    # 🫠 情绪灰区（非常危险但好笑）
    ("Feeling fine / 別に普通", "Not feeling bad / 悪くはない"),
    ("Kind of tired / なんか疲れた", "Mentally tired / 心が疲れた"),
    ("Need alone time / 一人になりたい", "Don't want to be lonely / 寂しくはなりたくない"),
    ("Want to disappear / 消えたい", "Want to sleep forever / 永遠に寝たい"),
]


def create_state(participant_ids: List[str], rng: random.Random) -> Dict:
    """
    Returns a dict state:
    - pair: {common: str, undercover: str}
    - undercover_id: str
    - assignments: {participant_id: word}
    """
    if not participant_ids:
        return {"pair": None, "undercover_id": None, "assignments": {}}

    common, undercover = rng.choice(UNDERCOVER_WORD_PAIRS)
    undercover_id = rng.choice(participant_ids)
    assignments = {}
    for pid in participant_ids:
        assignments[pid] = undercover if pid == undercover_id else common
    return {
        "pair": {"common": common, "undercover": undercover},
        "undercover_id": undercover_id,
        "assignments": assignments,
    }


class _UndercoverRenderer:
    def render_participant(
        self,
        *,
        state: Dict,
        participant_id: str,
        round_no: int,
        table_number: str,
        updated_by: str,
    ) -> None:
        my_word = (state.get("assignments") or {}).get(participant_id)
        if my_word:
            st.markdown(
                f"""
                <div class="word-card">
                    <div class="word-title">Your word / あなたの単語</div>
                    <div class="word-text">{my_word}</div>
                    <div class="hint">
                        EN: Describe your word without saying it. Vote for the undercover.<br/>
                        JP: 単語を言わずに説明しよう。ウソつきを投票で決めよう。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Waiting for your word... / 単語を準備中…（少し待って更新してください）")

        st.write("")
        col_a, _, _ = st.columns([0.42, 0.16, 0.42])
        with col_a:
            if st.button("単語変更 / New words", width="stretch"):
                # Local import to avoid circular import:
                # data.firebase_db imports activities.registry -> imports this module for registration.
                from data.firebase_db import regenerate_undercover_words  # noqa: WPS433

                regenerate_undercover_words(round_no, str(table_number), updated_by)
                st.rerun()


# Register activity + renderer
register_activity(META, create_state)
register_participant_renderer(ACTIVITY_UNDERCOVER, _UndercoverRenderer())

