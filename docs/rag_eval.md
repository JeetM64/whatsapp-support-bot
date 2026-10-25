# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below use the held-out test split.
Split seed: 20261024; test cases: 70.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 69.8% | report | INFO |
| In-KB top-3 accuracy | 90.6% | >=95% | FAIL |
| Decision accuracy | 97.1% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |

## Thresholds selected on dev

- Answer: 0.38
- High-risk answer: 0.50
- Margin: 0.00
- Low: 0.08
- Ambiguity margin: 0.03

## Decision accuracy per type

| Split | Type | Count | Decision accuracy |
|---|---|---:|---:|
| dev | direct | 21 | 95.2% |
| dev | hinglish | 14 | 100.0% |
| dev | one_word | 4 | 100.0% |
| dev | out_of_kb | 20 | 100.0% |
| dev | prompt_injection | 5 | 100.0% |
| dev | shorthand | 3 | 100.0% |
| dev | typo | 3 | 100.0% |
| test | ambiguous | 5 | 100.0% |
| test | direct | 20 | 100.0% |
| test | hinglish | 18 | 94.4% |
| test | one_word | 1 | 100.0% |
| test | out_of_kb | 10 | 100.0% |
| test | prompt_injection | 7 | 100.0% |
| test | shorthand | 2 | 100.0% |
| test | typo | 7 | 85.7% |

## Failure classification

Over-cautious: 1; wrong entry: 2; missed clarification: 0; missed out-of-scope/injection block: 0; wrong CSV expectation: 0.

## Failures on both splits

- [dev] RAG-072 (direct, wrong entry): “What conditions apply if I cancel and ask for money back?” — expected ANSWER; got NO_MATCH; confidence=0.420; margin=0.162; reason=answer_threshold_not_met; top3=CAT-047,CAT-046,CAT-048.
- [test] RAG-008 (typo, wrong entry): “what does the carrer support cover” — expected ANSWER; got NO_MATCH; confidence=0.318; margin=0.000; reason=answer_threshold_not_met; top3=CAT-031,CAT-044,CAT-067.
- [test] RAG-046 (hinglish, over-cautious): “fee ki receipt email pe mil sakti hai” — expected ANSWER; got NO_MATCH; confidence=0.431; margin=0.066; reason=answer_threshold_not_met; top3=CAT-011,CAT-014,CAT-068.
