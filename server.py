import os
import random
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 全域統計數據 (任務三)
stats = {
    "total_games": 0,
    "wins": 0
}

# 記憶體資料庫
games_db: Dict[str, dict] = {}


class NewGameRequest(BaseModel):
    hard_mode: bool = False


class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.get("/api/stats")
def get_stats():
    """ 取得統計數據 """
    return stats


@app.post("/api/new-game")
def start_new_game(req: Optional[NewGameRequest] = None):
    """ 建立新一局遊戲，支援硬核模式參數 (任務四) """
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    hard_mode = req.hard_mode if req else False

    # 記錄一局遊戲開始
    stats["total_games"] += 1

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": hard_mode,
        "revealed_green": {}  # 紀錄先前已確認為綠色 (Correct) 的位置與字母 {index: char}
    }
    
    win_rate = (stats["wins"] / stats["total_games"] * 100) if stats["total_games"] > 0 else 0
    return {
        "game_id": game_id,
        "message": "New game started!",
        "stats": {
            "total_games": stats["total_games"],
            "wins": stats["wins"],
            "win_rate": round(win_rate, 2)
        }
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 接收玩家猜測，進行字庫檢查、硬核模式驗證與勝負判定 """
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game_state = games_db[game_id]

    if game_state["status"] != "PLAYING":
        raise HTTPException(status_code=400, detail="Game already ended.")

    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：單字合法性檢查
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    # 任務四：硬核模式驗證
    if game_state["hard_mode"]:
        for idx, char in game_state["revealed_green"].items():
            if guess[idx] != char:
                raise HTTPException(
                    status_code=400,
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    target = game_state["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 標記綠色 correct 並記錄於 revealed_green
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            game_state["revealed_green"][i] = guess[i]

    # 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    game_state["attempts"] += 1
    is_correct = (guess == target)
    
    if is_correct:
        game_state["status"] = "WON"
        stats["wins"] += 1
    elif game_state["attempts"] >= 6:
        game_state["status"] = "LOST"

    # 計算當前勝率
    win_rate = (stats["wins"] / stats["total_games"] * 100) if stats["total_games"] > 0 else 0

    # 任務一：當第 6 次猜錯（遊戲結束）時，回傳正確答案 target_word
    revealed_target = target if (is_correct or game_state["attempts"] >= 6) else None

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": revealed_target,
        "attempts": game_state["attempts"],
        "stats": {
            "total_games": stats["total_games"],
            "wins": stats["wins"],
            "win_rate": round(win_rate, 2)
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)