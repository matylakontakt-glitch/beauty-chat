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
    welcome_text = (
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨"
    )
    return jsonify({'reply': welcome_text})

# === Endpoint chatu (backend) ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # === 1️⃣ CENA ===
    price_keywords = ["ile", "koszt", "cena"]
    excluded_phrases = ["utrzymuje", "trwa", "gojenie", "czas", "dni"]
    if any(word in text_lower for word in price_keywords) and not any(p in text_lower for p in excluded_phrases):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 2️⃣ TERMINY ===
    booking_keywords = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy mogę", "czy są miejsca", "dostępny"]
    if any(word in text_lower for word in booking_keywords):
        return jsonify({'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 Zadzwoń: 881 622 882"})

    # === 3️⃣ LEKI ===
    medication_keywords = ["lek", "leki", "tabletki", "antybiotyk", "antybiotyki", "antykoncepcję", "antykoncepcja"]
    if any(word in text_lower for word in medication_keywords):
        if "izotek" in text_lower:
            return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 Zabieg można wykonać po zakończeniu leczenia."})
        else:
            return jsonify({'reply': "W przypadku przyjmowania leków najlepiej skontaktować się bezpośrednio z salonem, by upewnić się, że zabieg będzie bezpieczny 🌸"})

    # === 4️⃣ ANALIZA CZASU I INTENCJI ===
    NOW_WORDS = ["mam", "jestem", "mnie", "swędzi", "łuszczy się", "goi się", "odpada", "szczypie"]
    PAST_WORDS = ["miałam", "robiłam", "byłam"]
    FUTURE_WORDS = ["będę", "czy po", "czy potem", "czy po zabiegu", "czy po brwiach", "czy po ustach"]

    if any(w in text_lower for w in NOW_WORDS):
        context = "aftercare"
    elif any(w in text_lower for w in FUTURE_WORDS):
        context = "healing_info"
    elif any(w in text_lower for w in PAST_WORDS):
        context = "experience"
    else:
        context = "general"

    # === 5️⃣ ODPOWIEDZI WG KONTEKSTU ===
    if context == "aftercare":
        if "brwi" in text_lower:
            reply = (
                "To naturalne 🌿 Brwi po zabiegu mogą delikatnie swędzieć lub się łuszczyć — to znak, że skóra się goi. "
                "Smaruj je zaleconą maścią od linergistki i unikaj słońca. "
                "Pigment się stabilizuje w ciągu kilku tygodni ✨"
            )
        elif "usta" in text_lower:
            reply = (
                "Po zabiegu ust 💋 skóra może być lekko napięta lub sucha — to normalne. "
                "Pamiętaj o regularnym nawilżaniu balsamem lub maścią i unikaj gorących napojów przez kilka dni. "
                "Efekt końcowy pojawi się po kilku tygodniach 🌸"
            )
        else:
            reply = (
                "Po zabiegu 🌿 najważniejsza jest delikatna pielęgnacja i cierpliwość. "
                "Nie mocz obszaru pigmentacji, smaruj go zalecaną maścią i unikaj słońca — pigment się ułoży ✨"
            )
        return jsonify({'reply': reply})

    elif context == "healing_info":
        if "brwi" in text_lower:
            reply = (
                "Po zabiegu brwi zwykle goją się ok. 5–10 dni 🌿 — mogą lekko się łuszczyć lub swędzieć. "
                "To naturalny etap regeneracji skóry, a kolor z czasem łagodnieje ✨"
            )
        elif "usta" in text_lower:
            reply = (
                "Usta po zabiegu goją się szybciej niż brwi 💋 — zazwyczaj w 3–5 dni. "
                "W tym czasie mogą być delikatnie suche lub napięte, ale to całkowicie normalne 🌿"
            )
        else:
            reply = (
                "Proces gojenia po PMU trwa zwykle od 5 do 10 dni 🌸, a efekt końcowy stabilizuje się w ciągu kilku tygodni."
            )
        return jsonify({'reply': reply})

    elif context == "experience":
        reply = (
            "O, czyli masz już doświadczenie z PMU ✨ To super! Każda skóra reaguje inaczej, "
            "ale zasady pielęgnacji po zabiegu są zawsze podobne 🌿"
        )
        return jsonify({'reply': reply})

    # === 6️⃣ GPT – DLA INNYCH PYTAŃ ===
    try:
        system_prompt = (
            "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
            "Piszesz w przyjazny, ekspercki sposób. Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. "
            "Unikasz sztywnych opisów — doradzasz jak stylistka, która zna się na rzeczy. "
            "Używasz emotek z wyczuciem (💋✨🌿), maksymalnie 2–4 zdania. "
            "Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust. "
            "Nie wspominaj o promocjach, ofertach ani sprzedaży. "
            "Co pewien czas, gdy to naturalne, dodaj delikatne zaproszenie do kontaktu: "
            "'Jeśli chcesz, możemy ustalić wszystko przez telefon 💋 881 622 882' lub "
            "'Zadzwoń, a pomożemy Ci znaleźć idealny termin ✨'."
        )

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

# === URUCHOMIENIE SERWERA ===
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False
    )












