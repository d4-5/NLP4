# Лабораторна робота 13 — Multi-agent crew

## 1. Use case
Multi-agent extraction для українських юридично-новинних текстів. Crew витягує:
`document_id`, `document_type`, `date_iso`, `date_text`, `amount_value`, `amount_currency`.

## 2. Агенти
- `TriagerAgent` визначає route, expected fields, difficulty і special handling.
- `ExtractorAgent` повертає schema-only JSON.
- `ReviewerAgent` перевіряє валідність, schema, consistency і grounding.
- `RepairAgent` запускається тільки після reviewer verdict, якщо потрібен repair/fallback.

## 3. Workflow
`input -> Triager -> Extractor -> Reviewer -> final output / fallback`

## 4. Delegation rules
1. Triager завжди викликається першим.
2. Extractor отримує input і triage route.
3. Reviewer завжди перевіряє output Extractor.
4. Якщо verdict=`accept`, crew повертає final output.
5. Якщо verdict не `accept`, запускається Repair/Fallback.
6. Якщо repair не дає schema-valid extraction, застосовується rule-based partial fallback.
7. Якщо partial output небезпечний або порожній, case отримує manual review status.

## 5. Reviewer
Reviewer поєднує Groq review step і локальні deterministic checks:
- JSON parse;
- JSON schema;
- consistency між null-полями;
- grounded `document_id`, `date_text`, `amount_value`;
- missed fields за rule evidence.

## 6. Fallback
Fallback спрацьовує при invalid JSON, schema errors, hallucinated value, contradiction або missed field.
Порядок: `RepairAgent -> rule_based_partial -> safe failure/manual review`.

## 7. Metrics
Обчислюються:
- valid final output rate;
- reviewer catch rate;
- fallback activation rate;
- fallback success rate;
- manual review rate;
- single-agent vs crew valid output comparison;
- hallucination/missing-field issue counts;
- average agents called per case.

## 8. Головний висновок
Multi-agent crew корисний не через кількість агентів, а через контрольований workflow:
triage задає маршрут, extraction виконується за schema, reviewer ловить помилки, а fallback не дає системі вигадувати небезпечні значення.
