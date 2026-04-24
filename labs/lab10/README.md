# Лабораторна робота 10 — NER pipeline + hybrid rules

## 1. Корпус / evaluation set
- Основний корпус: `data/processed_v2.csv`
- Gold labels: `data/labels.csv`
- Малий evaluation set: `data/sample/lab10_ner_eval.jsonl`
- Формат evaluation set: `text`, `expected_entities`, `comment`
- Розмір evaluation set: 20 вручну відібраних документів з прикладами `PERS`, `ORG`, `DATE`, `MON`, `LOC`

## 2. Який pipeline запущено
- Baseline: `Stanza uk` з процесорами `tokenize,ner`
- Мета: практичний NER inference без fine-tuning

## 3. Які rules додано
- Regex для `MON`
- Regex для `DATE`
- Rule-based `ORG` extraction для юридичних форм і абревіатур
- Post-processing для розширення меж `ORG` span

## 4. Що baseline знаходив добре
Baseline очікувано краще працює на:
- класичних `PERS`;
- частині коротких `ORG`;
- очевидних `LOC`.

## 5. Що baseline пропускав
Найтиповіші слабкі місця:
- суми у форматі `млн грн`, `тис грн`, `$25 тис`;
- дати в коротких новинних патернах;
- доменні `ORG` зі скороченнями та юридичними префіксами;
- довгі назви установ, де baseline дає boundary error.

## 6. Що rules покращили
Hybrid layer покращує:
- coverage для `MON` і `DATE`;
- виявлення `ORG` з `ТОВ` / `ПАТ` / `ДП` / `ГО`;
- окремі boundary помилки для корпоративних назв.

## 7. Які проблеми ще не вирішені
- дуже довгі складені назви установ;
- nested spans;
- неоднозначні кейси `ORG` vs `LOC`;
- noise через лапки, пунктуацію й непослідовну нормалізацію в тексті.
