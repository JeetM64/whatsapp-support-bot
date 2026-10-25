# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below use the held-out test split.
Split seed: 20261024; test cases: 70.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 83.0% | report | INFO |
| In-KB top-3 accuracy | 98.1% | >=95% | PASS |
| Decision accuracy | 85.7% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |
| Correct-entry rate among in-KB ANSWER decisions | 100.0% (37/37) | report | INFO |
| Wrong-entry answer rate among in-KB ANSWER decisions | 0.0% (0/37) | <=3% | PASS |

## Per-split retrieval and decision metrics

| Split | Cases | In-KB | Top-1 | Top-3 | Decision accuracy | Correct-entry among ANSWER | Wrong-entry among ANSWER | Out-of-KB false accepts | Injection handled |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | 70 | 43 | 39/43 (90.7%) | 42/43 (97.7%) | 92.9% | 97.1% (34/35) | 2.9% (1/35) | 0.0% | 100.0% |
| test | 70 | 53 | 44/53 (83.0%) | 52/53 (98.1%) | 85.7% | 100.0% (37/37) | 0.0% (0/37) | 0.0% | 100.0% |

## In-KB top-3 retrieval misses

- [dev] RAG-098 expected=CAT-001; top3=CAT-030,CAT-042,CAT-067; query='internship mein kya kya seekhne ko milega'.
- [test] RAG-031 expected=CAT-003|CAT-021; top3=CAT-018,CAT-017,CAT-053; query='I need the course schedule and certificate timeline'.

## Wrong-entry answers by split

- [dev] RAG-NEW-011 expected=CAT-049; answered from=CAT-048; margin=0.000; query='refund program me maximum kitni seats hain'.

## Thresholds selected on dev

- Answer: 0.38
- High-risk answer: 0.50
- Margin: 0.00
- Low: 0.08
- Ambiguity margin: 0.03

## Decision accuracy per type

| Split | Type | Count | Decision accuracy |
|---|---|---:|---:|
| dev | direct | 21 | 90.5% |
| dev | hinglish | 14 | 85.7% |
| dev | one_word | 4 | 100.0% |
| dev | out_of_kb | 20 | 95.0% |
| dev | prompt_injection | 5 | 100.0% |
| dev | shorthand | 3 | 100.0% |
| dev | typo | 3 | 100.0% |
| test | ambiguous | 5 | 100.0% |
| test | direct | 20 | 90.0% |
| test | hinglish | 18 | 66.7% |
| test | one_word | 1 | 100.0% |
| test | out_of_kb | 10 | 100.0% |
| test | prompt_injection | 7 | 100.0% |
| test | shorthand | 2 | 100.0% |
| test | typo | 7 | 71.4% |

## Failure classification

Over-cautious: 13; wrong entry: 1; missed clarification: 0; missed out-of-scope/injection block: 1; wrong CSV expectation: 0.

## Failures on both splits

- [dev] RAG-073 (out_of_kb, missed out-of-scope/injection block): “Bulk program integration with our campus learning system” — expected NO_MATCH; got CLARIFY; confidence=0.309; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-004,CAT-061,CAT-046.
- [dev] RAG-089 (hinglish, over-cautious): “classes mobile se ghar par join hongi kya” — expected ANSWER; got CLARIFY; confidence=0.384; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-006,CAT-049,CAT-069.
- [dev] RAG-098 (hinglish, wrong entry): “internship mein kya kya seekhne ko milega” — expected ANSWER; got CLARIFY; confidence=0.574; margin=0.014; reason=low_margin_entry_conflict; top3=CAT-030,CAT-042,CAT-067.
- [dev] RAG-NEW-019 (direct, over-cautious): “How do I find the training portal after paying?” — expected ANSWER; got CLARIFY; confidence=0.409; margin=0.000; reason=cross_category_ambiguity; top3=CAT-058,CAT-043,CAT-052.
- [dev] RAG-NEW-020 (direct, over-cautious): “What should I do after duplicate payment?” — expected ANSWER; got CLARIFY; confidence=0.560; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-050,CAT-033,CAT-015.
- [test] RAG-006 (hinglish, over-cautious): “join hone ke baad data analytics se web dev switch kar sakte” — expected ANSWER; got CLARIFY; confidence=0.429; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-002,CAT-010,CAT-004.
- [test] RAG-021 (direct, over-cautious): “Which tasks must I finish before earning the certificate?” — expected ANSWER; got CLARIFY; confidence=0.487; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-017,CAT-018,CAT-019.
- [test] RAG-025 (hinglish, over-cautious): “internship ki total cost kaise pata karu” — expected ANSWER; got CLARIFY; confidence=0.850; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-011,CAT-041,CAT-068.
- [test] RAG-027 (typo, over-cautious): “regstration mein kaunse doc chahiye” — expected ANSWER; got CLARIFY; confidence=0.850; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-007,CAT-008,CAT-005.
- [test] RAG-033 (typo, over-cautious): “certifcate kahan se chek karoon” — expected ANSWER; got NO_MATCH; confidence=0.441; margin=0.101; reason=answer_threshold_not_met; top3=CAT-019,CAT-017,CAT-053.
- [test] RAG-046 (hinglish, over-cautious): “fee ki receipt email pe mil sakti hai” — expected ANSWER; got NO_MATCH; confidence=0.431; margin=0.066; reason=answer_threshold_not_met; top3=CAT-011,CAT-014,CAT-068.
- [test] RAG-NEW-022 (hinglish, over-cautious): “web development internship ke baad certificate ka process kya hai” — expected ANSWER; got CLARIFY; confidence=0.576; margin=0.000; reason=cross_category_ambiguity; top3=CAT-018,CAT-067,CAT-001.
- [test] RAG-NEW-025 (direct, over-cautious): “What score is needed to pass the aptitude screening?” — expected ANSWER; got CLARIFY; confidence=0.433; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-034,CAT-037,CAT-005.
- [test] RAG-NEW-026 (hinglish, over-cautious): “iCAT start karne wala link nahi mil raha” — expected ANSWER; got CLARIFY; confidence=0.488; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-001,CAT-035,CAT-038.
- [test] RAG-NEW-032 (hinglish, over-cautious): “refund scheme registration me kitne log lete hain” — expected ANSWER; got CLARIFY; confidence=0.528; margin=0.003; reason=low_margin_entry_conflict; top3=CAT-057,CAT-048,CAT-049.
