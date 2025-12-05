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
- Parking: Klienci nie muszą się martwić o miejsce. Salon posiada **własny parking**, zapewniający bezproblemowe miejsca postojowe tuż przy wejściu 🚗.

DEFINICJE I FAKTY:
- Makijaż permanentny (PMU/mikropigmentacja): Wprowadzenie pigmentu płytko do naskórka lub granicy naskórkowo-skórnej.
- Różnica vs Tatuaż: Tatuaż jest w skórze właściwej. PMU jest półtrwały (1-3 lata, czasem do 5).
- Bezpieczeństwo chemiczne: Pigmenty muszą spełniać normy UE REACH 2020/2081 (np. limit ołowiu 0,00007%). Używamy tylko atestowanych, bezpiecznych barwników.
- **Korekta/Dopigmentowanie/Poprawka (Zabieg II):** Jest to zabieg uzupełniający, który wykonuje się po około 4-8 tygodniach od pierwszego zabiegu. Ma na celu wyrównanie koloru i stabilizację pigmentu po wygojeniu. Ten drugi zabieg jest integralną częścią usługi i jest **zawarty w cenie** głównego pigmentowania.
- **Odświeżenie/Cover-up (Zabieg Pózniejszy):** Odświeżenie to zabieg wykonywane po upływie dłuższego czasu (np. 1-2 lata), aby przywrócić intensywność koloru. Jeśli makijaż permanentny był wykonany w **innym salonie** (tzw. inna linergistka, czyli cover-up), nie możemy go traktować jako standardowe odświeżenie. W takim przypadku, aby ocenić stan pigmentu, konieczna jest **obowiązkowa, bezpłatna konsultacja** z linergistką.

TECHNIKI - BRWI:
1. Pudrowa (Powder Brows): Maszynowe cieniowanie, efekt "przyprószenia". Bardziej trwała (2-3 lata), idealna dla każdego typu skóry (także tłustej).
2. Ombre Brows: Gradient – jaśniejsza nasada, ciemniejszy koniec i dół.
3. Hybrydowa (Combo): Włoski na początku łuku + cień na reszcie.

TECHNIKI - USTA:
- Lip Blush: Akwarelowe, delikatne uwydatnienie czerwieni.
- Full Lip Color: Efekt szminki.
- Wymagana osłona przeciwwirusowa (Heviran) 3 dni przed i 3 dni po zabiegu (profilaktyka opryszczki).

**UWAGA: W naszym salonie nie wykonujemy makijażu permanentnego powiek (eyeliner/zagęszczenie linii rzęs), Microbladingu oraz metody Nano Brows. Skupiamy się wyłącznie na brwiach i ustach, w sprawdzonych i najmodniejszych technikach.**

PRZECIWWSKAZANIA (BEZPIECZEŃSTWO):
- Bezwzględne: Ciąża, laktacja, nowotwory (bez zgody lekarza), **aktywna opryszczka**, **inne infekcje wirusowe** (np. przeziębienie, grypa), **mocna/świeża opalenizna**, łuszczyca w miejscu zabiegu.
- Czasowe (Karencja):
  * Odżywki do rzęs: Odstawić 3-6 mies. przed zabiegiem (jeśli planowany zabieg na oczy, ale my go nie wykonujemy).
  * Retinoidy/Izotek: Odstawić 6 mies. przed (ryzyko blizn).
  * Kwas hialuronowy w ustach: Odstęp 4 tyg.
  * Leki rozrzedzające krew (aspiryna): Odstawić 24h przed.
  * Kofeina/Kawa: Odstawić 24h przed.
  * Alkohol: Odstawić 24h przed.

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

---
**CENNIK (do użycia w Fallbacku GPT):**
- Brwi Powder Brows (Pudrowe): 1200 zł (dopigmentowanie/korekta w cenie ✨)
- Brwi Ombre Brows: 1200 zł (dopigmentowanie/korekta w cenie ✨)
- Brwi Hybrydowe (Combo): 1400 zł (dopigmentowanie/korekta w cenie ✨)
- Usta Lip Blush: 1000 zł (dopigmentowanie/korekta w cenie 💋)
- Usta Full Lip Color: 1200 zł (dopigmentowanie/korekta w cenie 💋)
- Laserowe usuwanie PMU brwi: 350 zł za jeden obszar 🌿
"""

# === INICJALIZACJA ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=api_key)

# === CENNIK ===
PRICE_LIST = {
    "brwi_pudrowe": "Makijaż permanentny brwi (Powder Brows): **1200 zł** — dopigmentowanie/korekta w cenie ✨",
    "brwi_ombre": "Makijaż permanentny brwi (Ombre Brows): **1200 zł** — dopigmentowanie/korekta w cenie ✨",
    "brwi_combo": "Makijaż permanentny brwi (Hybryda/Combo): **1400 zł** — dopigmentowanie/korekta w cenie ✨",
    "usta_blush": "Makijaż permanentny ust (Lip Blush): **1000 zł** — dopigmentowanie/korekta w cenie 💋",
    "usta_full": "Makijaż permanentny ust (Full Lip Color): **1200 zł** — dopigmentowanie/korekta w cenie 💋",
    "laser": "Laserowe usuwanie makijażu permanentnego brwi — jeden obszar **350 zł** 🌿"
}
# === KONFIGURACJA TELEFONU ===
PHONE_NUMBER = "881 622 882"
PHONE_MESSAGES = [
    f"\n\nJeśli wolisz porozmawiać o szczegółach, zadzwoń do nas: {PHONE_NUMBER} 📞",
    f"\n\nChętnie odpowiemy na bardziej złożone pytania telefonicznie! {PHONE_NUMBER} 🌿",
    f"\n\nMasz ochotę na konsultację lub rezerwację terminu? Jesteśmy pod numerem: {PHONE_NUMBER} 🌸"
]
# === BAZA WIEDZY (Tylko po to, by INTENCJE mogły być wykryte) ===
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        r"\bprzeciwwskaz\w*", r"\bchorob\w*", r"\blek\w*", r"\btablet\w*", r"\bciąża\w*", r"\bw\s+ciąży\b", r"\bw\s+ciazy\b",
        r"\bkaw\w*", r"\bpi\w+\s+kaw\w*", r"\bespresso\w*", r"\blatte\w*", r"\bkofein\w*",
        r"\balkohol\w*", r"\bwino\w*", r"\bpiwo\w*", r"\bizotek\w*", r"\bretinoid\w*", r"\bsteroid\w*", r"\bheviran\w*", r"\bhormon\w*",
        r"\bopryszczk\w*", r"\bopalenizn\w*", r"\binfekcj\w*", r"\bwirus\w*"
    ],
    "pielęgnacja": [
        r"\bpielęgnac\w*", r"\bgojenie\w*", r"\bpo\s+zabiegu\w*", r"\bstrup\w*", r"\błuszcz\w*", r"\bzłuszcz\w*",
        r"\bsmarow\w*", r"\bmyc\w*", r"\bmyć\w*", r"\bjak\s+dbac\w*", r"\bjak\s+dbać\w*", r"\bprzygotowan\w*"
    ],
    "techniki_brwi": [
        r"\bbrwi\w*", r"\bpowder\w*", r"\bpudrow\w*", r"\bombre\w*", r"\bmetoda\s+pudrowa\w*", r"\bmetoda\s+ombre\w*",
        r"\bmetody\s+brwi\w*", r"\bpigmentacj\w+\s+brwi\w*", r"\bhybrydow\w*", r"\bcombo\w*"
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
        "last_intent": None, "history": deque()
    }
    welcome_text = "Dzień dobry! Jestem Pani osobistą ekspertką od makijażu permanentnego. O co chciałaby Pani zapytać? 🌸" 
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
            "last_intent": None, "history": deque()
        }

    if not user_message:
        reply = 'Napisz coś, żebym mogła pomóc 💬'
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    reply = ""

    new_intent = detect_intent(text_lower)
    
    # === LOGIKA ZARZĄDZANIA INTENCJĄ ===
    if new_intent and new_intent != session["last_intent"]:
        session["last_intent"] = new_intent
    intent = new_intent or session.get("last_intent") 
    
    # === 1. OBSŁUGA CEN, CZASU I REGUŁY KRYTYCZNE (PRIORYTET 1) ===

    # ** REGUŁA CENOWA (PRIORYTET 1) **
    if any(word in text_lower for word in ["ile\w*", "koszt\w*", "kosztuje\w*", "cena\w*", "za ile\w*", "cennik\w*"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = "Oto nasz aktualny cennik:\n\n" + all_prices
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    elif any(w in text_lower for w in ["ile go\w*", "jak dlugo sie go\w*", "czas gojeni\w*", "gojenie trwa\w*", "goi się\w*"]):
        reply = "Pełny proces gojenia dzieli się na etapy: **Faza Sączenia** (Dni 1-3) oraz **Łuszczenie się naskórka** (Dni 4-10, pojawiają się mikrostrupki, których nie wolno zdrapywać!). Pełna **stabilizacja koloru** następuje po około **28 dniach** (cykl odnowy naskórka). ✨"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # REGUŁA ADRESU I PARKINGU
    elif any(w in text_lower for w in ["gdzie\w*", "adres\w*", "lokalizacj\w*", "dojazd\w*", "parking\w*", "gdzie parkowac\w*"]):
        reply = "Nasz salon znajduje się pod adresem: **ul. Junikowska 9** 🌸. Zapraszamy od poniedziałku do piątku w godzinach 09:00 - 19:00. Nie musi się Pani martwić o parking! Posiadamy **własne miejsca postojowe** tuż przy salonie 🚗."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    elif any(w in text_lower for w in ["ile trwa\w*", "jak długo\w*", "czas\w*", "długo\w*"]) and not any(w in text_lower for w in ["konsultacj\w*", "doradztwo\w*", "porada\w*"]):
        reply = "Sam zabieg makijażu permanentnego trwa zazwyczaj **około 2 do 3 godzin**. Ten czas obejmuje szczegółową konsultację, rysunek wstępny (najważniejszy etap!) oraz samą pigmentację. Prosimy, aby zarezerwowała Pani sobie na wizytę właśnie tyle czasu. 😊"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    elif any(w in text_lower for w in ["ile trwa\w*", "jak długo\w*", "czas\w*", "długo\w*"]) and any(w in text_lower for w in ["konsultacj\w*", "doradztwo\w*", "porada\w*"]):
        reply = "Bezpłatna konsultacja trwa **około 1 godziny**. Jest to czas przeznaczony na omówienie szczegółów, wybór metody, kolorów i odpowiedzi na Pani wszystkie pytania. 🌿"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # REGUŁA: Oczy / Nano Brows / Microblading / Wypełnienie (Tego nie robimy)
    elif any(w in text_lower for w in ["oczy\w*", "powieki\w*", "eyeliner\w*", "zagęszczen\w*", "microblading\w*", "włoskow\w*", "wypełnieni\w*", "insta\w*"]) or "nano brows" in text_lower:
        reply = f"W naszym salonie skupiamy się wyłącznie na **brwiach i ustach** w sprawdzonych i najmodniejszych technikach (Pudrowa, Ombre, Hybrydowa, Lip Blush, Full Lip Color). **Nie wykonujemy Microbladingu, Metody Wypełnienia (Insta) oraz makijażu permanentnego powiek (eyeliner, zagęszczanie rzęs)**. Jeśli interesuje Pani rezerwacja na brwi lub usta, prosimy o kontakt telefoniczny: {PHONE_NUMBER} 💋."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    elif any(w in text_lower for w in ["bol\w*", "ból\w*", "potrzebn\w*", "boli\w*", "czy boli\w*"]):
        reply = "Ból jest minimalny, ponieważ stosujemy **znieczulenie lidokainą**. PMU jest półtrwałe, więc potrwa tylko chwilę. W naszym salonie dążymy do maksymalnego komfortu dla każdej klientki podczas zabiegu. ✨"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # NOWA REGUŁA: KAWA/ALKOHOL/OPALENIZNA/INFEKCJE (Priorytet 1)
    elif re.search(r"\b(kawa\w*|kofein\w*|alkohol\w*|opryszczk\w*|opalenizn\w*|infekcj\w*|wirus\w*)\b", text_lower):
        
        przeciwwskazania = []
        if re.search(r"\b(kawa\w*|kofein\w*|alkohol\w*)\b", text_lower):
            przeciwwskazania.append("Kawa/Kofeina/Alkohol: Prosimy o **odstawienie na 24 godziny** przed zabiegiem, ponieważ rozrzedzają krew.")
        if re.search(r"\b(opryszczk\w*|infekcj\w*|wirus\w*)\b", text_lower):
            przeciwwskazania.append("Aktywna opryszczka/Infekcje: Zabieg **musi zostać przełożony**. Jeśli planuje Pani makijaż ust, konieczna jest też profilaktyka **Heviranem** (3 dni przed i 3 dni po).")
        if re.search(r"\b(opalenizn\w*|świeża\s+opalenizna\w*)\b", text_lower):
            przeciwwskazania.append("Mocna/Świeża opalenizna: Prosimy o unikanie intensywnego słońca w miejscu zabiegu. Skóra musi być **nieopalona i wygojona**.")

        if przeciwwskazania:
            reply = "To bardzo ważne dla Pani bezpieczeństwa i najlepszego efektu końcowego! Oto najważniejsze zasady dotyczące tych kwestii:\n\n* " + "\n* ".join(przeciwwskazania) + "\n\nJeśli ma Pani wątpliwości, zawsze najlepiej skontaktować się z nami telefonicznie: " + PHONE_NUMBER + " 🌿"
            update_history(session, user_message, reply)
            return jsonify({'reply': reply})

    # BEZWZGLĘDNY WYMÓG: HEVIRAN/OPRYSZCZKA PRZY ZABIEGU UST (Reguła pozostawiona dla bezpieczeństwa)
    elif re.search(r"\b(usta\w*|opryszczka\w*|herpes\w*|heviran\w*|aciklovir\w*)\b", text_lower):
        reply = """
        To jest **absolutnie kluczowe** pytanie! Przed zabiegiem makijażu permanentnego ust konieczna jest profilaktyka przeciwwirusowa.
        
        * Prosimy o zażywanie **Heviranu** (lub innej osłony przepisanej przez lekarza) na **3 dni przed** zabiegiem oraz kontynuowanie przez **3 dni po** zabiegu.
        * Jeśli ma Pani aktywną opryszczkę w dniu wizyty, zabieg **musi zostać przełożony**.
        * Profilaktyka jest niezbędna, aby uniknąć nawrotu opryszczki, która może zniszczyć efekt pigmentacji.
        
        Dbamy o Pani zdrowie i najlepszy efekt końcowy! 💋
        """
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # NOWA REGUŁA: BRAMKA PRECYZUJĄCA (ODŚWIEŻENIE/KOREKTA) - ZAKTUALIZOWANA WERSJA
    elif re.search(r"\b(odśwież\w*|poprawka\w*|dopigmentowani\w*|korekta\w*)\b", text_lower):
        reply = f"""
        Rozumiem, to bardzo ważne pytanie! Aby mogła Pani otrzymać precyzyjną informację, proszę o doprecyzowanie:

        1.  Czy chodzi Pani o **dopigmentowanie/korektę** po pierwszym zabiegu (wykonuje się je po 4-8 tygodniach)? (Jeśli tak, to jest **w cenie**).
        2.  Czy pyta Pani o **odświeżenie** po dłuższym czasie (np. po roku)? Wtedy musimy ustalić, **czy makijaż był wykonany w naszym salonie, czy w innym** (inna linergistka)?

        Jeśli makijaż był wykonany **w innym salonie** (praca innej linergistki), konieczna jest **obowiązkowa, bezpłatna konsultacja**, aby ocenić obecny pigment. Czasem, aby uzyskać najlepszy efekt i uniknąć niechcianych kolorów, **konieczne może być wcześniejsze usunięcie starego makijażu laserem** 🌿. Dopiero po ocenie linergistki będziemy mogły zdecydować o kolejnych krokach (cover-up lub usunięcie).

        Prosimy o kontakt telefoniczny w celu umówienia się na konsultację: {PHONE_NUMBER} 📞
        """
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # REGUŁA: OSOBY TOWARZYSZĄCE
    elif re.search(
        r"\b("
        r"m[aą]ż\w*|m[eę]żem\w*|maz\w*|z\s+m[eę]żem\w*|"
        r"partner\w*|"
        r"przyjaci[oó]łk\w*|koleżank\w*|"
        r"dzieck\w*|dzieci\w*|"
        r"z\s+dzieckiem\w*|z\s+dzieci\w*|"
        r"zwierzak\w*|pies\w*|kot\w*|"
        r"osob\w*\s+towarzysz\w*|towarzysz\w*|"
        r"razem\w*|sam\w*|mog[eę]\s+przyj\w*"
        r")\b",
        text_lower
    ):
        reply = "Zależy nam na pełnym skupieniu, sterylności i higienie podczas zabiegu. Prosimy o **bezwzględne przyjście na wizytę bez osób towarzyszących** (w tym dzieci), oraz bez zwierząt. Nie możemy przyjąć nikogo poza Panią w gabinecie. Dziękujemy za zrozumienie i dostosowanie się do naszych zasad bezpieczeństwa! 😊"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: UMÓWIENIE KONSULTACJI ===
    elif any(w in text_lower for w in ["umówić\w*", "termin\w*", "zapis\w*", "woln\w*", "rezerwacj\w*"]) and any(w in text_lower for w in ["konsultacj\w*", "doradztwo\w*", "porada\w*"]):
        reply = f"Chętnie umówimy Panią na **bezpłatną konsultację**! Prosimy o kontakt telefoniczny z recepcją: {PHONE_NUMBER}, aby znaleźć dogodny dla Pani termin spotkania. Zarezerwuje Pani około 1 godziny 🌿."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: UMÓWIENIE ZABIEGU ===
    elif any(w in text_lower for w in ["termin\w*", "umówić\w*", "zapis\w*", "woln\w*", "rezerwacj\w*", "zabieg\w*"]):
        reply = f"Chętnie umówimy Panią na **zabieg**! Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy i dobrać pasujący dzień. Czy możemy zaproponować Pani kontakt telefoniczny? {PHONE_NUMBER} 🌸"
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})
        
    # === REGUŁA: OGÓLNE PYTANIE O KONSULTACJĘ ===
    elif any(w in text_lower for w in ["konsultacj\w*", "doradztwo\w*", "porada\w*"]):
        reply = f"Oferujemy bezpłatne konsultacje, które trwają około 1 godziny. Jest to idealny czas na omówienie wszelkich obaw i dobranie metody. Czy chciałaby Pani umówić termin? Możemy to zrobić telefonicznie: {PHONE_NUMBER} 🌿."
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 2. WSZYSTKIE INNE PYTANIA -> FALLBACK GPT (PRIORYTET 3) ===
    if new_intent is None:
        session["last_intent"] = None

    # --- WZMOCNIONY SYSTEM PROMPT ---
    system_prompt = f"""
    {PMU_FULL_KNOWLEDGE}

    INSTRUKCJE SPECJALNE DLA MODELU:
    1. Jesteś ekspertem-mikropigmentologiem z 20-letnim doświadczeniem. Odpowiadasz w języku polskim.
    2. Ton: **BARDZO CIEPŁY, PRZYJACIELSKI, LEKKI i LUDZKI.** Twój styl powinien być **ciepły, wspierający i osobisty, jak rozmowa z przyjazną specjalistką**, unikaj sztywnej, chłodnej formalności.
    3. **BEZPOŚREDNIE ZWRACANIE SIĘ:** Zawsze zwracaj się bezpośrednio do Klientki, używając formy **"Pani"**. **Koniecznie stosuj żeńskie formy czasowników** (np. "chciałaby Pani", "powinna Pani", "rozumiemy Pani obawy"). **Unikaj** błędnych, potocznych konstrukcji typu "interesuje Pani" lub "Panią interesuje technika". Zamiast tego używaj poprawnych zaimków i czasowników: "Jaka technika Panią interesuje?", "Czy szuka Pani naturalnego efektu?". **NIGDY nie używaj formy trzeciej osoby, takich jak "klientka musi"**.
    4. **Emocje i Zaufanie:** Aktywnie używaj wyrażeń budujących zaufanie i bliskość: "Rozumiemy Pani obawy", "To bardzo ważne pytanie, chętnie pomożemy", "W naszym salonie dbamy o...".
    5. Unikaj formy "ja". Używaj form: "nasz salon", "eksperci robią", "możemy doradzić". Używaj emotek z wyczuciem (max 2-3 w całej odpowiedzi).
    6. Zawsze bazuj na faktach zawartych w DANYCH SALONU i WIEDZY PMU.
    7. **Brak Informacji:** Jeśli użytkownik pyta o rzecz, która **nie jest zawarta** w bazie wiedzy (np. skomplikowane pytania logistyczne), zalecaj kontakt telefoniczny z recepcją salonu ({PHONE_NUMBER}).
    8. **Formatowanie:** W przypadku złożonych pytań (jak techniki lub przeciwwskazania) używaj **list punktowanych** i **pogrubień** w tekście.
    9. **ZASADA KOMUNIKACJI:** Odpowiadaj bezpośrednio na pytanie, traktując to jako ciągłą konwersację.
    10. **CENA/TERMIN:** Jeśli użytkownik pyta o cenę, podaj ją, używając danych z sekcji CENNIK w WIEDZY PMU. TYLKO w sprawie rezerwacji terminu lub jeśli pytania dot. innych szczegółów logistycznych, zachęcaj do kontaktu telefonicznego: {PHONE_NUMBER}.
    11. **ANGAAŻOWANIE (Opcjonalne):** Po udzieleniu wyczerpującej odpowiedzi, model **może** (ale nie musi) zasugerować kolejny logiczny temat lub zadać delikatne, otwarte pytanie związane z kontekstem. Rób to tylko wtedy, gdy czujesz, że Klientka potrzebuje dalszej pomocy lub kierunku, np. po omówieniu ceny zapytaj o **metodę** lub po omówieniu gojenia zapytaj o **przeciwwskazania**. To ma budować płynność rozmowy, a nie być sztywnym wymogiem.
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
    except Exception as e:
        reply = f"Przepraszamy, wystąpił chwilowy błąd komunikacji z naszym systemem. Prosimy o kontakt telefoniczny pod numerem {PHONE_NUMBER} lub spróbuj za chwilę 💔."

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)







