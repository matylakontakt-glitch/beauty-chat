from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re
from collections import deque

# === DANE SALONU I WIEDZA (PRZENIESIONE Z knowledgeBase.ts) ===
# TA WIEDZA JEST PRZEKAZYWANA DO GPT W FALLBACKU!
PMU_FULL_KNOWLEDGE = """
Jesteś **ekspertką/ekspertem salonu** z 20-letnim doświadczeniem w mikropigmentacji. Wypowiadasz się w imieniu salonu, używając formy "nasz salon," "eksperci robią," "możemy doradzić."

DANE SALONU:
- Adres: ul. Junikowska 9
- Godziny otwarcia: Poniedziałek - Piątek: 09:00 - 19:00
- Kontakt: 881 622 882
- Zespół: W naszym salonie zabiegi wykonuje certyfikowany i zgrany **zespół linergistek** z wieloletnim doświadczeniem. Każda z nich specjalizuje się w różnych aspektach makijażu permanentnego, co gwarantuje najwyższą jakość i dobór idealnej techniki. Aby potwierdzić personalia eksperta, który będzie Cię przyjmował, prosimy o kontakt telefoniczny z recepcją.
- Czas trwania zabiegu: Około 2-3 godzin (w zależności od obszaru i techniki).

DEFINICJE I FAKTY:
- Makijaż permanentny (PMU/mikropigmentacja): Wprowadzenie pigmentu płytko do naskórka lub granicy naskórkowo-skórnej.
- Różnica vs Tatuaż: Tatuaż jest w skórze właściwej. PMU jest półtrwały (1-3 lata, czasem do 5).
- Bezpieczeństwo chemiczne: Pigmenty muszą spełniać normy UE REACH 2020/2081 (np. limit ołowiu 0,00007%). Używamy tylko atestowanych, bezpiecznych barwników.

TECHNIKI - BRWI:
1. Microblading (Włoskowa): Manualne nacinanie skóry ("piórko"). Efekt naturalnego włosa. Mniej trwała (1-2 lata). ODRADZANA przy skórze tłustej (rozmywa się, słabo goi).
2. Pudrowa (Powder Brows): Maszynowe cieniowanie, efekt "przyprószenia". Bardziej trwała (2-3 lata), idealna dla każdego typu skóry (także tłustej).
3. Ombre Brows: Gradient – jaśniejsza nasada, ciemniejszy koniec i dół.
4. Hybrydowa (Combo): Włoski na początku łuku + cień na reszcie.
5. Nano Brows (Pixelowa): Maszynowe mikrokropki. Najmniej inwazyjna, hiperrealistyczny efekt. Hit 2025.
6. Metoda Wypełnienia (Insta): Mocny, graficzny efekt (niemodne, nienaturalne).

TECHNIKI - USTA:
- Lip Blush: Akwarelowe, delikatne uwydatnienie czerwieni.
- Full Lip Color: Efekt szminki.
- Wymagana osłona przeciwwirusowa (Heviran) 3 dni przed i 3 dni po zabiegu (profilaktyka opryszczki).

**UWAGA: W naszym salonie nie wykonujemy makijażu permanentnego powiek (eyeliner/zagęszczenie linii rzęs), skupiamy się wyłącznie na brwiach i ustach.**

PRZECIWWSKAZANIA (BEZPIECZEŃSTWO):
- Bezwzględne: Ciąża, laktacja, nowotwory (bez zgody lekarza), aktywne infekcje, łuszczyca w miejscu zabiegu.
- Czasowe (Karencja):
  * Odżywki do rzęs: Odstawić 3-6 mies. przed zabiegiem (jeśli planowany zabieg na oczy, ale my go nie wykonujemy).
  * Retinoidy/Izotek: Odstawić 6 mies. przed (ryzyko blizn).
  * Kwas hialuronowy w ustach: Odstęp 4 tyg.
  * Leki rozrzedzające krew (aspiryna): Odstawić 24h przed.

PROCES GOJENIA I PIELĘGNACJA (KLUCZOWE):
- Dni 1-3 (Faza sączenia): Przemywać wacikiem z wodą (przegotowaną/destylowaną), by zmyć osocze. NIE nakładać grubej warstwy maści (gojenie "na sucho" lub minimalne).
- Dni 4-10 (Łuszczenie): Pojawiają się mikrostrupki. NIE WOLNO ICH DRAPAĆ (grozi blizną i ubytkiem koloru). Można lekko nawilżać (np. Alantan) gdy skóra ciągnie.
- Zakazy: Słońce (UV niszczy pigment), sauna, basen przez 2 tyg.
- Kolor: Po wygojeniu jaśnieje o 30-50%. Bezpośrednio po zabiegu jest ciemny.
- Stabilizacja: Pełny kolor widoczny po ok. 28 dniach (cykl naskórka).

RYZYKA I PROBLEMY:
- Kolor niebieski/szary: Zbyt głęboka pigmentacja (efekt Tyndalla/tatuaż) lub użycie czystej czerni.
- Kolor łososiowy: Utlenienie się tlenków żelaza w brązach.
- Ból: Minimalny (stosujemy znieczulenie lidokainą).

PAMIĘTAJ: Makijaż permanentny to wygoda, oszczędność czasu i korekta asymetrii.
"""

# === INICJALIZACJA ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === CENNIK ===
PRICE_LIST = {
    "brwi": "Makijaż permanentny brwi kosztuje 1200 zł — dopigmentowanie jest w cenie ✨",
    "usta": "Makijaż permanentny ust kosztuje 1200 zł — dopigmentowanie jest w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar 350 zł 🌿"
}
# === KONFIGURACJA TELEFONU ===
PHONE_NUMBER = "881 622 882"
PHONE_MESSAGES = [
    f"\n\nJeśli wolisz porozmawiać o szczegółach, zadzwoń do nas: {PHONE_NUMBER} 📞",
    f"\n\nChętnie odpowiemy na bardziej złożone pytania telefonicznie! {PHONE_NUMBER} 🌿",
    f"\n\nMasz ochotę na konsultację lub rezerwację terminu? Jesteśmy pod numerem: {PHONE_NUMBER} 🌸"
]

# === BAZA WIEDZY (Tylko po to, by INTENCJE mogły być wykryte) ===
KNOWLEDGE = {
    "pielęgnacja": [], "techniki_brwi": [], "techniki_usta": [], 
    "trwalosc": [], "fakty_mity": [], "przeciwwskazania": []
}

# === SŁOWA KLUCZOWE (BEZ ZMIAN) ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        r"\bprzeciwwskaz\w*", r"\bchorob\w*", r"\blek\w*", r"\btablet\w*", r"\bciąża\w*", r"\bw\s+ciąży\b", r"\bw\s+ciazy\b",
        r"\bkaw\w*", r"\bpi\w+\s+kaw\w*", r"\bespresso\w*", r"\blatte\w*", r"\bkofein\w*",
        r"\balkohol\w*", r"\bwino\w*", r"\bpiwo\w*", r"\bizotek\w*", r"\bretinoid\w*", r"\bsteroid\w*", r"\bheviran\w*", r"\bhormon\w*"
    ],
    "pielęgnacja": [
        r"\bpielęgnac\w*", r"\bgojenie\w*", r"\bpo\s+zabiegu\w*", r"\bstrup\w*", r"\błuszcz\w*", r"\bzłuszcz\w*",
        r"\bsmarow\w*", r"\bmyc\w*", r"\bmyć\w*", r"\bjak\s+dbac\w*", r"\bjak\s+dbać\w*", r"\bprzygotowan\w*"
    ],
    "techniki_brwi": [
        r"\bbrwi\w*", r"\bpowder\w*", r"\bpudrow\w*", r"\bombre\w*", r"\bmetoda\s+pudrowa\w*", r"\bmetoda\s+ombre\w*",
        r"\bmetody\s+brwi\w*", r"\bpigmentacj\w+\s+brwi\w*"
    ],
    "techniki_usta": [
        r"\busta\w*", r"\bust\w*", r"\bwargi\w*", r"\blip\w*", r"\bblush\w*", r"\bkontur\w*", r"\bliner\w*", r"\bfull\s+lip\w*", r"\baquarelle\w*"
    ],
    "trwalosc": [
        r"\butrzymuje\w*", r"\btrwa\w*", r"\bblak\w*", r"\bblednie\w*", r"\bzanika\w*", r"\bodświeżeni\w*", r"\bkolor\w*", r"\bczas\w*", r"\btrwałość\w*"
    ],
    "fakty_mity": [
        r"\bmit\w*", r"\bfakt\w*", r"\bbol\w*", r"\ból\w*", r"\bprawda\w*", r"\bfałsz\w*", r"\blaser\w*", r"\bremover\w*", r"\bmaszyna\w*",
        r"\beyeliner\w*", r"\boczy\w*", r"\b powieki\w*", 
    ]
}
INTENT_PRIORITIES = [
    "przeciwwskazania", "pielęgnacja", "techniki_brwi", "techniki_usta", "trwalosc", "fakty_mity"
]

HISTORY_LIMIT = 10
SESSION_DATA = {}

# === POMOCNICZE FUNKCJE (bez zmian) ===
def detect_intent(text):
    scores = {}
    for intent, patterns in INTENT_KEYWORDS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > 0:
            scores[intent] = score
    best_intent = max(scores, key=scores.get) if scores else None
    if best_intent:
        tied = [i for i, s in scores.items() if s == scores[best_intent]]
        if len(tied) > 1:
            for p in INTENT_PRIORITIES:
                if p in tied:
                    return p
    return best_intent

def emojis_for(intent):
    mapping = {
        "przeciwwskazania": ["🌿", "💋"],
        "pielęgnacja": ["🌿", "✨"],
        "techniki_brwi": ["✨", "🌸"],
        "techniki_usta": ["💋", "💄"],
        "trwalosc": ["💄", "✨"],
        "fakty_mity": ["🌸", "✨"]
    }
    return " ".join(random.sample(mapping.get(intent, ["✨", "🌸"]), 2))

def add_phone_once(reply, session, count):
    # Częstotliwość podawania numeru telefonu (co 5. wiadomość)
    if count % 5 == 0 and not session["last_phone"]:
        reply += random.choice(PHONE_MESSAGES).replace('**', '') 
        session["last_phone"] = True
    else:
        session["last_phone"] = False
    return reply

def update_history(session, user_msg, bot_reply):
    session["history"].append(("user", user_msg))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()
    
    session["history"].append(("assistant", bot_reply))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()

# === STRONA GŁÓWNA, POWITANIE (bez zmian) ===
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/start', methods=['GET'])
def start_message():
    user_ip = request.remote_addr or "default"
    SESSION_DATA[user_ip] = {
        "message_count": 0, "last_intent": None, "last_phone": False, "history": deque()
    }
    welcome_text = "Dzień dobry! Jestem Twoją osobistą ekspertką od makijażu permanentnego. O co chciałabyś zapytać? 🌸" 
    update_history(SESSION_DATA[user_ip], "Cześć, kim jesteś?", welcome_text)
    return jsonify({'reply': welcome_text})

# === GŁÓWNY ENDPOINT ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()
    
    if user_ip not in SESSION_DATA:
         SESSION_DATA[user_ip] = {
            "message_count": 0, "last_intent": None, "last_phone": False, "history": deque()
        }

    if not user_message:
        reply = 'Napisz coś, żebym mogła pomóc 💬'
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]
    reply = ""

    new_intent = detect_intent(text_lower)
    
    # === LOGIKA ZARZĄDZANIA INTENCJĄ ===
    if new_intent and new_intent != session["last_intent"]:
        session["last_intent"] = new_intent
    intent = new_intent or session.get("last_intent") 
    
    
    # === 1. OBSŁUGA CEN, CZASU I TERMINÓW (PRIORYTET 1) ===
    
    # === REGUŁA: CZAS TRWANIA ZABIEGU (Wysoki priorytet, bo może użyć słowa 'ile') ===
    if any(w in text_lower for w in ["ile trwa", "jak długo", "czas", "długo"]) and not any(w in text_lower for w in ["konsultacj", "doradztwo", "porada"]):
        reply = "Sam zabieg makijażu permanentnego trwa zazwyczaj **około 2 do 3 godzin**. Ten czas obejmuje szczegółową konsultację, rysunek wstępny (najważniejszy etap!) oraz samą pigmentację. Prosimy, aby zarezerwowała Pani sobie na wizytę właśnie tyle czasu. 😊"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
    
    # === REGUŁA: CZAS TRWANIA KONSULTACJI ===
    elif any(w in text_lower for w in ["ile trwa", "jak długo", "czas", "długo"]) and any(w in text_lower for w in ["konsultacj", "doradztwo", "porada"]):
        reply = "Bezpłatna konsultacja trwa **około 1 godziny**. Jest to czas przeznaczony na omówienie szczegółów, wybór metody, kolorów i odpowiedzi na Pani wszystkie pytania. 🌿"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: CENNIK (Wykonuje się, jeśli nie było pytania o 'ile trwa') ===
    elif any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = "Oto nasz aktualny cennik:\n\n" + all_prices
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: O CZYMŚ, CZEGO NIE ROBIMY (PMU OCZU/Eyeliner) ===
    elif any(w in text_lower for w in ["oczy", "powieki", "eyeliner", "zagęszczen"]):
        reply = f"W naszym salonie skupiamy się wyłącznie na **brwiach i ustach**, aby zapewnić najwyższą jakość i specjalizację w tych obszarach. **Nie wykonujemy makijażu permanentnego powiek (eyeliner, zagęszczanie rzęs)**. Jeśli interesuje Pani rezerwacja na brwi lub usta, prosimy o kontakt telefoniczny: {PHONE_NUMBER} 💋."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === NOWA REGUŁA: BÓL/POTRZEBNE (PRIORYTET ZARAZ ZA PMU OCZU) ===
    elif any(w in text_lower for w in ["bol", "ból", "potrzebne", "boli", "czy boli"]):
        reply = "Ból jest minimalny, ponieważ stosujemy **znieczulenie lidokainą**. PMU jest półtrwałe, więc potrwa tylko chwilę. W naszym salonie dążymy do maksymalnego komfortu dla każdej klientki podczas zabiegu. ✨"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})


    # === 1.5 REGUŁA LOGISTYCZNA (PRIORYTET 2) - KATEGORYCZNY ZAKAZ OSÓB TOWARZYSZĄCYCH ===
    elif any(w in text_lower for w in ["dzieckiem", "dzieci", "sama", "samemu", "zwierzak", "pies", "kot", "osoba towarzysząca", "mąż", "maz", "partner", "przyjaciółka", "koleżank", "razem"]) \
        and any(w in text_lower for w in ["mogę", "przyjść", "na zabieg", "z"]): 
        reply = "Zależy nam na pełnym skupieniu, sterylności i higienie podczas zabiegu. Prosimy o **bezwzględne przyjście na wizytę bez osób towarzyszących** (w tym dzieci), oraz bez zwierząt. Nie możemy przyjąć nikogo poza Panią w gabinecie. Dziękujemy za zrozumienie i dostosowanie się do naszych zasad bezpieczeństwa! 😊"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === WŁAŚCIWA KOLEJNOŚĆ: KONSULTACJE ORAZ TERMINY (TERAZ NIŻSZY PRIORYTET) ===
    
    # === REGUŁA: UMÓWIENIE KONSULTACJI (Słowa kluczowe: 'umówić', 'termin', 'konsultacja') ===
    elif any(w in text_lower for w in ["umówić", "termin", "zapis", "wolne", "rezerwacja"]) and any(w in text_lower for w in ["konsultacj", "doradztwo", "porada"]):
        # Numer telefonu podany celowo, ponieważ jest to odpowiedź na pytanie o rezerwację
        reply = f"Chętnie umówimy Panią na **bezpłatną konsultację**! Prosimy o kontakt telefoniczny z recepcją: {PHONE_NUMBER}, aby znaleźć dogodny dla Pani termin spotkania. Zarezerwuje Pani około 1 godziny 🌿."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: UMÓWIENIE ZABIEGU (Słowa kluczowe: 'umówić', 'termin', 'zabieg' lub BRAK słowa 'konsultacja') ===
    elif any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "zabieg"]):
        # Numer telefonu podany celowo, ponieważ jest to odpowiedź na pytanie o rezerwację
        reply = f"Chętnie umówimy Panią na **zabieg**! Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy i dobrać pasujący dzień. Czy możemy zaproponować Pani kontakt telefoniczny? {PHONE_NUMBER} 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: OGÓLNE PYTANIE O KONSULTACJĘ (Słowa kluczowe: 'konsultacja' bez 'terminu') ===
    elif any(w in text_lower for w in ["konsultacja", "doradztwo", "porada"]):
        reply = f"Oferujemy bezpłatne konsultacje, które trwają około 1 godziny. Jest to idealny czas na omówienie wszelkich obaw i dobranie metody. Czy chciałaby Pani umówić termin? Możemy to zrobić telefonicznie: {PHONE_NUMBER} 🌿."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    
    # === 2. WSZYSTKIE INNE PYTANIA -> FALLBACK GPT (PRIORYTET 3) ===
    
    # Zabezpieczenie: Jeśli nie rozpoznano nowej intencji (new_intent is None), 
    if new_intent is None:
        session["last_intent"] = None # Resetujemy intencję, aby GPT potraktował to jako nowy, nieznany temat, który musi obsłużyć.
        
    
    # --- WZMOCNIONY SYSTEM PROMPT ---
    system_prompt = f"""
    {PMU_FULL_KNOWLEDGE}

    INSTRUKCJE SPECJALNE DLA MODELU:
    1. Jesteś ekspertem-mikropigmentologiem z 20-letnim doświadczeniem. Odpowiadasz w języku polskim.
    2. Ton: **KOBIECY, BARDZO EMPATYCZNY, LEKKI i LUDZKI.** Twój styl powinien być **ciepły, wspierający i osobisty**, unikając technicznego żargonu tam, gdzie to możliwe, chyba że odpowiadasz na konkretne pytanie techniczne.
    3. **BEZPOŚREDNIE ZWRACANIE SIĘ:** Zawsze zwracaj się bezpośrednio do Klientki, używając formy **"Pani"** ("powinna Pani", "rozumiemy Pani obawy"). **NIGDY nie używaj formy trzeciej osoby, takich jak "klientka musi"**.
    4. **Emocje i Zaufanie:** Aktywnie używaj wyrażeń budujących zaufanie: "Rozumiemy Pani obawy", "To bardzo ważne pytanie, chętnie pomożemy", "W naszym salonie dbamy o...".
    5. Unikaj formy "ja". Używaj form: "nasz salon", "eksperci robią", "możemy doradzić". Używaj emotek z wyczuciem (max 2).
    6. Zawsze bazuj na faktach zawartych w DANYCH SALONU i WIEDZY PMU.
    7. **Brak Informacji:** Jeśli użytkownik pyta o rzecz, która **nie jest zawarta** w bazie wiedzy (np. skomplikowane pytania logistyczne, których nie obsługują reguły), zalecaj kontakt telefoniczny z recepcją salonu, aby to potwierdzić ({PHONE_NUMBER}).
    8. **Formatowanie:** W przypadku złożonych pytań (jak techniki lub przeciwwskazania) używaj **list punktowanych** i **pogrubień** w tekście, aby zwiększyć czytelność. (Nie używaj symboli *).
    9. **ZASADA KOMUNIKACJI:** Odpowiadaj bezpośrednio na pytanie, traktując to jako ciągłą konwersację.
    10. **CENA/TERMIN:** Jeśli użytkownik pyta o cenę lub termin/rezerwację, użyj informacji z DANYCH SALONU i ZACHĘCAJ do kontaktu telefonicznego pod numerem: {PHONE_NUMBER}.
    """

    messages = [{"role": "system", "content": system_prompt}]
    
    for role, content in session["history"]:
        messages.append({"role": role, "content": content})
        
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.9, 
            max_tokens=600,
            messages=messages
        )
        reply = completion.choices[0].message.content.strip()
        
        reply = add_phone_once(reply, session, count)
        
    except Exception as e:
        reply = f"Przepraszamy, wystąpił chwilowy błąd komunikacji z naszym systemem. Prosimy o kontakt telefoniczny pod numerem {PHONE_NUMBER} lub spróbuj za chwilę 💔."

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)








