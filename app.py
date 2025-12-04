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
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie w cenie 💋"
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
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨\n\n"
        "O co chciałabyś zapytać na początek? 🌸 O zabieg, przygotowanie, pielęgnację, trwałość czy terminy?"
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

# === Endpoint chatu (backend) ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"

    # Inicjalizacja licznika
    if user_ip not in SESSION_DATA:
        SESSION_DATA[user_ip] = {"message_count": 0}
    SESSION_DATA[user_ip]["message_count"] += 1
    count = SESSION_DATA[user_ip]["message_count"]

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # === 1️⃣ CENA — z wykluczeniem pytań o trwałość i czas ===
    price_keywords = ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]
    excluded_phrases = ["utrzymuje", "trwa", "gojenie", "czas", "dni"]

    if any(word in text_lower for word in price_keywords) and not any(phrase in text_lower for phrase in excluded_phrases):
        if "cennik" in text_lower:
            return jsonify({'reply': f"{PRICE_LIST['brwi']}\n\n{PRICE_LIST['usta']}"})
        elif "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 2️⃣ TERMINY ===
    booking_keywords = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]
    if any(word in text_lower for word in booking_keywords):
        reply = "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        # telefon dodajemy tylko co 4 wiadomości
        if count % 4 == 0:
            reply += " Zadzwoń: 881 622 882 💋"
        return jsonify({'reply': reply})

    # === 3️⃣ LEKI ===
    medication_keywords = ["lek", "leki", "tabletki", "antybiotyk", "antybiotyki", "antykoncepcję", "antykoncepcja"]
    if any(word in text_lower for word in medication_keywords):
        if "izotek" in text_lower:
            return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 Zabieg można wykonać po zakończeniu leczenia."})
        else:
            return jsonify({'reply': "W przypadku przyjmowania leków najlepiej skontaktować się z salonem, by upewnić się, że zabieg będzie bezpieczny 🌸"})

    # === 4️⃣ KONTEKST GPT ===
    system_prompt = (
        "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
        "Piszesz w przyjazny, ekspercki sposób. Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. "
        "Unikasz sztywnych opisów — doradzasz jak stylistka, która zna się na rzeczy. "
        "Używasz emotek z wyczuciem (💋✨🌿), maksymalnie 2–4 zdania. "
        "Nie wspominaj o numerze telefonu, dopóki nie padnie pytanie o termin, kontakt lub dopóki klientka nie ma obaw. "
        "Nie wspominaj o promocjach ani ofertach. "
        "Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust."
    )

    # === 5️⃣ Odpowiedź GPT ===
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

        # naturalny follow-up
        follow_up = should_ask_followup(user_message)
        if follow_up and count % 3 == 0:  # follow-up co kilka wiadomości
            reply = f"{reply}\n\n{follow_up}"

        # 💬 empatyczne zaproszenie do kontaktu — tylko gdy klientka ma obawy
        concern_words = [
            "boję", "obawiam", "zastanawiam", "nie wiem", "czy warto",
            "pierwszy raz", "czy się uda", "czy boli", "trochę się boję", "waha", "martwię"
        ]
        if any(word in text_lower for word in concern_words):
            reply += random.choice([
                "\n\nJeśli masz wątpliwości, możemy wszystko spokojnie omówić przez telefon 💋 881 622 882",
                "\n\nTo całkowicie normalne mieć obawy 🌿 Zadzwoń, a wyjaśnimy wszystko krok po kroku 💋 881 622 882",
                "\n\nRozumiem, że możesz mieć pytania 💋 Zadzwoń, pomożemy dobrać najlepsze rozwiązanie: 881 622 882"
            ])

        # 🔸 delikatne zaproszenie po dłuższej rozmowie (co 5 wiadomości)
        elif count % 5 == 0 and not any(x in text_lower for x in ["zadzwoń", "telefon", "kontakt"]):
            reply += random.choice([
                "\n\nJeśli chcesz, możemy omówić szczegóły przez telefon 💋 881 622 882",
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
















