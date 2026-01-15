from __future__ import annotations

import random
from typing import Dict, List

import streamlit as st

from .registry import ActivityMeta, ACTIVITY_STORY_CHAIN, register_activity
from .ui import register_participant_renderer


META = ActivityMeta(
    id=ACTIVITY_STORY_CHAIN,
    title="物語リレー / Story Chain",
    description=(
        "EN: Tell the story out loud. The app only shows turns + remaining counts.\n"
        "JP: 実際に声で物語をつなげましょう。アプリは『順番』と『残り回数』だけを表示します。"
    ),
)

OPENING_PROMPTS = [
    {
        "jp": "電車の中で、全員が同じタイミングでスマホを見た。",
        "en": "On the train, everyone checked their phone at the exact same time.",
    },
    {
        "jp": "今日の日記には、まだ起きていない出来事が書かれていた。",
        "en": "Today’s diary described things that hadn’t happened yet.",
    },
    {
        "jp": "ドアをノックしたのは、今出かけたはずの自分だった。",
        "en": "The person knocking was me, who had just left.",
    },
    {
        "jp": "レストランで注文した料理は、名前を聞いたことがなかった。",
        "en": "The dish I ordered had a name I’d never heard before.",
    },
    {
        "jp": "グループチャットに、誰も追加していない人がいた。",
        "en": "There was someone in the group chat that no one added.",
    },
    {
        "jp": "夜中に届いたメッセージは、「まだ起きてる？」だけだった。",
        "en": "The message sent at midnight just said, “Are you still awake?”",
    },
    {
        "jp": "カレンダーには、覚えのない予定が入っていた。",
        "en": "There was an event on my calendar I didn’t remember adding.",
    },
    {
        "jp": "いつもの道なのに、今日は出口が見つからなかった。",
        "en": "It was my usual road, but today I couldn’t find the exit.",
    },
    {
        "jp": "エレベーターの中で、全員が階数ボタンを押さなかった。",
        "en": "In the elevator, no one pressed a floor button.",
    },
    {
        "jp": "コンビニの店員が、私の名前を呼んだ。",
        "en": "The convenience store clerk called me by my name.",
    },
    {
        "jp": "写真フォルダに、昨夜撮った覚えのない写真があった。",
        "en": "There was a photo in my gallery I didn’t remember taking last night.",
    },
    {
        "jp": "電気を消したはずの部屋が、まだ明るかった。",
        "en": "The room was still bright, even though I had turned the lights off.",
    },
    {
        "jp": "通知音が鳴ったが、画面には何も表示されなかった。",
        "en": "The notification sound rang, but nothing appeared on the screen.",
    },
    {
        "jp": "隣の席の人が、私と同じ独り言を言った。",
        "en": "The person next to me said the exact same thing I was thinking.",
    },
    {
        "jp": "目の前の人は、私の質問に先に答えた。",
        "en": "The person in front of me answered my question before I asked it.",
    },
    {
        "jp": "いつものカフェに、席が一つだけ空いていた。",
        "en": "At my usual café, there was exactly one empty seat.",
    },
    {
        "jp": "アラームが鳴ったが、今日は休日だった。",
        "en": "The alarm went off, but today was supposed to be a day off.",
    },
    {
        "jp": "誰もいないはずの部屋で、拍手が聞こえた。",
        "en": "I heard clapping in a room that should’ve been empty.",
    },
    {
        "jp": "メニューに載っていない選択肢を勧められた。",
        "en": "I was offered an option that wasn’t on the menu.",
    },
    {
        "jp": "今日が何曜日か、全員の答えが違った。",
        "en": "Everyone gave a different answer about what day it was.",
    },
    {
        "jp": "電車が止まった理由を、誰もアナウンスしなかった。",
        "en": "The train stopped, but no announcement was made.",
    },
    {
        "jp": "全員が同時にため息をついた。",
        "en": "Everyone sighed at the exact same time.",
    },
    {
        "jp": "知らない番号からの着信なのに、なぜか出てしまった。",
        "en": "It was an unknown number, but I answered anyway.",
    },
    {
        "jp": "スマホの予測変換が、私の考えを先に出してきた。",
        "en": "My phone’s auto-suggestion showed what I was thinking.",
    },
    {
        "jp": "エレベーターの中で、全員が目を合わせなかった。",
        "en": "Inside the elevator, no one made eye contact.",
    },
    {
        "jp": "今日だけは、信号がすべて赤だった。",
        "en": "Today, every traffic light was red.",
    },
    {
        "jp": "レストランで、私だけメニューを渡されなかった。",
        "en": "At the restaurant, I was the only one without a menu.",
    },
    {
        "jp": "写真を撮ったはずなのに、保存されていなかった。",
        "en": "I was sure I took a photo, but it wasn’t saved.",
    },
    {
        "jp": "イヤホンを外しても、音楽が止まらなかった。",
        "en": "The music didn’t stop even after I took my earphones off.",
    },
    {
        "jp": "誰かが私の名前を呼んだが、振り返ると誰もいなかった。",
        "en": "Someone called my name, but no one was there.",
    },
    {
        "jp": "時計を見た全員が、違う時間を言った。",
        "en": "Everyone said a different time when they checked the clock.",
    },
    {
        "jp": "メッセージを送った直後、後悔した。",
        "en": "I regretted the message immediately after sending it.",
    },
    {
        "jp": "いつも座る席に、今日は誰かが座っていた。",
        "en": "Someone was sitting in my usual seat today.",
    },
    {
        "jp": "店内BGMが、私の気分に合いすぎていた。",
        "en": "The background music matched my mood a little too well.",
    },
    {
        "jp": "カレンダーを見て、今日が今日じゃない気がした。",
        "en": "I checked the calendar and felt like today wasn’t really today.",
    },
    {
        "jp": "ドアを閉めたはずなのに、鍵がかかっていなかった。",
        "en": "I was sure I locked the door, but it wasn’t locked.",
    },
    {
        "jp": "全員が「あと5分」と言い続けていた。",
        "en": "Everyone kept saying, “Just five more minutes.”",
    },
    {
        "jp": "通知は来ているのに、開く勇気がなかった。",
        "en": "There was a notification, but I didn’t dare open it.",
    },
    {
        "jp": "今日の予定は、すべて予定通りに進みすぎていた。",
        "en": "Everything went exactly as planned today — too exactly.",
    },
    {
        "jp": "電気をつけた瞬間、誰かが咳払いをした。",
        "en": "The moment I turned on the light, someone cleared their throat.",
    },
    {
        "jp": "なぜか今日は、誰も急いでいなかった。",
        "en": "For some reason, no one seemed to be in a hurry today.",
    },
    {
        "jp": "グラスの水が、少しずつ減っていた。",
        "en": "The water in the glass was slowly decreasing.",
    },
    {
        "jp": "何もしていないのに、疲れていた。",
        "en": "I was tired even though I hadn’t done anything.",
    },
    {
        "jp": "全員が笑ったが、理由は誰も説明しなかった。",
        "en": "Everyone laughed, but no one explained why.",
    },
    {
        "jp": "帰り道なのに、知らない場所に出た。",
        "en": "I was heading home, but ended up somewhere unfamiliar.",
    },
]


def _pick_quota(rng: random.Random) -> int:
    # Prefer 2, sometimes 3
    return rng.choice([2, 2, 3])


def create_state(participant_ids: List[str], rng: random.Random) -> Dict:
    quota = {pid: _pick_quota(rng) for pid in participant_ids}
    remaining = dict(quota)
    prompt = rng.choice(OPENING_PROMPTS) if OPENING_PROMPTS else {"jp": "", "en": ""}
    return {
        "order": list(participant_ids),  # stable labels for the table
        "quota": quota,
        "remaining": remaining,
        "turn_idx": 0,
        "prompt": prompt,
        "done": False,
    }


class _StoryChainRenderer:
    def render_participant(
        self,
        *,
        state: Dict,
        participant_id: str,
        round_no: int,
        table_number: str,
        updated_by: str,
    ) -> None:
        remaining = (state.get("remaining") or {}).get(participant_id, 0)
        quota = (state.get("quota") or {}).get(participant_id, 0)
        done = bool(state.get("done"))
        order = state.get("order") or []
        turn_idx = int(state.get("turn_idx") or 0)
        current_turn_pid = order[turn_idx] if order and 0 <= turn_idx < len(order) else None
        prompt = state.get("prompt") or {}
        prompt_jp = str(prompt.get("jp", "")).strip()
        prompt_en = str(prompt.get("en", "")).strip()

        idx_map = {pid: i + 1 for i, pid in enumerate(order)}
        me_label = f"P{idx_map.get(participant_id, '?')}"
        turn_label = f"P{idx_map.get(current_turn_pid, '?')}" if current_turn_pid else "—"

        prompt_block = ""
        if prompt_jp:
            prompt_block += f"<div class='prompt-jp'>{prompt_jp}</div>"
        if prompt_en:
            prompt_block += f"<div class='prompt-en'>{prompt_en}</div>"

        st.markdown(
            f"""
            <div class="info-card">
              <div class="info-title">お題 / Opening</div>
              {prompt_block}
              <div class="stats-grid">
                <div class="stat">
                  <div class="stat-label">あなた / You</div>
                  <div class="stat-value">{me_label}</div>
                </div>
                <div class="stat">
                  <div class="stat-label">残り / Remaining</div>
                  <div class="stat-value">{remaining}/{quota}</div>
                </div>
                <div class="stat">
                  <div class="stat-label">現在 / Now</div>
                  <div class="stat-value">{turn_label}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if done:
            st.success("物語リレーは終了！ / Story chain finished!")
            st.caption("この後はみんなで『どんな話だったか』を軽くまとめて終わりましょう。 / Wrap up by summarizing together.")
            st.write("")
            if st.button("もう一回（リセット） / Restart", width="stretch"):
                # Local import to avoid circular import on module load
                from data.firebase_db import story_chain_restart  # noqa: WPS433

                story_chain_restart(round_no, str(table_number), updated_by)
                st.rerun()
            return

        is_my_turn = (participant_id == current_turn_pid) and (remaining > 0)
        if is_my_turn:
            st.subheader("あなたの番 / Your turn")
            st.markdown(
                "- JP: 前の人の内容を**短く復述**してから、**新しい展開を1つ**足しましょう。\n"
                "- EN: **Briefly recap** the previous part, then add **one new twist**."
            )
        else:
            st.subheader("待機 / Waiting")
            st.caption("順番が来たらボタンが押せます。 / You can press the button when it's your turn.")

        st.write("")
        if st.button(
            "完了（次の人へ） / I'm done → Next",
            width="stretch",
            disabled=not is_my_turn,
            type="primary",
        ):
            # Local import to avoid circular import on module load
            from data.firebase_db import story_chain_finish_turn  # noqa: WPS433

            story_chain_finish_turn(
                round_no=round_no,
                table_no=str(table_number),
                participant_id=participant_id,
                updated_by=updated_by,
            )
            st.rerun()


# Register activity + renderer
register_activity(META, create_state)
register_participant_renderer(ACTIVITY_STORY_CHAIN, _StoryChainRenderer())

