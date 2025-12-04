from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
import os, random, re
from collections import deque # Dodajemy dla lepszej obsługi historii

# === INICJALIZACJA ===
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
        "Zabieg nie jest wykonywany w ciąży ani podczas karmienia piersią 🌿💋",
        "Aktywne infekcje, nowotwory, kuracja sterydami lub retinoidami — wtedy zabiegu nie wykonujemy 🌿💋",
        "Przed zabiegiem nie pij kawy ani alkoholu — kofeina i alkohol rozrzedzają krew, co może utrudnić przyjęcie pigmentu 🌿💋"
    ],
    "pielęgnacja": [
        "Po zabiegu nie drap i nie zrywaj strupków; skóra goi się ok. 7 dni, a kolor stabilizuje po ~30 dniach 🌿✨",
        "Przez tydzień unikaj słońca, sauny, basenu i intensywnego wysiłku 🌿✨",
        "Brwi przemywaj przegotowaną wodą 3–5× dziennie przez pierwsze 3 dni, potem delikatnie nawilżaj cienką warstwą preparatu 🌿✨"
    ],
    "techniki_brwi": [
        "W naszym salonie wykonujemy dwie metody brwi: • Powder Brows — miękki efekt cienia • Ombre — jaśniejsze u nasady, ciemniejsze na końcach ✨🌸",
        "Powder Brows: delikatny, pudrowy cień. Ombre: subtelny gradient (jaśniej przy nasadzie, ciemniej na końcu łuku) ✨🌸"
    ],
    "techniki_usta": [
        "Najczęstsze techniki ust: • Lip Blush — naturalny rumieniec • Kontur ust — subtelne zdefiniowanie linii • Full Lip Color — pełne, równomierne wypełnienie 💋💄",
        "Lip Blush daje lekki, świeży kolor; Full Lip Color — efekt klasycznej szminki; Kontur wyrównuje kształt ust 💋💄"
    ],
    "trwalosc": [
        "Efekt utrzymuje się zwykle 1–3 lata; zależy od pielęgnacji, fototypu i stylu życia ✨💄",
        "Szybsze blaknięcie bywa przy cerze tłustej, częstej ekspozycji na słońce lub braku zaleceń pozabiegowych ✨💄"
    ],
    "fakty_mity": [
        "Dzięki znieczuleniu większość klientek czuje jedynie lekkie szczypanie ✨🌸",
        "PMU nie powoduje wypadania włosków — pigment jest wprowadzany płytko ✨🌸",
        "Makijaż permanentny jest półtrwały — naturalnie blednie i wymaga odświeżenia ✨🌸"
    ]
}

# === SŁOWA KLUCZOWE ===
# Używamy surowych stringów (r'') dla lepszej czytelności i bezpieczeństwa z RegExp
INTENT_KEYWORDS = {
    "przeciwwskazania": [
        r"\bprzeciwwskaz\w*", r"\bchorob\w*", r"\blek\w*", r"\btablet\w*", r"\bciąż\w*", r"\bw\s+ciąży\b", r"\bw\s+ciazy\b",
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
        r"\bmit\w*", r"\bfakt\w*", r"\bbol\w*", r"\ból\w*", r"\bprawda\w*", r"\bfałsz\w*", r"\blaser\w*", r"\bremover\w*", r"\bmaszyna\w*"
    ]
}

# Kolejność rozstrzygania przy konfliktach
INTENT_PRIORITIES = [
    "przeciwwskazania", "pielęgnacja", "techniki_brwi", "techniki_usta", "trwalosc", "fakty_mity"
]

# Pytania dopytujące (Zostawiamy, ale poprawimy ich użycie)
FOLLOWUP_QUESTIONS = {
    "techniki_brwi": "Czy pytasz o metody brwi (Powder vs Ombre)?",
    "techniki_usta": "Chodzi o techniki ust (Lip Blush / Kontur / Full Lip Color)?",
    "trwalosc": "Pytasz przed zabiegiem czy już po — chcesz wiedzieć, jak długo trzyma efekt?",
    "pielęgnacja": "Chodzi o przygotowanie przed zabiegiem czy pielęgnację po?"
}

# === SESJE ===
# Używamy deque do historii dla automatycznego usuwania starych wiadomości
# Limit historii: 10 wiadomości (5 par W-O)
HISTORY_LIMIT = 10
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
    # Resetuj sesję przy każdym /start
    user_ip = request.remote_addr or "default"
    SESSION_DATA[user_ip] = {
        "message_count": 0, "last_intent": None, "asked_context": False, 
        "last_phone": False, "history": deque()
    }
    return jsonify({'reply': welcome_text})

# === POMOCNICZE ===
def detect_intent(text):
    scores = {}
    
    # Używamy re.search dla elastycznego dopasowania RegExp
    for intent, patterns in INTENT_KEYWORDS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return None
    
    # Wybieranie najlepszej intencji na podstawie score (a w przypadku remisu, priorytetu)
    best_intent = max(scores, key=scores.get)
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
    if count % 3 == 0 and not session["last_phone"]:
        reply += random.choice([
            "\n\nJeśli chcesz, mogę pomóc dobrać termin 💋 881 622 882",
            "\n\nMasz ochotę na konsultację? Zadzwoń: 881 622 882 🌿"
        ])
        session["last_phone"] = True
    else:
        session["last_phone"] = False
    return reply

def update_history(session, user_msg, bot_reply):
    # Ograniczenie historii do HISTORY_LIMIT
    session["history"].append(("user", user_msg))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()
    
    session["history"].append(("assistant", bot_reply))
    if len(session["history"]) > HISTORY_LIMIT:
        session["history"].popleft()
    
# === GŁÓWNY ENDPOINT ===
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()
    user_ip = request.remote_addr or "default"
    text_lower = user_message.lower()
    
    # Inicjalizacja sesji jeśli nie istnieje
    if user_ip not in SESSION_DATA:
         SESSION_DATA[user_ip] = {
            "message_count": 0, "last_intent": None, "asked_context": False, 
            "last_phone": False, "history": deque()
        }

    if not user_message:
        reply = 'Napisz coś, żebym mogła Ci pomóc 💬'
        update_history(SESSION_DATA[user_ip], user_message, reply)
        return jsonify({'reply': reply})

    session = SESSION_DATA[user_ip]
    session["message_count"] += 1
    count = session["message_count"]
    
    # Domyślna odpowiedź na koniec, jeśli żaden warunek się nie spełni
    reply = ""

    # Reset flagi kontekstu, jeśli użytkownik zmienił temat
    new_intent = detect_intent(text_lower)
    if new_intent and new_intent != session["last_intent"]:
        session["asked_context"] = False
    
    # Używamy intent, który jest aktualny lub był ostatnio aktywny (kontekst)
    intent = new_intent or session.get("last_intent")

    # === 1. CENNIK (Najwyższy priorytet) ===
    if any(word in text_lower for word in ["ile", "koszt", "kosztuje", "cena", "za ile", "cennik"]):
        all_prices = "\n\n".join(PRICE_LIST.values())
        reply = add_phone_once(all_prices, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 2. TERMINY (Wysoki priorytet) ===
    if any(w in text_lower for w in ["termin", "umówić", "zapis", "wolne", "rezerwacja", "kiedy", "dostępny"]):
        reply = "Najlepiej skontaktować się bezpośrednio z salonem, aby poznać aktualne terminy 🌸"
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 3. BAZA WIEDZY (Jeśli znaleziono intencję) ===
    if intent and intent in KNOWLEDGE:
        
        # Logika pytań dopytujących - Zadawaj TYLKO, jeśli kontekst nie został jeszcze określony
        if intent in FOLLOWUP_QUESTIONS and not session["asked_context"]:
            session["asked_context"] = True # Oznacz, że zapytaliśmy
            # Nie ustawiaj last_intent, aby przy kolejnej wiadomości system spróbował wrócić do bazy wiedzy
            reply = FOLLOWUP_QUESTIONS[intent]
            update_history(session, user_message, reply)
            return jsonify({'reply': reply})
        
        # Jeśli kontekst jest już określony LUB intencja nie wymaga dopytywania
        session["last_intent"] = intent # Ustaw kontekst (do następnego razu)
        session["asked_context"] = False # Resetuj
        reply = random.choice(KNOWLEDGE[intent]) + " " + emojis_for(intent)
        reply = add_phone_once(reply, session, count)
        update_history(session, user_message, reply)
        return jsonify({'reply': reply})

    # === 4. FALLBACK GPT (Gdy nie pasuje żadna kategoria) ===
    
    # Jeśli nowa intencja nie została znaleziona, a ostatnia była ustawiona na coś,
    # co nie było w KNOWLEDGE (np. w poprzedniej pętli fallback), spróbuj ją wyczyścić
    if not new_intent:
        session["last_intent"] = None
        session["asked_context"] = False

    system_prompt = (
        "Jesteś Beauty Chat — inteligentną, empatyczną asystentką salonu makijażu permanentnego (PMU). "
        "Twoja rola to odpowiadanie na pytania dotyczące PMU brwi i ust. "
        "Odpowiadasz krótko, konkretnie i kobieco. Używasz maksymalnie 2 emotek z wyczuciem. "
        "Nie wymyślasz informacji. Jeśli pytanie jest poza obszarem PMU brwi/ust, grzecznie sugeruj kontakt z obsługą klienta."
    )

    # Konstruowanie historii wiadomości dla GPT
    messages = [{"role": "system", "content": system_prompt}]
    
    # Dodanie wcześniejszych wiadomości z historii sesji
    for role, content in session["history"]:
        # Używamy role: "user" lub "assistant"
        messages.append({"role": role, "content": content})
        
    # Dodanie aktualnej wiadomości użytkownika
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7, # Zwiększono, aby odpowiedzi były bardziej naturalne
            max_tokens=600,
            messages=messages # Przekazujemy całą historię
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Ups! Coś poszło nie tak 💔 Spróbuj ponownie. ({e})"

    update_history(session, user_message, reply)
    return jsonify({'reply': reply})

# === START ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

















