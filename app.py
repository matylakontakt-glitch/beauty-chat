from flask import Flask, request, jsonify, send_from_directory, session
from dotenv import load_dotenv
from openai import OpenAI
import os

# === Inicjalizacja ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "beauty_secret_key")  # dla sesji
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
    welcome_text = (
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania "
        "o makijaż permanentny brwi i ust 💋✨"
    )
    session['msg_count'] = 0
    session['last_intent'] = None
    return jsonify({'reply': welcome_text})

# === Klasyfikacja intencji użytkowniczki ===
def classify_intent(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["termin", "umówić", "zapisać", "rezerwacja", "wolne"]):
        return "termin"
    if any(w in text_lower for w in ["boję", "strach", "pewna", "nie wiem", "obawiam"]):
        return "emocje"
    if any(w in text_lower for w in ["cena", "koszt", "ile", "brwi", "usta"]):
        return "info"
    if any(w in text_lower for w in ["izotek"]):
        return "izotek"
    if any(w in text_lower for w in ["lek", "antybiotyk", "tabletki", "biorę", "leczę", "leki"]):
        return "leki"
    return "inne"

# === Endpoint chatu ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()
    session['msg_count'] = session.get('msg_count', 0) + 1
    intent = classify_intent(user_message)
    session['last_intent'] = intent

    # === 1️⃣ Pytania o leki ===
    if intent == "izotek":
        return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego — należy odczekać minimum 6 miesięcy po zakończeniu leczenia 🌿"})
    if intent == "leki":
        return jsonify({'reply': "W przypadku przyjmowania leków najlepiej skontaktować się bezpośrednio z salonem — ocenimy indywidualnie, czy zabieg jest bezpieczny 💬"})

    # === 2️⃣ Ceny ===
    price_keywords = ["ile", "koszt", "cena"]
    if any(word in text_lower for word in price_keywords):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 3️⃣ Terminy ===
    if intent == "termin":
        return jsonify({'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"})

    # === 4️⃣ Tworzenie promptu systemowego ===
    msg_count = session['msg_count']
    phone_suggestion = ""

    # Logika subtelnego zaproszenia do kontaktu
    if intent in ["emocje", "termin"] and msg_count % 3 == 0:
        phone_suggestion = (
            " Jeśli chcesz, możemy ustalić wszystko przez telefon — 881 622 882 💬"
            if intent == "termin" else
            " Jeśli masz wątpliwości, możemy spokojnie omówić to przez telefon — 881 622 882 💋"
        )

    system_prompt = f"""
    Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. 
    Twoja rola to doradzić z klasą, spokojem i empatią. 
    Znasz wszystkie etapy makijażu permanentnego brwi i ust — od przygotowania po pielęgnację.
    Odpowiadasz konkretnie (2–4 zdania), kobieco, przyjaźnie i ciepło. 
    Unikasz encyklopedycznych opisów i słów typu 'promocja', 'sprzedaż', 'oferta'.
    Nie powtarzaj numeru telefonu, jeśli już go użyłaś w ostatnich odpowiedziach.
    Jeśli rozmowa dotyczy decyzji, obaw lub terminu — możesz delikatnie dodać zdanie o kontakcie telefonicznym.
    Nie udzielasz porad medycznych. Jeśli pytanie dotyczy leków — napisz, że należy skontaktować się z salonem.
    Jeśli ktoś pyta o Izotek — powiedz, że zabiegu nie wykonuje się w trakcie kuracji i trzeba odczekać 6 miesięcy.
    Unikasz powtarzania treści, dbasz o naturalny ton rozmowy.
    {phone_suggestion}
    """

    # === 5️⃣ Wywołanie OpenAI ===
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=500
        )
        reply = completion.choices[0].message.content.strip()
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








