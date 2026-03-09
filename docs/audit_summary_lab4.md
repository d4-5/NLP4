# Audit Summary Lab 4

- Updated at: 2026-03-09
- Extraction types: DATE, AMOUNT, DOC_ID
- Strategy: precision-first (regex + dictionaries + anti-rules)

## Precision (gold subset)
- DATE: precision=0.6316 (12/19), gold_size=12
- AMOUNT: precision=0.8333 (10/12), gold_size=10
- DOC_ID: precision=0.9091 (10/11), gold_size=10

## Error analysis (10 FP)
1. [DATE] `19.02.2018` (text_id=text_9326)
   Причина: валідна дата знайдена rules-модулем, але відсутня у gold.
   Дія: додати пропущену DATE-розмітку в цьому ж text_id.
2. [DATE] `21.03.2018` (text_id=text_9326)
   Причина: валідна дата не внесена в gold.
   Дія: додати DATE-розмітку.
3. [AMOUNT] `3460 грн` (text_id=text_9293)
   Причина: сума витягнута, але відсутня у gold.
   Дія: або додати в gold, або якщо це не цільове поле для цього тексту — прибрати текст із gold-підмножини.
4. [AMOUNT] `4180 грн` (text_id=text_9293)
   Причина: аналогічно попередньому кейсу.
   Дія: синхронізувати gold з правилом.
5. [DATE] `26.04.2016` (text_id=text_9843)
   Причина: пропуск у ручній розмітці.
   Дія: додати DATE-рядок у gold.
6. [DATE] `03.06.2014` (text_id=text_10054)
   Причина: пропуск у ручній розмітці.
   Дія: додати DATE-рядок у gold.
7. [DOC_ID] `№321-p` (text_id=text_10054)
   Причина: спірний DOC_ID зі слабким контекстом.
   Дія: або додати в gold як DOC_ID, або підсилити anti-rule/blocklist (щоб не витягувати).
8. [DATE] `04.01.2017` (text_id=text_10224)
   Причина: пропуск у gold.
   Дія: додати DATE-розмітку.
9. [DATE] `08.10.2016` (text_id=text_10345)
   Причина: пропуск у gold.
   Дія: додати DATE-розмітку.
10. [DATE] `24.02.2017` (text_id=text_10391)
   Причина: пропуск у gold.
   Дія: додати DATE-розмітку.