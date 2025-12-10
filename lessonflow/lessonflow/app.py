from flask import Flask, request, jsonify, render_template
import os
import json
from google import genai
from google.genai.errors import APIError
from google.genai import types 

app = Flask(__name__)

BASE_PROMPT = "" # Инициализация переменной

# --- Функции инициализации ---
def load_base_prompt(filepath='prompt.txt'):
    """Загружает базовый системный промпт из файла."""
    try:
        # Проверяем, существует ли файл перед чтением
        if not os.path.exists(filepath):
            print(f"ВНИМАНИЕ: Файл промпта '{filepath}' не найден. Используется промпт по умолчанию.")
            return "You are a helpful assistant for creating structured educational materials. Your response MUST be a single, valid JSON object, strictly following the specified structure."
            
        with open(filepath, 'r', encoding='utf-8') as f:
            # Используем strip() для удаления лишних пробелов в начале/конце промпта
            return f.read().strip() 
    except Exception as e:
        print(f"Ошибка при загрузке промпта: {e}")
        return "You are a helpful assistant for creating structured educational materials. Your response MUST be a single, valid JSON object, strictly following the specified structure."

# --- Точки входа ---

@app.route('/')
def index():
    """Простая точка рендера главной страницы."""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    """Эндпойнт для генерации контента."""
    
    # 1. Проверка и получение данных
    if not request.json:
        return jsonify({"error": "Missing JSON data"}), 400
    
    data = request.json
    
    # Получение и очистка данных пользователя
    topic = data.get('topic', '').strip()
    klass = data.get('class', '').strip()
    goal = data.get('goal', '').strip()
    level = data.get('level', 'basic').strip()
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    global BASE_PROMPT
    
    # Формирование пользовательского запроса
    user_request = (
        f"Сгенерируй учебные материалы, строго следуя следующей структуре и данным:\n"
        f"Тема: {topic}\n"
        f"Класс: {klass}\n"
        f"Цель: {goal}\n"
        f"Уровень сложности: {level}\n"
    )


    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "API Key not found. Set GEMINI_API_KEY environment variable."}), 500
        
    try:
        # Инициализация клиента Gemini
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                {"role": "user", "parts": [{"text": user_request}]}
            ],
            config=types.GenerateContentConfig(
                system_instruction=BASE_PROMPT,
                # Указываем, что ждем JSON
                response_mime_type="application/json", 
                # SCHEMA определяет структуру, которую ДОЛЖНА вернуть модель
                response_schema={
                    "type": "object",
                    "properties": {
                         "plan": {"type": "string", "description": "Подробный план урока."},
                         "flashcards": {"type": "array", "items": {"type": "object", "properties": {"q": {"type": "string", "description": "Вопрос"}, "a": {"type": "string", "description": "Ответ"}}}},
                         "test": {"type": "array", "items": {"type": "object", "properties": {"q": {"type": "string", "description": "Вопрос теста"}, "type": {"type": "string", "description": "Тип вопроса (mcq/tf)"}, "answer": {"type": "string", "description": "Правильный ответ"}, "explanation": {"type": "string", "description": "Объяснение"}}}},
                         "trainer": {"type": "array", "items": {"type": "object", "properties": {"level": {"type": "string", "description": "Уровень задачи (L1, L2)"}, "task": {"type": "string", "description": "Текст задачи"}, "answer": {"type": "string", "description": "Правильный ответ"}, "explain": {"type": "string", "description": "Объяснение решения"}}}}
                    }
                }
            )
        )
        
        # Модель возвращает JSON-строку в response.text, парсим ее
        model_output = json.loads(response.text)
    
    except json.JSONDecodeError:
        return jsonify({"error": "Model returned invalid JSON format. Try again or check the BASE_PROMPT."}), 500
        
    except APIError as e:
        return jsonify({"error": f"Gemini API Error: {e}"}), 500
        
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {e}"}), 500

    return jsonify(model_output)


if __name__ == '__main__':
    # Загружаем промпт при старте
    BASE_PROMPT = load_base_prompt()
    
    # Проверка на наличие API ключа при старте
    if not os.environ.get('GEMINI_API_KEY'):
        print("\n--- ВАЖНО ---\nПеременная окружения 'GEMINI_API_KEY' не установлена. Приложение не сможет вызвать API.\nУстановите ключ для запуска.\n---\n")
        
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)