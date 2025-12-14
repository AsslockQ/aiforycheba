import json
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from functools import wraps # ВОССТАНОВЛЕНО: Новый импорт для декоратора

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash

# --- 1. КОНФИГУРАЦИЯ СРЕДЫ И API ---

load_dotenv() 
# В начале файла

app = Flask(__name__)
app.secret_key = 'lessonflow-mpit2025-secret-key' 

# === КОНФИГУРАЦИЯ DeepSeek API ===
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-9e41cfcb49fb40cdb383f2a52a9da1f8") 
DEFAULT_LLM_MODEL = "deepseek-v3.2-chat" 
deepseek_client = None
try:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1" 
    )
except Exception as e:
    print(f"FATAL: Ошибка инициализации DeepSeek клиента: {e}")

# === КОНФИГУРАЦИЯ Ollama-совместимого Cloud API ===
OLLAMA_CLOUD_API_URL = "https://[ВАШ_ХОСТ_OLLAMA_CLOUD]/api/generate" 
OLLAMA_CLOUD_API_KEY = "b013b8ea99604562a656de11bd76599f.FlYgASqJ1c6oqrjgt9dje0pl"


# --- 2. ДАННЫЕ КУРСОВ (Без изменений) ---

COURSES = {
    "math-basic": {"name": "Математика. Базовый курс ЕГЭ/ОГЭ", "price": 399, "full_price": 799},
    "english-b1b2": {"name": "Английский язык, B1-B2", "price": 899, "full_price": 899},
    "physics-basic": {"name": "Физика. Базовый курс ЕГЭ/ОГЭ", "price": 699, "full_price": 699},
    "history-full": {"name": "История. Базовый и углублённый курсы ЕГЭ/ОГЭ", "price": 799, "full_price": 1199},
    "chemistry-full": {"name": "Химия. Базовый и углублённый курсы ЕГЭ/ОГЭ", "price": 999, "full_price": 1499},
    "biology-full": {"name": "Биология. Базовый и углублённый курсы ЕГЭ/ОГЭ", "price": 999, "full_price": 1299}
}

SUBJECT_PROMPTS = {
    "math": "Эксперт по школьной математике и подготовке к ЕГЭ/ОГЭ. Отвечай подробно.",
    "physics": "Специалист по физике, кинематике и динамике. Используй формулы LaTeX.",
    "history": "Знаток истории России и мира, ориентированный на формат экзаменов. Используй даты и факты.",
    "chemistry": "Специалист по химии, реакциям и таблице Менделеева. Используй химические формулы.",
    "biology": "Эксперт по биологии, генетике и экологии. Используй терминологию.",
    "english": "Преподаватель английского B1-B2, фокусирующийся на грамматике и лексике.",
    "literature": "Эксперт по русской и зарубежной литературе. Анализируй произведения.",
    "art": "Специалист по истории искусств и живописи. Описывай стили и периоды.",
    "programming": "Эксперт по базовому программированию и алгоритмам. Предоставляй примеры кода."
}

# --- 3. ЛОГИКА АУТЕНТИФИКАЦИИ (ВОССТАНОВЛЕНО) ---

def is_logged_in():
    """Проверяет, авторизован ли пользователь (по наличию user_id в сессии)."""
    return 'user_id' in session

def require_login(f):
    """Декоратор: требует авторизации для доступа к маршруту."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            # Если не авторизован, перенаправляем на страницу регистрации
            return redirect(url_for('register'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. ФУНКЦИИ КОРЗИНЫ И LLM (Без изменений) ---

def get_cart():
    return session.get('cart', [])

def add_to_cart(course_id):
    if course_id in COURSES:
        cart = get_cart()
        if course_id not in cart:
            cart.append(course_id)
            session['cart'] = cart

def clear_cart():
    session.pop('cart', None)

def generate_response_with_llm(subject: str, user_prompt: str, llm_model: str):
    # ... (Ваша функция LLM остается без изменений) ...
    system_role = SUBJECT_PROMPTS.get(subject, "Просто полезный AI-ассистент.")
    prompt_content = f"{system_role}\n\nПользователь спрашивает: \"{user_prompt}\"\n\nОтветь максимально полно и по делу, структурируя ответ с использованием Markdown."

    # --- ЛОГИКА ДЛЯ DEEPSEEK API ---
    if "deepseek" in llm_model.lower() or "gpt" in llm_model.lower():
        if deepseek_client is None:
            return {"error": "DeepSeek/OpenAI-совместимый клиент не инициализирован."}
        
        try:
            response = deepseek_client.chat.completions.create(
                model=llm_model, 
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7 
            )
            return {"response": response.choices[0].message.content}
        except Exception as e:
            print(f"Ошибка DeepSeek/OpenAI: {e}")
            return {"error": f"Ошибка DeepSeek/OpenAI API: {e}"}

    # --- ЛОГИКА ДЛЯ OLLAMA-СОВМЕСТИМОГО CLOUD API (Для Qwen) ---
    elif "qwen" in llm_model.lower() or "llama3" in llm_model.lower():
        if "[ВАШ_ХОСТ_OLLAMA_CLOUD]" in OLLAMA_CLOUD_API_URL:
             return {"error": "Необходимо указать URL для Ollama Cloud API в app.py."}
             
        headers = {
            "Authorization": f"Bearer {OLLAMA_CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        request_data = {
            "model": llm_model,
            "prompt": prompt_content,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        
        try:
            response = requests.post(
                OLLAMA_CLOUD_API_URL,
                headers=headers,
                json=request_data,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            if 'response' in data:
                return {"response": data['response'].strip()}
            
            return {"error": f"Некорректный ответ от Ollama Cloud: {data}"}

        except requests.exceptions.RequestException as e:
            print(f"Ошибка Ollama Cloud: {e}")
            return {"error": f"Ошибка Ollama Cloud API. Проверьте URL и ключ. {e}"}

    return {"error": f"Неизвестная модель: {llm_model}"}

# === 5. МАРШРУТЫ FLASK (ВОССТАНОВЛЕНО) ===

# --- Аутентификационные маршруты ---

@app.route('/register')
def register():
    """Страница регистрации/входа (заглушка)."""
    return render_template('register.html', is_logged_in=is_logged_in())

@app.route('/login', methods=['POST'])
def login():
    """Обработчик входа (заглушка)."""
    # Для целей проекта просто устанавливаем флаг:
    session['user_id'] = 'temp_user_123' 
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Обработчик выхода."""
    session.pop('user_id', None)
    return redirect(url_for('index'))

# --- Основные и защищенные маршруты ---

@app.route('/')
def index():
    if 'add' in request.args:
        # ЗАЩИТА: Если пытаемся добавить в корзину, но не авторизованы, перенаправляем на регистрацию
        if not is_logged_in():
            return redirect(url_for('register'))
        add_to_cart(request.args.get('add'))
        return redirect(url_for('cart')) 
        
    return render_template('index.html', is_logged_in=is_logged_in())


@app.route('/generate')
@require_login # ЗАЩИТА: Требует авторизации
def generate_form():
    """Рендеринг страницы AI-Ассистента."""
    return render_template('generate_form.html', is_logged_in=is_logged_in())

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API-маршрут для общения с LLM (должен быть защищен на фронтенде)."""
    # В реальном приложении здесь также нужна проверка сессии
    if not request.json:
        return jsonify({"error": "Ожидался JSON в теле запроса"}), 400
        
    data = request.json
    subject = data.get('subject', 'math').strip() 
    prompt = data.get('prompt', '').strip()     
    model = data.get('model', DEFAULT_LLM_MODEL).strip()
    
    if not prompt:
        return jsonify({"error": "Вопрос не может быть пустым"}), 400
        
    result = generate_response_with_llm(subject, prompt, model)
    
    if "error" in result:
        return jsonify(result), 503
        
    return jsonify(result)

@app.route('/cart')
@require_login # ЗАЩИТА: Требует авторизации
def cart():
    cart_ids = get_cart()
    cart_items = [COURSES[cid] for cid in cart_ids if cid in COURSES]
    total = sum(item['price'] for item in cart_items)
    cart_count = len(cart_items) 
    
    return render_template('cart.html', items=cart_items, total=total, cart_count=cart_count, is_logged_in=is_logged_in())

@app.route('/cart/add/<course_id>')
@require_login # ЗАЩИТА: Требует авторизации
def add_to_cart_route(course_id):
    add_to_cart(course_id)
    return redirect(url_for('cart'))

@app.route('/cart/clear')
@require_login # ЗАЩИТА: Требует авторизации
def clear_cart_route():
    clear_cart()
    return redirect(url_for('cart'))

@app.route('/cart/buy', methods=['POST'])
@require_login # ЗАЩИТА: Требует авторизации
def buy_courses():
    clear_cart()
    return render_template('success.html', is_logged_in=is_logged_in())

# --- Информационные маршруты (Без изменений) ---
@app.route('/rules')
def rules():
    return render_template('rules.html', is_logged_in=is_logged_in())
@app.route('/faq')
def faq():
    return render_template('faq.html', is_logged_in=is_logged_in())
@app.route('/pricing')
def pricing():
    return render_template('pricing.html', is_logged_in=is_logged_in())
@app.route('/about')
def about():
    return render_template('about.html', is_logged_in=is_logged_in())
@app.route('/cart/apply-promo', methods=['POST'])
def apply_promo():
    data = request.get_json()
    promo = data.get('code', '').strip().upper()
    valid_promos = {
        "START2025": 0.2,
        "MPIT2025": 0.3,
        "FREE": 1.0
    }
    discount = valid_promos.get(promo, 0)
    cart_ids = get_cart()
    cart_items = [COURSES[cid] for cid in cart_ids if cid in COURSES]
    total = sum(item['price'] for item in cart_items)
    discounted = round(total * (1 - discount), 2)
    return jsonify({
        "success": discount > 0,
        "discounted_total": discounted,
        "message": "Промокод применён!" if discount > 0 else "Неверный промокод."
    })
@app.route('/cart/checkout')
@require_login
def checkout():
    """Страница оплаты."""
    cart_ids = get_cart()
    if not cart_ids:
        flash("Корзина пуста", "warning")
        return redirect(url_for('cart'))
    
    cart_items = [COURSES[cid] for cid in cart_ids if cid in COURSES]
    total = sum(item['price'] for item in cart_items)
    
    return render_template('checkout.html', items=cart_items, total=total, is_logged_in=is_logged_in())

# --- Запуск ---
if __name__ == '__main__':
    print("🚀 LessonFlow запущен! Открой http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
