# Audit Summary Lab 6
- Classification task: dominant entity label per text_id (NO_ENTITY if none)
- Split: seed=42, ratios=0.8/0.1/0.1 (stratified by dominant_label)
- Baseline 1 (word 1-1): accuracy=0.6165, macro-F1=0.2200
- Baseline 2 (word 1-2): accuracy=0.6147, macro-F1=0.2162
- Best baseline: B1_word_1_1 (by val macro-F1)

## Error categories
- NO_ENTITY домінує, багато пропусків сутностей або слабкі сигнали в тексті.
- Перекриття типів: DATE vs MON/PERIOD, ORG vs MISC, LOC vs NO_ENTITY.
- Короткі або контекстно-неоднозначні фрагменти, де біграми не допомагають.

## Next fixes
- Перевірити дисбаланс (class_weight="balanced") і/або леми, додати прості правила для часу/дат/грошей.
