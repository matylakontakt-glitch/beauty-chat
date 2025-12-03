from flask import Flask, request, jsonify, send_from_directory, session
from dotenv import load_dotenv
from openai import OpenAI
import os

# === Inicjalizacja ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "beauty_secret_key")
client = OpenAI(api_key=api_key)

# === Cennik zabiegów ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie w cenie 💋"
}

# === Pomocnicza funkcja: klasyfikacja intencji ===
def classify_intent(text):
    text_lower = text.lower()

    # Termin / rezerwacja
    if any(w in text_lower for w in [
        "termin", "umówić", "zapisać", "zapis", "rezerwacja",
        "wolne", "kiedy", "dostępne", "najbliższy", "chcę się umówić", "mogę przyjść"
    ]):
        return "termin"

    # Emocje / decyzja
    if any(w in text_lower for w in [
        "boję", "strach", "pewna", "nie wiem", "zastanawiam",
        "czy warto", "czy boli", "obawiam", "waham", "czy to bezpieczne"
    ]):
        return "emocje"

    # Leki
    if "izotek" in text_lower:
        return "izotek"
    if any(w in text_lower for w in [
        "lek", "antybiotyk", "tabletki", "biorę", "leczę", "leki", "antykoncepcja"
    ]):
        return "leki"

    # Informacje ogólne
    if any(w in text_lower for w in ["cena", "koszt", "brwi", "usta", "zabieg"]):
        return "info"

    return "inne"

# === Strona główna (frontend chatu) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === Wiadomość powitalna ===
@app.route('/start', methods=['GET'])
def start_message():
    welcome_text = "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨"
    return jsonify({'reply': welcome_text})

# === Endpoint chatu (backend) ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()
    intent = classify_intent(user_message)

    # Zliczanie wiadomości w sesji
    session['msg_count'] = session.get('msg_count', 0) + 1
    msg_count = session['msg_count']

    # === 1️⃣ Sprawdzenie, czy pytanie dotyczy ceny ===
    if any(word in text_lower for word in ["ile", "koszt", "cena"]):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 2️⃣ Sprawdzenie, czy pytanie dotyczy terminów ===
    if intent == "termin":
        return jsonify({
            'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 — zadzwoń pod 881 622 882 💋"
        })

    # === 3️⃣ Sprawdzenie, czy pytanie dotyczy leków ===
    if intent == "izotek":
        return jsonify({
            'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego. Zabieg można wykonać dopiero po zakończeniu leczenia 💊"
        })
    if intent == "leki":
        return jsonify({
            'reply': "W przypadku przyjmowania leków najlepiej skontaktować się bezpośrednio z salonem, aby ocenić bezpieczeństwo zabiegu 💬 881 622 882"
        })

    # === 4️⃣ Generowanie odpowiedzi GPT z kontekstem ===
    phone_suggestion = ""
    # Subtelne zaproszenie do kontaktu co 3 wiadomości, tylko gdy ma sens
    if intent in ["emocje", "termin", "inne"] and msg_count % 3 == 0:
        phone_suggestion = (
            " Jeśli chcesz, możemy ustalić wszystko przez telefon — 881 622 882 💬"
            if intent == "termin"
            else " Jeśli masz pytania lub chcesz dobrać zabieg idealny dla siebie — zadzwoń, chętnie pomogę 💋 881 622 882"
        )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. \
                    Piszesz w przyjazny, ekspercki sposób. \
                    Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. \
                    Unikasz sztywnych, encyklopedycznych tekstów — zamiast tego doradzasz jak stylistka, która zna się na rzeczy. \
                    Używasz emotek z wyczuciem (💋✨🌿), nie przesadzasz. \
                    Każda odpowiedź ma maksymalnie 2–4 zdania. \
                    Unikaj powtarzania informacji i nie wspominaj ponownie o numerze telefonu, jeśli już został podany. \
                    Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust. \
                    Jeśli ktoś zapyta o coś spoza tej tematyki — grzecznie przekierowujesz, np: 'To pytanie wykracza poza moją specjalizację, skupmy się na tematach PMU, dobrze?' \
                    Twoim celem jest pomóc klientce zrozumieć zabiegi, pielęgnację i poczuć się zaopiekowaną."
                },
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
            max_tokens=600
        )

        reply = completion.choices[0].message.content.strip()

        # Dodaj sugestię kontaktu tylko jeśli kontekst uzasadnia
        if phone_suggestion and "881" not in reply:
            reply += phone_suggestion

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









