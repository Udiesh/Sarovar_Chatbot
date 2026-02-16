from flask import Flask, request, jsonify, session
import json
import random
import uuid
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from groq import Groq
from collections import defaultdict
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sarovar_south_spice_2026_secret')

# --- Database Setup ---
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- Rate Limiting ----#

rate_limit_store = defaultdict(list)
RATE_LIMIT = 20  # max requests per window
RATE_WINDOW = 60  # window in seconds (1 minute)

def is_rate_limited(session_id):
    now = time.time()
    # Clean old entries
    rate_limit_store[session_id] = [t for t in rate_limit_store[session_id] if now - t < RATE_WINDOW]
    if len(rate_limit_store[session_id]) >= RATE_LIMIT:
        return True
    rate_limit_store[session_id].append(now)
    return False

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                name TEXT,
                date TEXT,
                time TEXT,
                party_size INTEGER,
                special_requests TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                category TEXT NOT NULL,
                is_veg BOOLEAN DEFAULT TRUE,
                is_vegan BOOLEAN DEFAULT FALSE,
                is_spicy BOOLEAN DEFAULT FALSE,
                is_bestseller BOOLEAN DEFAULT FALSE,
                image_url TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('SELECT COUNT(*) as count FROM menu_items')
        if cur.fetchone()['count'] == 0:
            seed_menu(cur)
        
        conn.commit()
        cur.close()
        conn.close()
        print("DB initialized.")
    except Exception as e:
        print(f"DB init error: {e}")



def seed_menu(cur):
    menu = [
    # Breakfast
    ("Masala Dosa", "Crispy rice crepe filled with spiced potato, served with sambar & chutneys", 199, "Breakfast", True, True, False, True),
    ("Plain Dosa", "Thin crispy rice & lentil crepe with sambar & chutneys", 149, "Breakfast", True, True, False, False),
    ("Idli Sambar", "Steamed rice cakes (3 pcs) with sambar & coconut chutney", 149, "Breakfast", True, True, False, True),
    ("Medu Vada", "Crispy lentil donuts (3 pcs) with sambar & chutney", 169, "Breakfast", True, True, False, False),
    ("Uttapam", "Thick rice pancake topped with onions, tomatoes & chilies", 199, "Breakfast", True, True, False, False),
    ("Pongal", "Creamy rice & lentil porridge tempered with pepper & cumin", 179, "Breakfast", True, False, False, False),
    ("Upma", "Semolina cooked with vegetables & spices", 149, "Breakfast", True, True, False, False),

    # Main Course – Non-Veg
    ("Chettinad Chicken Curry", "Fiery chicken curry with freshly ground spices", 399, "Main Course", False, False, True, True),
    ("Hyderabadi Biryani", "Fragrant basmati rice layered with spiced meat & saffron", 349, "Main Course", False, False, True, True),

    # Main Course – Veg
    ("Vegetable Biryani", "Aromatic basmati rice with seasonal vegetables", 279, "Main Course", True, True, False, False),
    ("Paneer Tikka Masala", "Cottage cheese in creamy tomato-spice gravy", 329, "Main Course", True, False, False, False),
    ("Fish Moilee", "Kerala-style fish in coconut milk & turmeric sauce", 429, "Main Course", False, False, False, False),
    ("Sambar Rice", "Lentil stew with vegetables served over steamed rice", 229, "Main Course", True, True, False, False),
    ("Rasam Rice", "Tangy tamarind-pepper soup with rice & papad", 199, "Main Course", True, True, False, False),
    ("Sarovar Special Thali", "Complete meal: rice, sambar, rasam, 2 curries, curd, papad, dessert", 499, "Main Course", True, False, False, True),

    # Snacks
    ("Bajji Platter", "Assorted vegetable fritters with mint chutney", 199, "Snacks", True, True, False, False),
    ("Chicken 65", "Spicy deep-fried chicken bites, Hyderabad style", 299, "Snacks", False, False, True, True),
    ("Mysore Bonda", "Crispy fried lentil balls with coconut chutney", 179, "Snacks", True, True, False, False),
    ("Paneer Pakora", "Cottage cheese fritters with spiced batter", 249, "Snacks", True, False, False, False),

    # Beverages
    ("Filter Coffee", "Traditional South Indian drip coffee with chicory", 99, "Beverages", True, False, False, True),
    ("Masala Chai", "Spiced tea with cardamom, ginger & cinnamon", 79, "Beverages", True, False, False, False),
    ("Mango Lassi", "Sweet yogurt drink blended with mango pulp", 149, "Beverages", True, False, False, True),
    ("Buttermilk", "Spiced churned yogurt drink (Neer Mor)", 79, "Beverages", True, False, False, False),
    ("Rose Milk", "Chilled milk infused with rose syrup", 99, "Beverages", True, False, False, False),
    ("Fresh Lime Soda", "Freshly squeezed lime with soda", 89, "Beverages", True, True, False, False),

    # Desserts
    ("Gulab Jamun", "Deep-fried milk dumplings in rose-cardamom syrup (2 pcs)", 149, "Desserts", True, False, False, True),
    ("Payasam", "South Indian rice pudding with cashews & raisins", 179, "Desserts", True, False, False, False),
    ("Mysore Pak", "Ghee-rich gram flour fudge", 149, "Desserts", True, False, False, False),
    ("Rava Kesari", "Semolina halwa with saffron, ghee & dry fruits", 149, "Desserts", True, False, False, False),
]

    
    for item in menu:
        cur.execute('''
            INSERT INTO menu_items (name, description, price, category, is_veg, is_vegan, is_spicy, is_bestseller)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', item)

# --- Groq LLM ---
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = """You are Dexter, AI assistant for Sarovar South Spice restaurant.

RULES:
1. Keep responses to 1-2 sentences MAX. Be concise.
2. No markdown, no asterisks, no bullet points. Plain text only.
3. Be warm but brief. No filler words or unnecessary pleasantries.
4. For bookings, say: use the booking form in the chat.
5. Never invent info not listed below.

RESTAURANT: 123 Flavor Street, Thanjavur | 11AM-10PM daily | 040-23456789 | contact@sarovarsouthspice.com | Free parking, valet weekends | Free WiFi | Est. 2023"""

def get_llm_response(message, history=None):
    if not groq_client:
        return None
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": message})
        
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=150,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"LLM error: {e}")
        return None

# --- Rule-Based Fallback ---
def detect_intent(text):
    text = text.lower().strip()
    scores = {"greeting": 0, "book_table": 0, "menu": 0, "hours": 0, "bye": 0, "contact": 0, "location": 0, "dietary_restrictions": 0, "chef_recommendation": 0, "fallback": 0}
    
    if any(w in text for w in ["hello", "hi", "hey", "greetings", "namaste", "vanakkam"]): scores["greeting"] += 10
    if any(w in text for w in ["book", "reservation", "table", "reserve", "seat"]): scores["book_table"] += 10
    if any(w in text for w in ["menu", "food", "eat", "order", "dish", "price", "cost"]): scores["menu"] += 10
    if any(w in text for w in ["hour", "timing", "open", "close", "when", "schedule"]): scores["hours"] += 10
    if any(w in text for w in ["bye", "goodbye", "see you", "thanks", "thank you"]): scores["bye"] += 10
    if any(w in text for w in ["contact", "phone", "email", "reach", "call"]): scores["contact"] += 10
    if any(w in text for w in ["where", "location", "address", "direction", "parking"]): scores["location"] += 10
    if any(w in text for w in ["vegetarian", "vegan", "allergy", "gluten", "spicy", "diet"]): scores["dietary_restrictions"] += 10
    if any(w in text for w in ["recommend", "special", "best", "chef", "popular", "try"]): scores["chef_recommendation"] += 10
    
    max_intent = max(scores, key=scores.get)
    return max_intent if scores[max_intent] > 4 else "fallback"

try:
    with open('full.json') as f:
        intent_data = json.load(f)
except:
    intent_data = {"intents": []}

def get_rule_response(tag):
    for intent in intent_data['intents']:
        if intent['tag'] == tag:
            resp = random.choice(intent['responses'])
            if '{{booking_id}}' in resp:
                resp = resp.replace('{{booking_id}}', str(uuid.uuid4())[:8].upper())
            return resp
    
    defaults = {
        "greeting": "Welcome to Sarovar South Spice! How can I help you today?",
        "menu": "We serve authentic South Indian cuisine. Check out our full menu using the Menu button!",
        "hours": "We're open daily from 11 AM to 10 PM. Last orders at 9:30 PM.",
        "contact": "Reach us at (123) 456-7890 or contact@sarovarsouthspice.com",
        "location": "We're at 123 Flavor Street, Culinary District. Free parking available!",
        "dietary_restrictions": "We have extensive vegetarian and vegan options. Spice levels can be adjusted.",
        "chef_recommendation": "Chef recommends the Masala Dosa ($8.99), Chettinad Chicken ($14.99), and Sarovar Special Thali ($16.99)!",
        "bye": "Thank you for visiting! Have a wonderful day!",
        "book_table": "I'd love to help you book a table! Use the booking form in the chat.",
    }
    return defaults.get(tag, "I'm not sure about that. Could you try rephrasing?")

# --- Routes ---

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'response': 'Please type a message.', 'intent': 'fallback'})
    
    if not session.get('session_id'):
        session['session_id'] = str(uuid.uuid4())
    if 'history' not in session:
        session['history'] = []
    
    if is_rate_limited(session.get('session_id', '')):
        return jsonify({'response': 'You\'re sending messages too fast. Please wait a moment.', 'intent': 'fallback'})
    
    
    intent = detect_intent(message)
    
    # Try LLM, fallback to rules
    response = get_llm_response(message, session.get('history', [])) if groq_client else None
    if not response:
        response = get_rule_response(intent)
    
    # Update history
    session['history'] = session.get('history', [])
    session['history'].append({"role": "user", "content": message})
    session['history'].append({"role": "assistant", "content": response})
    session['history'] = session['history'][-20:]
    session.modified = True
    
    return jsonify({'response': response, 'intent': intent})

@app.route('/menu', methods=['GET'])
def get_menu():
    category = request.args.get('category')
    veg_only = request.args.get('veg')
    
    try:
        conn = get_db()
        cur = conn.cursor()
        query = 'SELECT * FROM menu_items'
        params, conditions = [], []
        
        if category:
            conditions.append('category = %s')
            params.append(category)
        if veg_only == 'true':
            conditions.append('is_veg = TRUE')
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY category, is_bestseller DESC, name'
        
        cur.execute(query, params)
        items = cur.fetchall()
        for item in items:
            item['price'] = float(item['price'])
        cur.close()
        conn.close()
        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'items': [], 'error': str(e)})

@app.route('/menu/categories', methods=['GET'])
def get_categories():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT category FROM menu_items ORDER BY category')
        cats = [r['category'] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'categories': cats})
    except:
        return jsonify({'categories': ['Breakfast', 'Main Course', 'Snacks', 'Beverages', 'Desserts']})

@app.route('/book', methods=['POST'])
def book_table():
    data = request.json
    booking_id = str(uuid.uuid4())[:8].upper()
    session_id = session.get('session_id', str(uuid.uuid4()))
    
    name = data.get('name', '').strip()
    date = data.get('date', '').strip()
    time = data.get('time', '').strip()
    party_size = data.get('party_size', 2)
    special = data.get('special_requests', '').strip()
    
    if not name or not date or not time:
        return jsonify({'status': 'error', 'message': 'Name, date, and time are required.'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO bookings (id, session_id, name, date, time, party_size, special_requests) VALUES (%s,%s,%s,%s,%s,%s,%s)',
            (booking_id, session_id, name, date, time, party_size, special)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            'status': 'success',
            'booking_id': booking_id,
            'message': f'Table booked for {name}! Booking ID: {booking_id}. Party of {party_size} on {date} at {time}.'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Booking failed. Please try again.'}), 500

@app.route('/booking/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM bookings WHERE id = %s', (booking_id.upper(),))
        booking = cur.fetchone()
        cur.close()
        conn.close()
        if booking:
            return jsonify({'status': 'found', 'booking': dict(booking)})
        return jsonify({'status': 'not_found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/rate', methods=['POST'])
def rate_conversation():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'No session'}), 400
    
    rating = request.json.get('rating')
    feedback = request.json.get('feedback', '')
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'status': 'error', 'message': 'Invalid rating'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT INTO ratings (session_id, rating, feedback) VALUES (%s,%s,%s)', (session_id, rating, feedback))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Rating error: {e}")
    
    return jsonify({'status': 'success', 'message': 'Thank you for your feedback!'})

@app.route('/test')
def test():
    return jsonify({'status': 'ok', 'llm_enabled': bool(groq_client), 'db_connected': bool(DATABASE_URL)})

@app.route('/reset-menu')
def reset_menu():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('DELETE FROM menu_items')
        seed_menu(cur)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Menu reset'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Init DB on startup
try:
    if DATABASE_URL:
        init_db()
except:
    pass

if __name__ == '__main__':
    if DATABASE_URL:
        init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
