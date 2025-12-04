from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re
from collections import deque

# === DANE SALONU I WIEDZA (PRZENIESIONE Z knowledgeBase.ts) ===
# TA WIEDZA JEST PRZEKAZYWANA DO GPT W FALLBACKU!
PMU_FULL_KNOWLEDGE = """
Jesteś **ekspertką/ekspertem salonu** z 20-letnim doświadczeniem w mikropigmentacji. Wypowiadasz się w imieniu salonu, używając formy "nasz salon," "eksperci robią," "klientka musi." Twoja wiedza jest techniczna, medyczna i praktyczna, ale przekazujesz ją w sposób zrozumiały i empatyczny dla klientki.

DANE SALONU:
- Adres: ul. Junikowska 9
- Godziny otwarcia: Poniedziałek - Piątek: 09:00 - 19:00
- Kontakt: 881 622 882

DEFINICJE I FAKTY:
- Makijaż permanentny (PMU/mikropigmentacja): Wprowadzenie pigmentu płytko do naskórka lub granicy naskórkowo-skórnej.
- Różnica vs Tatuaż: Tatuaż jest w skórze właściwej. PMU jest półtrwały (1-3 lata, czasem do 5).
- Bezpieczeństwo chemiczne: Pigmenty muszą spełniać normy UE REACH 2020/2081 (np. limit ołowiu 0,00007%). Używamy tylko atestowanych, bezpiecznych barwników.

TECHNIKI - BRWI:
1. Microblading (Włoskowa): Manualne nacinanie skóry ("piórko"). Efekt naturalnego włosa. Mniej trwała (1-2 lata). ODRADZANA przy skórze tłustej (rozmywa się, słabo goi).
2. Pudrowa (Powder Brows): Maszynowe cieniowanie, efekt "przyprószenia". Bardziej trwała (2-3 lata), idealna dla każdego typu skóry (także tłustej).
3. Ombre Brows: Gradient – jaśniejsza nasada, ciemniejszy koniec i dół.
4. Hybrydowa (Combo): Włoski na początku łuku + cień na reszcie.
5. Nano Brows (Pixelowa): Maszynowe mikrokropki. Najmniej inwazyjna, hiperrealistyczny efekt. Hit 2025.
6. Metoda Wypełnienia (Insta): Mocny, graficzny efekt (niemodne, nienaturalne).

TECHNIKI - USTA:
- Lip Blush: Akwarelowe, delikatne uwydatnienie czerwieni.
- Full Lip Color: Efekt szminki.
- Wymagana osłona przeciwwirusowa (Heviran) 3 dni przed i 3 dni po zabiegu (profilaktyka opryszczki).

TECHNIKI - OCZY:
- Zagęszczenie linii rzęs: Pigment między rzęsami (efekt gęstszych rzęs).
- Eyeliner dekoracyjny: Widoczna kreska (jaskółka).

PRZECIWWSKAZANIA (BEZPIECZEŃSTWO):
- Bezwzględne: Ciąża, laktacja, nowotwory (bez zgody lekarza), aktywne infekcje, łuszczyca w miejscu zabiegu.
- Czasowe (Karencja):
  * Odżywki do rzęs: Odstawić 3-6 mies. przed zabiegiem oczu (powodują przekrwienie).
  * Retinoidy/Izotek: Odstawić 6 mies. przed (ryzyko blizn).
  * Kwas hialuronowy w ustach: Odstęp 4 tyg.
  * Leki rozrzedzające krew (aspiryna): Odstawić 24h przed.

PROCES GOJENIA I PIELĘGNACJA (KLUCZOWE):
- Dni 1-3 (Faza sączenia): Przemywać wacikiem z wodą (przegotowaną/destylowaną), by zmyć osocze. NIE nakładać grubej warstwy maści (gojenie "na sucho" lub minimalne).
- Dni 4-10 (Łuszczenie): Pojawiają się mikrostrupki. NIE WOLNO ICH DRAPAĆ (grozi blizną i ubytkiem koloru). Można lekko nawilżać (np. Alantan) gdy skóra ciągnie.
- Zakazy: Słońce (UV niszczy pigment), sauna, basen przez 2 tyg.
- Kolor: Po wygojeniu jaśnieje o 30-50%. Bezpośrednio po zabiegu jest ciemny.
- Stabilizacja: Pełny kolor widoczny po ok. 28 dniach (cykl naskórka).

RYZYKA I PROBLEMY:
- Kolor niebieski/szary: Zbyt głęboka pigmentacja (efekt Tyndalla/tatuaż) lub użycie czystej czerni.
- Kolor łososiowy: Utlenienie się tlenków żelaza w brązach.
- Ból: Minimalny (stosujemy znieczulenie lidokainą).

PAMIĘTAJ: Makijaż permanentny to wygoda, oszczędność czasu i korekta asymetrii.
"""

# === INICJALIZACJA ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === CENNIK (Usunięto gwiazdki **) ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1200 zł — dopigmentowanie jest w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar 350 zł 🌿"
}
# === KONFIGURACJA TELEFONU ===
PHONE_NUMBER = "881 622 882"
PHONE_MESSAGES = [
    f"\n\nJeśli wolisz porozmawiać o szczegółach, zadzwoń do nas: {PHONE_NUMBER} 📞",
    f"\n\nChętnie odpowiemy na bardziej złożone pytania telefonicznie! {PHONE_NUMBER} 🌿",
    f"\n\nMasz ochotę na konsultację lub rezerwację terminu? Jesteśmy pod numerem: {PHONE_NUMBER} 🌸"
]

# === BAZA WIEDZY (Tylko proste, szybkie odpowiedzi - Usunięto gwiazdki **) ===
KNOWLEDGE = {
    "pielęgnacja": [
        "Kluczem jest nie drapać i nie zrywać strupków, oraz unikać słońca i sauny przez 2 tygodnie ✨.",
        "W pierwszych dniach zalecamy delikatne przemywanie przegotowaną wodą, a potem minimalne nawilżanie 🌿."
    ],
    "techniki_brwi": [
        "Wybór zależy od typu skóry: Powder Brows (cieniowanie) jest idealna dla każdego, a Microblading jest odradzany przy skórze tłustej 🌸."
    ],
    "techniki_usta": [
        "Oferujemy Lip Blush (akwarelowy, naturalny efekt) lub Full Lip Color (efekt szminki) 💋."
    ],
    "trwalosc": [
        "Efekt utrzymuje się zwykle 1–3 lata, zależy to od pielęgnacji i fototypu skóry ✨.",
    ],
    "fakty_mity": [
        "Ból jest minimalny, ponieważ stosujemy znieczulenie lidokainą. PMU jest półtrwały 🌸.",
    ],
    "przeciwwskazania": [
         "Twoje pytanie jest bardzo ważne. O wszystkie szczegóły dotyczące przeciwwskazań zapytaj naszego eksperta — przełączamy na bardziej szczegółową odpowiedź. 🌿"
    ]
}

# === SŁOWA KLUCZOWE ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        r"\bprzeciwwskaz\w*", r"\bchorob\w*", r"\blek\w*", r"\btablet\w*", r"\bciąż\w*", r"\bw\s+ciąży\b", r"\bw\s+ciazy\b",
        r"\bkaw\w*", r"\bpi\w+\s+kaw\w*", r"\bespresso\w*", r"\blatte\w*", r"\bkofein\w*",
        r"\balkohol\w*", r"\bwino\w*", r"\bpiwo\w*", r"\bizotek\w*", r"\bretinoid\w*", r"\bsteroid\w*", r"\bheviran\w*", r"\bhormon\w*"
    ],
    "pielęgnacja": [
        r"\bpielęgnac\w*", r"\bgojenie\w*", r"\bpo\s+zabiegu\w*", r"\bstrup\w*", r"\błuszcz\w*", r"\bzłuszcz\w*",
        r"\bsmarow\w*", r"\bmyc\w*", r"\bmyć\w*", r"\bjak\s+dbac\w*", r"\bjak\s+dbać\w*", r"\bprzygotowan\w*"
    ],
    "techniki_brwi": [
        r"\bbrwi\w*", r"\bpowder\w*", r"\bpudrow\w*", r"\bombre\w*", r"\bmetoda\s+pudrowa\w*", r"\bmetoda\s+ombre\w*",
        r"\bmetody\s+brwi\w*", r"\bpigmentacj\w+\s+brwi\w*"
    ],
    "techniki_usta": [
        r"\busta\w*", r"\bust\w*", r"\bwargi\w*", r"\blip\w*", r"\bblush\w*", r"\bkontur\w*", r"\bliner\w*", r"\bfull\s+lip\w*", r"\baquarelle\w*"
    ],
    "trwalosc": [
        r"\butrzymuje\w*", r"\btrwa\w*", r"\bblak\w*", r"\bblednie\w*", r"\bzanika\w*", r"\bodświeżeni\w*", r"\bkolor\w*", r"\bczas\w*", r"\btrwałość\w*"
    ],
    "fakty_mity": [
        r"\bmit\w*", r"\bfakt\w*", r"\bbol\w*", r"\ból\w*", r"\bprawda\w*", r"\bfałsz\w*", r"\blaser\w*", r"\bremover\w*", r"\bmaszyna\w*"
    ]
}
INTENT_PRIORITIES = [
    "przeciwwskazania", "pielęgnacja", "techniki_brwi", "techniki_usta", "trwalosc", "fakty_mity"
]

FOLLOWUP_QUESTIONS = {
    # Pytania dopytujące tylko dla technik
    "techniki_brwi": "Czy pytasz o metody brwi (Powder vs Ombre)?",
    "techniki_usta": "Chodzi o techniki ust (Lip Blush / Kontur / Full Lip Color)?"
}
HISTORY_LIMIT = 10
SESSION_DATA = {}

# === POMOCNICZE FUNKCJE (bez zmian) ===
def detect_intent(text):
    scores = {}
    for intent, patterns in INTENT_KEYWORDS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > 0:
            scores[intent] = score
    if not scores:
        return None
    best_intent = max(scores, key=scores.get)
    tied = [i for i, s in scores.items() if s == scores[best_intent]]
    if len(tied) > 1:
        for p in INTENT_PRIORITIES:
            if p in tied:
                return p
    return best_intent

def emojis_for(intent):
    mapping = {
        "przeciwwskazania": ["🌿", "💋"],
        "pielęgnacja": ["🌿", "✨"],
        "techniki_brwi": ["✨", "🌸"],
        "techniki_usta": ["💋", "💄"],
        "trwalosc": ["💄", "✨"],
        "fakty_mity": ["🌸", "✨"]
    }
    return " ".join(random.sample(mapping.get(intent, ["✨", "🌸"]), 2))

def add_phone_once(reply, session, count):
    if count % 3 == 0 and not session["last_phone"]:
        reply += random.choice(PHONE_MESSAGES).replace('**', '') 
        session["last_phone"] = True
    else:
        session["last_phone"] = False
    return reply

def update_history(session, user_msg, bot_reply):
    session["history"].append(("user", user_msg))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()
    
    session["history"].append(("assistant", bot_reply))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()

# === STRONA GŁÓWNA, POWITANIE (bez zmian) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/start', methods=['GET'])
def start_message():
    user_ip = request.remote_addr or "default"
    SESSION_DATA[user_ip] = {
        "message_count": 0, "last_intent": None, "asked_context": False, 
        "last_phone": False, "history": deque()
    }
    welcome_text = "Dzień dobry! Jesteśmy Twoją osobistą ekspertką od makijażu permanentnego. Chętnie doradzimy w wyborze najlepszej metody. O co chciałabyś zapytać? 🌸" 
    update_history(SESSION_DATA[user_ip], "Cześć, kim jesteś?", welcome_text)
    return jsonify({'reply': welcome_text})

# === GŁÓWNY ENDPOINT ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()
    
    if user_ip not in SESSION_DATA:
         SESSION_DATA[user_ip] = {
            "message_count": 0, "last_intent": None, "asked_context": False, 
            "last_phone": False, "history": deque()
        }

    if not user_message:
        reply = 'Napisz coś, żebym mogła pomóc 💬'
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]
    reply = ""

    new_intent = detect_intent(text_lower)
    
    # === LOGIKA ZARZĄDZANIA INTENCJĄ ===
    if new_intent and new_intent != session["last_intent"]:
        session["asked_context"] = False
        session["last_intent"] = new_intent
    # Ta linia musi być tutaj, aby obsłużyć przypadek, gdy klient odpowiada na pytanie dopytujące!
    intent = new_intent or session.get("last_intent") 
    
    # --- LOGIKA DLA NAPRAWY BŁĘDU POTWIERDZENIA ---
    is_confirmation_only = re.search(r"^\s*(tak|dokładnie|oczywiście|zgadza się|dobrze)\s*$", text_lower)
    
    was_last_bot_message_a_followup = False
    if session["history"] and session["history"][-1][0] == "assistant":
        last_bot_reply = session["history"][-1][1].lower()
        if any(q in last_bot_reply for q in FOLLOWUP_QUESTIONS.values()):
            was_last_bot_message_a_followup = True
            
    # Jeśli jest CZYSTE potwierdzenie i dotyczyło to pytania dopytującego:
    if is_confirmation_only and was_last_bot_message_a_followup:
        intent = session.get("last_intent")
        session["asked_context"] = False
        pass # Kontynuuj do sekcji 3 (FALLBACK GPT)
    # --- KONIEC LOGIKI NAPRAWY ---


    # === 1. OBSŁUGA CEN I TERMINÓW (PRIORYTET 1) ===
    elif any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = "Oto nasz aktualny cennik:\n\n" + all_prices
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    elif any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]):
        reply = f"Chętnie umówimy Cię na zabieg! Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy i dobrać pasujący dzień. Czy możemy zaproponować Ci kontakt telefoniczny? {PHONE_NUMBER} 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
    
    # === 1.5 REGUŁA LOGISTYCZNA (PRIORYTET 2) ===
    elif any(w in text_lower for w in ["dzieckiem", "dzieci", "sama", "samemu", "zwierzak", "pies", "kot", "osoba towarzysząca"]):
        reply = "Zależy nam na pełnym skupieniu i higienie podczas zabiegu. Prosimy o **przyjście na wizytę bez osób towarzyszących** (w tym dzieci) oraz bez zwierząt. Dziękujemy za zrozumienie! 😊"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === 2. BAZA WIEDZY (ODPOWIEDZI PROSTE I PYTANIA DOPYTUJĄCE) ===
    elif intent and intent in KNOWLEDGE:
        
        # === WARUNEK PRZEKIEROWANIA DO GPT (Wszystko, co nie jest techniką) ===
        # Jeśli wykryto intencję, ale NIE MA jej w FOLLOWUP_QUESTIONS (np. 'trwalosc', 'pielęgnacja', 'przeciwwskazania')
        if intent not in FOLLOWUP_QUESTIONS:
             pass # Kontynuuj do sekcji 3 (FALLBACK GPT)
        
        # === WARUNEK PYTANIA DOPYTUJĄCEGO (Tylko Techniki) ===
        elif intent in FOLLOWUP_QUESTIONS and not session["asked_context"]:
            session["asked_context"] = True
            session["last_intent"] = intent
            reply = FOLLOWUP_QUESTIONS[intent]
            update_history(session, user_message, reply)
            return jsonify({'reply': reply})
        
        # Jeśli klient odpowiedział na pytanie dopytujące, ale NIE słowem "tak" (czyli ma nowe info), 
        # przechodzimy do GPT (FALLBACK 3).
        elif session["asked_context"] == True:
            pass # Kontynuuj do sekcji 3 (FALLBACK GPT)
        
        # Jeśli nie złapał nic, co wymaga GPT, daje prostą odpowiedź (powinno być rzadkie)
        else:
            session["last_intent"] = intent
            session["asked_context"] = False
            reply = random.choice(KNOWLEDGE[intent]) + " " + emojis_for(intent)
            reply = add_phone_once(reply, session, count)
            update_history(session, user_message, reply)
            return jsonify({'reply': reply})

    # === 3. FALLBACK GPT (Logika Eksperta z pełną wiedzą) ===
    # Wszelkie nierozpoznane intencje, złożone pytania i potwierdzenia trafiają tutaj!
    
    # === KLUCZOWE WZMOCNIENIE FALLBACKU! ===
    # Jeśli do tego momentu nie rozpoznano nowej intencji (new_intent jest None)
    # I nie jest to czyste potwierdzenie ('tak'), które zostało obsłużone wcześniej
    # ORAZ bot w poprzednim kroku nie zadawał pytania dopytującego (które ma być obsłużone przez GPT)
    # ZMUSZAMY SYSTEM DO TRAFIENIA DO GPT Z NOWYM PYTANIEM.
    if new_intent is None and not is_confirmation_only:
        session["last_intent"] = None # Resetujemy intencję, aby GPT potraktował to jako nowy, nieznany temat.
        session["asked_context"] = False
    # **************************************
        
    # --- WZMOCNIONY SYSTEM PROMPT (Bez zmian od ostatniej wersji, jest już dobry) ---
    system_prompt = f"""
    {PMU_FULL_KNOWLEDGE}

    INSTRUKCJE SPECJALNE DLA MODELU:
    1. Jesteś ekspertem-mikropigmentologiem z 20-letnim doświadczeniem. Odpowiadasz w języku polskim.
    2. Ton: **BARDZO EMPATYCZNY, PROFESJONALNY i LUDZKI.** Aktywnie używaj wyrażeń budujących zaufanie: "Rozumiemy Twoje obawy", "To bardzo ważne pytanie", "Chętnie pomożemy", "W naszym salonie dbamy o...".
    3. **Unikaj formy "ja"**. Używaj form: "nasz salon", "eksperci robią", "możemy doradzić". Unikaj powtarzania tych samych fraz i zawsze parafrazuj. Używaj emotek z wyczuciem (max 2).
    4. Zawsze bazuj na faktach zawartych w DANYCH SALONU i WIEDZY PMU.
    5. **Brak Informacji:** Jeśli użytkownik pyta o rzecz, która **nie jest zawarta** w bazie wiedzy (np. nietypowe pytania logistyczne, o których nie ma reguł, np. 'kto wykonuje zabieg?'), odpowiedz, że nie masz takiej informacji, ale **zalecasz kontakt telefoniczny z recepcją salonu, aby to potwierdzić** ({PHONE_NUMBER}). Nie wymyślaj reguł.
    6. **Formatowanie:** W przypadku złożonych pytań (jak techniki lub przeciwwskazania) używaj **list punktowanych** i **pogrubień** w tekście, aby zwiększyć czytelność. (Nie używaj symboli *).
    7. **ZASADA KOMUNIKACJI:** Odpowiadaj bezpośrednio na pytanie, traktując to jako ciągłą konwersację.
    8. **CENA/TERMIN:** Jeśli użytkownik pyta o cenę lub termin/rezerwację, użyj informacji z DANYCH SALONU i ZACHĘCAJ do kontaktu telefonicznego pod numerem: {PHONE_NUMBER}.
    """

    messages = [{"role": "system", "content": system_prompt}]
    
    for role, content in session["history"]:
        messages.append({"role": role, "content": content})
        
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.9, 
            max_tokens=600,
            messages=messages
        )
        reply = completion.choices[0].message.content.strip()
        
        reply = add_phone_once(reply, session, count)
        
    except Exception as e:
        reply = f"Przepraszamy, wystąpił chwilowy błąd komunikacji z naszym systemem. Prosimy o kontakt telefoniczny pod numerem {PHONE_NUMBER} lub spróbuj za chwilę 💔."

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)















