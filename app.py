from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re
from collections import deque

# === DANE SALONU I WIEDZA (PRZENIESIONE Z knowledgeBase.ts) ===

# Cała wiedza, która będzie wstrzyknięta do System Promptu GPT
PMU_FULL_KNOWLEDGE = """
Jesteś ekspertem-mikropigmentologiem z 20-letnim doświadczeniem. Twoja wiedza jest techniczna, medyczna i praktyczna, ale przekazujesz ją w sposób zrozumiały i empatyczny dla klientki.

DANE SALONU:
- Adres: ul. Promienista 10
- Godziny otwarcia: Poniedziałek - Piątek: 09:00 - 18:00
- Kontakt: 881 622 882

DEFINICJE I FAKTY:
- Makijaż permanentny (PMU/mikropigmentacja): Wprowadzenie pigmentu płytko do naskórka lub granicy naskórkowo-skórnej.
- Różnica vs Tatuaż: Tatuaż jest w skórze właściwej. PMU jest półtrwały (1-3 lata, czasem do 5).
- Bezpieczeństwo chemiczne: Pigmenty muszą spełniać normy UE REACH 2020/2081 (np. limit ołowiu 0,00007%). Używamy tylko atestowanych, bezpiecznych barwników.

TECHNIKI - BRWI:
1. Pudrowa (Powder Brows): Maszynowe cieniowanie, efekt "przyprószenia". Bardziej trwała (2-3 lata), idealna dla każdego typu skóry (także tłustej).
2. Ombre Brows: Gradient – jaśniejsza nasada, ciemniejszy koniec i dół.

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

# === CENNIK (Zaktualizowany do danych z knowledgeBase) ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje **1200 zł** — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje **1200 zł** — dopigmentowanie jest w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar **350 zł** 🌿"
}
# === KONFIGURACJA TELEFONU ===
PHONE_NUMBER = "881 622 882"
PHONE_MESSAGES = [
    f"\n\nJeśli wolisz porozmawiać o szczegółach, zadzwoń do nas: **{PHONE_NUMBER}** 📞",
    f"\n\nChętnie odpowiemy na bardziej złożone pytania telefonicznie! **{PHONE_NUMBER}** 🌿",
    f"\n\nMasz ochotę na konsultację lub rezerwację terminu? Jesteśmy pod numerem: **{PHONE_NUMBER}** 🌸"
]

# === BAZA WIEDZY (Do reguł, nie do GPT) ===
# Zachowujemy, by szybko odpowiadać na proste pytania bez angażowania GPT
KNOWLEDGE = {
    # Używamy tylko najprostszych odpowiedzi, by nie konkurować z GPT
    "przeciwwskazania": [
        "Bezwzględnymi przeciwwskazaniami są ciąża, laktacja oraz aktywne infekcje 🌿.",
        "Pamiętaj o odstawieniu leków rozrzedzających krew 24h wcześniej oraz konsultacji w przypadku chorób przewlekłych 💋."
    ],
    "pielęgnacja": [
        "Kluczem jest nie drapać i nie zrywać strupków, oraz unikać słońca i sauny przez 2 tygodnie ✨.",
        "W pierwszych dniach zalecamy delikatne przemywanie przegotowaną wodą, a potem minimalne nawilżanie 🌿."
    ],
    "techniki_brwi": [
        "Wybór zależy od typu skóry: *Powder Brows* (cieniowanie) jest idealna dla każdego, a *Microblading* jest odradzany przy skórze tłustej 🌸."
    ],
    "techniki_usta": [
        "Oferujemy *Lip Blush* (akwarelowy, naturalny efekt) lub *Full Lip Color* (efekt szminki) 💋."
    ],
    "trwalosc": [
        "Efekt utrzymuje się zwykle 1–3 lata, zależy to od pielęgnacji i fototypu skóry ✨.",
    ],
    "fakty_mity": [
        "Ból jest minimalny, ponieważ stosujemy znieczulenie lidokainą. PMU jest półtrwały 🌸.",
    ]
}

# === SŁOWA KLUCZOWE (Bez zmian od ostatniej wersji, są OK) ===
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
    "techniki_brwi": "Czy pytasz o metody brwi (Powder vs Ombre)?",
    "techniki_usta": "Chodzi o techniki ust (Lip Blush / Kontur / Full Lip Color)?",
    "trwalosc": "Pytasz przed zabiegiem czy już po — chcesz wiedzieć, jak długo trzyma efekt?",
    "pielęgnacja": "Chodzi o przygotowanie przed zabiegiem czy pielęgnację po?"
}
HISTORY_LIMIT = 10
SESSION_DATA = {}

# === POMOCNICZE FUNKCJE ===

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
    # Logika zachęcania do kontaktu co kilka wiadomości (co 3)
    if count % 3 == 0 and not session["last_phone"]:
        reply += random.choice(PHONE_MESSAGES)
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

# === STRONA GŁÓWNA ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === POWITANIE (Używamy teraz promptu Gemini) ===
@app.route('/start', methods=['GET'])
def start_message():
    user_ip = request.remote_addr or "default"
    # Resetuj sesję przy każdym /start
    SESSION_DATA[user_ip] = {
        "message_count": 0, "last_intent": None, "asked_context": False, 
        "last_phone": False, "history": deque()
    }
    
    # Powitanie z Gemini AI Studio
    welcome_text = "Dzień dobry! Jestem Twoją osobistą ekspertką od makijażu permanentnego brwi i ust. Chętnie doradzę Ci w wyborze najlepszej metody. O co chciałabyś zapytać? 🌸"
    
    # Dodaj powitanie do historii, by model o nim "pamiętał"
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
        reply = 'Napisz coś, żebym mogła Ci pomóc 💬'
        update_history(SESSION_DATA[user_ip], user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]
    reply = ""

    # Reset flagi kontekstu
    new_intent = detect_intent(text_lower)
    if new_intent and new_intent != session["last_intent"]:
        session["asked_context"] = False
    intent = new_intent or session.get("last_intent")

    # === 1. OBSŁUGA CEN I TERMINÓW (Wysoki priorytet) ===
    # Zachowujemy reguły, ale odpowiedzi są logicznie wplecione w GPT, jeśli nie pasują do prostego cennika

    if any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = "Oto nasz aktualny cennik:\n\n" + all_prices
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    if any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]):
        # Odpowiedź zgodna z instrukcją Gemini
        reply = f"Chętnie umówimy Cię na zabieg! Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy i dobrać pasujący dzień. Czy mogę zaproponować Ci kontakt telefoniczny? **{PHONE_NUMBER}** 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 2. BAZA WIEDZY (Jeśli znaleziono intencję) ===
    if intent and intent in KNOWLEDGE:
        
        # Jeśli jest dopytywanie, zadaj pytanie
        if intent in FOLLOWUP_QUESTIONS and not session["asked_context"]:
            session["asked_context"] = True
            reply = FOLLOWUP_QUESTIONS[intent]
            update_history(session, user_message, reply)
            return jsonify({'reply': reply})
        
        # Jeśli kontekst jest już określony LUB intencja nie wymaga dopytywania, daj prostą odpowiedź
        # Używamy tej prostej odpowiedzi TYLKO dla bardzo szybkich i powtarzalnych pytań.
        # W innych przypadkach - Fallback GPT, aby użyć pełnej bazy wiedzy.
        session["last_intent"] = intent
        session["asked_context"] = False
        reply = random.choice(KNOWLEDGE[intent]) + " " + emojis_for(intent)
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 3. FALLBACK GPT (Logika Eksperta z pełną wiedzą) ===
    
    if not new_intent:
        session["last_intent"] = None
        session["asked_context"] = False

    # PRZENIESIONY I ZOPTYMALIZOWANY SYSTEM PROMPT Z Gemini
    system_prompt = f"""
    {PMU_FULL_KNOWLEDGE}

    INSTRUKCJE SPECJALNE DLA MODELU:
    1. Jesteś ekspertem-mikropigmentologiem z 20-letnim doświadczeniem. Odpowiadaj w języku polskim.
    2. Ton: **Profesjonalny, empatyczny, budujący zaufanie.** Bądź miła i używaj emotek z umiarem.
    3. Zawsze bazuj na faktach zawartych w DANYCH SALONU i WIEDZY PMU powyżej.
    4. **Formatowanie:** Używaj formatowania Markdown (pogrubienia **kluczowych terminów**, listy punktowane).
    5. **ZASADA KOMUNIKACJI:** Odpowiadaj bezpośrednio na pytanie, traktując to jako ciągłą konwersację. Nie używaj zbędnych powitań po pierwszej wiadomości (za wyjątkiem /start).
    6. **CENA/TERMIN:** Jeśli użytkownik pyta o cenę lub termin/rezerwację, użyj informacji z DANYCH SALONU i ZACHĘCAJ do kontaktu telefonicznego pod numerem: {PHONE_NUMBER}.
    """

    messages = [{"role": "system", "content": system_prompt}]
    
    # Dodanie wcześniejszych wiadomości z historii sesji
    for role, content in session["history"]:
        messages.append({"role": role, "content": content})
        
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7, # Zapewnia naturalną i logiczną odpowiedź
            max_tokens=600,
            messages=messages
        )
        reply = completion.choices[0].message.content.strip()
        
        # Dodatkowe sprawdzenie, czy nie dodać numeru telefonu (jeśli GPT nie zrobił tego logicznie)
        reply = add_phone_once(reply, session, count)
        
    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 Spróbuj ponownie. ({e})"

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
















