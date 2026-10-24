# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below use the held-out test split.
Split seed: 20261024; test cases: 50.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 73.5% | report | INFO |
| In-KB top-3 accuracy | 97.1% | >=95% | PASS |
| Decision accuracy | 88.0% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |

## Thresholds selected on dev

- Answer: 0.34
- High-risk answer: 0.45
- Margin: 0.00
- Low: 0.08
- Ambiguity margin: 0.03

## Decision accuracy per type

| Split | Type | Count | Decision accuracy |
|---|---|---:|---:|
| dev | direct | 9 | 55.6% |
| dev | hinglish | 7 | 71.4% |
| dev | one_word | 4 | 100.0% |
| dev | out_of_kb | 20 | 100.0% |
| dev | prompt_injection | 4 | 100.0% |
| dev | shorthand | 3 | 66.7% |
| dev | typo | 3 | 100.0% |
| test | ambiguous | 5 | 100.0% |
| test | direct | 11 | 63.6% |
| test | hinglish | 8 | 87.5% |
| test | one_word | 1 | 100.0% |
| test | out_of_kb | 10 | 100.0% |
| test | prompt_injection | 6 | 100.0% |
| test | shorthand | 2 | 100.0% |
| test | typo | 7 | 85.7% |

## Failure classification

Over-cautious: 13; wrong entry: 0; missed clarification: 0; missed out-of-scope/injection block: 0; wrong CSV expectation: 0.

## Failures on both splits

- [dev] RAG-053 (hinglish, over-cautious): “hafte mein kitna time nikalna hoga” — expected ANSWER; got NO_MATCH; confidence=0.333; margin=0.000; reason=no_lexical_agreement; top3=CAT-001,CAT-003,CAT-007.
- [dev] RAG-054 (hinglish, over-cautious): “data analytics ka track choose kar sakte kya” — expected ANSWER; got NO_MATCH; confidence=0.336; margin=0.000; reason=answer_threshold_not_met; top3=CAT-002,CAT-011,CAT-004.
- [dev] RAG-057 (direct, over-cautious): “Do my degree year and department affect eligibility?” — expected ANSWER; got NO_MATCH; confidence=0.288; margin=0.085; reason=answer_threshold_not_met; top3=CAT-005,CAT-021,CAT-018.
- [dev] RAG-063 (shorthand, over-cautious): “fee txn failed debit no LMS” — expected ANSWER; got NO_MATCH; confidence=0.407; margin=0.069; reason=answer_threshold_not_met; top3=CAT-013,CAT-023,CAT-011.
- [dev] RAG-072 (direct, over-cautious): “What conditions apply if I cancel and ask for money back?” — expected ANSWER; got NO_MATCH; confidence=0.320; margin=0.000; reason=answer_threshold_not_met; top3=CAT-015,CAT-033,CAT-032.
- [dev] RAG-085 (direct, over-cautious): “Will checkout show every extra cost?” — expected ANSWER; got NO_MATCH; confidence=0.344; margin=0.146; reason=answer_threshold_not_met; top3=CAT-016,CAT-011,CAT-033.
- [dev] RAG-094 (direct, over-cautious): “Where can I download proof of payment?” — expected ANSWER; got NO_MATCH; confidence=0.396; margin=0.000; reason=answer_threshold_not_met; top3=CAT-012,CAT-014,CAT-028.
- [test] RAG-003 (direct, over-cautious): “The transfer shows failed but my balance dropped; what next?” — expected ANSWER; got NO_MATCH; confidence=0.394; margin=0.276; reason=answer_threshold_not_met; top3=CAT-013,CAT-015,CAT-023.
- [test] RAG-016 (direct, over-cautious): “How much should I budget to join?” — expected ANSWER; got NO_MATCH; confidence=0.296; margin=0.000; reason=answer_threshold_not_met; top3=CAT-011,CAT-033,CAT-003.
- [test] RAG-018 (typo, over-cautious): “passwrd bhool gaya reset ka tarika batao” — expected ANSWER; got NO_MATCH; confidence=0.379; margin=0.084; reason=answer_threshold_not_met; top3=CAT-013,CAT-022,CAT-001.
- [test] RAG-021 (direct, over-cautious): “Which tasks must I finish before earning the certificate?” — expected ANSWER; got NO_MATCH; confidence=0.417; margin=0.055; reason=answer_threshold_not_met; top3=CAT-017,CAT-021,CAT-018.
- [test] RAG-043 (direct, over-cautious): “Which specializations can I select from?” — expected ANSWER; got NO_MATCH; confidence=0.232; margin=0.000; reason=answer_threshold_not_met; top3=CAT-002,CAT-017,CAT-019.
- [test] RAG-046 (hinglish, over-cautious): “fee ki receipt email pe mil sakti hai” — expected ANSWER; got NO_MATCH; confidence=0.399; margin=0.105; reason=answer_threshold_not_met; top3=CAT-011,CAT-033,CAT-014.
