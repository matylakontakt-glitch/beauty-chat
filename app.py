from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random

# === Inicjalizacja ===
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
        "Zabieg nie jest wykonywany w ciąży, podczas karmienia piersią, przy infekcjach, chorobach nowotworowych lub przyjmowaniu sterydów i retinoidów.",
        "Przed zabiegiem nie pij kawy ani alkoholu — kofeina i alkohol rozrzedzają krew, przez co pigment może się gorzej przyjąć lub szybciej wypłukać 💋"
    ],
    "pielęgnacja": [
        "Po zabiegu nie dotykaj, nie drap i nie zrywaj strupków. Skóra goi się ok. 7 dni, a kolor stabilizuje się po 30 dniach ✨",
        "Unikaj słońca, sauny, basenu i intensywnego wysiłku przez minimum tydzień 🌿",
        "Brwi po zabiegu przemywaj przegotowaną wodą 3–5 razy dziennie przez pierwsze 3 dni, potem delikatnie nawilżaj cienką warstwą preparatu 💧"
    ],
    "techniki_brwi": [
        "Metoda pudrowa (Powder Brows) daje miękki, cieniowany efekt przypominający makijaż cieniem — idealna dla każdego typu skóry.",
        "Metoda ombre tworzy delikatny gradient: jaśniejsze brwi u nasady i ciemniejsze na końcach, dla naturalnego efektu 3D ✨",
        "Metoda łączona (Hybrid) to połączenie włosków z przodu i cienia w dalszej części brwi — naturalny, ale wyraźny efekt 💋",
        "Nano Brows (pixelowa technika) to bardzo precyzyjne kropkowanie, które daje efekt hiperrealistycznych brwi."
    ],
    "techniki_usta": [
        "Lip Blush to delikatne podkreślenie naturalnego koloru ust — efekt świeżych, lekko zaróżowionych warg 💋",
        "Full Lip Color zapewnia jednolite, pełne wypełnienie kolorem, przypominające klasyczną szminkę 💄",
        "Kontur ust (Lip Liner) pozwala wyrównać kształt i delikatnie podkreślić linię warg, zachowując naturalność ✨"
    ],
    "trwalosc": [
        "Efekt makijażu permanentnego utrzymuje się średnio 1–3 lata. Po tym czasie zalecane jest odświeżenie pigmentu 💋",
        "Zbyt szybkie blaknięcie może wynikać z tłustej cery, ekspozycji na słońce lub nieprzestrzegania zaleceń pozabiegowych.",
        "Trwałość zależy od pielęgnacji i indywidualnych procesów regeneracji skóry 🌿"
    ],
    "fakty_mity": [
        "Zabieg nie jest bolesny — dzięki znieczuleniu większość klientek czuje jedynie lekkie szczypanie ✨",
        "Makijaż permanentny nie powoduje wypadania włosków — pigment wprowadzany jest bardzo płytko.",
        "To nie tatuaż — pigment z czasem naturalnie blednie, dlatego po roku lub dwóch warto zrobić odświeżenie 💋"
    ]
}

# === SŁOWA KLUCZOWE ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        "przeciwwskaz", "chorob", "lek", "tablet", "ciąża", "kawa", "pić kaw", "napój",
        "alkohol", "wino", "piwo", "izotek", "heviran", "hormony"
    ],
    "pielęgnacja": [
        "pielęgnac", "gojenie", "po zabiegu", "dbac", "dbanie", "po wszystkim",
        "strup", "łuszcz", "smarowac", "złuszczanie"
    ],
    "techniki_brwi": [
        "brwi", "ombre", "pudrow", "powder", "microblading", "hybrid", "pixel", "nano", "metoda pudrowa", "metoda ombre"
    ],
    "techniki_usta": [
        "usta", "lip", "blush", "kontur", "liner", "full lip", "aquarelle", "ust", "wargi"
    ],
    "trwalosc": [
        "utrzymuje", "trwa", "blak", "kolor", "odświeżenie", "zanika", "blednie", "czas", "trwałość"
    ],
    "fakty_mity": [
        "mit", "fakt", "bol", "ból", "włoski", "usuwa", "laser", "prawda", "fałsz"
    ]
}

INTENT_PRIORITIES = ["przeciwwskazania", "pielęgnacja", "techniki_brwi", "techniki_usta", "trwalosc", "fakty_mity"]

FOLLOWUP_QUESTIONS = {
    "techniki_brwi": "Czy pytasz o metody makijażu brwi, jak pudrowa czy ombre? 🌿",
    "techniki_usta": "Czy chodzi Ci o techniki ust, np. Lip Blush albo Full Lip Color? 💋",
    "trwalosc": "Czy pytasz, bo dopiero rozważasz zabieg, czy masz już wykonany i chcesz wiedzieć, jak długo efekt się utrzymuje? ✨",
    "pielęgnacja": "Czy chodzi Ci o pielęgnację po zabiegu, czy o przygotowanie przed pierwszym PMU? 💫"
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

# === FUNKCJE POMOCNICZE ===
def detect_intent(text):
    matched = []
    for intent, words in INTENT_KEYWORDS.items():
        if any(w in text for w in words):
            matched.append(intent)
    if not matched:
        return None
    for priority in INTENT_PRIORITIES:
        if priority in matched:
            return priority
    return matched[0]

def random_emojis(n=3):
    all_emojis = ["💋", "✨", "🌿", "💄", "🌸"]
    return " ".join(random.sample(all_emojis, n))

# === GŁÓWNY ENDPOINT CHATU ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()

    if not user_message:
        return jsonify({'reply': 'Napisz coś, żebym mogła Ci pomóc 💬'})

    # Sesja
    if user_ip not in SESSION_DATA:
        SESSION_DATA[user_ip] = {"message_count": 0, "last_intent": None, "asked_context": False, "last_phone": False}
    SESSION_DATA[user_ip]["message_count"] += 1
    count = SESSION_DATA[user_ip]["message_count"]

    # === CENNIK ===
    if any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        if count % 3 == 0 and not SESSION_DATA[user_ip]["last_phone"]:
            all_prices += "\n\nJeśli chcesz, mogę pomóc dobrać termin 💋 881 622 882"
            SESSION_DATA[user_ip]["last_phone"] = True
        else:
            SESSION_DATA[user_ip]["last_phone"] = False
        return jsonify({'reply': all_prices})

    # === TERMINY ===
    if any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]):
        reply = "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        if count % 3 == 0 and not SESSION_DATA[user_ip]["last_phone"]:
            reply += " Zadzwoń: 881 622 882 💋"
            SESSION_DATA[user_ip]["last_phone"] = True
        else:
            SESSION_DATA[user_ip]["last_phone"] = False
        return jsonify({'reply': reply})

    # === INTENCJE ===
    intent = detect_intent(text_lower) or SESSION_DATA[user_ip].get("last_intent")
    SESSION_DATA[user_ip]["last_intent"] = intent

    if intent and intent in KNOWLEDGE:
        if not SESSION_DATA[user_ip]["asked_context"] and intent in FOLLOWUP_QUESTIONS:
            SESSION_DATA[user_ip]["asked_context"] = True
            return jsonify({'reply': FOLLOWUP_QUESTIONS[intent]})
        reply = random.choice(KNOWLEDGE[intent])
        # dodaj emotki co 2 wiadomości
        if count % 2 == 0:
            reply += f" {random_emojis(3)}"
        # numer telefonu maks. co 3 wiadomość i nigdy dwa razy pod rząd
        if count % 3 == 0 and not SESSION_DATA[user_ip]["last_phone"]:
            reply += random.choice([
                "\n\nJeśli chcesz, mogę pomóc dobrać termin 💋 881 622 882",
                "\n\nMasz ochotę na konsultację? Zadzwoń: 881 622 882 🌿"
            ])
            SESSION_DATA[user_ip]["last_phone"] = True
        else:
            SESSION_DATA[user_ip]["last_phone"] = False
        return jsonify({'reply': reply})

    # === FALLBACK GPT ===
    system_prompt = (
        "Jesteś Beauty Chat — inteligentną, empatyczną asystentką salonu PMU. "
        "Odpowiadasz konkretnie, z klasą i kobiecą lekkością. "
        "Nie wymyślasz nowych informacji, korzystasz tylko z wiedzy o makijażu permanentnym brwi i ust. "
        "Nie wspominaj o promocjach. Nie powtarzaj się. "
        "Używaj emotek z wyczuciem (💋✨🌿) i pisz maksymalnie 2–4 zdania."
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


# === URUCHOMIENIE ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

















