const form = document.getElementById('generateForm');
const resultContainer = document.getElementById('result');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // 1. Очистка и индикация загрузки
    resultContainer.innerHTML = '<div class="loading-indicator">Генерация учебных материалов... Пожалуйста, подождите.</div>';
    
    // Блокируем кнопку на время запроса для предотвращения повторных отправок
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    // 2. Сбор данных (используем FormData для более чистого сбора данных)
    const formData = new FormData(form);
    const payload = {};
    for (const [key, value] of formData.entries()) {
        payload[key] = value.trim(); // Добавлено trim() для очистки пробелов
    }

    try {
        // 3. Отправка запроса
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        // 4. Обработка ошибок HTTP
        if (!resp.ok) {
            // Пытаемся получить детали ошибки из JSON-ответа
            const errorData = await resp.json().catch(() => ({})); 
            const errorMessage = errorData.error || `Произошла ошибка HTTP: ${resp.status} (${resp.statusText}).`;
            resultContainer.innerHTML = `<div class="error-message">❌ Ошибка: ${errorMessage}</div>`;
            return;
        }

        // 5. Парсинг и отрисовка успешного ответа
        const data = await resp.json();
        
        // Очищаем контейнер перед финальной отрисовкой
        resultContainer.innerHTML = '';
        
        // Функции для создания HTML-блоков
        const renderPlan = (plan) => `
            <section class="result-block plan-block">
                <h2>📝 План урока</h2>
                <p>${plan}</p>
            </section>`;

        const renderFlashcards = (cards) => `
            <section class="result-block flashcards-block">
                <h3>🎴 Карточки для запоминания (${cards.length})</h3>
                <ul class="flashcard-list">
                    ${cards.map(c => 
                        `<li>
                            <div class="card-q"><b>Вопрос:</b> ${c.q}</div>
                            <div class="card-a"><b>Ответ:</b> ${c.a}</div>
                        </li>`).join('')}
                </ul>
            </section>`;

        const renderTest = (testItems) => `
            <section class="result-block test-block">
                <h3>❓ Тест/Вопросы (${testItems.length})</h3>
                <ol class="test-list">
                    ${testItems.map((q, index) => 
                        `<li>
                            <p><strong>${index + 1}. ${q.q}</strong></p>
                            <div class="test-details">
                                <p>Правильный ответ: <b>${q.answer || 'Не указан'}</b></p>
                                ${q.explanation ? `<p class="explanation">Объяснение: ${q.explanation}</p>` : ''}
                            </div>
                        </li>`).join('')}
                </ol>
            </section>`;
            
        // 6. Сборка финального HTML
        let finalHTML = '';
        if (data.plan) {
            finalHTML += renderPlan(data.plan);
        }
        if (data.flashcards && data.flashcards.length) {
            finalHTML += renderFlashcards(data.flashcards);
        }
        if (data.test && data.test.length) {
            finalHTML += renderTest(data.test);
        }
        if (data.trainer && data.trainer.length) {
            // Тренажер можно отрисовать проще
            finalHTML += `
                <section class="result-block trainer-block">
                    <h3>💡 Задания тренажёра (${data.trainer.length})</h3>
                    <ol class="trainer-list">
                        ${data.trainer.map(t => `<li><b>${t.level}:</b> ${t.task}</li>`).join('')}
                    </ol>
                </section>`;
        }
        
        // Если ничего не вернулось
        if (finalHTML === '') {
             resultContainer.innerHTML = `<div class="info-message">⚠️ Модель не смогла сгенерировать контент по вашему запросу.</div>`;
        } else {
            resultContainer.innerHTML = finalHTML;
        }
        
    } catch (error) {
        // 7. Обработка сетевых и других ошибок
        console.error('Ошибка при выполнении запроса:', error);
        resultContainer.innerHTML = `<div class="error-message">❌ Критическая ошибка соединения. Проверьте консоль.</div>`;
    } finally {
        // 8. Разблокировка кнопки
        submitButton.disabled = false;
    }
});