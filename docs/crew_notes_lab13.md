# Lab 13 Crew Notes

## 1. Use case
Обрано schema-first document signal extraction як продовження ЛР11: з українських юридично-новинних текстів витягуються `document_id`, `document_type`, `date_iso`, `date_text`, `amount_value`, `amount_currency`.

## 2. Agents
- `TriagerAgent`
- `ExtractorAgent`
- `ReviewerAgent`
- `RepairAgent`

## 3. Ролі
- Triager читає input і визначає route, expected fields, difficulty та special handling.
- Extractor отримує input + triage і повертає тільки schema JSON.
- Reviewer перевіряє schema, missing fields, hallucinated values і consistency із source text.
- RepairAgent виправляє тільки проблемні поля; якщо repair не допомагає, fallback застосовує локальні rules.

## 4. Delegation rules
Triager завжди перший, Extractor завжди другий, Reviewer завжди перевіряє Extractor. Repair/Fallback запускається тільки коли Reviewer verdict не `accept`.

## 5. Що перевіряє Reviewer
- JSON parse success;
- schema validity;
- null consistency;
- чи `document_id` і `date_text` присутні в source;
- чи `amount_value` підтверджується rule evidence;
- чи LLM не пропустив очевидні rule-based сигнали.

## 6. Коли спрацьовує fallback
Fallback спрацьовує при invalid JSON, schema error, hallucinated field, contradiction, likely missed field або reviewer verdict `repair_needed` / `fallback_needed` / `manual_review`.

## 7. Що crew покращив
Crew додає незалежну перевірку після extraction і контрольований safe failure path. Це краще за single-agent baseline, де формально валідний JSON може містити hallucinated або пропущені значення без окремого reviewer verdict.

## 8. Де multi-agent підхід зайвий
Для дуже простих текстів з однією датою або однією сумою single-agent або rule-based extraction достатні. Crew додає latency і вартість.

## 9. Які помилки залишилися
- Relative dates не нормалізуються без поточної дати.
- Короткі номери на кшталт `№15` потребують контекстної перевірки.
- Reviewer може дати false alarm, якщо rule evidence не покриває рідкісний формат.

## 10. Що фіксити далі
- Додати span-level evidence до final output.
- Додати token/cost logging per agent.
- Розширити rule fallback для нестандартних валют і дат.
