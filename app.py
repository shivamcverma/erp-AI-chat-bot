from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from rapidfuzz import fuzz
from dotenv import load_dotenv
import json
import os
import re
from spellchecker import SpellChecker
from datetime import datetime

def save_chat(question, response_source):

    log_file = "chat_logs.json"

    log = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "source": response_source
    }

    try:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(log)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print("Log Error:", e)
# ================= LOAD ENV =================
load_dotenv()

# ================= FLASK APP =================
app = Flask(__name__)

# ================= OPENROUTER CLIENT =================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ================= LOAD KNOWLEDGE BASE =================
with open("knowledge_hi.json", "r", encoding="utf-8") as f:
    knowledge_hi = json.load(f)

with open("knowledge_en.json", "r", encoding="utf-8") as f:
    knowledge_en = json.load(f)

# print("Loaded Intents:")
# for item in knowledge_hi:
#     print(item["intent"])
# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are an ERP Support Assistant for school and college management software.

CRITICAL RULES:
- ONLY answer based on the user's question
- DO NOT generate or add new steps under any condition
- DO NOT repeat or expand steps if they already exist
- If steps are provided in the context, use ONLY those steps as-is
- NEVER rewrite steps in a different form
- Keep answers short, clear, and practical

FORMAT RULES:
- If steps exist: return only step-by-step instructions
- If no steps exist: give a short simple explanation
- Do NOT mix explanation + steps unless explicitly required
- Do NOT add extra content like examples or extra guidance

LANGUAGE RULE:
- Reply in the same language as the user (Hindi or English)
- Do not translate unless explicitly asked

BEHAVIOR RULE:
- Strictly act like a static ERP help system
- Do not behave like a creative AI assistant
"""
COMMON_FIXES = {
    "vehical": "vehicle",
    "vehicals": "vehicles",
    "managment": "management",
    "admision": "admission",
    "attandance": "attendance",
    "attendence": "attendance",
    "libary": "library",
    "tranport": "transport",
    "studnt": "student",
    "feees": "fees"
}
spell = SpellChecker()
# ================= ERP KEYWORDS =================
ERP_KEYWORDS = [
    # Student
    "student", "students", "student management", "student profile",
    "student details", "student record", "new admission",
    "admission", "enrollment", "enroll student",

    # Fees
    "fees", "fee", "fee collection", "collect fees",
    "fee receipt", "receipt", "payment", "pending fees",
    "due fees", "fee structure", "installment",

    # Attendance
    "attendance", "student attendance", "staff attendance",
    "mark attendance", "daily attendance",

    # Academics
    "class", "section", "subject", "subjects",
    "timetable", "class routine", "period",
    "academic", "syllabus", "curriculum",

    # Exams
    "exam", "examination", "result", "marks",
    "marksheet", "grade", "grading", "report card",
    "promotion", "pass", "fail",

    # Teachers & Staff
    "teacher", "teachers", "staff", "employee",
    "faculty", "staff management", "salary",
    "payroll", "designation", "department",

    # Parents
    "parent", "guardian", "parent login",

    # Library
    "library", "book", "books", "add book",
    "manage books", "issue book", "return book",
    "library management", "book category",

    # Hostel
    "hostel", "hostel room", "room allotment",
    "hostel management",

    # Transport
    "transport", "vehicle", "bus", "route",
    "driver", "pickup point", "transport management",

    # Accounts
    "account", "accounts", "finance",
    "income", "expense", "ledger", "voucher",
    "cashbook", "transaction",

    # HR
    "hr", "human resource", "staff salary",
    "leave", "leave management", "employee record",

    # Certificates
    "certificate", "tc", "transfer certificate",
    "bonafide", "character certificate",

    # Reports
    "report", "reports", "export", "print",
    "analytics", "summary",

    # User & Login
    "login", "logout", "password", "reset password",
    "username", "user account", "role",
    "permission", "access control",

    # Dashboard
    "dashboard", "home page", "overview",

    # ID Card
    "id card", "student id", "staff id",

    # Communication
    "sms", "email", "notification",
    "announcement", "notice", "message",

    # Inventory
    "inventory", "stock", "item", "asset",

    # General ERP
    "erp", "school", "college",
    "school management", "college management",
    "management system","edit book category","edit book","delete book","add vehicle","edit vehicle","delete vehicle"
]

# ================= CLEAN FUNCTION =================
def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"[?,.]", "", text)
    text = text.replace("ki", "")
    text = text.replace("kaise", "")
    text = text.replace("kare", "")
    return text

def normalize(text):
    text = text.lower()
    noise_words = ["ki", "kaise", "kare", "karo", "please"]
    for w in noise_words:
        text = text.replace(w, "")
    return " ".join(text.split())

def fix_common_words(text):

    words = text.split()

    fixed = [
        COMMON_FIXES.get(word, word)
        for word in words
    ]

    return " ".join(fixed)


def correct_spelling(text):

    words = text.split()

    corrected = []

    for word in words:

        if len(word) <= 2:
            corrected.append(word)
            continue

        corrected_word = spell.correction(word)

        if corrected_word:
            corrected.append(corrected_word)
        else:
            corrected.append(word)

    return " ".join(corrected)

# ================= SMART LANGUAGE DETECTION =================
def detect_language(text):

    text = text.lower()

    hindi_words = [

        # Question words
        "kaise", "kese", "kaisy",
        "kya", "kya hai",
        "kab", "kahan", "kidhar",
        "kyun", "kyu", "kisliye",

        # Common action words
        "karna", "krna",
        "kare", "kre",
        "karu", "kru",
        "karna hai",
        "kar sakte",
        "kar sakta",
        "kar sakti",

        # Help words
        "batao", "bataye",
        "samjhao", "samjhaye",
        "dikhao", "dikhaye",
        "help", "madad",

        # Common ERP phrases
        "kaise kare",
        "kaise karen",
        "kaise karu",
        "kaise karna hai",

        "kaise add kare",
        "kaise edit kare",
        "kaise delete kare",
        "kaise update kare",

        "kaise banaye",
        "kaise banau",

        "kahan milega",
        "kahan hoga",

        "nahi ho raha",
        "nhi ho raha",
        "kam nahi kar raha",
        "work nahi kar raha",

        "problem aa rahi",
        "issue aa raha",
        "error aa raha",

        "step batao",
        "process batao",

        # Daily use words
        "mujhe",
        "mera",
        "meri",
        "mere",
        "hum",
        "ham",
        "hamara",

        "ye",
        "isko",
        "isse",
        "iska",

        "wo",
        "usko",
        "uska",

        "bhi",
        "abhi",
        "fir",
        "phir",

        "krke",
        "karke",

        "chahiye",
        "jarurat",
        "zarurat",

        "sakta",
        "sakti",
        "sakte",

        "btao",
        "btaye",
        "dikha do",
        "samjha do"
    ]

    for word in hindi_words:
        if word in text:
            return "hindi"

    hindi_chars = len(
        re.findall(r'[\u0900-\u097F]', text)
    )

    if hindi_chars > 0:
        return "hindi"

    return "english"

# ================= TRANSLATION =================
def translate_to_english(text):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Translate this ERP instruction into simple clear English step-by-step without adding extra information."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )
        return response.choices[0].message.content
    except:
        return text

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= CHAT API =================
@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "source": "error",
            "reply": "Please enter a message."
        })

    # ================= LANGUAGE DETECTION =================

    lang = detect_language(user_message)

    if lang == "english":
        knowledge_base = knowledge_en
    else:
        knowledge_base = knowledge_hi

    user_message_clean = normalize(user_message)
    user_message_clean = fix_common_words(
        user_message_clean
    )

    user_message_clean = correct_spelling(
        user_message_clean
    )

    # print("\nUSER:", user_message)
    # print("USER CLEAN:", user_message_clean)

    # =====================================================
    # 1. EXACT KEYWORD MATCH (Highest Priority)
    # =====================================================

# =====================================================
# 1. EXACT KEYWORD MATCH (Longest Keyword Priority)
# =====================================================

    best_exact_match = None
    best_exact_keyword = ""
    best_keyword_length = 0

    for item in knowledge_base:

        for kw in item.get("keywords", []):

            kw_clean = normalize(kw)

            if kw_clean and kw_clean in user_message_clean:

                if len(kw_clean) > best_keyword_length:

                    best_keyword_length = len(kw_clean)
                    best_exact_match = item
                    best_exact_keyword = kw_clean

    if best_exact_match:

        print("EXACT MATCH FOUND")
        print("INTENT:", best_exact_match.get("intent"))
        print("KEYWORD:", best_exact_keyword)
        save_chat(user_message, "exact_match")

        return jsonify({
            "source": "knowledge_base",
            "intent": best_exact_match.get("intent"),
            "answer": best_exact_match.get("answer"),
            "steps": best_exact_match.get("steps", []),
            "score": 100
        })

    # =====================================================
    # 2. FUZZY MATCHING
    # =====================================================
    # print("TOTAL INTENTS:", len(knowledge_base))

    # for item in knowledge_base:
    #     print(item["intent"])
    best_match = None
    best_score = 0

    for item in knowledge_base:

        item_best_score = 0

        for kw in item.get("keywords", []):

            kw_clean = normalize(kw)

            token_score = fuzz.token_set_ratio(
                user_message_clean,
                kw_clean
            )

            partial_score = fuzz.partial_ratio(
                user_message_clean,
                kw_clean
            )
            ratio_score = fuzz.ratio(
                user_message_clean,
                kw_clean
            )
            score = max(
                token_score,
                partial_score,
                ratio_score
            )

            if score > item_best_score:
                item_best_score = score

        print(
            f"Intent: {item.get('intent')} | Score: {item_best_score}"
        )

        if item_best_score > best_score:
            best_score = item_best_score
            best_match = item

    print("BEST SCORE:", best_score)
    print("BEST MATCH:", best_match)
    print(type(knowledge_base))
    print(knowledge_base)
    

    # =====================================================
    # 3. KNOWLEDGE BASE RESPONSE
    # =====================================================

    if best_match and best_score >= 75:
        save_chat(user_message, "knowledge_base")
        return jsonify({
            "source": "knowledge_base",
            "intent": best_match.get("intent"),
            "answer": best_match.get("answer"),
            "steps": best_match.get("steps", []),
            "score": best_score
        })

    # =====================================================
    # 4. ERP QUESTION DETECTION
    # =====================================================

    is_erp_question = any(
        fuzz.partial_ratio(
            user_message_clean,
            normalize(kw)
        ) >= 70
        for kw in ERP_KEYWORDS
    )
    save_chat(user_message, "restricted")

    if not is_erp_question:
        save_chat(user_message, "knowledge_base")
        return jsonify({
            "source": "restricted",
            "reply": "Main sirf ERP software related questions me help kar sakta hu."
        })

    # =====================================================
    # 5. AI FALLBACK
    # =====================================================

    try:

        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        reply = response.choices[0].message.content
        save_chat(user_message, "ai")
        return jsonify({
            "source": "ai",
            "reply": reply
        })

    except Exception as e:
        save_chat(user_message, "error")

        # print("AI ERROR:", str(e))

        return jsonify({
            "source": "error",
            "reply": "Hamari support team jald hi aapse connect karegi."
        })

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
