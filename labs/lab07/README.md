# Лабораторна робота 7: Linear SVM + char-ngrams + imbalance

## 1) Classification-підзадача
Класифікація `text_id` за домінантним типом сутності (`dominant_label` з `labels.csv`, `NO_ENTITY`, якщо сутності відсутні).

## 2) Baseline із ЛР6
Для чесного порівняння взято той самий split і baseline `processed_v2` + TF-IDF `word(1,2)` + Logistic Regression. На test він дав `accuracy=0.6147`, `macro-F1=0.2162`.

## 3) Перевірені SVM-варіанти
- `LinearSVC` + TF-IDF `word(1,2)`
- `LinearSVC` + TF-IDF `char_wb(3,5)`
- `LinearSVC` + TF-IDF `word(1,2)+char_wb(3,5)`
- Для найкращої SVM-сім'ї окремо перевірено `class_weight="balanced"`

## 4) Чи був imbalance
Так. Клас `NO_ENTITY` домінує, а хвіст дуже малий: у train `TIME=7`, `PCT=31`, `DOC=38`, `QUANT=45`. Через це `macro-F1` був важливішим за саму `accuracy`, а `class_weight="balanced"` виявився корисним для рідкісних класів.

## 5) Який поріг обрано і чому
Для multi-class задачі зроблено one-vs-rest аналіз для класу `PERIOD`. На validation обрано поріг `-0.6706`, бо він максимізував F1 для рідкісного класу в recall-first логіці: модель почала краще знаходити `PERIOD`, навіть ціною частини помилок у бік `NO_ENTITY`.

## 6) Яка модель виявилась найкращою
Найкращою фінальною конфігурацією стала `LinearSVC word(1,2)+char_wb(3,5) + class_weight=balanced` з custom threshold для `PERIOD`. На test вона дала `accuracy=0.7249`, `macro-F1=0.4454`.

## 7) Що робити далі
Наступні кроки: перевірити leakage між сплітами, окремо підсилити very-low-support класи (`TIME`, `DOC`, `PCT`), а також протестувати більш бізнес-орієнтовані threshold policy для інших важливих класів.
