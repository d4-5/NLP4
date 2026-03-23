# Лабораторна робота 6: TF-IDF + Logistic baseline

## 1) Напрям
B (Extraction / NER)

## 2) Classification-підзадача
Класифікація `text_id` за домінантним типом сутності (`dominant_label` з `labels.csv` + `NO_ENTITY`, якщо сутності відсутні).

## 3) Порівняні baseline-варіанти
- Baseline 1: `processed_v2` + TF-IDF word `(1,1)` + Logistic Regression.
- Baseline 2: `processed_v2` + TF-IDF word `(1,2)` + Logistic Regression.

## 4) Основні метрики
- Baseline 1 (word 1-1): accuracy=0.6165, macro-F1=0.2200
- Baseline 2 (word 1-2): accuracy=0.6147, macro-F1=0.2162
- Best baseline: B1_word_1_1 (за val macro-F1)

## 5) Error analysis і наступні кроки
Найтиповіші помилки: домінування `NO_ENTITY` (сутність є, але слабкий сигнал), перекриття типів (DATE vs MON/PERIOD, ORG vs MISC), короткі або неоднозначні контексти. Першим кроком перевірю `class_weight=\"balanced\"` та/або леми, а також додам прості правила/ознаки для дат і сум.
