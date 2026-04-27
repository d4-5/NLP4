# Lab 11 Extraction Schema

## 1. Яка extraction-задача
Schema-first extraction для українських новинних / юридичних текстів: потрібно витягти структуровані сигнали документа, дати та суми з одного текстового фрагмента.

Обраний кейс:
- `document_id`
- `document_type`
- `date_iso`
- `date_text`
- `amount_value`
- `amount_currency`

Правило агрегації:
- для кожного поля беремо перший релевантний сигнал у порядку читання;
- якщо поля в тексті немає, повертаємо `null`.

## 2. Які поля у JSON
- `document_id`: `string | null`
- `document_type`: `string | null`
- `date_iso`: `string | null`
- `date_text`: `string | null`
- `amount_value`: `number | null`
- `amount_currency`: `string | null`

## 3. Які поля required
У schema всі 6 полів є `required`, але кожне з них може мати значення `null`, якщо сигнал у тексті відсутній.

## 4. Як виглядає JSON schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Lab 11 document signal extraction schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "document_id": {
      "type": ["string", "null"],
      "minLength": 1
    },
    "document_type": {
      "type": ["string", "null"],
      "enum": ["CASE_ID", "CONTRACT_ID", "ORDER_ID", "GENERIC_DOC_ID", null]
    },
    "date_iso": {
      "type": ["string", "null"],
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "date_text": {
      "type": ["string", "null"],
      "minLength": 1
    },
    "amount_value": {
      "type": ["number", "null"],
      "minimum": 0
    },
    "amount_currency": {
      "type": ["string", "null"],
      "enum": ["UAH", "USD", "EUR", "UNKNOWN", null]
    }
  },
  "required": [
    "document_id",
    "document_type",
    "date_iso",
    "date_text",
    "amount_value",
    "amount_currency"
  ]
}
```

## 5. Які правила для null / missing values
- Значення відсутнє в тексті: повертаємо `null`.
- `document_id=null` вимагає `document_type=null`.
- `amount_value=null` вимагає `amount_currency=null`.
- `date_iso=null` вимагає `date_text=null`.
- Вихід без одного з required keys вважається schema violation.

## 6. Які поля найчастіше проблемні
На evaluation set `data/sample/lab11_eval_20.jsonl` найчастіше ламалися:
- `document_id`: 11 mismatch cases;
- `document_type`: 11 mismatch cases;
- `date_text`: 11 mismatch cases;
- `date_iso`: 9 mismatch cases;
- `amount_value`: 3 mismatch cases;
- `amount_currency`: 3 mismatch cases.

## 7. Що repair loop реально виправляє
Repair loop цілиться в три групи збоїв:
- текст замість чистого JSON;
- JSON, який не проходить schema validation;
- JSON, який формально парситься, але ламає null-consistency rules.

Фактичний результат:
- raw valid JSON rate: `70%`;
- post-repair valid JSON rate: `100%`;
- repair був потрібен у `30%` прикладів;
- repair не провалився жодного разу на структурному рівні.

Що repair loop виправив добре:
- null-consistency issues;
- структурні проблеми у виході, через які raw JSON не вважався валідним.

Що лишилося проблемним навіть після repair:
- semantic extraction errors при формально валідному JSON;
- пропуски `document_id` / `document_type` у юридичних фрагментах;
- окремі hallucinated values на date-only прикладах.
