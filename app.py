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

# === Strona główna (frontend chatu) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === Wiadomość powitalna ===
@app.route('/start', methods=['GET'])
def start_message():
    welcome_text = "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨"
    return jsonify({'reply': welcome_text})

# === Pomocnicza funkcja: czy trzeba dopytać o doświadczenie ===
def should_ask_followup(user_message):
    text_lower = user_message.lower()
    trigger_words = ["pierwszy", "boję", "zastanawiam", "nie wiem", "rozważam", "czy warto", "myślę", "chciałabym"]
    area_words = ["usta", "brwi", "brew"]
    if any(word in text_lower for word in trigger_words) and not any(word in text_lower for word in area_words):
        if random.random() < 0.4:  # tylko w ok. 40% przypadków, by zachować naturalność
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

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # === 1️⃣ Pytania o cenę ===
    price_keywords = ["ile", "koszt", "cena"]
    if any(word in text_lower for word in price_keywords):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 2️⃣ Pytania o terminy ===
    booking_keywords = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy mogę", "czy są miejsca", "dostępny"]
    if any(word in text_lower for word in booking_keywords):
        return jsonify({'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 Zadzwoń: 881 622 882"})

    # === 3️⃣ Pytania o leki ===
    medication_keywords = ["lek", "leki", "tabletki", "antybiotyk", "antybiotyki", "antykoncepcję", "antykoncepcja"]
    if any(word in text_lower for word in medication_keywords):
        if "izotek" in text_lower:
            return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 Zabieg można wykonać po zakończeniu leczenia."})
        else:
            return jsonify({'reply': "W przypadku przyjmowania leków najlepiej skontaktować się bezpośrednio z salonem, by upewnić się, że zabieg będzie bezpieczny 🌸"})

    # === 4️⃣ Tworzenie kontekstu systemowego GPT ===
    system_prompt = (
        "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
        "Piszesz w przyjazny, ekspercki sposób. Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. "
        "Unikasz sztywnych, encyklopedycznych tekstów — doradzasz jak stylistka, która zna się na rzeczy. "
        "Używasz emotek z wyczuciem (💋✨🌿), nie przesadzasz. Każda odpowiedź ma maksymalnie 2–4 zdania. "
        "Nie powtarzaj numeru telefonu częściej niż co kilka odpowiedzi. "
        "W naturalnych momentach, gdy klientka jest niezdecydowana, zadaj subtelne pytanie pogłębiające rozmowę, np. o doświadczenie lub preferencje. "
        "Nie wspominaj o ofertach, promocjach, sprzedaży. "
        "Nie odpowiadaj na pytania spoza tematu makijażu permanentnego brwi i ust. "
        "Twoim celem jest pomóc klientce zrozumieć zabiegi, pielęgnację i poczuć się zaopiekowaną."
    )

    # === 5️⃣ Zapytanie do GPT ===
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

        # sprawdź, czy warto dodać pytanie follow-up
        follow_up = should_ask_followup(user_message)
        if follow_up:
            reply = f"{reply}\n\n{follow_up}"

        # delikatnie i losowo dodaj zaproszenie do kontaktu
        if random.random() < 0.25 and not any(x in text_lower for x in ["zadzwoń", "telefon", "kontakt"]):
            reply += random.choice([
                "\n\nJeśli chcesz, możemy omówić szczegóły przez telefon 💋 881 622 882",
                "\n\nChcesz, żebym pomogła dobrać idealną technikę? Zadzwoń: 881 622 882 ✨",
                "\n\nJeśli wolisz, możesz zadzwonić — wszystko spokojnie wyjaśnimy 🌿 881 622 882"
            ])

    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 ({e})"

    return jsonify({'reply': reply})


# === Uruchomienie serwera ===
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False
    )










