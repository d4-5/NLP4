# Підсумок аудиту ЛР13

## 1. Вибраний use case
- Multi-agent витягування структурованих сигналів із українських юридичних і новинних текстів.
- Поля: `document_id`, `document_type`, `date_iso`, `date_text`, `amount_value`, `amount_currency`.

## 2. Реалізовані агенти
- Triager: обирає маршрут, очікувані поля, складність і спеціальну обробку.
- Extractor: повертає лише JSON, що відповідає схемі.
- Reviewer: перевіряє валідність JSON, відповідність схемі, grounding і узгодженість.
- Repair/Fallback: виправляє проблеми, знайдені reviewer, і застосовує rule-based partial extraction, якщо repair не спрацював.

## 3. Кількість тестових кейсів: `10`

## 4. Метрики
- Частка валідних фінальних результатів: `90.00%`
- Частка проблем, які спіймав reviewer: `100.00%`
- Частка кейсів, де активувався fallback: `100.00%`
- Частка успішних fallback-спроб: `80.00%`
- Частка кейсів, що пішли на manual review: `60.00%`

## 5. Порівняння single-agent і crew
| Варіант | Частка валідних результатів | Примітки |
|---|---:|---|
| Single-agent baseline | 50.00% | Один виклик Groq для extraction без незалежної перевірки. |
| Multi-agent crew | 90.00% | Triager + Extractor + Reviewer + fallback. |

## 6. Вдалі приклади роботи crew
- `case_001`: status=`accepted_after_repair`, fallback=True
- `case_002`: status=`accepted_after_repair`, fallback=True
- `case_006`: status=`accepted_after_repair`, fallback=True

## 7. Проблемні приклади
- `case_001`: status=`accepted_after_repair`, review=`fallback_needed`
- `case_002`: status=`accepted_after_repair`, review=`fallback_needed`
- `case_003`: status=`partial_manual_review`, review=`repair_needed`

## 8. Аналіз помилок
- `case_001` | category=`simple_valid` | fallback=`repair_agent` | fix: переглянути зауваження reviewer і додати точніше правило або prompt constraint.
- `case_002` | category=`missing_required_signal` | fallback=`repair_agent` | fix: переглянути зауваження reviewer і додати точніше правило або prompt constraint.
- `case_003` | category=`ambiguous_entity` | fallback=`rule_based_partial` | fix: посилити grounding rules для `document_id` і вимагати явний юридичний контекст.
- `case_004` | category=`relative_date` | fallback=`rule_based_partial` | fix: додати optional current-date-aware policy для нормалізації relative dates.
- `case_005` | category=`hallucination_prone` | fallback=`safe_failure` | fix: переглянути зауваження reviewer і додати точніше правило або prompt constraint.
- `case_006` | category=`noisy_typos` | fallback=`repair_agent` | fix: переглянути зауваження reviewer і додати точніше правило або prompt constraint.
- `case_007` | category=`fallback_required` | fallback=`repair_agent` | fix: зберегти rule-based fallback для коротких ID, dates і currency normalization.
- `case_008` | category=`reviewer_rejection` | fallback=`rule_based_partial` | fix: посилити grounding rules для `document_id` і вимагати явний юридичний контекст.
- `case_009` | category=`repair_succeeds` | fallback=`rule_based_partial` | fix: зберегти rule-based fallback для коротких ID, dates і currency normalization.
- `case_010` | category=`manual_review_after_failed_repair` | fallback=`safe_failure` | fix: повертати безпечний partial output і відправляти кейс на manual review.

## 9. Що покращувати далі
- Додати сильніший span-level grounding для значень, які вибирає LLM.
- Додати current-date-aware handling, якщо relative dates увійдуть у scope.
- Логувати token/cost metrics для кожного agent call для кращого operational comparison.
