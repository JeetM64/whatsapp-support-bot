# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below use the held-out test split.
Split seed: 20261024; test cases: 50.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 76.5% | report | INFO |
| In-KB top-3 accuracy | 97.1% | >=95% | PASS |
| Decision accuracy | 60.0% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |

## Thresholds selected on dev

- Answer: 0.42
- High-risk answer: 0.58
- Margin: 0.04
- Low: 0.12

## Per-type breakdown

| Type | Count | Top-3 accuracy | Decision accuracy |
|---|---:|---:|---:|
| ambiguous | 5 | 100.0% | 60.0% |
| direct | 11 | 100.0% | 36.4% |
| hinglish | 8 | 100.0% | 37.5% |
| one_word | 1 | 100.0% | 100.0% |
| out_of_kb | 10 | 0.0% | 100.0% |
| prompt_injection | 6 | 0.0% | 100.0% |
| shorthand | 2 | 100.0% | 50.0% |
| typo | 7 | 85.7% | 28.6% |

## Failures

- RAG-003 (direct): “The transfer shows failed but my balance dropped; what next?” — expected ANSWER / CAT-013; got NO_MATCH / CAT-013,CAT-015,CAT-023.
- RAG-008 (typo): “what does the carrer support cover” — expected ANSWER / CAT-030; got NO_MATCH / CAT-030,CAT-031,CAT-032.
- RAG-010 (hinglish): “refund ke liye request kaise dalu” — expected ANSWER / CAT-015; got CLARIFY / CAT-015,CAT-018,CAT-023.
- RAG-014 (direct): “What academic details do I need to submit?” — expected ANSWER / CAT-008; got CLARIFY / CAT-008,CAT-018,CAT-024.
- RAG-016 (direct): “How much should I budget to join?” — expected ANSWER / CAT-011; got CLARIFY / CAT-011,CAT-033,CAT-003.
- RAG-018 (typo): “passwrd bhool gaya reset ka tarika batao” — expected ANSWER / CAT-022; got CLARIFY / CAT-013,CAT-022,CAT-001.
- RAG-021 (direct): “Which tasks must I finish before earning the certificate?” — expected ANSWER / CAT-018; got NO_MATCH / CAT-017,CAT-021,CAT-018.
- RAG-025 (hinglish): “internship ki total cost kaise pata karu” — expected ANSWER / CAT-011; got CLARIFY / CAT-011,CAT-007,CAT-012.
- RAG-026 (hinglish): “coding bilkul nahi aati phir bhi start karu” — expected ANSWER / CAT-004; got CLARIFY / CAT-032,CAT-004,CAT-007.
- RAG-027 (typo): “regstration mein kaunse doc chahiye” — expected ANSWER / CAT-008; got CLARIFY / CAT-014,CAT-001,CAT-007.
- RAG-030 (ambiguous): “Tell me who can apply and how to check a certificate” — expected CLARIFY / CAT-005|CAT-019; got NO_MATCH / CAT-019,CAT-017,CAT-018.
- RAG-031 (ambiguous): “I need the course schedule and certificate timeline” — expected CLARIFY / CAT-003|CAT-021; got NO_MATCH / CAT-017,CAT-021,CAT-018.
- RAG-033 (typo): “certifcate kahan se chek karoon” — expected ANSWER / CAT-019; got CLARIFY / CAT-019,CAT-026,CAT-014.
- RAG-036 (hinglish): “debit card se payment karna accepted h kya” — expected ANSWER / CAT-012; got NO_MATCH / CAT-013,CAT-012,CAT-023.
- RAG-037 (direct): “Where should I begin an application?” — expected ANSWER / CAT-007; got CLARIFY / CAT-007,CAT-004,CAT-020.
- RAG-038 (direct): “Where can an employer check my certificate?” — expected ANSWER / CAT-019; got NO_MATCH / CAT-019,CAT-017,CAT-021.
- RAG-043 (direct): “Which specializations can I select from?” — expected ANSWER / CAT-002; got CLARIFY / CAT-002,CAT-017,CAT-019.
- RAG-045 (typo): “where do i uplod my project work” — expected ANSWER / CAT-024; got CLARIFY / CAT-024,CAT-018,CAT-008.
- RAG-046 (hinglish): “fee ki receipt email pe mil sakti hai” — expected ANSWER / CAT-014; got CLARIFY / CAT-011,CAT-033,CAT-014.
- RAG-050 (shorthand): “certificate reqs and project submit” — expected ANSWER / CAT-018; got CLARIFY / CAT-024,CAT-018,CAT-017.
