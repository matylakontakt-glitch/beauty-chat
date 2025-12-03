from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os

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

# === Endpoint chatu (backend) ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # === 1️⃣ Sprawdzenie, czy pytanie dotyczy ceny ===
    price_keywords = ["ile", "koszt", "cena"]
    if any(word in text_lower for word in price_keywords):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': 'Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋'})

    # === 2️⃣ Sprawdzenie, czy pytanie dotyczy terminów ===
    booking_keywords = [
        "termin", "termine", "zapis", "umówić", "wolne", "rezerwacja",
        "dostępny", "kiedy mogę", "czy są miejsca"
    ]
    if any(word in text_lower for word in booking_keywords):
        return jsonify({
            'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        })

    # === 3️⃣ Standardowa odpowiedź GPT ===
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. \
                Piszesz w przyjazny, ekspercki sposób. \
                Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. \
                Unikasz sztywnych, encyklopedycznych tekstów — zamiast tego doradzasz jak stylistka, która zna się na rzeczy. \
                Używasz emotek z wyczuciem (💋✨🌿), nie przesadzasz. \
                Każda odpowiedź ma maksymalnie 2–4 zdania. \
                Co 3-5 odpowiedzi (nie zawsze, tylko naturalnie, wtedy gdy rozmowa dotyczy decyzji, obaw, zaufania lub efektu zabiegu)\
                Dodaj delikatne, ludzkie zaproszenie do kontaktu telefonicznego - np: \
                ' Jeśli chcesz mozemy ustalić wszystko przez telefon - 881 622 882', albo \
                ' Jeśli wolisz porozmawiać zadzwon, razem znajdziemy najlepsze rozwiązanie - 881 622 882' albo \
                ' Zadzwoń, a pomoemy Ci znaleźć idealny termin dla Ciebie - 881 622 882' \
                Wybieraj te zdania tylko wtedy gdy to naturalne dla kontekstu rozmowy. \
                Nie dodawaj ich do kazdej odpowiedzi. \
                Nie powtarzaj tego samego dwa razy. \
                Nie uzywaj słów typu 'promocja', 'oferta', 'sprzedaz'. \
                Unikasz długich opisów, tylko sedno — z klasą, ciepłem i pewnością. \
                Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust. \
                Jeśli ktoś zapyta o coś spoza tej tematyki — grzecznie przekierowujesz, np: 'To pytanie wykracza poza moją specjalizację, skupmy się na tematach PMU, dobrze?' \
                Twoim celem jest pomóc klientce zrozumieć zabiegi, pielęgnację i poczuć się zaopiekowaną."},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
            max_tokens=600
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 ({e})"

    return jsonify({'reply': reply})


# === Uruchomienie serwera ===
if __name__ == '__main__':
    app.run(debug=True)







