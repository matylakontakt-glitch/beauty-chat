from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os

# === Inicjalizacja ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === Konfiguracja podstawowa ===
PHONE = "881 622 882"

PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1000 zł — dopigmentowanie w cenie 💋"
}

# ——— Pomocnicze ———
def any_in(text: str, words) -> bool:
    return any(w in text for w in words)

def all_in(text: str, words) -> bool:
    return all(w in text for w in words)

def reply_json(msg: str):
    return jsonify({"reply": msg})

# === Front (index.html) ===
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

# === Wiadomość powitalna (dla frontu) ===
@app.route("/start", methods=["GET"])
def start_message():
    return reply_json(
        "Cześć! 👋 Jestem Beauty Ekspertką salonu — chętnie odpowiem na Twoje pytania o makijaż permanentny brwi i ust 💋✨"
    )

# === Główny endpoint chatu ===
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return reply_json("Napisz coś, żebym mogła Ci pomóc 💬")

    t = user_message.lower()

    # ——— Rozpoznanie intencji (flagi) ———
    price_triggers = ["ile", "koszt", "cena"]
    price_exclude  = ["utrzymuje", "trwa", "trzyma się", "gojenie", "dni", "czas"]

    terms_triggers = ["termin", "umówić", "zapis", "rezerwac", "wolne", "dostępny", "czy są miejsca", "kalendarz"]

    med_triggers = ["lek", "leki", "tabletki", "antybiotyk", "antykoncepc"]
    izotek_words = ["izotek", "isotretinoin", "izotretinoina", "roaccutane"]

    dopigment_words = ["dopigment", "korekt", "poprawk"]

    aftercare_words = ["moczyć", "myć", "smarować", "łuszczy", "złuszcza", "swędzi", "goi", "piecze", "szczypie", "maść", "balsam", "higiena"]
    moisten_brows_question = ("brwi" in t) and ("moczyć" in t) and any_in(t, ["kiedy", "mogę", "od kiedy"])

    duration_words = ["utrzymuje", "utrzymują", "trwa", "trzyma się", "trzymają", "jak długo się trzyma", "na ile wystarcza", "po jakim czasie zanika"]
    healing_words  = ["goi", "gojenie", "kiedy się zagoi", "po jakim czasie się goi"]

    past_experience_words = ["robiłam", "miałam", "byłam"]  # nie przesądzamy intencji

    has_question_intent = any_in(t, ["czy", "kiedy", "mogę", "jak", "ile"])

    mentions_brows = any_in(t, ["brwi", "brew", "brw"])
    mentions_lips  = any_in(t, ["usta", "ust"])

    # ——— PRIORYTETY I ROZSTRZYGANIE NIEJASNOŚCI ———

    # 0) Dopytanie przy niejasnej „przeszłości” bez pytania
    if any_in(t, past_experience_words) and not any_in(t, dopigment_words + aftercare_words + duration_words + healing_words + ["czy", "mogę", "kiedy"]):
        return reply_json(
            "Świetnie 🌿 Czy pytasz o pielęgnację po zabiegu, czy raczej o dopigmentowanie (drugi etap po 6–8 tygodniach)? 💋"
        )

    # 1) DOPIGMENTOWANIE (ma pierwszeństwo nad terminami)
    if any_in(t, dopigment_words):
        if any_in(t, ["kiedy", "mogę", "od kiedy", "po ilu"]):
            return reply_json(
                "Dopigmentowanie zaleca się wykonać między 6. a 8. tygodniem po głównym zabiegu 🌿 "
                "W tym czasie pigment się stabilizuje i efekt będzie najrówniejszy 💋"
            )
        # Jeśli jednocześnie pojawiają się „terminy” i „dopigment” — najpierw reguła merytoryczna, potem delikatne CTA
        if any_in(t, terms_triggers):
            return reply_json(
                f"Dopigmentowanie zwykle planujemy po 6–8 tygodniach od zabiegu 🌿 "
                f"Jeśli chcesz, ustalimy dogodny termin telefonicznie: {PHONE} 💗"
            )
        # W pozostałych przypadkach eleganckie dopytanie
        return reply_json(
            "Czy chcesz ustalić, *kiedy* najlepiej wykonać dopigmentowanie (6–8 tygodni), czy od razu porozmawiać o terminie? 📅"
        )

    # 2) CENA (wykluczamy durację/gojenie)
    if any_in(t, price_triggers) and not any_in(t, price_exclude):
        if mentions_lips:
            return reply_json(PRICE_LIST["usta"])
        if mentions_brows:
            return reply_json(PRICE_LIST["brwi"])
        return reply_json("Nie mam tej pozycji w cenniku 🌸 — mogę pomóc w tematach brwi i ust permanentnych 💋")

    # 3) MOCZENIE BRWI — pytanie „kiedy mogę/od kiedy mogę moczyć”
    if moisten_brows_question:
        return reply_json(
            "Brwi możesz delikatnie moczyć dopiero, gdy wszystkie strupki się złuszczą 🌿 "
            "Zazwyczaj po około 7–10 dniach od zabiegu. Do tego czasu unikaj sauny, basenu i ekspozycji na słońce ✨"
        )

    # 4) AFTERCARE (ogólne pytania pielęgnacyjne)
    if any_in(t, aftercare_words):
        if mentions_brows:
            return reply_json(
                "Po zabiegu brwi nie mocz ich przez pierwsze dni 🌿 "
                "Lekka łuska lub swędzenie są normalne — to gojenie. "
                "Stosuj maść zaleconą przez linergistkę i unikaj słońca ok. 10 dni ✨"
            )
        if mentions_lips:
            return reply_json(
                "Po zabiegu ust 💋 skóra może być delikatnie sucha. "
                "Nawilżaj regularnie balsamem/maścią zaleconą przez linergistkę i unikaj gorących napojów przez kilka dni 🌿"
            )
        return reply_json(
            "Po zabiegu 🌸 nie mocz pigmentowanego miejsca, stosuj zaleconą maść i daj skórze czas — "
            "pigment ustabilizuje się w kolejnych tygodniach ✨"
        )

    # 5) TRWAŁOŚĆ EFEKTU (2–3 lata) — przed gojeniem
    if any_in(t, duration_words):
        if mentions_brows:
            return reply_json(
                "Efekt makijażu permanentnego brwi utrzymuje się średnio 2–3 lata ✨ "
                "Wpływ ma pielęgnacja, typ skóry i ekspozycja na słońce 🌿"
            )
        if mentions_lips:
            return reply_json(
                "Makijaż permanentny ust utrzymuje się około 2 lat 💋 — "
                "z czasem kolor delikatnie blednie, można odświeżyć dopigmentowaniem 🌸"
            )
        return reply_json(
            "Makijaż permanentny najczęściej utrzymuje się 2–3 lata 🌿 — zależnie od pielęgnacji i typu skóry ✨"
        )

    # 6) GOJENIE (ile trwa)
    if any_in(t, healing_words):
        if mentions_brows:
            return reply_json(
                "Brwi goją się zwykle 5–10 dni 🌿 "
                "Kolor może się zmieniać — pigment stabilizuje się w kolejnych tygodniach ✨"
            )
        if mentions_lips:
            return reply_json(
                "Usta goją się szybciej niż brwi 💋 — zazwyczaj 3–5 dni. "
                "Początkowo kolor bywa intensywniejszy, później się uspokaja 🌿"
            )
        return reply_json("Gojenie po makijażu permanentnym trwa zwykle około tygodnia 🌸")

    # 7) LEKI (z wyjątkiem Izoteku)
    if any_in(t, med_triggers):
        if any_in(t, izotek_words):
            return reply_json(
                "Podczas kuracji Izotekiem nie wykonuje się makijażu permanentnego 🌿 "
                "Zabieg planujemy po zakończeniu leczenia."
            )
        return reply_json(
            "Jeśli przyjmujesz leki, najlepiej skontaktować się bezpośrednio z salonem, aby potwierdzić bezpieczeństwo zabiegu 🌸"
        )

    # 8) TERMINY / ZAPISY (na końcu, po wszystkich merytorycznych regułach)
    if any_in(t, terms_triggers) or all_in(t, ["kiedy", "mogę"]):
        return reply_json(f"Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸 Zadzwoń: {PHONE}")

    # 9) DOPRECYZOWANIE, gdy pytanie ogólne „kiedy mogę” bez kontekstu
    if has_question_intent and not (mentions_brows or mentions_lips) and not any_in(t, ["pmu", "makijaż permanentny"]):
        return reply_json("Czy chodzi Ci o brwi czy usta? Podpowiem dokładnie, jak postąpić ✨")

    # 10) Fallback — GPT (krótko, kobieco, bez medycznych porad)
    try:
        system_prompt = (
            "Jesteś Beauty Chat — inteligentnym asystentem salonu beauty. "
            "Odpowiadasz krótko (2–4 zdania), kobieco i profesjonalnie. "
            "Unikasz porad medycznych i tematów spoza PMU brwi/ust. "
            "Gdy rozmowa dotyczy decyzji lub obaw, możesz naturalnie zaprosić do kontaktu telefonicznego: "
            f"{PHONE}. Używaj emotek oszczędnie (💋✨🌿)."
        )
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.45,
            max_tokens=350,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
        )
        text = completion.choices[0].message.content.strip()
        return reply_json(text)
    except Exception as e:
        return reply_json(f"Ups! Coś poszło nie tak 💔 ({e})")

# === Uruchomienie serwera (Render/localhost) ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)















