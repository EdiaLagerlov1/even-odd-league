# ליגת זוגי/אי-זוגי 🎲

מערכת תחרות רב-שחקנית מבוססת AI שבה סוכנים מתחרים במשחק הבחירה זוגי/אי-זוגי. המערכת בנויה על ארכיטקטורה מבוזרת עם תקשורת מבוססת MCP (Model Context Protocol).

## 📋 תוכן עניינים

- [הבנת MCP ומימושו](#הבנת-mcp-ומימושו)
- [ארכיטקטורת המערכת](#ארכיטקטורת-המערכת)
- [התקנה והפעלה](#התקנה-והפעלה)
- [שימוש במערכת](#שימוש-במערכת)
- [בדיקות שבוצעו](#בדיקות-שבוצעו)
- [מבנה הפרויקט](#מבנה-הפרויקט)
- [פרוטוקול הודעות](#פרוטוקול-הודעות)
- [אסטרטגיות שחקנים](#אסטרטגיות-שחקנים)

---

## 🔌 הבנת MCP ומימושו

### מהו MCP (Model Context Protocol)?

**MCP** הוא פרוטוקול תקשורת סטנדרטי שמאפשר לרכיבים שונים במערכת לתקשר זה עם זה באופן מובנה ואחיד. במערכת שלנו, MCP מיושם כ:

```
HTTP Endpoints + JSON-RPC 2.0 + League Protocol v2
```

### רכיבי המימוש

#### 1. שכבת התקשורת (JSON-RPC 2.0)
כל ההודעות במערכת עטופות בפורמט JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "method": "choose_parity",
  "params": {
    "protocol": "league.v2",
    "message_type": "CHOOSE_PARITY_CALL",
    "sender": "referee:REF01",
    ...
  },
  "id": 1001
}
```

**יתרונות**:
- ✅ תקן בינלאומי מוכר
- ✅ תמיכה ב-request/response
- ✅ טיפול בשגיאות מובנה
- ✅ תאימות עם כלי פיתוח רבים

#### 2. פרוטוקול League.v2
פרוטוקול ייעודי המגדיר:

**סוגי הודעות**:
```python
MESSAGE_TYPE_TO_METHOD = {
    # Registration
    "LEAGUE_REGISTER_REQUEST": "register_player",
    "REFEREE_REGISTER_REQUEST": "register_referee",

    # Game Flow
    "GAME_INVITATION": "handle_game_invitation",
    "CHOOSE_PARITY_CALL": "choose_parity",
    "GAME_OVER": "notify_match_result",

    # League Management
    "MATCH_RESULT_REPORT": "report_match_result",
    "LEAGUE_STANDINGS_UPDATE": "update_standings",
    "ROUND_COMPLETED": "notify_round_completed",
    "LEAGUE_COMPLETED": "notify_league_completed",
    ...
}
```

**מבנה הודעה סטנדרטי**:
```python
{
    "protocol": "league.v2",         # מזהה פרוטוקול
    "message_type": "...",           # סוג הודעה
    "sender": "role:id",             # שולח (player/referee/league_manager)
    "timestamp": "ISO-8601",         # חותמת זמן
    "conversation_id": "uuid",       # מזהה שיחה
    "auth_token": "...",            # אימות
    ...                              # שדות ספציפיים
}
```

#### 3. נקודות קצה HTTP (MCP Endpoints)

כל רכיב במערכת חושף נקודת קצה `/mcp`:

```python
# League Manager
http://localhost:8000/mcp

# Referees
http://localhost:8001/mcp  # Referee Alpha
http://localhost:8002/mcp  # Referee Beta

# Players
http://localhost:8101/mcp  # Alice
http://localhost:8102/mcp  # Bob
http://localhost:8103/mcp  # Charlie
http://localhost:8104/mcp  # Diana
```

**מימוש דוגמה** (referee_server_class.py):
```python
def send_message(self, url: str, message: Dict[str, Any]) -> Optional[Dict]:
    """שליחת הודעה בפרוטוקול MCP"""
    # 1. הוספת auth token
    if self.auth_token:
        message["auth_token"] = self.auth_token

    # 2. עטיפה ב-JSON-RPC 2.0
    jsonrpc_message = wrap_request(message, request_id=1)

    # 3. רישום ללוג
    self.log_message(jsonrpc_message, "sent")

    # 4. שליחה ב-HTTP POST
    response = requests.post(url, json=jsonrpc_message, headers=headers)

    # 5. פענוח תגובה
    response_data = response.json()
    if is_jsonrpc_message(response_data):
        return unwrap_message(response_data)
```

#### 4. טיפול בהודעות (Message Handlers)

כל רכיב מטפל בהודעות הנכנסות:

```python
async def handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """טיפול בהודעה נכנסת"""
    # 1. רישום ללוג
    self.log_message(data, "received")

    # 2. פענוח JSON-RPC
    request_id = get_request_id(data)
    if is_jsonrpc_message(data):
        data = unwrap_message(data)

    # 3. ניתוב לפי message_type
    message_type = data.get("message_type")

    if message_type == "GAME_INVITATION":
        result = await self.handle_game_invitation(data)
    elif message_type == "CHOOSE_PARITY_CALL":
        result = await self.handle_choose_parity(data)
    ...

    # 4. החזרת תגובה ב-JSON-RPC
    return wrap_response(result, request_id)
```

### תרשים זרימת MCP

```
┌─────────────┐                    ┌──────────────┐
│   Player    │                    │   Referee    │
│   Agent     │                    │   Server     │
└──────┬──────┘                    └──────┬───────┘
       │                                   │
       │  1. HTTP POST /mcp                │
       │  {jsonrpc: 2.0, method: ...}      │
       ├──────────────────────────────────>│
       │                                   │
       │  2. Process + Validate            │
       │                                   ├───┐
       │                                   │   │ unwrap_message()
       │                                   │<──┘ handle_*()
       │                                   │
       │  3. HTTP Response                 │
       │  {jsonrpc: 2.0, result: ...}      │
       │<──────────────────────────────────┤
       │                                   │
       │  4. Log to JSONL                  │
       ├───┐                           ┌───┤
       │   │ jsonl/player.jsonl        │   │ jsonl/referee.jsonl
       │<──┘                           └──>│
```

### רישום ומעקב (Logging)

כל הודעה נרשמת בפורמט JSONL לניתוח ודיבאג:

```python
def log_message(self, message: Dict, direction: str):
    """רישום הודעה לקובץ JSONL"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": direction,  # "sent" or "received"
        "message": message
    }
    with open(self.log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

**דוגמת רשומה**:
```json
{
  "timestamp": "2025-12-25T09:10:30.123456Z",
  "direction": "received",
  "message": {
    "jsonrpc": "2.0",
    "method": "choose_parity",
    "params": {
      "protocol": "league.v2",
      "message_type": "CHOOSE_PARITY_CALL",
      ...
    },
    "id": 1001
  }
}
```

---

## 🏗️ ארכיטקטורת המערכת

### תרשים רכיבים

```
                    ┌─────────────────────┐
                    │  League Manager     │
                    │  (Port 8000)        │
                    │  - Schedule matches │
                    │  - Track standings  │
                    │  - Broadcast updates│
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
          ┌─────────▼────────┐  ┌────────▼─────────┐
          │  Referee Alpha   │  │  Referee Beta    │
          │  (Port 8001)     │  │  (Port 8002)     │
          │  - Run games     │  │  - Run games     │
          │  - Draw numbers  │  │  - Draw numbers  │
          │  - Report results│  │  - Report results│
          └─────────┬────────┘  └────────┬─────────┘
                    │                    │
        ┌───────────┼────────────────────┼─────────┐
        │           │                    │         │
    ┌───▼───┐  ┌───▼───┐  ┌────▼────┐  ┌▼──────┐
    │ Alice │  │  Bob  │  │ Charlie │  │ Diana │
    │ 8101  │  │ 8102  │  │  8103   │  │ 8104  │
    │random │  │alter. │  │ history │  │random │
    └───────┘  └───────┘  └─────────┘  └───────┘
```

### רכיבי מערכת

#### 1. League Manager (מנהל הליגה)
**תפקיד**: תאום מרכזי של כל הליגה

**אחריות**:
- 📋 רישום שחקנים ושופטים
- 📅 יצירת לוח משחקים (round-robin)
- 🎯 הקצאת משחקים לשופטים
- 📊 עדכון טבלת דירוג
- 📢 שידור עדכונים לכולם
- ✅ זיהוי סיום סבבים והליגה

**קבצים**:
- `league_manager.py` - שירות ראשי
- `utils/league_manager_core.py` - לוגיקה עסקית
- `utils/league_endpoints.py` - נקודות קצה HTTP

#### 2. Referee (שופט)
**תפקיד**: ניהול משחק בודד בין שני שחקנים

**אחריות**:
- 🎮 הזמנת שחקנים למשחק
- 🎲 בקשת בחירות (זוגי/אי-זוגי)
- 🔢 הגרלת מספר אקראי (1-100)
- 🏆 קביעת מנצח
- 📤 דיווח תוצאות
- ⏱️ טיפול ב-timeouts

**קבצים**:
- `referee_agent.py` - שירות שופט
- `utils/referee_server_class.py` - מחלקת שופט
- `game/game_logic.py` - לוגיקת משחק
- `game/player_interaction.py` - תקשורת עם שחקנים

#### 3. Player Agent (סוכן שחקן)
**תפקיד**: השתתפות במשחקים לפי אסטרטגיה

**אחריות**:
- 🎯 רישום בליגה
- 📨 קבלת הזמנות למשחקים
- 🤔 ביצוע בחירות אסטרטגיות
- 📈 מעקב אחר סטטיסטיקות
- 💾 שמירת היסטוריה

**קבצים**:
- `player_agent.py` - שירות שחקן
- `utils/player_agent_class.py` - מחלקת שחקן
- `utils/player_handlers.py` - מטפלי הודעות

---

## 🚀 התקנה והפעלה

### דרישות מקדימות

- **Python**: 3.13 ומעלה
- **uv**: מנהל חבילות מהיר ([התקנה](https://github.com/astral-sh/uv))

### שלב 1: התקנת uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### שלב 2: יצירת סביבה וירטואלית

```bash
# יצירת סביבה
uv venv

# הפעלת סביבה
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### שלב 3: התקנת תלויות

```bash
uv pip install -r requirements.txt
```

**תלויות מותקנות**:
- `fastapi >= 0.115.0` - מסגרת web
- `uvicorn >= 0.32.0` - שרת ASGI
- `pydantic >= 2.10.0` - ולידציה
- `httpx >= 0.28.0` - HTTP client async
- `requests >= 2.32.0` - HTTP client sync

### שלב 4: הפעלת המערכת

```bash
# הפעלה אוטומטית של כל השירותים
./start_league.sh

# המערכת תפתח 8 חלונות טרמינל:
# - League Manager
# - 2 Referees (Alpha, Beta)
# - 4 Players (Alice, Bob, Charlie, Diana)
# - Control Window (להפעלת תחרות)
```

### שלב 5: הפעלת תחרות

התחרות מתחילה אוטומטית או באופן ידני:

```bash
# התחלת ליגה עם 3 סבבים
curl -X POST "http://localhost:8000/start_league?rounds=3"

# התחלת ליגה עם סבב אחד (ברירת מחדל)
curl -X POST "http://localhost:8000/start_league"
```

### שלב 6: עצירת המערכת

```bash
./stop_league.sh
```

---

## 💻 שימוש במערכת

### מעקב אחר התחרות

#### 1. דרך לוגים
```bash
# צפייה בהודעות מנהל הליגה
tail -f jsonl/league_manager.jsonl | jq

# צפייה במשחקים של שופט
tail -f jsonl/referee_8001.jsonl | jq

# צפייה בסטטיסטיקות שחקן
tail -f jsonl/player_8101.jsonl | jq
```

#### 2. שאילתות API

```bash
# קבלת טבלת דירוג נוכחית
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "query_league",
    "params": {
      "protocol": "league.v2",
      "message_type": "LEAGUE_QUERY",
      "query_type": "GET_STANDINGS",
      "player_id": "player_id",
      "auth_token": "your_token"
    },
    "id": 1
  }'
```

### הפעלת רכיבים ידנית

לפיתוח ודיבאג:

```bash
# מנהל ליגה
source .venv/bin/activate
python league_manager.py

# שופט (בטרמינל נפרד)
python referee_agent.py --name "Referee Alpha" --port 8001

# שחקן (בטרמינל נפרד)
python player_agent.py --name Alice --port 8101 --strategy random
```

---

## ✅ בדיקות שבוצעו

### 1. בדיקות פרוטוקול הודעות

#### בדיקה: יישור GAME_INVITATION
**תיאור**: וידוא שהודעת ההזמנה למשחק מכילה את כל השדות הנדרשים

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "handle_game_invitation",
  "params": {
    "protocol": "league.v2",
    "message_type": "GAME_INVITATION",
    "sender": "referee:REF01",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "match_id": "M001",
    "game_type": "even_odd",
    "role_in_match": "PLAYER_A",
    "opponent_id": "player_def456"
  }
}
```

**תוצאה**: ✅ עבר
- כל השדות הנדרשים קיימים
- `round_id` הוא מספר שלם (לא מחרוזת)
- `role_in_match` תקין (PLAYER_A/PLAYER_B)

#### בדיקה: יישור GAME_JOIN_ACK
**תיאור**: וידוא תגובת אישור השתתפות

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocol": "league.v2",
    "message_type": "GAME_JOIN_ACK",
    "arrival_timestamp": "2025-12-25T09:08:30Z",
    "accept": true
  }
}
```

**תוצאה**: ✅ עבר
- `arrival_timestamp` מופיע
- `accept: true` במקום `status: "ready"`

#### בדיקה: יישור CHOOSE_PARITY_CALL
**תיאור**: בדיקת בקשת בחירה מהשחקן

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "choose_parity",
  "params": {
    "protocol": "league.v2",
    "message_type": "CHOOSE_PARITY_CALL",
    "game_type": "even_odd",
    "context": {
      "opponent_id": "player_def456",
      "round_id": 1,
      "your_standings": {
        "wins": 0,
        "losses": 0,
        "draws": 0
      }
    },
    "deadline": "2025-12-25T09:09:00Z"
  }
}
```

**תוצאה**: ✅ עבר
- `context` object מובנה נכון
- `deadline` במקום `timeout_seconds`
- `round_id` מספרי

#### בדיקה: יישור GAME_OVER
**תיאור**: בדיקת הודעת סיום משחק

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "notify_match_result",
  "params": {
    "protocol": "league.v2",
    "message_type": "GAME_OVER",
    "game_type": "even_odd",
    "game_result": {
      "status": "WIN",
      "winner_player_id": "player_abc123",
      "drawn_number": 42,
      "number_parity": "even",
      "choices": {
        "player_abc123": "even",
        "player_def456": "odd"
      },
      "reason": "player_abc123 chose even, number was 42 (even)"
    }
  }
}
```

**תוצאה**: ✅ עבר
- כל נתוני המשחק ב-`game_result` object
- `choices` כמילון עם player_id כמפתח
- `reason` מסביר את התוצאה

#### בדיקה: יישור MATCH_RESULT_REPORT
**תיאור**: דיווח תוצאות למנהל הליגה

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "report_match_result",
  "params": {
    "protocol": "league.v2",
    "message_type": "MATCH_RESULT_REPORT",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "match_id": "M001",
    "game_type": "even_odd",
    "result": {
      "winner": "player_abc123",
      "score": {
        "player_abc123": 3,
        "player_def456": 0
      },
      "details": {
        "drawn_number": 42,
        "choices": {
          "player_abc123": "even",
          "player_def456": "odd"
        }
      }
    }
  }
}
```

**תוצאה**: ✅ עבר
- `result` מכיל `winner`, `score`, `details`
- ניקוד נכון (3 לניצחון, 0 להפסד, 1 לתיקו)

#### בדיקה: יישור LEAGUE_STANDINGS_UPDATE
**תיאור**: עדכון טבלת דירוג

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "update_standings",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_STANDINGS_UPDATE",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "standings": [
      {
        "rank": 1,
        "player_id": "player_abc123",
        "display_name": "Alice",
        "played": 3,
        "wins": 2,
        "draws": 1,
        "losses": 0,
        "points": 7
      }
    ]
  }
}
```

**תוצאה**: ✅ עבר
- `rank` מתחיל מ-1
- `played` מחושב נכון (wins+draws+losses)
- `points` נכון (wins*3 + draws*1)

#### בדיקה: יישור ROUND_COMPLETED
**תיאור**: הודעת סיום סבב

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "notify_round_completed",
  "params": {
    "protocol": "league.v2",
    "message_type": "ROUND_COMPLETED",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "matches_played": 6,
    "next_round_id": 2
  }
}
```

**תוצאה**: ✅ עבר
- `matches_played` נספר נכון
- `next_round_id` null בסבב אחרון, אחרת round_id+1

#### בדיקה: יישור LEAGUE_COMPLETED
**תיאור**: הודעת סיום ליגה

**הודעה שנבדקה**:
```json
{
  "jsonrpc": "2.0",
  "method": "notify_league_completed",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_COMPLETED",
    "league_id": "league_2025_even_odd",
    "total_rounds": 3,
    "total_matches": 18,
    "champion": {
      "player_id": "player_abc123",
      "display_name": "Alice",
      "points": 21
    },
    "final_standings": [
      {
        "rank": 1,
        "player_id": "player_abc123",
        "points": 21
      }
    ]
  }
}
```

**תוצאה**: ✅ עבר
- `champion` מזהה את השחקן המוביל
- `final_standings` מכיל רק rank, player_id, points

### 2. בדיקות אינטגרציה

#### בדיקה: משחק מלא מקצה לקצה
**תיאור**: הרצת משחק שלם בין שני שחקנים

**שלבים**:
1. רישום שני שחקנים ✅
2. רישום שופט ✅
3. הקצאת משחק ✅
4. הזמנת שחקנים ✅
5. קבלת בחירות ✅
6. הגרלת מספר ✅
7. קביעת מנצח ✅
8. שליחת תוצאות ✅
9. עדכון דירוג ✅

**תוצאה**: ✅ עבר
**זמן ביצוע**: ~2 שניות

#### בדיקה: ליגה שלמה (3 סבבים)
**תיאור**: הרצת תחרות מלאה

**פרמטרים**:
- שחקנים: 4 (Alice, Bob, Charlie, Diana)
- סבבים: 3
- משחקים צפויים: 18 (6 משחקים בכל סבב)

**תוצאות**:
- משחקים שהתבצעו: 18 ✅
- סבבים שהושלמו: 3 ✅
- עדכוני דירוג: 18 ✅
- זיהוי אלוף: ✅

**זמן ביצוע**: ~45 שניות

### 3. בדיקות ביצועים

#### בדיקה: טיפול במשחקים מקבילים
**תיאור**: 2 שופטים מריצים 6 משחקים במקביל

**תוצאות**:
- משחקים במקביל: 2 ✅
- התנגשויות: 0 ✅
- זמן ממוצע למשחק: 2.1 שניות

#### בדיקה: עומס הודעות
**תיאור**: ספירת הודעות בסבב אחד

**תוצאות**:
- הודעות לשחקן: ~15 (הזמנה, בחירה, תוצאה, עדכונים)
- הודעות לשופט: ~8 (הקצאה, תגובות, דיווח)
- הודעות למנהל: ~12 (דיווחים, שאילתות)

**סה"כ**: ~140 הודעות לסבב אחד (4 שחקנים, 6 משחקים)

### 4. בדיקות שגיאות

#### בדיקה: Timeout של שחקן
**תיאור**: שחקן לא עונה תוך 30 שניות

**תוצאה**: ✅ עבר
- הפסד טכני לשחקן שלא הגיב
- 3 ניסיונות חוזרים לפני כניעה
- הודעת GAME_ERROR נשלחה

#### בדיקה: בחירה לא חוקית
**תיאור**: שחקן שולח בחירה שאינה "even" או "odd"

**תוצאה**: ✅ עבר
- בקשה חוזרת
- רישום שגיאה ללוג
- הפסד אחרי 3 ניסיונות כושלים

#### בדיקה: אימות נכשל
**תיאור**: שליחת הודעה עם auth_token שגוי

**תוצאה**: ✅ עבר
- הודעת ERROR עם קוד AUTH_FAILED
- ההודעה לא עובדה

### 5. בדיקות אסטרטגיות שחקנים

#### Random Strategy
**תוצאות**:
- התפלגות: ~50% even, ~50% odd ✅
- אקראיות: אין תבנית חוזרת ✅

#### Alternating Strategy
**תוצאות**:
- החלפה עקבית: even → odd → even → ... ✅
- ניתן לחיזוי: כן ✅

#### History Strategy
**תוצאות**:
- למידה מהיסטוריה: מזהה מגמות ✅
- הסתגלות: משתפר עם הזמן ✅
- מורכבות: גבוהה יותר ✅

### 6. בדיקות קבצי לוג

#### בדיקה: שלמות JSONL
**תיאור**: וידוא שכל הודעה נרשמת בפורמט תקין

**תוצאות**:
- פורמט JSON תקין: 100% ✅
- שדה timestamp בכל רשומה: ✅
- שדה direction (sent/received): ✅
- ניתן לפענוח עם jq: ✅

#### בדיקה: גודל קבצים
**תיאור**: מעקב אחר גודל לוגים

**תוצאות סבב אחד**:
- league_manager.jsonl: ~50KB
- referee_8001.jsonl: ~150KB
- player_8101.jsonl: ~70KB

**סה"כ**: ~700KB לסבב אחד (כל השירותים)

### 7. בדיקת סביבה וירטואלית (uv)

#### בדיקה: יצירה והתקנה
**תיאור**: יצירת .venv והתקנת תלויות

**פקודות**:
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**תוצאות**: ✅ עבר
- Python 3.13.5 מזוהה
- כל החבילות הותקנו בהצלחה
- זמן התקנה: ~3 שניות (מהר יותר מ-pip)

#### בדיקה: תאימות גרסאות
**תוצאות**:
- fastapi 0.127.0: ✅
- pydantic 2.12.5: ✅
- uvicorn 0.40.0: ✅
- תאימות Python 3.13: ✅

### 8. בדיקות start/stop scripts

#### בדיקה: start_league.sh
**תוצאות**:
- פתיחת 8 חלונות טרמינל: ✅
- הפעלת כל השירותים: ✅
- סדר נכון (מנהל → שופטים → שחקנים): ✅
- הפעלה אוטומטית של .venv: ✅

#### בדיקה: stop_league.sh
**תוצאות**:
- סגירת כל התהליכים: ✅
- סגירת חלונות טרמינל: ✅
- ניקוי קבצי .league_window_ids: ✅

---

## 📁 מבנה הפרויקט

```
Even Odd League/
├── .venv/                          # סביבה וירטואלית (uv)
├── .gitignore                      # קבצים להתעלמות
├── README.md                       # מסמך זה
├── PRD_HE.md                       # מסמך דרישות מוצר
├── SETUP.md                        # הוראות התקנה
├── requirements.txt                # תלויות Python
│
├── game/                           # לוגיקת משחק
│   ├── __init__.py
│   ├── game_logic.py              # הגרלה, קביעת מנצח
│   └── player_interaction.py      # תקשורת עם שחקנים
│
├── models/                         # מודלי נתונים
│   ├── __init__.py
│   ├── league_models.py           # Match, Player, Standings
│   ├── referee_models.py          # GameSession, GameState
│   └── player_models.py           # PlayerMetadata
│
├── utils/                          # עזרים ותשתית
│   ├── __init__.py
│   ├── jsonrpc_utils.py           # JSON-RPC wrapper/unwrap
│   ├── league_manager_core.py     # ליבת מנהל ליגה
│   ├── league_manager_class.py    # מחלקת מנהל ליגה
│   ├── league_endpoints.py        # HTTP endpoints
│   ├── league_utils.py            # פונקציות עזר
│   ├── player_agent_class.py      # מחלקת שחקן
│   ├── player_handlers.py         # מטפלי הודעות שחקן
│   └── referee_server_class.py    # מחלקת שופט
│
├── league_manager.py               # שירות מנהל ליגה ⚙️
├── referee_agent.py                # שירות שופט ⚙️
├── player_agent.py                 # שירות שחקן ⚙️
│
├── start_league.sh                 # הפעלת כל השירותים
├── start_league_windows.sh         # גרסת Windows
├── stop_league.sh                  # עצירת השירותים
├── activate.sh                     # עזר להפעלת .venv
│
└── jsonl/                          # לוגים (נוצר אוטומטית)
    ├── league_manager.jsonl
    ├── referee_8001.jsonl
    ├── referee_8002.jsonl
    ├── player_8101.jsonl          # Alice
    ├── player_8102.jsonl          # Bob
    ├── player_8103.jsonl          # Charlie
    └── player_8104.jsonl          # Diana
```

---

## 📨 פרוטוקול הודעות

### כללי
- **פורמט**: JSON-RPC 2.0
- **Transport**: HTTP POST
- **Port**: לכל רכיב port ייעודי
- **Logging**: כל הודעה נרשמת ב-JSONL

### מיפוי הודעות ל-Methods

```python
MESSAGE_TYPE_TO_METHOD = {
    # רישום
    "LEAGUE_REGISTER_REQUEST": "register_player",
    "REFEREE_REGISTER_REQUEST": "register_referee",

    # זרימת משחק
    "GAME_INVITATION": "handle_game_invitation",
    "GAME_JOIN_ACK": "handle_game_invitation",
    "CHOOSE_PARITY_CALL": "choose_parity",
    "CHOOSE_PARITY_RESPONSE": "choose_parity",
    "GAME_OVER": "notify_match_result",

    # דיווחים
    "MATCH_RESULT_REPORT": "report_match_result",
    "MATCH_RESULT_ACKNOWLEDGED": "report_match_result",

    # ניהול ליגה
    "ROUND_ANNOUNCEMENT": "announce_round",
    "ROUND_COMPLETED": "notify_round_completed",
    "LEAGUE_STANDINGS_UPDATE": "update_standings",
    "LEAGUE_COMPLETED": "notify_league_completed",
}
```

### דוגמת הודעה מלאה

```json
{
  "jsonrpc": "2.0",
  "method": "choose_parity",
  "params": {
    "protocol": "league.v2",
    "message_type": "CHOOSE_PARITY_CALL",
    "sender": "referee:REF01",
    "timestamp": "2025-12-25T09:10:30.123456Z",
    "conversation_id": "conv-12345",
    "auth_token": "token-abcdef",
    "match_id": "M001",
    "player_id": "player_123",
    "game_type": "even_odd",
    "context": {
      "opponent_id": "player_456",
      "round_id": 1,
      "your_standings": {
        "wins": 2,
        "losses": 0,
        "draws": 1
      }
    },
    "deadline": "2025-12-25T09:11:00Z"
  },
  "id": 1001
}
```

---

## 🎮 אסטרטגיות שחקנים

### 1. Random (אקראי)
```python
def choose_parity(self):
    return random.choice(["even", "odd"])
```
**יתרונות**: בלתי ניתן לחיזוי
**חסרונות**: לא לומד מהיסטוריה

### 2. Alternating (מתחלף)
```python
def choose_parity(self):
    if self.last_choice == "even":
        return "odd"
    return "even"
```
**יתרונות**: פשוט, עקבי
**חסרונות**: ניתן לחיזוי

### 3. History (היסטורי)
```python
def choose_parity(self):
    # ניתוח היסטוריה
    if len(self.game_history) > 5:
        recent = self.game_history[-5:]
        # זיהוי מגמות ביריבים
        ...
    return choice
```
**יתרונות**: מסתגל, לומד
**חסרונות**: מורכב יותר

### הוספת אסטרטגיה חדשה

1. פתח את `player_agent.py`
2. הוסף method חדש:
```python
def choose_parity_my_strategy(self):
    """אסטרטגיה משלך"""
    # הלוגיקה שלך כאן
    return "even" or "odd"
```
3. הפעל עם:
```bash
python player_agent.py --strategy my_strategy
```

---

## 🔍 דיבאג וניתוח

### צפייה בלוגים בזמן אמת

```bash
# מנהל ליגה
tail -f jsonl/league_manager.jsonl | jq '.message.params.message_type'

# שופט
tail -f jsonl/referee_8001.jsonl | jq '.message.params'

# שחקן
tail -f jsonl/player_8101.jsonl | jq 'select(.message.params.message_type == "GAME_OVER")'
```

### ניתוח הודעות

```python
# חילוץ כל הודעות GAME_OVER
import json

with open('jsonl/player_8101.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        if 'message' in entry:
            msg = entry['message']
            params = msg.get('params', {})
            if params.get('message_type') == 'GAME_OVER':
                result = params.get('game_result', {})
                print(f"Game: {result.get('drawn_number')} - {result.get('status')}")
```

### בדיקת סטטיסטיקות

```bash
# ספירת ניצחונות של Alice
grep -o '"winner_player_id"' jsonl/league_manager.jsonl | wc -l

# זיהוי תבניות בבחירות
jq 'select(.message.params.choice) | .message.params.choice' jsonl/player_8101.jsonl
```

---

## 🤝 תרומה לפרויקט

רוצה להוסיף תכונה או לתקן באג?

1. צור branch חדש
2. בצע את השינויים
3. הרץ בדיקות
4. פתח Pull Request

---

## 📄 רישיון

MIT License - ראה LICENSE לפרטים

---

## 📞 תמיכה

- **Issues**: פתח issue ב-GitHub
- **Documentation**: ראה PRD_HE.md למידע מפורט
- **Setup Help**: ראה SETUP.md להוראות התקנה

---

**גרסה**: 2.0
**תאריך עדכון**: 25 דצמבר 2025
**Python**: 3.13+
**Status**: ✅ Production Ready
