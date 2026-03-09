# Лабораторна робота 4: Rule-based IE (regex + dictionaries)

## 1) Які 3 типи полів витягуються
- `DATE`
- `AMOUNT`
- `DOC_ID`

## 2) Які правила/словники використано
- Regex для `DATE` у форматах `DD.MM.YYYY`, `D.M.YYYY`, а також з роздільниками `-` і `/`.
- Regex для `AMOUNT` з валютними маркерами (`грн`, `гривень`, `доларів`, `$`, `€`, `UAH`, `USD`, `EUR`).
- Regex для `DOC_ID` за шаблоном `№ ...` + контекстні anti-rules.
- Словник валют: `resources/currencies.json`.
- Словник контекстних слів для DOC_ID: `resources/doc_id_context_words.txt`.

## 3) Precision по кожному типу поля (gold subset)
| Field type | Correct | All extractions | Precision |
|---|---:|---:|---:|
| DATE | 12 | 19 | 0.6316 |
| AMOUNT | 10 | 12 | 0.8333 |
| DOC_ID | 10 | 11 | 0.9091 |

## 4) Топ-5 edge cases у корпусі
- `... договору №3 від 25.05.2011 ...` — DATE і DOC_ID поруч.
- `... від 31.10.2007 р.` — короткий суфікс `р.` після дати.
- `... у таборі № 36 ...` — не вважати номер табору DOC_ID.
- `100%` — не вважати AMOUNT.
- `... 10.04.2008 №610 ...` — не змішувати DATE із DOC_ID.