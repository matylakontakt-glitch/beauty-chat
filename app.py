from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re
from collections import deque

# === DANE SALONU I WIEDZA ===
PMU_FULL_KNOWLEDGE = """
Jesteś **ekspertką salonu** z 20-letnim doświadczeniem w mikropigmentacji. Odpowiadasz w imieniu salonu, używając formy "nasz salon", "eksperci robią", "możemy doradzić".

DANE SALONU:
- Adres: ul. Junikowska 9
- Godziny otwarcia: Poniedziałek - Piątek: 09:00 - 19:00
- Kontakt: 881 622 882
- Zespół: Nasze linergistki mają wieloletnie doświadczenie i pracują wyłącznie na atestowanych pigmentach.
- Czas zabiegu: ok. 2–3 godziny (w zależności od obszaru i techniki).

TECHNIKI – BRWI:
- Powder Brows: miękki cień przypominający makijaż cieniem.
- Ombre Brows: delikatny gradient – jaśniej u nasady, ciemniej na końcach.
- Nano Brows: mikropigmentacja punktowa, bardzo delikatna.

TECHNIKI – USTA:
- Lip Blush: naturalne podkreślenie koloru.
- Full Lip Color: pełne, jednolite wypełnienie.
- Kontur: wyrównanie kształtu ust.

PRZECIWWSKAZANIA:
- Ciąża, karmienie piersią, nowotwory (bez zgody lekarza), infekcje, retinoidy, sterydy, antybiotyki, zabiegi estetyczne poniżej 4 tygodni.

PIELĘGNACJA:
- Po zabiegu nie drapać i nie moczyć – skóra goi się ok. 7 dni.
- Unikać słońca, sauny, basenu przez 2 tygodnie.
- Kolor stabilizuje się po ok. 28 dniach.

BEZPIECZEŃSTWO:
- Wszystkie narzędzia są jednorazowe, pigmenty zgodne z normą REACH.
"""

# === INICJALIZACJA ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === CENNIK ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1200 zł — dopigmentowanie w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego — jeden obszar 350 zł 🌿"
}
PHONE_NUMBER = "881 622 882"
PHONE_MESSAGES = [
    f"\n\nJeśli wolisz porozmawiać o szczegółach, zadzwoń: {PHONE_NUMBER} 📞",
    f"\n\nMasz pytania? Jesteśmy dostępni: {PHONE_NUMBER} 🌿",
    f"\n\nChętnie dobierzemy termin telefonicznie: {PHONE_NUMBER} 🌸"
]

# === INTENCJE ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        r"\bprzeciwwskaz\w*", r"\bchorob\w*", r"\bciąż\w*", r"\bw\s+ciąży\b",
        r"\balkohol\w*", r"\bkaw\w*", r"\bpić\w*\s+kaw\w*", r"\bpic\w*\s+kaw\w*", r"\bwino\w*", r"\bpiwo\w*",
        r"\bizotek\w*", r"\bretinoid\w*", r"\bsteroid\w*", r"\bheviran\w*", r"\bhormon\w*"
    ],
    "pielęgnacja": [
        r"\bpielęgnac\w*", r"\bgojenie\w*", r"\bpo\s+zabiegu\b", r"\bstrup\w*", r"\błuszcz\w*", r"\bzłuszcz\w*",
        r"\bsmarow\w*", r"\bmyć\w*", r"\bprzed\s+zabiegiem\b"
    ],
    "techniki_brwi": [r"\bbrwi\w*", r"\bpowder\w*", r"\bpudrow\w*", r"\bombre\w*"],
    "techniki_usta": [r"\busta\w*", r"\bust\w*", r"\blip\w*", r"\bkontur\w*", r"\bblush\w*", r"\bfull\s+lip\w*"],
    "trwalosc": [r"\btrwa\w*", r"\bblak\w*", r"\bkolor\w*", r"\bczas\w*"],
    "fakty_mity": [r"\bmit\w*", r"\bfakt\w*", r"\bbol\w*", r"\ból\w*"]
}
INTENT_PRIORITIES = ["przeciwwskazania", "pielęgnacja", "techniki_brwi", "techniki_usta", "trwalosc", "fakty_mity"]

HISTORY_LIMIT = 10
SESSION_DATA = {}

# === FUNKCJE POMOCNICZE ===
def detect_intent(text):
    scores = {}
    for intent, patterns in INTENT_KEYWORDS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > 0:
            scores[intent] = score
    best_intent = max(scores, key=scores.get) if scores else None
    if best_intent:
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
    if count % 5 == 0 and not session["last_phone"]:
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

# === STRONA GŁÓWNA ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/start', methods=['GET'])
def start_message():
    user_ip = request.remote_addr or "default"
    SESSION_DATA[user_ip] = {"message_count": 0, "last_intent": None, "last_phone": False, "history": deque()}
    welcome_text = "Cześć! 🌸 Jestem Beauty Ekspertką — chętnie odpowiem na pytania o makijaż permanentny brwi i ust. O co chciałabyś zapytać?"
    update_history(SESSION_DATA[user_ip], "start", welcome_text)
    return jsonify({'reply': welcome_text})

# === GŁÓWNY ENDPOINT ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()

    if user_ip not in SESSION_DATA:
        SESSION_DATA[user_ip] = {"message_count": 0, "last_intent": None, "last_phone": False, "history": deque()}

    if not user_message:
        reply = 'Napisz coś, żebym mogła pomóc 💬'
        update_history(SESSION_DATA[user_ip], user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]

    # === REGUŁA: OSOBY TOWARZYSZĄCE / DZIECI / ZWIERZĘTA (Priorytet 1) ===
    if re.search(
        r"\b("
        r"m[aą]ż|m[eę]żem|maz|z\s+m[eę]żem|"
        r"partner\w*|"
        r"przyjaci[oó]ł\w*|koleżank\w*|"
        r"dzieck\w*|dzieci\w*|"
        r"z\s+dzieckiem|z\s+dzieci|"
        r"zwierzak\w*|pies\w*|kot\w*|"
        r"osob\w*\s+towarzysz\w*|towarzysz\w*|"
        r"razem|sama|samemu|mog[eę]\s+przyj\w*"
        r")\b",
        text_lower
    ):
        reply = (
            "Podczas zabiegu dbamy o pełne skupienie, sterylność i komfort. "
            "Prosimy o przyjście **bez osób towarzyszących (również dzieci, partnerów i przyjaciółek)** oraz **bez zwierząt**. "
            "W gabinecie może przebywać wyłącznie osoba, która wykonuje zabieg 🌿."
        )
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: GOJENIE ===
    if any(w in text_lower for w in ["ile go", "czas gojenia", "po zabiegu", "goi się", "jak długo się goi"]):
        reply = "Skóra po zabiegu goi się etapami: przez 3 dni oczyszcza się, a między 4–10 dniem lekko się łuszczy. Pełny kolor stabilizuje się po ok. **28 dniach**. 🌿"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: CENNIK ===
    if any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = "Oto nasz aktualny cennik:\n\n" + all_prices
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: ADRES ===
    if any(w in text_lower for w in ["gdzie", "adres", "lokalizacja", "dojazd"]):
        reply = f"Nasz salon znajduje się przy **ul. Junikowskiej 9 w Poznaniu**. Zapraszamy od poniedziałku do piątku, 09:00–19:00 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: CZAS TRWANIA ZABIEGU ===
    if any(w in text_lower for w in ["ile trwa", "jak dlugo", "dlugo", "czas"]) and not any(w in text_lower for w in ["konsultacj", "doradztwo", "porada"]):
        reply = "Sam zabieg makijażu permanentnego trwa zazwyczaj **około 2 do 3 godzin**. Ten czas obejmuje konsultację, rysunek wstępny i samą pigmentację. Prosimy o rezerwację odpowiedniej ilości czasu. 😊"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: CZAS TRWANIA KONSULTACJI ===
    if any(w in text_lower for w in ["ile trwa", "jak dlugo", "dlugo", "czas"]) and any(w in text_lower for w in ["konsultacj", "doradztwo", "porada"]):
        reply = "Bezpłatna konsultacja trwa **około 1 godziny**. To czas na omówienie szczegółów, wybór metody i kolorów. 🌿"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: O CZYMŚ, CZEGO NIE ROBIMY (PMU OCZU) ===
    if any(w in text_lower for w in ["oczy", "powieki", "eyeliner", "zagęszczen"]):
        reply = f"W naszym salonie skupiamy się wyłącznie na **brwiach i ustach**, aby zapewnić najwyższą specjalizację. **Nie wykonujemy makijażu permanentnego powiek (eyeliner, zagęszczanie rzęs)**. Prosimy o kontakt w sprawie brwi lub ust: {PHONE_NUMBER} 💋."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === REGUŁA: UMÓWIENIE ZABIEGU (z poprawką „po/przed zabiegu”) ===
    if (
        any(w in text_lower for w in ["umówić", "zapis", "wolne", "rezerwacja"]) or
        ("zabieg" in text_lower and not any(p in text_lower for p in ["po zabiegu", "przed zabiegiem"]))
    ):
        reply = f"Chętnie umówimy Panią na **zabieg**! Najlepiej skontaktować się z salonem, aby dobrać dogodny termin: {PHONE_NUMBER} 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === FALLBACK GPT ===
    system_prompt = f"""
    {PMU_FULL_KNOWLEDGE}
    INSTRUKCJE DLA MODELU:
    - Odpowiadaj kobieco, empatycznie i naturalnie.
    - Nie wymyślaj nowych faktów.
    - Maksymalnie 2 emotki.
    - Jeśli pytanie dotyczy czegoś spoza PMU — zaproponuj kontakt telefoniczny: {PHONE_NUMBER}.
    """

    messages = [{"role": "system", "content": system_prompt}]
    for role, content in session["history"]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.8,
            max_tokens=600,
            messages=messages
        )
        reply = completion.choices[0].message.content.strip()
        reply = add_phone_once(reply, session, count)
    except Exception as e:
        reply = f"Wystąpił błąd komunikacji. Skontaktuj się z nami telefonicznie: {PHONE_NUMBER} 💔"

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})


# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)









