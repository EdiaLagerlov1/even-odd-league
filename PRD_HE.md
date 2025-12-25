# מסמך דרישות מוצר - ליגת זוגי/אי-זוגי

## סקירה כללית

### מטרת המערכת
מערכת ליגת זוגי/אי-זוגי היא פלטפורמת תחרות רב-שחקנית שבה סוכני AI מתחרים במשחק הבחירה זוגי/אי-זוגי. המערכת מנהלת ליגה שלמה עם סבבים מרובים, משחקים מקבילים, וטבלת דירוג דינמית.

### עקרונות עיצוב מרכזיים
- **ארכיטקטורה מבוזרת**: כל רכיב (מנהל ליגה, שופטים, שחקנים) פועל כשירות עצמאי
- **תקשורת מבוססת הודעות**: כל האינטראקציות מתבצעות באמצעות פרוטוקול הודעות JSON-RPC 2.0
- **הרחבה קלה**: ניתן להוסיף שחקנים, שופטים ואסטרטגיות חדשות בקלות
- **שקיפות מלאה**: כל ההודעות נרשמות בקבצי JSONL למעקב ודיבאג

## ארכיטקטורת המערכת

### רכיבים עיקריים

#### 1. מנהל הליגה (League Manager)
**תיאור**: מתאם מרכזי המנהל את כל הליגה

**אחריות**:
- רישום שחקנים ושופטים
- יצירת לוח משחקים (round-robin)
- הקצאת משחקים לשופטים
- עדכון טבלת דירוג
- שידור עדכונים לכל המשתתפים
- זיהוי סיום סבבים והליגה

**נקודת קצה**: `http://localhost:8000/mcp`

**יכולות**:
```python
- register_player() - רישום שחקן חדש
- register_referee() - רישום שופט
- create_schedule() - יצירת לוח משחקים
- update_match_result() - עדכון תוצאות משחק
- get_standings() - קבלת טבלת דירוג
- broadcast_to_all() - שידור הודעות לכולם
```

#### 2. שופט (Referee)
**תיאור**: מנהל משחק בודד בין שני שחקנים

**אחריות**:
- קבלת הקצאות משחקים ממנהל הליגה
- הזמנת שחקנים למשחק
- בקשת בחירות מהשחקנים (זוגי/אי-זוגי)
- הגרלת מספר אקראי (1-100)
- קביעת מנצח לפי הכללים
- שליחת תוצאות למנהל הליגה
- טיפול בתקלות ו-timeout של שחקנים

**נקודות קצה**:
- `http://localhost:8001/mcp` (Referee Alpha)
- `http://localhost:8002/mcp` (Referee Beta)

**תהליך משחק**:
1. קבלת הקצאת משחק (MATCH_ASSIGNMENT)
2. שליחת הזמנות (GAME_INVITATION) לשני השחקנים
3. המתנה לאישורים (GAME_JOIN_ACK)
4. בקשת בחירות (CHOOSE_PARITY_CALL) במקביל משני השחקנים
5. הגרלת מספר אקראי
6. קביעת מנצח
7. שליחת תוצאות (GAME_OVER) לשחקנים
8. דיווח תוצאה (MATCH_RESULT_REPORT) למנהל הליגה

#### 3. שחקן (Player Agent)
**תיאור**: סוכן AI המשתתף במשחקים

**אחריות**:
- רישום בליגה
- קבלת הזמנות למשחקים
- ביצוע בחירות (זוגי/אי-זוגי) לפי אסטרטגיה
- עקבות אחר סטטיסטיקות אישיות
- שמירת היסטוריית משחקים

**נקודות קצה**:
- `http://localhost:8101/mcp` (Alice)
- `http://localhost:8102/mcp` (Bob)
- `http://localhost:8103/mcp` (Charlie)
- `http://localhost:8104/mcp` (Diana)

**אסטרטגיות זמינות**:
1. **random** - בחירה אקראית
2. **alternating** - החלפה בין זוגי לאי-זוגי
3. **history** - למידה מהיסטוריה (ניתוח מגמות)

**מבנה נתונים**:
```python
{
    "stats": {
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "total_games": 0
    },
    "game_history": [
        {
            "match_id": "...",
            "opponent": "player_id",
            "my_choice": "even/odd",
            "opponent_choice": "even/odd",
            "number": 42,
            "result": "win/loss/draw",
            "timestamp": "..."
        }
    ]
}
```

## פרוטוקול הודעות (league.v2)

### כללי
- כל ההודעות עוטפות ב-JSON-RPC 2.0
- כל הודעה מכילה: `protocol`, `message_type`, `sender`, `timestamp`, `conversation_id`
- אימות באמצעות `auth_token`

### הודעות רישום

#### LEAGUE_REGISTER_REQUEST
```json
{
  "jsonrpc": "2.0",
  "method": "register_player",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_REGISTER_REQUEST",
    "sender": "player:UNREGISTERED",
    "timestamp": "2025-01-15T10:00:00Z",
    "conversation_id": "conv-001",
    "player_meta": {
      "display_name": "Alice",
      "version": "1.0.0",
      "strategies": ["random"],
      "agent_endpoint": "http://localhost:8101/mcp"
    }
  },
  "id": 1
}
```

#### LEAGUE_REGISTER_RESPONSE
```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_REGISTER_RESPONSE",
    "sender": "league_manager",
    "timestamp": "2025-01-15T10:00:01Z",
    "conversation_id": "conv-001",
    "player_id": "player_abc123",
    "auth_token": "token_xyz789"
  },
  "id": 1
}
```

### הודעות משחק

#### GAME_INVITATION
```json
{
  "jsonrpc": "2.0",
  "method": "handle_game_invitation",
  "params": {
    "protocol": "league.v2",
    "message_type": "GAME_INVITATION",
    "sender": "referee:REF01",
    "timestamp": "2025-01-15T10:10:00Z",
    "conversation_id": "conv-match-001",
    "auth_token": "tok-ref01-abc",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "match_id": "M001",
    "game_type": "even_odd",
    "role_in_match": "PLAYER_A",
    "opponent_id": "player_def456"
  },
  "id": 1001
}
```

#### CHOOSE_PARITY_CALL
```json
{
  "jsonrpc": "2.0",
  "method": "choose_parity",
  "params": {
    "protocol": "league.v2",
    "message_type": "CHOOSE_PARITY_CALL",
    "sender": "referee:REF01",
    "timestamp": "2025-01-15T10:10:30Z",
    "conversation_id": "conv-match-001",
    "auth_token": "tok-ref01-abc",
    "match_id": "M001",
    "player_id": "player_abc123",
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
    "deadline": "2025-01-15T10:11:00Z"
  },
  "id": 1101
}
```

#### GAME_OVER
```json
{
  "jsonrpc": "2.0",
  "method": "notify_match_result",
  "params": {
    "protocol": "league.v2",
    "message_type": "GAME_OVER",
    "sender": "referee:REF01",
    "timestamp": "2025-01-15T10:15:30Z",
    "conversation_id": "conv-match-001",
    "auth_token": "tok-ref01-abc",
    "match_id": "M001",
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
  },
  "id": 1201
}
```

### הודעות ליגה

#### LEAGUE_STANDINGS_UPDATE
```json
{
  "jsonrpc": "2.0",
  "method": "update_standings",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_STANDINGS_UPDATE",
    "sender": "league_manager",
    "timestamp": "2025-01-15T10:20:00Z",
    "conversation_id": "conv-standings-001",
    "league_id": "league_2025_even_odd",
    "round_id": 1,
    "standings": [
      {
        "rank": 1,
        "player_id": "player_abc123",
        "display_name": "Alice",
        "played": 1,
        "wins": 1,
        "draws": 0,
        "losses": 0,
        "points": 3
      }
    ]
  },
  "id": 1401
}
```

#### LEAGUE_COMPLETED
```json
{
  "jsonrpc": "2.0",
  "method": "notify_league_completed",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_COMPLETED",
    "sender": "league_manager",
    "timestamp": "2025-01-15T12:00:00Z",
    "conversation_id": "conv-complete",
    "league_id": "league_2025_even_odd",
    "total_rounds": 3,
    "total_matches": 18,
    "champion": {
      "player_id": "player_abc123",
      "display_name": "Alice",
      "points": 7
    },
    "final_standings": [
      {
        "rank": 1,
        "player_id": "player_abc123",
        "points": 7
      }
    ]
  },
  "id": 2001
}
```

## כללי המשחק

### חוקי זוגי/אי-זוגי
1. שני שחקנים בוחרים בו-זמנית: "even" (זוגי) או "odd" (אי-זוגי)
2. השופט מגריל מספר אקראי בין 1-100
3. השחקן שבחר נכון את זוגיות המספר - מנצח
4. אם שני השחקנים בחרו אותה בחירה - תיקו

### דוגמאות
- מספר: 42 (זוגי), שחקן א' בחר "even", שחקן ב' בחר "odd" → שחקן א' מנצח
- מספר: 17 (אי-זוגי), שני השחקנים בחרו "odd" → תיקו
- מספר: 50 (זוגי), שני השחקנים בחרו "odd" → תיקו

### מערכת ניקוד
- **ניצחון**: 3 נקודות
- **תיקו**: 1 נקודה (לכל שחקן)
- **הפסד**: 0 נקודות

### קביעת דירוג
1. **נקודות** (עיקרי)
2. **ניצחונות** (שובר שוויון ראשון)
3. **תיקו** (שובר שוויון שני)

## תהליכי עבודה

### הפעלת הליגה

```bash
# 1. יצירת סביבה וירטואלית
uv venv
source .venv/bin/activate

# 2. התקנת תלויות
uv pip install -r requirements.txt

# 3. הפעלת השירותים
./start_league.sh

# 4. התחלת תחרות (3 סבבים)
curl -X POST "http://localhost:8000/start_league?rounds=3"

# 5. עצירת השירותים
./stop_league.sh
```

### זרימת משחק מלא

```
1. מנהל הליגה יוצר לוח משחקים
2. מנהל הליגה שולח MATCH_ASSIGNMENT לשופט
3. שופט שולח GAME_INVITATION לשני השחקנים
4. שחקנים מגיבים GAME_JOIN_ACK
5. שופט שולח CHOOSE_PARITY_CALL לשני השחקנים
6. שחקנים מגיבים CHOOSE_PARITY_RESPONSE
7. שופט מגריל מספר וקובע מנצח
8. שופט שולח GAME_OVER לשחקנים
9. שופט שולח MATCH_RESULT_REPORT למנהל
10. מנהל מעדכן דירוג ושולח LEAGUE_STANDINGS_UPDATE
11. אם סבב הסתיים: שולח ROUND_COMPLETED
12. אם ליגה הסתיימה: שולח LEAGUE_COMPLETED
```

## דרישות טכניות

### סביבת פיתוח
- **Python**: 3.13+
- **מנהל חבילות**: uv
- **מערכת הפעלה**: macOS / Linux / Windows

### תלויות עיקריות
```
fastapi >= 0.115.0    # מסגרת web
uvicorn >= 0.32.0     # שרת ASGI
pydantic >= 2.10.0    # ולידציה
httpx >= 0.28.0       # HTTP client async
requests >= 2.32.0    # HTTP client sync
```

### נקודות קצה HTTP
- **מנהל ליגה**: http://localhost:8000/mcp
- **שופטים**: http://localhost:8001-8002/mcp
- **שחקנים**: http://localhost:8101-8104/mcp

### קבצי לוג
כל ההודעות נשמרות בפורמט JSONL:
```
jsonl/
├── league_manager.jsonl
├── referee_8001.jsonl
├── referee_8002.jsonl
├── player_8101.jsonl (Alice)
├── player_8102.jsonl (Bob)
├── player_8103.jsonl (Charlie)
└── player_8104.jsonl (Diana)
```

## מבנה פרויקט

```
Even Odd League/
├── .venv/                      # סביבה וירטואלית
├── game/
│   ├── game_logic.py          # לוגיקת משחק
│   └── player_interaction.py  # אינטראקציות שחקן
├── models/
│   ├── league_models.py       # מודלים של ליגה
│   ├── referee_models.py      # מודלים של שופט
│   └── player_models.py       # מודלים של שחקן
├── utils/
│   ├── jsonrpc_utils.py       # עזרי JSON-RPC
│   ├── league_manager_core.py # ליבת מנהל ליגה
│   ├── league_endpoints.py    # נקודות קצה HTTP
│   ├── player_handlers.py     # מטפלי הודעות שחקן
│   └── referee_server_class.py # מחלקת שופט
├── league_manager.py          # שירות מנהל ליגה
├── referee_agent.py           # שירות שופט
├── player_agent.py            # שירות שחקן
├── requirements.txt           # תלויות Python
├── start_league.sh           # סקריפט הפעלה
├── stop_league.sh            # סקריפט עצירה
└── SETUP.md                   # הוראות התקנה
```

## אבטחה ואימות

### מנגנון אימות
- כל שירות מקבל `auth_token` בעת הרישום
- כל בקשה חייבת לכלול את ה-token
- מנהל הליגה מאמת tokens לפני עיבוד בקשות

### טיפול בשגיאות
- **Timeout**: שחקן שלא עונה תוך 30 שניות - הפסד טכני
- **Invalid choice**: בחירה לא חוקית - בקשה חוזרת (עד 3 ניסיונות)
- **Connection errors**: רישום אוטומטי של שגיאות בקבצי לוג

## יכולות עתידיות

### שלב 1
- [ ] תמיכה במשחקים מרובי סבבים (best of N)
- [ ] ממשק web לצפייה בזמן אמת
- [ ] Dashboard עם גרפים וסטטיסטיקות

### שלב 2
- [ ] תמיכה במשחקים נוספים (לא רק זוגי/אי-זוגי)
- [ ] מערכת דירוג ELO
- [ ] טורנירים עם עצי הדחה

### שלב 3
- [ ] פלטפורמת AI marketplace
- [ ] תחרויות אונליין
- [ ] API ציבורי למפתחים

## סיכום

מערכת ליגת זוגי/אי-זוגי היא פלטפורמה מודולרית וניתנת להרחבה להרצת תחרויות AI. הארכיטקטורה המבוזרת מאפשרת הוספת שחקנים ושופטים בקלות, בעוד פרוטוקול ההודעות המובנה מבטיח תקשורת אמינה ושקופה.

---

**גרסה**: 2.0
**תאריך עדכון אחרון**: 25 דצמבר 2025
**מחבר**: מערכת ליגת זוגי/אי-זוגי
