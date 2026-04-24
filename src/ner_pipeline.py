import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

from src.ner_rules import collect_rule_entities, expand_org_boundaries

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_PATH = BASE_DIR / 'data' / 'sample' / 'lab10_ner_eval.jsonl'

LABEL_MAP = {
    'PERSON': 'PERS',
    'PER': 'PERS',
    'PERS': 'PERS',
    'ORG': 'ORG',
    'ORGANIZATION': 'ORG',
    'DATE': 'DATE',
    'TIME': 'DATE',
    'MONEY': 'MON',
    'MON': 'MON',
    'LOC': 'LOC',
    'GPE': 'LOC',
}


def normalize_label(label: str) -> str:
    return LABEL_MAP.get(label.upper(), label.upper())



def read_jsonl(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows



def write_jsonl(path: str | Path, rows: Iterable[dict[str, object]]) -> None:
    with Path(path).open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')



def build_eval_set(
    processed_path: str | Path,
    labels_path: str | Path,
    selected_ids: list[str],
    comments: dict[str, str],
    out_path: str | Path,
) -> list[dict[str, object]]:
    texts: dict[str, str] = {}
    with Path(processed_path).open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            texts[row['text_id']] = row['text_clean']

    labels_by_id = {text_id: [] for text_id in selected_ids}
    with Path(labels_path).open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            text_id = row['text_id']
            if text_id not in labels_by_id:
                continue
            labels_by_id[text_id].append(
                {
                    'text': row['span_text'],
                    'label': row['label'],
                    'start_char': int(row['start_char']),
                    'end_char': int(row['end_char']),
                }
            )

    rows: list[dict[str, object]] = []
    for text_id in selected_ids:
        rows.append(
            {
                'text_id': text_id,
                'text': texts[text_id],
                'expected_entities': sorted(
                    labels_by_id[text_id],
                    key=lambda x: (x['start_char'], x['end_char'], x['label']),
                ),
                'comment': comments.get(text_id, ''),
            }
        )
    write_jsonl(out_path, rows)
    return rows



def load_stanza_pipeline(lang: str = 'uk', use_gpu: bool = False):
    try:
        import stanza
    except ImportError as exc:
        raise RuntimeError(
            'Stanza не встановлено. Запустіть `pip install stanza` і `stanza.download("uk")`.'
        ) from exc
    return stanza.Pipeline(lang=lang, processors='tokenize,ner', use_gpu=use_gpu)



def _stanza_entities(doc) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    for entity in getattr(doc, 'entities', []):
        label = normalize_label(entity.type)
        entities.append(
            {
                'text': entity.text,
                'label': label,
                'start_char': int(entity.start_char),
                'end_char': int(entity.end_char),
                'source': 'baseline:stanza_uk',
            }
        )
    return entities



def _entity_key(entity: dict[str, object]) -> tuple[int, int, str, str]:
    return (
        int(entity['start_char']),
        int(entity['end_char']),
        str(entity['label']),
        str(entity['text']),
    )



def dedupe_entities(entities: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    seen: dict[tuple[int, int, str, str], dict[str, object]] = {}
    for entity in entities:
        item = dict(entity)
        key = _entity_key(item)
        if key not in seen:
            seen[key] = item
            continue
        previous_source = str(seen[key].get('source', ''))
        current_source = str(item.get('source', ''))
        merged_sources = sorted({s for s in (previous_source + '|' + current_source).split('|') if s})
        seen[key]['source'] = '|'.join(merged_sources)
    return sorted(seen.values(), key=lambda x: (int(x['start_char']), int(x['end_char']), str(x['label'])))



def _priority(entity: dict[str, object]) -> tuple[int, int]:
    source = str(entity.get('source', ''))
    length = int(entity['end_char']) - int(entity['start_char'])
    if 'boundary_expand_v1' in source:
        return (4, length)
    if 'org_legal_form_v1' in source:
        return (3, length)
    if source.startswith('rule:'):
        return (2, length)
    return (1, length)



def resolve_overlaps(entities: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for entity in sorted(entities, key=lambda x: (int(x['start_char']), -int(x['end_char']) + int(x['start_char']))):
        current = dict(entity)
        replaced = False
        for idx, previous in enumerate(kept):
            prev_start = int(previous['start_char'])
            prev_end = int(previous['end_char'])
            cur_start = int(current['start_char'])
            cur_end = int(current['end_char'])
            same_label = previous['label'] == current['label']
            overlaps = cur_start < prev_end and prev_start < cur_end
            if not overlaps or not same_label:
                continue
            if _priority(current) > _priority(previous):
                kept[idx] = current
            replaced = True
            break
        if not replaced:
            kept.append(current)
    return dedupe_entities(kept)



def run_baseline(records: list[dict[str, object]], pipeline) -> list[dict[str, object]]:
    outputs: list[dict[str, object]] = []
    for record in records:
        text = str(record['text'])
        doc = pipeline(text)
        predicted_entities = dedupe_entities(_stanza_entities(doc))
        outputs.append(
            {
                'text_id': record['text_id'],
                'text': text,
                'expected_entities': record['expected_entities'],
                'comment': record.get('comment', ''),
                'predicted_entities': predicted_entities,
            }
        )
    return outputs



def run_hybrid(records: list[dict[str, object]], pipeline) -> list[dict[str, object]]:
    outputs: list[dict[str, object]] = []
    for record in records:
        text = str(record['text'])
        doc = pipeline(text)
        baseline_entities = _stanza_entities(doc)
        expanded_baseline = expand_org_boundaries(text, baseline_entities)
        rule_entities = collect_rule_entities(text)
        predicted_entities = resolve_overlaps([*expanded_baseline, *rule_entities])
        outputs.append(
            {
                'text_id': record['text_id'],
                'text': text,
                'expected_entities': record['expected_entities'],
                'comment': record.get('comment', ''),
                'predicted_entities': predicted_entities,
            }
        )
    return outputs



def main() -> None:
    parser = argparse.ArgumentParser(description='Run baseline or hybrid NER on the lab10 evaluation set.')
    parser.add_argument('--eval-path', default=str(DEFAULT_EVAL_PATH))
    parser.add_argument('--out-path', required=True)
    parser.add_argument('--mode', choices=['baseline', 'hybrid'], default='baseline')
    args = parser.parse_args()

    records = read_jsonl(args.eval_path)
    pipeline = load_stanza_pipeline()
    outputs = run_baseline(records, pipeline) if args.mode == 'baseline' else run_hybrid(records, pipeline)
    write_jsonl(args.out_path, outputs)
    print(f'Saved {len(outputs)} records to {args.out_path}')


if __name__ == '__main__':
    main()
