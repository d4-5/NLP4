# Лабораторна робота 11 — LLM extraction (schema-first)

## 1. Який extraction-кейс обрано
З новинного / юридичного тексту українською витягуються структуровані сигнали:
- `document_id`
- `document_type`
- `date_iso`
- `date_text`
- `amount_value`
- `amount_currency`

Це продовжує попередні ЛР:
- `lab4`: rule-based IE для регулярних полів;
- `lab10`: NER pipeline + hybrid rules;
- `lab11`: LLM extraction як надійний structured-output pipeline.

## 2. Яка schema
Формальна JSON schema винесена в:
- `src/json_schema.py`
- `docs/extraction_schema_lab11.md`

Ключові правила:
- всі 6 полів є `required`;
- відсутні значення позначаються `null`;
- сторонні поля заборонені (`additionalProperties=false`);
- `document_type` та `amount_currency` мають enum-обмеження.

## 3. Як виглядає baseline prompt
Baseline prompt:
- дає моделі сам текст;
- явно перелічує required keys;
- вимагає `null` для missing values;
- вимагає тільки JSON без markdown і пояснень;
- дублює правила schema у текстовому вигляді.

Реалізація:
- `src/llm_extract.py`

## 4. Який validator використано
Pipeline перевіряє окремо:
- `parse success / fail`
- `schema success / fail`
- додаткові consistency rules для `null`

Реалізація:
- `src/validator.py`

## 5. Як працює repair loop
Логіка:
1. Робимо raw extraction.
2. Парсимо JSON.
3. Валідуюємо проти schema.
4. Якщо є помилка, запускаємо repair prompt з:
   - broken output;
   - повідомленням про validation errors;
   - вимогою повернути тільки валідний JSON.
5. Максимум `2` repair attempts.

Реалізація:
- `src/repair_loop.py`
- `src/lab11_pipeline.py`

## 6. Який valid JSON rate до і після repair
Після запуску pipeline реальні метрики зберігаються у:
- `data/sample/lab11_metrics.json`
- `docs/audit_summary_lab11.md`

Фактичний результат на `data/sample/lab11_eval_20.jsonl`:
- raw valid JSON rate: `70%`
- post-repair valid JSON rate: `100%`
- schema-valid JSON rate: `100%`
- average repairs per example: `0.3`
- semantic exact match rate: `25%`

## 7. Які проблеми залишаються
Навіть після repair loop лишаються ризики:
- semantic extraction error при формально валідному JSON;
- неправильна нормалізація `document_type` або `amount_currency`;
- hallucinated values у полях, де gold очікує `null`.

За підсумком прогону найчастіше ламалися:
- `document_id` і `document_type`;
- `date_text` / `date_iso`;
- рідше `amount_value` / `amount_currency`.
