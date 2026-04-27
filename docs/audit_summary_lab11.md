# Lab 11 Audit Summary

## 1. Який extraction-кейс
- Задача: schema-first LLM extraction для новинних/юридичних текстів українською.
- Поля: `document_id`, `document_type`, `date_iso`, `date_text`, `amount_value`, `amount_currency`.
- Модель: `llama-3.1-8b-instant`.

## 2. Скільки прикладів у evaluation set
- `20` текстів із `data/sample/lab11_eval_20.jsonl`.

## 3. Який raw valid JSON rate
- `70.00%`

## 4. Який post-repair valid JSON rate
- `100.00%`

## 5. Який schema-valid JSON rate
- `100.00%`

## 6. Які поля ламались найчастіше
- `document_id`: 11
- `document_type`: 11
- `date_text`: 11
- `date_iso`: 9
- `amount_value`: 3
- `amount_currency`: 3

## 7. Які типи помилок були наймасовішими
- `semantic extraction error despite valid JSON`: 15
- `normalization issue`: 13
- `hallucinated field/value`: 2

## 8. Чи schema-first підхід спрацював добре
- Пайплайн стабілізує structured output через `JSON -> validator -> repair loop`.
- Навіть коли semantic exact match не ідеальний, post-repair valid JSON rate показує, чи результат придатний для автоматичної обробки.

## 9. Мінімум 15 проблемних прикладів
1. `text_10054` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "136-26", "document_type": "GENERIC_DOC_ID", "date_iso": "2014-06-03", "date_text": "03.06.2014", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='136-26', predicted=None; document_type: expected='GENERIC_DOC_ID', predicted=None; date_iso: expected='2014-06-03', predicted=None
2. `text_10071` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "42014000000000523", "document_type": "CASE_ID", "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='42014000000000523', predicted=None; document_type: expected='CASE_ID', predicted=None
3. `text_10224` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "42017171090000003", "document_type": "CASE_ID", "date_iso": "2017-01-04", "date_text": "04.01.2017", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='42017171090000003', predicted=None; document_type: expected='CASE_ID', predicted=None; date_iso: expected='2017-01-04', predicted=None
4. `text_10345` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "42016000000002788", "document_type": "CASE_ID", "date_iso": "2016-10-08", "date_text": "08.10.2016", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='42016000000002788', predicted=None; document_type: expected='CASE_ID', predicted=None; date_iso: expected='2016-10-08', predicted=None
5. `text_10391` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "42017221050000013", "document_type": "CASE_ID", "date_iso": "2017-02-24", "date_text": "24.02.2017", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='42017221050000013', predicted=None; document_type: expected='CASE_ID', predicted=None; date_iso: expected='2017-02-24', predicted=None
6. `text_1723` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": 1000.0, "amount_currency": "UAH"}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=amount_value: expected=1000.0, predicted=None; amount_currency: expected='UAH', predicted=None
7. `text_4225` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": 3000.0, "amount_currency": "UAH"}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=amount_value: expected=3000.0, predicted=None; amount_currency: expected='UAH', predicted=None
8. `text_8894` | valid=True | categories=hallucinated field/value, normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": "2011-05-25", "date_text": "25.05.2011", "amount_value": null, "amount_currency": null}
   predicted={"document_id": "3", "document_type": "CONTRACT_ID", "date_iso": "2011-05-25", "date_text": "25.05.2011 року", "amount_value": null, "amount_currency": null}
   note=document_id: expected=None, predicted='3'; document_type: expected=None, predicted='CONTRACT_ID'; date_text: expected='25.05.2011', predicted='25.05.2011 року'
9. `text_8919` | valid=True | categories=hallucinated field/value, normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": "2013-04-24", "date_text": "24.04.2013", "amount_value": null, "amount_currency": null}
   predicted={"document_id": "GENERIC_DOC_ID", "document_type": "GENERIC_DOC_ID", "date_iso": "2013-04-24", "date_text": null, "amount_value": 1120000, "amount_currency": "UAH"}
   note=document_id: expected=None, predicted='GENERIC_DOC_ID'; document_type: expected=None, predicted='GENERIC_DOC_ID'; date_text: expected='24.04.2013', predicted=None
10. `text_8927` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "12016100000000042", "document_type": "CASE_ID", "date_iso": "2016-01-27", "date_text": "27.01.2016", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='12016100000000042', predicted=None; document_type: expected='CASE_ID', predicted=None; date_iso: expected='2016-01-27', predicted=None
11. `text_9076` | valid=True | categories=semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": "2010-08-16", "date_text": "16.08.2010", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=date_iso: expected='2010-08-16', predicted=None; date_text: expected='16.08.2010', predicted=None
12. `text_9256` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "610", "document_type": "ORDER_ID", "date_iso": "2008-04-10", "date_text": "10.04.2008", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='610', predicted=None; document_type: expected='ORDER_ID', predicted=None; date_iso: expected='2008-04-10', predicted=None
13. `text_9326` | valid=True | categories=semantic extraction error despite valid JSON
   expected={"document_id": null, "document_type": null, "date_iso": "2018-02-14", "date_text": "14.02.2018", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=date_iso: expected='2018-02-14', predicted=None; date_text: expected='14.02.2018', predicted=None
14. `text_9677` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "15", "document_type": "GENERIC_DOC_ID", "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='15', predicted=None; document_type: expected='GENERIC_DOC_ID', predicted=None
15. `text_9843` | valid=True | categories=normalization issue, semantic extraction error despite valid JSON
   expected={"document_id": "42016050000000308", "document_type": "CASE_ID", "date_iso": "2016-04-26", "date_text": "26.04.2016", "amount_value": null, "amount_currency": null}
   predicted={"document_id": null, "document_type": null, "date_iso": null, "date_text": null, "amount_value": null, "amount_currency": null}
   note=document_id: expected='42016050000000308', predicted=None; document_type: expected='CASE_ID', predicted=None; date_iso: expected='2016-04-26', predicted=None
