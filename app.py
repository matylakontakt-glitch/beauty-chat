from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re

# === INICJALIZACJA ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === CENNIK ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie jest w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar 350 zł 🌿"
}

# === BAZA WIEDZY ===
KNOWLEDGE = {
    "przeciwwskazania": [
        "Zabieg nie jest wykonywany w ciąży ani podczas karmienia piersią 🌿💋",
        "Aktywne infekcje, nowotwory, kuracja sterydami lub retinoidami — wtedy zabiegu nie wykonujemy 🌿💋",
        "Przed zabiegiem nie pij kawy ani alkoholu — kofeina i alkohol rozrzedzają krew, co może utrudnić przyjęcie pigmentu 🌿💋"
    ],
    "pielęgnacja": [
        "Po zabiegu nie drap i nie zrywaj strupków; skóra goi się ok. 7 dni, a kolor stabilizuje po ~30 dniach 🌿✨",
        "Przez tydzień unikaj słońca, sauny, basenu i intensywnego wysiłku 🌿✨",
        "Brwi przemywaj przegotowaną wodą 3–5× dziennie przez pierwsze 3 dni, potem delikatnie nawilżaj cienką warstwą preparatu 🌿✨"
    ],
    "techniki_brwi": [
        "W naszym salonie wykonujemy dwie metody brwi: • Powder Brows — miękki efekt cienia • Ombre — jaśniejsze u nasady, ciemniejsze na końcach ✨🌸",
        "Powder Brows: delikatny, pudrowy cień. Ombre: subtelny gradient (jaśniej przy nasadzie, ciemniej na końcu łuku) ✨🌸"
    ],
    "techniki_usta": [
        "Najczęstsze techniki ust: • Lip Blush — naturalny rumieniec • Kontur ust — subtelne zdefiniowanie linii • Full Lip Color — pełne, równomierne wypełnienie 💋💄",
        "Lip Blush daje lekki, świeży kolor; Full Lip Color — efekt klasycznej szminki; Kontur wyrównuje kształt ust 💋💄"
    ],
    "trwalosc": [
        "Efekt utrzymuje się zwykle 1–3 lata; zależy od pielęgnacji, fototypu i stylu życia ✨💄",
        "Szybsze blaknięcie bywa przy cerze tłustej, częstej ekspozycji na słońce lub braku zaleceń pozabiegowych ✨💄"
    ],
    "fakty_mity": [
        "Dzięki znieczuleniu większość klientek czuje jedynie lekkie szczypanie ✨🌸",
        "PMU nie powoduje wypadania włosków — pigment jest wprowadzany płytko ✨🌸",
        "Makijaż permanentny jest półtrwały — naturalnie blednie i wymaga odświeżenia ✨🌸"
    ]
}

# === SŁOWA KLUCZOWE ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        "przeciwwskaz", "chorob", "lek", "tablet", "ciąża", "w ciazy", "w ciąży",
        "kawa", "pić kaw", "espresso", "latte", "kofein",
        "alkohol", "wino", "piwo", "izotek", "retinoid", "steroid", "heviran", "hormony"
    ],
    "pielęgnacja": [
        "pielęgnac", "gojenie", "po zabiegu", "strup", "strupk", "łuszcz", "złuszcz",
        "smarow", "myc", "myć", "jak dbac", "jak dbać"
    ],
    "techniki_brwi": [
        "brwi", "powder", "pudrow", "ombre", "metoda pudrowa", "metoda ombre",
        "metody brwi", "pigmentacji brwi"
    ],
    "techniki_usta": [
        "usta", "ust", "wargi", "lip", "blush", "kontur", "liner", "full lip", "aquarelle"
    ],
    "trwalosc": [
        "utrzymuje", "trwa", "blak", "blednie", "zanika", "odświeżenie", "kolor", "czas", "trwałość"
    ],
    "fakty_mity": [
        "mit", "fakt", "bol", "ból", "prawda", "fałsz", "laser", "remover"
    ]
}

# Kolejność rozstrzygania przy konfliktach
INTENT_PRIORITIES = [
    "przeciwwskazania",
    "pielęgnacja",
    "techniki_brwi",
    "techniki_usta",
    "trwalosc",
    "fakty_mity"
]

# Pytania dopytujące
FOLLOWUP_QUESTIONS = {
    "techniki_brwi": "Czy pytasz o metody brwi (Powder vs Ombre)?",
    "techniki_usta": "Chodzi o techniki ust (Lip Blush / Kontur / Full Lip Color)?",
    "trwalosc": "Pytasz przed zabiegiem czy już po — chcesz wiedzieć, jak długo trzyma efekt?",
    "pielęgnacja": "Chodzi o przygotowanie przed zabiegiem czy pielęgnację po?"
}

# === SESJE ===
SESSION_DATA = {}

# === STRONA GŁÓWNA ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === POWITANIE ===
@app.route('/start', methods=['GET'])
def start_message():
    welcome_text = (
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨\n"
        "\nO co chciałabyś zapytać na początek?"
    )
    return jsonify({'reply': welcome_text})

# === POMOCNICZE ===
def detect_intent(text):
    scores = {}
    for intent, words in INTENT_KEYWORDS.items():
        score = sum(1 for w in words if w in text)
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
        reply += random.choice([
            "\n\nJeśli chcesz, mogę pomóc dobrać termin 💋 881 622 882",
            "\n\nMasz ochotę na konsultację? Zadzwoń: 881 622 882 🌿"
        ])
        session["last_phone"] = True
    else:
        session["last_phone"] = False
    return reply

# === GŁÓWNY ENDPOINT ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    # Sesja użytkownika
    if user_ip not in SESSION_DATA:
        SESSION_DATA[user_ip] = {"message_count": 0, "last_intent": None, "asked_context": False, "last_phone": False}
    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]

    # === CENNIK ===
    if any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = add_phone_once(all_prices, session, count)
        return jsonify({'reply': reply})

    # === TERMINY ===
    if any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]):
        reply = "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        reply = add_phone_once(reply, session, count)
        return jsonify({'reply': reply})

    # === INTENCJA ===
    intent = detect_intent(text_lower) or session.get("last_intent")
    session["last_intent"] = intent

    # === Specjalny wyjątek: pytanie o kawę ===
    if "kaw" in text_lower or "espresso" in text_lower or "latte" in text_lower:
        reply = "Przed zabiegiem nie pij kawy — kofeina rozrzedza krew i może pogorszyć przyjęcie pigmentu 🌿💋"
        return jsonify({'reply': reply})

    # === Jeśli znaleziono intencję z bazy wiedzy ===
    if intent and intent in KNOWLEDGE:
        if not session["asked_context"] and intent in FOLLOWUP_QUESTIONS:
            session["asked_context"] = True
            return jsonify({'reply': FOLLOWUP_QUESTIONS[intent]})
        reply = random.choice(KNOWLEDGE[intent]) + " " + emojis_for(intent)
        reply = add_phone_once(reply, session, count)
        return jsonify({'reply': reply})

    # === FALLBACK GPT (gdy nie pasuje żadna kategoria) ===
    system_prompt = (
        "Jesteś Beauty Chat — inteligentną, empatyczną asystentką salonu PMU. "
        "Odpowiadasz krótko, konkretnie i kobieco. "
        "Używasz maksymalnie 2 emotek z wyczuciem. "
        "Nie wymyślasz rzeczy spoza makijażu permanentnego brwi i ust."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=600,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 ({e})"

    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

















