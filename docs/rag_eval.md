# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below include the test evaluation split; the test split is partially seen and should not be treated as a pristine holdout.
Split seed: 20261024; test cases: 70.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 81.1% | report | INFO |
| In-KB top-3 accuracy | 96.2% | >=95% | PASS |
| Decision accuracy | 85.7% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |
| Correct-entry rate among in-KB ANSWER decisions | 94.6% (35/37) | report | INFO |
| Wrong-entry answer rate among in-KB ANSWER decisions | 5.4% (2/37) | <=6% | PASS |

## Per-split retrieval and decision metrics

| Split | Cases | In-KB | Top-1 | Top-3 | Decision accuracy | Correct-entry among ANSWER | Wrong-entry among ANSWER | Out-of-KB false accepts | Injection handled |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | 96 | 69 | 62/69 (89.9%) | 66/69 (95.7%) | 86.5% | 98.1% (52/53) | 1.9% (1/53) | 0.0% | 100.0% |
| test | 70 | 53 | 43/53 (81.1%) | 51/53 (96.2%) | 85.7% | 94.6% (35/37) | 5.4% (2/37) | 0.0% | 100.0% |

High-risk wrong-entry answers: 0 (target 0).
In-KB test ANSWER replies containing a link, number, or next step: 37/37 (100.0%).

## In-KB test decision audit

Counts: ANSWER 37; CLARIFY 15; NO_MATCH 1; total 53.

| Case | Query | Expected | Actual |
|---|---|---|---|
| RAG-001 | When is the next cohort scheduled to begin? | ANSWER | ANSWER |
| RAG-002 | paid no portal access | ANSWER | ANSWER |
| RAG-003 | The transfer shows failed but my balance dropped; what next? | ANSWER | ANSWER |
| RAG-005 | Does program completion include a certificate? | ANSWER | ANSWER |
| RAG-006 | join hone ke baad data analytics se web dev switch kar sakte | ANSWER | CLARIFY |
| RAG-007 | refund | CLARIFY | CLARIFY |
| RAG-008 | what does the carrer support cover | ANSWER | ANSWER |
| RAG-009 | Can I move to another track once enrolled? | ANSWER | ANSWER |
| RAG-010 | refund ke liye request kaise dalu | ANSWER | CLARIFY |
| RAG-013 | my videos are frezing what can i try | ANSWER | ANSWER |
| RAG-014 | What academic details do I need to submit? | ANSWER | ANSWER |
| RAG-016 | How much should I budget to join? | ANSWER | ANSWER |
| RAG-018 | passwrd bhool gaya reset ka tarika batao | ANSWER | ANSWER |
| RAG-019 | What does the program cost and is a certificate part of it | CLARIFY | CLARIFY |
| RAG-020 | How many weeks should I reserve and how much time weekly? | ANSWER | ANSWER |
| RAG-021 | Which tasks must I finish before earning the certificate? | ANSWER | CLARIFY |
| RAG-025 | internship ki total cost kaise pata karu | ANSWER | CLARIFY |
| RAG-026 | coding bilkul nahi aati phir bhi start karu | ANSWER | ANSWER |
| RAG-027 | regstration mein kaunse doc chahiye | ANSWER | CLARIFY |
| RAG-030 | Tell me who can apply and how to check a certificate | CLARIFY | CLARIFY |
| RAG-031 | I need the course schedule and certificate timeline | CLARIFY | CLARIFY |
| RAG-032 | When does the batch start and what certificate do you provide | CLARIFY | CLARIFY |
| RAG-033 | certifcate kahan se chek karoon | ANSWER | NO_MATCH |
| RAG-034 | how long is the intership and weekly hours | ANSWER | ANSWER |
| RAG-036 | debit card se payment karna accepted h kya | ANSWER | ANSWER |
| RAG-037 | Where should I begin an application? | ANSWER | ANSWER |
| RAG-038 | Where can an employer check my certificate? | ANSWER | ANSWER |
| RAG-039 | registration ke waqt marksheet bhi deni hai | ANSWER | ANSWER |
| RAG-040 | Payment went through but my learning portal still fails | CLARIFY | CLARIFY |
| RAG-043 | Which specializations can I select from? | ANSWER | ANSWER |
| RAG-045 | where do i uplod my project work | ANSWER | ANSWER |
| RAG-046 | fee ki receipt email pe mil sakti hai | ANSWER | ANSWER |
| RAG-048 | admission form kis page par bharna hai | ANSWER | ANSWER |
| RAG-050 | certificate reqs and project submit | ANSWER | ANSWER |
| RAG-NEW-021 | iCAT ka full form aur test ka purpose batao | ANSWER | ANSWER |
| RAG-NEW-022 | web development internship ke baad certificate ka process kya hai | ANSWER | ANSWER |
| RAG-NEW-023 | fee 880 hai ya 8500 | ANSWER | ANSWER |
| RAG-NEW-024 | internship karne ke liye alag paise dene padte hain kya | ANSWER | ANSWER |
| RAG-NEW-025 | What score is needed to pass the aptitude screening? | ANSWER | CLARIFY |
| RAG-NEW-026 | iCAT start karne wala link nahi mil raha | ANSWER | CLARIFY |
| RAG-NEW-027 | My online test stopped working halfway through | ANSWER | ANSWER |
| RAG-NEW-028 | Which certificate comes after the mentor approves my project? | ANSWER | ANSWER |
| RAG-NEW-029 | AICTE approved hai kya | ANSWER | ANSWER |
| RAG-NEW-030 | I am in the Regular batch and want my cancellation money back | ANSWER | ANSWER |
| RAG-NEW-031 | refund program me attendance aur assignment ki kya shart hai | ANSWER | ANSWER |
| RAG-NEW-032 | refund scheme registration me kitne log lete hain | ANSWER | CLARIFY |
| RAG-NEW-033 | Two transactions went through for one enrollment | ANSWER | ANSWER |
| RAG-NEW-034 | How long until the portal reflects a successful transfer? | ANSWER | ANSWER |
| RAG-NEW-035 | login password bhool gaya reset page bhejo | ANSWER | ANSWER |
| RAG-NEW-036 | Is the company office in Pune or Ahmednagar? | ANSWER | ANSWER |
| RAG-NEW-037 | Where do I apply for paid internships after finishing training? | ANSWER | ANSWER |
| RAG-NEW-038 | extension lene ka tareeka aur charges kya hain | ANSWER | CLARIFY |
| RAG-NEW-039 | How can I enroll in another internship? | ANSWER | ANSWER |

Direct-question CLARIFY/NO_MATCH rate: 10/47 (21.3%).

Direct questions needing review (proposed fixes only; do not apply to test):
- 'join hone ke baad data analytics se web dev switch kar sakte': expected CAT-010; got CLARIFY; top3=CAT-002,CAT-010,CAT-004; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'refund ke liye request kaise dalu': expected CAT-015; got CLARIFY; top3=CAT-015,CAT-048,CAT-050; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'Which tasks must I finish before earning the certificate?': expected CAT-018; got CLARIFY; top3=CAT-018,CAT-017,CAT-019; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'internship ki total cost kaise pata karu': expected CAT-011; got CLARIFY; top3=CAT-011,CAT-041,CAT-068; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'regstration mein kaunse doc chahiye': expected CAT-008; got CLARIFY; top3=CAT-007,CAT-008,CAT-005; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'certifcate kahan se chek karoon': expected CAT-019; got NO_MATCH; top3=CAT-019,CAT-017,CAT-053; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'What score is needed to pass the aptitude screening?': expected CAT-037; got CLARIFY; top3=CAT-034,CAT-037,CAT-005; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'iCAT start karne wala link nahi mil raha': expected CAT-038; got CLARIFY; top3=CAT-001,CAT-035,CAT-038; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'refund scheme registration me kitne log lete hain': expected CAT-049; got CLARIFY; top3=CAT-057,CAT-048,CAT-049; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'extension lene ka tareeka aur charges kya hain': expected CAT-055; got CLARIFY; top3=CAT-055,CAT-016,CAT-001; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.

## In-KB top-3 retrieval misses

- [dev] RAG-098 expected=CAT-001; top3=CAT-030,CAT-042,CAT-067; query='internship mein kya kya seekhne ko milega'.
- [dev] RAG-NEW-047 expected=CAT-007; top3=CAT-001,CAT-059,CAT-018; query='How do I enroll in the internship program?'.
- [dev] RAG-NEW-048 expected=CAT-007; top3=CAT-059,CAT-043,CAT-041; query='internship ke liye enroll kaise karu'.
- [test] RAG-031 expected=CAT-003|CAT-021; top3=CAT-018,CAT-017,CAT-053; query='I need the course schedule and certificate timeline'.
- [test] RAG-NEW-022 expected=CAT-018; top3=CAT-017,CAT-067,CAT-001; query='web development internship ke baad certificate ka process kya hai'.

## Wrong-entry answers by split

- [dev] RAG-NEW-057 expected=CAT-062; answered from=CAT-063; margin=0.203; query='Do I get a reward for referring a friend?'.
- [test] RAG-046 expected=CAT-014; answered from=CAT-011; margin=0.066; query='fee ki receipt email pe mil sakti hai'.
- [test] RAG-NEW-022 expected=CAT-018; answered from=CAT-017; margin=0.207; query='web development internship ke baad certificate ka process kya hai'.

## Thresholds selected on dev

- Answer: 0.42
- High-risk answer: 0.50
- Margin: 0.02
- Low: 0.08
- Ambiguity margin: 0.06

## Decision accuracy per type

| Split | Type | Count | Decision accuracy |
|---|---|---:|---:|
| dev | direct | 30 | 83.3% |
| dev | hinglish | 22 | 72.7% |
| dev | in_kb | 2 | 100.0% |
| dev | one_word | 4 | 100.0% |
| dev | out_of_kb | 20 | 95.0% |
| dev | prompt_injection | 5 | 100.0% |
| dev | shorthand | 3 | 100.0% |
| dev | typo | 10 | 90.0% |
| test | ambiguous | 5 | 100.0% |
| test | direct | 20 | 90.0% |
| test | hinglish | 18 | 66.7% |
| test | one_word | 1 | 100.0% |
| test | out_of_kb | 10 | 100.0% |
| test | prompt_injection | 7 | 100.0% |
| test | shorthand | 2 | 100.0% |
| test | typo | 7 | 71.4% |

## Failure classification

Over-cautious: 19; wrong entry: 3; missed clarification: 0; missed out-of-scope/injection block: 1; wrong CSV expectation: 0.

## Failures on both splits

- [dev] RAG-058 (hinglish, over-cautious): “amount kat gaya aur account open nahi ho raha” — expected ANSWER; got CLARIFY; confidence=0.517; margin=0.036; reason=low_margin_entry_conflict; top3=CAT-013,CAT-058,CAT-052.
- [dev] RAG-073 (out_of_kb, missed out-of-scope/injection block): “Bulk program integration with our campus learning system” — expected NO_MATCH; got CLARIFY; confidence=0.309; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-004,CAT-061,CAT-046.
- [dev] RAG-089 (hinglish, over-cautious): “classes mobile se ghar par join hongi kya” — expected ANSWER; got CLARIFY; confidence=0.384; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-006,CAT-049,CAT-035.
- [dev] RAG-098 (hinglish, wrong entry): “internship mein kya kya seekhne ko milega” — expected ANSWER; got CLARIFY; confidence=0.574; margin=0.014; reason=low_margin_entry_conflict; top3=CAT-030,CAT-042,CAT-067.
- [dev] RAG-NEW-009 (direct, over-cautious): “Does the program promise a job placement?” — expected ANSWER; got CLARIFY; confidence=0.512; margin=0.056; reason=cross_category_ambiguity; top3=CAT-030,CAT-041,CAT-042.
- [dev] RAG-NEW-011 (hinglish, over-cautious): “refund program me maximum kitni seats hain” — expected ANSWER; got NO_MATCH; confidence=0.536; margin=0.000; reason=answer_threshold_not_met; top3=CAT-048,CAT-049,CAT-057.
- [dev] RAG-NEW-019 (direct, over-cautious): “How do I find the training portal after paying?” — expected ANSWER; got CLARIFY; confidence=0.409; margin=0.000; reason=cross_category_ambiguity; top3=CAT-058,CAT-043,CAT-052.
- [dev] RAG-NEW-020 (direct, over-cautious): “What should I do after duplicate payment?” — expected ANSWER; got CLARIFY; confidence=0.560; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-050,CAT-033,CAT-015.
- [dev] RAG-NEW-043 (direct, over-cautious): “What is iCAT used for?” — expected ANSWER; got CLARIFY; confidence=0.502; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-034,CAT-037,CAT-035.
- [dev] RAG-NEW-047 (direct, wrong entry): “How do I enroll in the internship program?” — expected ANSWER; got CLARIFY; confidence=0.584; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-001,CAT-059,CAT-018.
- [dev] RAG-NEW-048 (hinglish, wrong entry): “internship ke liye enroll kaise karu” — expected ANSWER; got CLARIFY; confidence=0.726; margin=0.029; reason=low_margin_entry_conflict; top3=CAT-059,CAT-043,CAT-041.
- [dev] RAG-NEW-058 (typo, over-cautious): “friend refer karne ka link kaha h” — expected ANSWER; got CLARIFY; confidence=0.687; margin=0.050; reason=low_margin_entry_conflict; top3=CAT-062,CAT-063,CAT-032.
- [dev] RAG-NEW-066 (hinglish, over-cautious): “payment ke baad dashboard update nahi hua” — expected ANSWER; got CLARIFY; confidence=0.656; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-023,CAT-051,CAT-013.
- [test] RAG-006 (hinglish, over-cautious): “join hone ke baad data analytics se web dev switch kar sakte” — expected ANSWER; got CLARIFY; confidence=0.429; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-002,CAT-010,CAT-004.
- [test] RAG-010 (hinglish, over-cautious): “refund ke liye request kaise dalu” — expected ANSWER; got CLARIFY; confidence=0.594; margin=0.030; reason=low_margin_entry_conflict; top3=CAT-015,CAT-048,CAT-050.
- [test] RAG-021 (direct, over-cautious): “Which tasks must I finish before earning the certificate?” — expected ANSWER; got CLARIFY; confidence=0.524; margin=0.006; reason=low_margin_entry_conflict; top3=CAT-018,CAT-017,CAT-019.
- [test] RAG-025 (hinglish, over-cautious): “internship ki total cost kaise pata karu” — expected ANSWER; got CLARIFY; confidence=0.850; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-011,CAT-041,CAT-068.
- [test] RAG-027 (typo, over-cautious): “regstration mein kaunse doc chahiye” — expected ANSWER; got CLARIFY; confidence=0.850; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-007,CAT-008,CAT-005.
- [test] RAG-033 (typo, over-cautious): “certifcate kahan se chek karoon” — expected ANSWER; got NO_MATCH; confidence=0.441; margin=0.101; reason=answer_threshold_not_met; top3=CAT-019,CAT-017,CAT-053.
- [test] RAG-NEW-025 (direct, over-cautious): “What score is needed to pass the aptitude screening?” — expected ANSWER; got CLARIFY; confidence=0.433; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-034,CAT-037,CAT-005.
- [test] RAG-NEW-026 (hinglish, over-cautious): “iCAT start karne wala link nahi mil raha” — expected ANSWER; got CLARIFY; confidence=0.488; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-001,CAT-035,CAT-038.
- [test] RAG-NEW-032 (hinglish, over-cautious): “refund scheme registration me kitne log lete hain” — expected ANSWER; got CLARIFY; confidence=0.528; margin=0.003; reason=low_margin_entry_conflict; top3=CAT-057,CAT-048,CAT-049.
- [test] RAG-NEW-038 (hinglish, over-cautious): “extension lene ka tareeka aur charges kya hain” — expected ANSWER; got CLARIFY; confidence=0.617; margin=0.035; reason=low_margin_entry_conflict; top3=CAT-055,CAT-016,CAT-001.

## Escalation evaluation by split

| Split | Must escalate | Correct escalations | Must-escalate recall | Must answer | False escalations | False-escalation rate |
|---|---:|---:|---:|---:|---:|---:|
| dev | 51 | 51 | 100.0% | 20 | 0 | 0.0% |
| test | 51 | 51 | 100.0% | 20 | 2 | 10.0% |

## Known limitations

- Sample sizes are modest: 96 dev cases (including 26 dev-only additions) and 70 test cases; 53 test cases are in-KB and 37 received ANSWER.
- The test split is partially seen from prior review and is not a pristine holdout.
- There are 2 wrong-entry test answers (2/37, 5.4%): RAG-046 (CAT-014 expected, CAT-011 answered) and RAG-NEW-022 (CAT-018 expected, CAT-017 answered). Both are low/medium-risk neighboring entries; high-risk wrong-entry answers: 0.
- Direct questions received CLARIFY/NO_MATCH in 10/47 cases (21.3%). The query-by-query audit and proposed wording/lexicon/margin fixes are listed above.
- Those A4 fixes remain deferred until the KB content update. No test queries or expectations were changed to force a pass; do not tune from the test cases.
- Current test gates: wrong-entry <=6% PASS (5.4%); high-risk wrong-entry 0 PASS; out-of-KB false-accept 0% PASS; injection 100% PASS; must-escalate recall 100% PASS; false escalation <=10% PASS (10.0%).
