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

    # 1️⃣ CENA — nie myli „ile się utrzymuje” z kosztami
    price_triggers = ["ile", "koszt", "cena"]
    exclude_price = ["utrzymuje", "trwa", "gojenie", "czas", "dni"]
    if any(w in text_lower for w in price_triggers) and not any(e in text_lower for e in exclude_price):
        if "usta" in text_lower or "ust" in text_lower:
            return jsonify({'reply': PRICE_LIST["usta"]})
        elif "brwi" in text_lower or "brew" in text_lower:
            return jsonify({'reply': PRICE_LIST["brwi"]})
        else:
            return jsonify({'reply': "Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋"})

    # 2️⃣ TERMINY
    booking_words = ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy mogę", "dostępny", "czy są miejsca"]
    if any(w in text_lower for w in booking_words):
        return jsonify({'reply': "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 Zadzwoń: 881 622 882"})

    # 3️⃣ LEKI (poza Izotekiem)
    med_words = ["lek", "leki", "tabletki", "antybiotyk", "antykoncepc"]
    if any(w in text_lower for w in med_words):
        if "izotek" in text_lower:
            return jsonify({'reply': "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 Zabieg można wykonać po zakończeniu leczenia."})
        else:
            return jsonify({'reply': "Jeśli przyjmujesz leki, najlepiej skontaktować się bezpośrednio z salonem, aby potwierdzić bezpieczeństwo zabiegu 🌸"})

    # 4️⃣ DOPIGMENTOWANIE / KOREKTA
    if any(w in text_lower for w in ["dopigment", "korekt", "poprawk"]):
        reply = (
            "Dopigmentowanie wykonuje się zwykle po 4–8 tygodniach od zabiegu 🌿 "
            "Wtedy pigment się stabilizuje, a skóra jest już w pełni zagojona. "
            "Skontaktuj się z salonem, żeby dobrać idealny termin 💋 881 622 882"
        )
        return jsonify({'reply': reply})

    # 5️⃣ AFTERCARE (pielęgnacja po zabiegu)
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

    # 6️⃣ NIEJASNA INTENCJA (np. „robiłam brwi tydzień temu”)
    if any(w in text_lower for w in ["robiłam", "miałam", "byłam"]) and not any(x in text_lower for x in ["czy", "mogę", "dopigment", "moczyć", "goić", "łuszczy", "smarować"]):
        reply = (
            "Świetnie 🌿 Czy pytasz, jak teraz dbać o brwi po zabiegu, "
            "czy raczej chcesz je odświeżyć (dopigmentowanie)? 💋"
        )
        return jsonify({'reply': reply})

    # 7️⃣ CZASY / INTENCJE
    NOW_WORDS = ["mam", "swędzi", "łuszczy się", "goi się", "piecze", "szczypie", "spuchnięte"]
    FUTURE_WORDS = ["będę", "czy po", "czy potem", "czy po zabiegu", "czy po brwiach", "czy po ustach"]

    if any(w in text_lower for w in NOW_WORDS):
        context = "aftercare"
    elif any(w in text_lower for w in FUTURE_WORDS):
        context = "healing_info"
    else:
        context = "general"

    # 8️⃣ ODPOWIEDZI wg kontekstu
    if context == "healing_info":
        if "brwi" in text_lower:
            reply = (
                "Po zabiegu brwi zwykle goją się ok. 5–10 dni 🌿 — może wystąpić lekkie łuszczenie. "
                "Kolor z czasem się stabilizuje, a efekt końcowy jest widoczny po kilku tygodniach ✨"
            )
        elif "usta" in text_lower:
            reply = (
                "Usta goją się szybciej niż brwi 💋 — najczęściej 3–5 dni. "
                "W tym czasie pigment może wyglądać intensywniej, ale potem się uspokoi 🌿"
            )
        else:
            reply = "Gojenie po makijażu permanentnym trwa zwykle 5–10 dni 🌸, a pigment stabilizuje się w ciągu 3–4 tygodni."
        return jsonify({'reply': reply})

    # 9️⃣ GPT fallback – jeśli nic nie pasuje
    try:
        system_prompt = (
            "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
            "Piszesz w przyjazny, ekspercki sposób. Odpowiadasz konkretnie, ale z klasą i kobiecą lekkością. "
            "Unikasz sztywnych opisów — doradzasz jak stylistka, która zna się na rzeczy. "
            "Używasz emotek z wyczuciem (💋✨🌿), maksymalnie 2–4 zdania. "
            "Nie odpowiadasz na pytania niezwiązane z makijażem permanentnym brwi i ust. "
            "Nie wspominaj o promocjach ani sprzedaży. "
            "Gdy rozmowa dotyczy obaw, decyzji lub efektów, możesz delikatnie zaprosić do kontaktu telefonicznego: 881 622 882."
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













