from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os

# === Inicjalizacja ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === Cennik ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie w cenie 💋"
}

# === Strona główna (frontend) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# === Wiadomość powitalna ===
@app.route('/start', methods=['GET'])
def start_message():
    welcome_text = "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨"
    return jsonify({'reply': welcome_text})

# === Endpoint chatu ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    text_lower = user_message.lower()

    # === 1️⃣ CENA ===
    price_triggers = ["ile", "koszt", "cena"]
    exclude_price = ["utrzymuje", "trwa", "gojenie", "czas", "dni"]
    if any(w in text_lower for w in price_triggers) and not any(e in text_lower for e in exclude_price):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': "Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋"})

    # === 2️⃣ TERMINY ===
    booking_words = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy mogę", "dostępny", "czy są miejsca"]
    if any(w in text_lower for w in booking_words):
        return jsonify({'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 Zadzwoń: 881 622 882"})

    # === 3️⃣ LEKI ===
    med_words = ["lek", "leki", "tabletki", "antybiotyk", "antykoncepc"]
    if any(w in text_lower for w in med_words):
        if "izotek" in text_lower:
            return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 Zabieg można wykonać po zakończeniu leczenia."})
        else:
            return jsonify({'reply': "Jeśli przyjmujesz leki, najlepiej skontaktować się z salonem, aby potwierdzić bezpieczeństwo zabiegu 🌸"})

    # === 4️⃣ DOPIGMENTOWANIE / KOREKTA ===
    if any(w in text_lower for w in ["dopigment", "korekt", "poprawk"]):
        if "kiedy" in text_lower or "mogę" in text_lower:
            reply = (
                "Dopigmentowanie zaleca się wykonać między 6. a 8. tygodniem po głównym zabiegu 🌿 "
                "Dzięki temu pigment zdąży się ustabilizować i efekt będzie równomierny 💋"
            )
        else:
            reply = (
                "Dopigmentowanie wykonuje się zwykle po 4–8 tygodniach od zabiegu 🌿 "
                "Wtedy pigment się stabilizuje, a skóra jest już w pełni zagojona. "
                "Skontaktuj się z salonem, żeby dobrać idealny termin 💋 881 622 882"
            )
        return jsonify({'reply': reply})

    # === 5️⃣ MOCZENIE BRWI ===
    if "brwi" in text_lower and "moczyć" in text_lower and ("kiedy" in text_lower or "mogę" in text_lower):
        reply = (
            "Brwi możesz delikatnie moczyć dopiero, gdy wszystkie strupki się złuszczą 🌿 "
            "Zazwyczaj po około 7–10 dniach od zabiegu ✨ Do tego czasu unikaj sauny, basenu i ekspozycji na słońce."
        )
        return jsonify({'reply': reply})

    # === 6️⃣ AFTERCARE (pielęgnacja po zabiegu) ===
    aftercare_words = ["moczyć", "myć", "smarować", "łuszczy", "swędzi", "goi", "piecze", "szczypie", "złuszcza", "maść", "balsam"]
    if any(w in text_lower for w in aftercare_words):
        if "brwi" in text_lower:
            reply = (
                "Nie mocz brwi przez pierwsze dni po zabiegu 🌿 "
                "To normalne, jeśli lekko się łuszczą lub swędzą — to proces gojenia. "
                "Stosuj maść zaleconą przez linergistkę i unikaj słońca przez ok. 10 dni ✨"
            )
        elif "usta" in text_lower:
            reply = (
                "Po zabiegu ust 💋 skóra może być delikatnie napięta lub sucha. "
                "Nawilżaj regularnie balsamem/maścią zaleconą przez linergistkę i unikaj gorących napojów przez kilka dni 🌿"
            )
        else:
            reply = (
                "Po zabiegu 🌸 nie mocz pigmentowanego miejsca, stosuj maść zaleconą przez linergistkę i daj skórze czas — pigment ustabilizuje się w kolejnych tygodniach ✨"
            )
        return jsonify({'reply': reply})

    # === 7️⃣ DOPRECYZOWANIE INTENCJI (np. "robiłam brwi tydzień temu") ===
    if any(w in text_lower for w in ["robiłam", "miałam", "byłam"]) and not any(x in text_lower for x in ["czy", "mogę", "dopigment", "moczyć", "goić", "łuszczy", "smarować"]):
        reply = (
            "Świetnie 🌿 Czy pytasz, jak teraz dbać o brwi po zabiegu, "
            "czy raczej chcesz je odświeżyć (dopigmentowanie)? 💋"
        )
        return jsonify({'reply': reply})

    # === 8️⃣ TRWAŁOŚĆ EFEKTU ===
    duration_keywords = ["utrzymuje", "utrzymują", "trwa", "trzyma się", "trzymają", "jak długo się trzyma"]
    if any(w in text_lower for w in duration_keywords):
        if "brwi" in text_lower:
            reply = (
                "Efekt makijażu permanentnego brwi utrzymuje się średnio 2–3 lata ✨ "
                "Wiele zależy od rodzaju skóry, pielęgnacji i ekspozycji na słońce 🌿"
            )
        elif "usta" in text_lower:
            reply = (
                "Makijaż permanentny ust utrzymuje się około 2 lat 💋 — "
                "z czasem kolor może delikatnie zblednąć, ale można go odświeżyć dopigmentowaniem 🌸"
            )
        else:
            reply = (
                "Makijaż permanentny utrzymuje się średnio 2–3 lata 🌿 "
                "Czas zależy od pielęgnacji, typu skóry i trybu życia ✨"
            )
        return jsonify({'reply': reply})

    # === 9️⃣ GOJENIE ===
    healing_keywords = ["goi", "gojenie", "jak długo się goi", "kiedy się zagoi"]
    if any(w in text_lower for w in healing_keywords):
        if "brwi" in text_lower:
            reply = (
                "Po zabiegu brwi goją się zwykle 5–10 dni 🌿 "
                "To normalne, że kolor może się zmieniać — pigment stabilizuje się w ciągu kilku tygodni ✨"
            )
        elif "usta" in text_lower:
            reply = (
                "Usta goją się szybciej niż brwi 💋 — zazwyczaj 3–5 dni. "
                "Po tym czasie pigment zaczyna się delikatnie wyrównywać 🌿"
            )
        else:
            reply = "Zazwyczaj gojenie po makijażu permanentnym trwa około tygodnia 🌸"
        return jsonify({'reply': reply})

    # === 🔟 GPT fallback ===
    try:
        system_prompt = (
            "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
            "Piszesz w przyjazny, ekspercki sposób. Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. "
            "Używasz emotek z wyczuciem (💋✨🌿), maksymalnie 2–4 zdania. "
            "Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust. "
            "Gdy rozmowa dotyczy decyzji lub obaw, możesz naturalnie zaprosić do kontaktu: 881 622 882. "
            "Nie wspominaj o promocjach ani sprzedaży."
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


# === Uruchomienie serwera ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)














