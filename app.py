from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random

# === Inicjalizacja ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === Cennik zabiegów ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar 350 zł 🌿"
}

# === Baza wiedzy ===
KNOWLEDGE = {
    "przeciwwskazania": [
        "Zabieg nie jest wykonywany w ciąży, podczas karmienia piersią, przy infekcjach, chorobach nowotworowych lub przyjmowaniu sterydów i retinoidów.",
        "Przed zabiegiem nie pij kawy ani alkoholu — rozrzedzają krew i mogą utrudnić pigmentację 💋"
    ],
    "pielęgnacja": [
        "Po zabiegu nie dotykaj, nie drap i nie zrywaj strupków. Skóra goi się ok. 7 dni, a kolor stabilizuje się do 30 dni ✨",
        "Unikaj słońca, sauny, basenu i intensywnego wysiłku przez minimum tydzień 🌿"
    ],
    "techniki": [
        "Metoda pudrowa daje efekt miękkiego cienia, idealna dla każdego typu skóry.",
        "Lip Blush delikatnie podkreśla kolor ust i daje efekt świeżości.",
        "Full Lip Color daje pełne, intensywne wypełnienie kolorem jak klasyczna szminka 💄"
    ],
    "trwalosc": [
        "Efekt makijażu permanentnego utrzymuje się średnio 1–3 lata. Po tym czasie zalecane jest odświeżenie pigmentu 💋",
        "Zbyt szybkie blaknięcie może wynikać z tłustej cery lub częstej ekspozycji na słońce."
    ],
    "fakty_mity": [
        "Zabieg nie jest bolesny — dzięki znieczuleniu większość klientek czuje tylko lekkie szczypanie 🌿",
        "Makijaż permanentny nie powoduje wypadania włosków, pigment wprowadzany jest bardzo płytko.",
        "To nie jest tatuaż — efekt utrzymuje się 1–3 lata i stopniowo blednie 💫"
    ]
}

# === Dane sesji (licznik wiadomości) ===
SESSION_DATA = {}

# === Strona główna (frontend chatu) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === Wiadomość powitalna ===
@app.route('/start', methods=['GET'])
def start_message():
    welcome_text = (
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨\n"
        "\nO co chciałabyś zapytać na początek?"
    )
    return jsonify({'reply': welcome_text})

# === Pomocnicza funkcja: czy warto dopytać ===
def should_ask_followup(user_message):
    text_lower = user_message.lower()
    trigger_words = ["pierwszy", "boję", "zastanawiam", "nie wiem", "rozważam", "czy warto", "myślę", "chciałabym"]
    if any(word in text_lower for word in trigger_words):
        return random.choice([
            "A robiłaś już wcześniej makijaż permanentny, czy to Twój pierwszy raz? 💋",
            "Zastanawiasz się nad PMU — a myślisz raczej o ustach czy o brwiach? ✨",
            "Dobrze, że pytasz 🌿 A powiedz — masz już jakieś doświadczenia z PMU czy dopiero rozważasz pierwszy zabieg?"
        ])
    return None

# === Funkcja rozpoznania kategorii pytania ===
def detect_intent(text):
    text = text.lower()
    if any(w in text for w in ["przeciwwskaz", "chorob", "lek", "ciąża", "kawa", "alkohol", "izotek"]):
        return "przeciwwskazania"
    if any(w in text for w in ["pielęgnac", "gojenie", "po zabiegu", "dbac", "smarowac"]):
        return "pielęgnacja"
    if any(w in text for w in ["metoda", "technika", "brwi", "ombre", "pudrow", "lip blush", "full lip"]):
        return "techniki"
    if any(w in text for w in ["utrzymuje", "trwa", "blak", "kolor", "odświeżenie"]):
        return "trwalosc"
    if any(w in text for w in ["mit", "fakt", "bol", "ból", "włoski", "usuwa"]):
        return "fakty_mity"
    return None

# === Endpoint chatu (backend) ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # Inicjalizacja sesji
    if user_ip not in SESSION_DATA:
        SESSION_DATA[user_ip] = {"message_count": 0}
    SESSION_DATA[user_ip]["message_count"] += 1
    count = SESSION_DATA[user_ip]["message_count"]

    # === 1️⃣ CENA — zawsze pokazuje pełny cennik, jeśli nie określono dokładnie ===
    price_keywords = ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]
    excluded_phrases = ["utrzymuje", "trwa", "gojenie", "czas", "dni"]
    if any(word in text_lower for word in price_keywords) and not any(p in text_lower for p in excluded_phrases):
        all_prices = "\n\n".join(PRICE_LIST.values())
        return jsonify({'reply': all_prices})

    # === 2️⃣ TERMINY ===
    booking_keywords = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]
    if any(word in text_lower for word in booking_keywords):
        reply = "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        if count % 3 == 0:
            reply += " Zadzwoń: 881 622 882 💋"
        return jsonify({'reply': reply})

    # === 3️⃣ WIEDZA — dopasowanie kategorii z KNOWLEDGE ===
    intent = detect_intent(text_lower)
    if intent and intent in KNOWLEDGE:
        reply = random.choice(KNOWLEDGE[intent])
        # subtelne zaproszenie po odpowiedzi
        if count % 4 == 0:
            reply += random.choice([
                "\n\nJeśli chcesz, mogę pomóc Ci dobrać termin lub doradzić najlepiej 💋 881 622 882",
                "\n\nMasz ochotę umówić się na konsultację? Zadzwoń: 881 622 882 🌿"
            ])
        return jsonify({'reply': reply})

    # === 4️⃣ GPT fallback ===
    system_prompt = (
        "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
        "Piszesz w przyjazny, kobiecy i ekspercki sposób. "
        "Używasz prostego języka, wyjaśniasz spokojnie i logicznie. "
        "Zachowujesz empatię, ale nie jesteś nachalna. "
        "Co kilka wiadomości subtelnie zapraszasz do kontaktu — numer 881 622 882. "
        "Unikaj suchych definicji i nie wspominaj o promocjach."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply = completion.choices[0].message.content.strip()

        follow_up = should_ask_followup(user_message)
        if follow_up and count % 3 == 0:
            reply += f"\n\n{follow_up}"

        # co 5 wiadomości — delikatne CTA z numerem
        if count % 5 == 0:
            reply += random.choice([
                "\n\nJeśli chcesz, mogę pomóc dobrać najlepszy termin 💋 881 622 882",
                "\n\nZadzwoń, jeśli wolisz porozmawiać 🌿 881 622 882"
            ])

    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 ({e})"

    return jsonify({'reply': reply})


# === URUCHOMIENIE SERWERA ===
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
















