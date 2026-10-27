# Generated report facts

Generated from current build and docs; content hash: `cb70569b0b7e86066e5431a9de9d3da9d50c9fa382cc9fa7cccaa8ca44a14b04`.

## Knowledge base (69 entries)

### Category counts

- certificates_offer_letter: 6
- enrolment: 6
- extension: 2
- fees_payments: 11
- icat_test: 7
- placement_hiring: 5
- program_info: 8
- projects_assignments: 3
- referral_campus: 4
- refunds: 6
- technical_access: 4
- trust_verification: 7

### Risk counts

- high: 15
- low: 22
- medium: 32

### Source status counts

- partly_verified: 63
- verified: 6

Handoff offers: 27

## Escalation and SLA

Rules: explicit human request, money loss/payment trouble, refund disputes, trust/approval, threats/abuse, sensitive data, repeated failures and high-risk unmatched questions are handled by configured guardrails. See `config/escalation_rules.yaml`.

Business hours and priority deadlines are loaded from runtime configuration. This report does not infer a deadline when configuration is absent.

## Evaluation

# Retrieval evaluation

Thresholds were selected using the dev split only. Metrics below use the held-out test split.
Split seed: 20261024; test cases: 70.

## Test metrics

| Metric | Result | Target | Status |
|---|---:|---:|---|
| In-KB top-1 accuracy | 81.1% | report | INFO |
| In-KB top-3 accuracy | 96.2% | >=95% | PASS |
| Decision accuracy | 94.3% | report | INFO |
| Out-of-KB false-accept rate (ANSWER decisions) | 0.0% | 0% | PASS |
| Prompt-injection handled | 100.0% | 100% | PASS |
| Correct-entry rate among in-KB ANSWER decisions | 90.7% (39/43) | report | INFO |
| Wrong-entry answer rate among in-KB ANSWER decisions | 9.3% (4/43) | <=6% | FAIL |

## Per-split retrieval and decision metrics

| Split | Cases | In-KB | Top-1 | Top-3 | Decision accuracy | Correct-entry among ANSWER | Wrong-entry among ANSWER | Out-of-KB false accepts | Injection handled |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | 96 | 69 | 60/69 (87.0%) | 66/69 (95.7%) | 92.7% | 89.8% (53/59) | 10.2% (6/59) | 0.0% | 100.0% |
| test | 70 | 53 | 43/53 (81.1%) | 51/53 (96.2%) | 94.3% | 90.7% (39/43) | 9.3% (4/43) | 0.0% | 100.0% |

High-risk wrong-entry answers: 0 (target 0).
In-KB test ANSWER replies containing a link, number, or next step: 43/43 (100.0%).

## In-KB test decision audit

Counts: ANSWER 43; CLARIFY 9; NO_MATCH 1; total 53.

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
| RAG-010 | refund ke liye request kaise dalu | ANSWER | ANSWER |
| RAG-013 | my videos are frezing what can i try | ANSWER | ANSWER |
| RAG-014 | What academic details do I need to submit? | ANSWER | ANSWER |
| RAG-016 | How much should I budget to join? | ANSWER | ANSWER |
| RAG-018 | passwrd bhool gaya reset ka tarika batao | ANSWER | ANSWER |
| RAG-019 | What does the program cost and is a certificate part of it | CLARIFY | CLARIFY |
| RAG-020 | How many weeks should I reserve and how much time weekly? | ANSWER | ANSWER |
| RAG-021 | Which tasks must I finish before earning the certificate? | ANSWER | ANSWER |
| RAG-025 | internship ki total cost kaise pata karu | ANSWER | ANSWER |
| RAG-026 | coding bilkul nahi aati phir bhi start karu | ANSWER | ANSWER |
| RAG-027 | regstration mein kaunse doc chahiye | ANSWER | ANSWER |
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
| RAG-NEW-025 | What score is needed to pass the aptitude screening? | ANSWER | ANSWER |
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
| RAG-NEW-038 | extension lene ka tareeka aur charges kya hain | ANSWER | ANSWER |
| RAG-NEW-039 | How can I enroll in another internship? | ANSWER | ANSWER |

Direct-question CLARIFY/NO_MATCH rate: 4/47 (8.5%).

Direct questions needing review (proposed fixes only; do not apply to test):
- 'join hone ke baad data analytics se web dev switch kar sakte': expected CAT-010; got CLARIFY; top3=CAT-002,CAT-010,CAT-004; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'certifcate kahan se chek karoon': expected CAT-019; got NO_MATCH; top3=CAT-019,CAT-017,CAT-053; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'iCAT start karne wala link nahi mil raha': expected CAT-038; got CLARIFY; top3=CAT-001,CAT-035,CAT-038; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.
- 'refund scheme registration me kitne log lete hain': expected CAT-049; got CLARIFY; top3=CAT-057,CAT-048,CAT-049; Expected entry is already in top 3: distinguish its question/variants from the neighboring candidate, then assess the ambiguity margin on DEV only.

## In-KB top-3 retrieval misses

- [dev] RAG-098 expected=CAT-001; top3=CAT-030,CAT-042,CAT-067; query='internship mein kya kya seekhne ko milega'.
- [dev] RAG-NEW-047 expected=CAT-007; top3=CAT-001,CAT-059,CAT-018; query='How do I enroll in the internship program?'.
- [dev] RAG-NEW-048 expected=CAT-007; top3=CAT-059,CAT-043,CAT-041; query='internship ke liye enroll kaise karu'.
- [test] RAG-031 expected=CAT-003|CAT-021; top3=CAT-018,CAT-017,CAT-053; query='I need the course schedule and certificate timeline'.
- [test] RAG-NEW-022 expected=CAT-018; top3=CAT-017,CAT-067,CAT-001; query='web development internship ke baad certificate ka process kya hai'.

## Wrong-entry answers by split

- [dev] RAG-098 expected=CAT-001; answered from=CAT-030; margin=0.014; query='internship mein kya kya seekhne ko milega'.
- [dev] RAG-NEW-007 expected=CAT-039; answered from=CAT-034; margin=0.000; query="I missed the aptitude test this time; what's next?".
- [dev] RAG-NEW-011 expected=CAT-049; answered from=CAT-048; margin=0.000; query='refund program me maximum kitni seats hain'.
- [dev] RAG-NEW-043 expected=CAT-034; answered from=CAT-037; margin=0.112; query='What is iCAT used for?'.
- [dev] RAG-NEW-057 expected=CAT-062; answered from=CAT-063; margin=0.203; query='Do I get a reward for referring a friend?'.
- [dev] RAG-NEW-058 expected=CAT-063; answered from=CAT-062; margin=0.050; query='friend refer karne ka link kaha h'.
- [test] RAG-027 expected=CAT-008; answered from=CAT-007; margin=0.000; query='regstration mein kaunse doc chahiye'.
- [test] RAG-046 expected=CAT-014; answered from=CAT-011; margin=0.066; query='fee ki receipt email pe mil sakti hai'.
- [test] RAG-NEW-022 expected=CAT-018; answered from=CAT-017; margin=0.207; query='web development internship ke baad certificate ka process kya hai'.
- [test] RAG-NEW-025 expected=CAT-037; answered from=CAT-034; margin=0.088; query='What score is needed to pass the aptitude screening?'.

## Thresholds selected on dev

- Answer: 0.42
- High-risk answer: 0.50
- Margin: 0.00
- Low: 0.08
- Ambiguity margin: 0.03

## Decision accuracy per type

| Split | Type | Count | Decision accuracy |
|---|---|---:|---:|
| dev | direct | 30 | 90.0% |
| dev | hinglish | 22 | 86.4% |
| dev | in_kb | 2 | 100.0% |
| dev | one_word | 4 | 100.0% |
| dev | out_of_kb | 20 | 95.0% |
| dev | prompt_injection | 5 | 100.0% |
| dev | shorthand | 3 | 100.0% |
| dev | typo | 10 | 100.0% |
| test | ambiguous | 5 | 100.0% |
| test | direct | 20 | 100.0% |
| test | hinglish | 18 | 83.3% |
| test | one_word | 1 | 100.0% |
| test | out_of_kb | 10 | 100.0% |
| test | prompt_injection | 7 | 100.0% |
| test | shorthand | 2 | 100.0% |
| test | typo | 7 | 85.7% |

## Failure classification

Over-cautious: 8; wrong entry: 2; missed clarification: 0; missed out-of-scope/injection block: 1; wrong CSV expectation: 0.

## Failures on both splits

- [dev] RAG-073 (out_of_kb, missed out-of-scope/injection block): “Bulk program integration with our campus learning system” — expected NO_MATCH; got CLARIFY; confidence=0.309; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-004,CAT-061,CAT-046.
- [dev] RAG-089 (hinglish, over-cautious): “classes mobile se ghar par join hongi kya” — expected ANSWER; got CLARIFY; confidence=0.384; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-006,CAT-049,CAT-035.
- [dev] RAG-NEW-019 (direct, over-cautious): “How do I find the training portal after paying?” — expected ANSWER; got CLARIFY; confidence=0.409; margin=0.000; reason=cross_category_ambiguity; top3=CAT-058,CAT-043,CAT-052.
- [dev] RAG-NEW-020 (direct, over-cautious): “What should I do after duplicate payment?” — expected ANSWER; got CLARIFY; confidence=0.560; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-050,CAT-033,CAT-015.
- [dev] RAG-NEW-047 (direct, wrong entry): “How do I enroll in the internship program?” — expected ANSWER; got CLARIFY; confidence=0.584; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-001,CAT-059,CAT-018.
- [dev] RAG-NEW-048 (hinglish, wrong entry): “internship ke liye enroll kaise karu” — expected ANSWER; got CLARIFY; confidence=0.726; margin=0.029; reason=low_margin_entry_conflict; top3=CAT-059,CAT-043,CAT-041.
- [dev] RAG-NEW-066 (hinglish, over-cautious): “payment ke baad dashboard update nahi hua” — expected ANSWER; got CLARIFY; confidence=0.656; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-023,CAT-051,CAT-013.
- [test] RAG-006 (hinglish, over-cautious): “join hone ke baad data analytics se web dev switch kar sakte” — expected ANSWER; got CLARIFY; confidence=0.429; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-002,CAT-010,CAT-004.
- [test] RAG-033 (typo, over-cautious): “certifcate kahan se chek karoon” — expected ANSWER; got NO_MATCH; confidence=0.441; margin=0.101; reason=answer_threshold_not_met; top3=CAT-019,CAT-017,CAT-053.
- [test] RAG-NEW-026 (hinglish, over-cautious): “iCAT start karne wala link nahi mil raha” — expected ANSWER; got CLARIFY; confidence=0.488; margin=0.000; reason=low_margin_entry_conflict; top3=CAT-001,CAT-035,CAT-038.
- [test] RAG-NEW-032 (hinglish, over-cautious): “refund scheme registration me kitne log lete hain” — expected ANSWER; got CLARIFY; confidence=0.528; margin=0.003; reason=low_margin_entry_conflict; top3=CAT-057,CAT-048,CAT-049.


Not run.

## Runtime measurements

- Tests: latest recorded full suite: 191 passed; rerun `python -m pytest -q` to refresh.
- Latency, cold start and RAM: not measured in this run.
- Cost per 1,000 messages: $0 in no-LLM mode; no provider token logs are generated.

## Unconfirmed details

- CAT-001: What does the Internship Studio program include? — Training is paired with an internship opportunity for iCAT qualifiers. I don't have the exact training modules confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-002: Which domains are listed? — Some listed iStudio domains are Artificial Intelligence, Data Science, Java, Digital Marketing, UI/UX Design, and DevOps. I don't have current batch availability confirmed; please check with the iStudio support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-003: How long is the program and how much time should I plan each week? — Training is paired with an internship opportunity for iCAT qualifiers. I don't have the program duration or weekly time commitment confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-004: Do I need prior knowledge? — I don't have the prior-knowledge requirement for iStudio training confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-005: Who is eligible to join? — Engineering, commerce/management, pharmaceutical, and psychology learners, plus campus ambassadors. I don't have the complete iStudio eligibility rules confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-006: Is training online and how does it work? — Training is paired with an internship opportunity for iCAT qualifiers. I don't have the exact training format or schedule confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-007: How do I enroll? — Enrollment at iStudio starts with iCAT. Qualifiers get training and an internship; the listed fee is Rs 880 for an iCAT-qualified student. Please confirm other details with the team; Fees can change, so please confirm on the official site before paying Registration steps and dates are unconfirmed; see https://internshipstudio.tawk.help/category/internship-related; support: contact@internshipstudio.com, 7507869003, 11 AM-7 PM IST.
- CAT-008: What details or documents do I need to enroll? — iCAT (Internship Common Aptitude Test). I don't have the required documents or enrollment details confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-009: When does the next batch start? — iCAT (Internship Common Aptitude Test). I don't have the next iStudio batch start date confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-010: Can I change my domain after joining? — Training is paired with an internship opportunity for iCAT qualifiers. I don't have the domain-change rules for an enrolled batch confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-012: Which payment methods are accepted? — Internship is free; the fee covers training. I don't have iStudio's accepted payment methods confirmed. Fees can change, so please confirm on the official site before paying. See the iStudio help center: https://internshipstudio.tawk.help/category/payment-related.
- CAT-014: How do I get a payment receipt? — email the payment receipt or screenshot, registered email, and contact details to contact@internshipstudio.com or call 7507869003; also check spam for the confirmation email. I don't have a separate dashboard receipt-download step confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/payment-related.
- CAT-016: Are there installments or any additional charges? — Internship is free; the fee covers training. Fees can change, so please confirm on the official site before paying. I don't have installment terms or other charges confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/payment-related.
- CAT-017: What certificate types are included in the program, and what are their names? — Yes. iStudio describes three certificate types: iCAT Participation for everyone who takes iCAT; Training after the training phase; and Internship after mentors review and approve the project. I don't have the exact issue date confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/certificates.
- CAT-018: What must I complete for the Internship certificate: project submission and mentor review? — The Internship certificate is issued after mentor review and project approval. I don't have the required project format or completion deadline confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/certificates.
- CAT-019: Are Internship Studio certificates approved by AICTE, UGC, or NSDC, or described as ISO-verified? — I don't have confirmed information about AICTE, UGC, or NSDC approval. iStudio describes its certificates as ISO-verified. These are different facts. Would you like me to connect you with the support team?
- CAT-020: When can I download an offer letter, and can its duration be changed? — The iStudio help center has an offer-letter section. I don't have the download date or duration-change rules confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/offer-letter.
- CAT-021: My certificate is delayed or has the wrong name. What should I do? — I don't have the certificate correction or delay process confirmed. Support hours: 11:00-19:00 IST (operating days not stated). Contact contact@internshipstudio.com or 7507869003; would you like me to connect you with the support team?
- CAT-022: How do I reset my password? — For the iStudio training portal, reset your password here: (https://cit2.internshipstudio.com/login/forgot_password.php). I don't have another account-recovery step confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-024: How do I submit my internship project? — iCAT Participation for everyone who takes iCAT; Training after the training phase; and Internship after mentors review and approve the project. I don't have the internship project submission steps confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/project.
- CAT-025: Videos or training content are not loading. What can I try? — I understand this can interrupt your training. I don't have a confirmed fix for videos that won't load. Support hours: 11:00-19:00 IST (operating days not stated). Contact contact@internshipstudio.com or 7507869003. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related. Please confirm this on the official site or with the team.
- CAT-027: What are the official website and contact channels? — https://internshipstudio.com. Contact contact@internshipstudio.com or 7507869003. Support hours: 11:00-19:00 IST (operating days not stated). I don't have another official channel confirmed; check with the iStudio support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-029: Are you iStudio Technologies or the same as another company? — iStudio (Internship Studio). I don't have confirmed information about a legal relationship with another company. Would you like me to connect you with the support team?
- CAT-030: What does iStudio Plus career support cover: career guidance, job search, and placement assistance? — Placement assistance only; no outcome guaranteed. I don't have the exact career-support steps or individual outcomes confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/placement-assistance.
- CAT-032: I contacted support but haven't heard back. What should I do? — I understand waiting for a reply is frustrating. I don't have your case status confirmed. Support hours: 11:00-19:00 IST (operating days not stated). Contact the iStudio support team at contact@internshipstudio.com or 7507869003; would you like me to raise a ticket?
- CAT-034: What is iCAT? — The iCAT is the Internship Common Aptitude Test that iStudio uses before its training and internship program. Learners who qualify get training and an internship opportunity, and everyone who takes it receives an iCAT Participation certificate. I don't have the latest syllabus, passing marks, or test dates confirmed; check the iCAT section of our help center: https://internshipstudio.tawk.help/category/internship-common-aptitude-test.
- CAT-035: Do I need to attempt iCAT to be eligible? — iCAT qualifiers are eligible for the training and internship opportunity; not attempting iCAT means not eligible. I don't have the current qualifying marks confirmed. See the iCAT help center: https://internshipstudio.tawk.help/category/internship-common-aptitude-test.
- CAT-036: How do I get my iCAT ID, password, or exam link? — I don't have the steps to get an iCAT ID, password, or exam link confirmed; please check with the support team. See the iCAT help center: https://internshipstudio.tawk.help/category/internship-common-aptitude-test.
- CAT-037: What are the iCAT qualifying marks and syllabus? — The iCAT is the Internship Common Aptitude Test used before the training and internship program. I don't have the latest syllabus or passing marks confirmed; check the iCAT help-center section: https://internshipstudio.tawk.help/category/curriculum.
- CAT-038: When can I start the iCAT and where is the exam link? — I don't have the current iCAT test window or exam link confirmed. Would you like me to connect you with the support team?
- CAT-039: I missed the iCAT or did not qualify. What happens next? — iCAT qualifiers are eligible for the training and internship opportunity; not attempting iCAT means not eligible. I don't have a retest or next-step process confirmed if you didn't qualify. Would you like me to connect you with the support team?
- CAT-040: I had a technical issue during the iCAT. What should I do? — I understand an iCAT technical issue is stressful. I don't have a confirmed troubleshooting step; would you like me to connect you with the support team?
- CAT-042: Is there a stipend during training or the internship? — No stipend during training and the internship. After completing training and internship, learners get access to the hiring portal to apply for stipend-based internships and jobs. I don't have the terms of a specific role confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/placement-assistance.
- CAT-043: How do I access the hiring portal and apply for jobs? — After completing training and internship, learners get access to the hiring portal to apply for stipend-based internships and jobs. I don't have the current hiring-portal login or application steps confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/placement-assistance.
- CAT-044: What are the placement terms for iStudio Plus? — Placement assistance only; no outcome guaranteed. The placement wording for iStudio Plus Digital Marketing and Robotics differs; a human can confirm the applicable terms. I don't have the terms for your specific iStudio Plus batch confirmed; would you like me to connect you with the support team?
- CAT-045: Do published stipend success stories guarantee my result? — Placement assistance only; no outcome guaranteed. Published success stories don't confirm an individual result. I don't have your specific outcome confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/placement-assistance. Please confirm this on the official site or with the team.
- CAT-049: How many students can join the Refund Guarantee Program? — Refund Guarantee Program: Enrollment is capped at 100 students per test registration, first come while the registration window is open. Expansion is expected but not promised. I don't have current seat availability confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/refund-program. Please confirm this on the official site or with the team.
- CAT-052: When will training-portal access arrive? — I don't have the training-portal access time confirmed. Contact the iStudio support team at contact@internshipstudio.com or 7507869003 during 11:00-19:00 IST (operating days not stated).
- CAT-053: When can I download my certificate? — iCAT Participation for everyone who takes iCAT; Training after the training phase; and Internship after mentors review and approve the project. I don't have the download date or certificate-page steps confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/certificates.
- CAT-054: How long can an internship extension be? — up to 6 months. I don't have the request process or any charges confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/extension.
- CAT-056: How do I choose or change my batch? — Refund rules depend on your batch. I don't have the batch-change process confirmed. Are you in the Regular batch or Refund Guarantee Program batch? See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-057: Can I move from a Regular batch to the Refund program batch? — I don't have confirmed rules for moving between a Regular batch and Refund Guarantee Program. Would you like me to connect you with the support team?
- CAT-058: Where can I find my assignments? — I don't have the training-portal location for iStudio assignments confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/project.
- CAT-059: How do I enroll in a second internship and pay for it? — iCAT (Internship Common Aptitude Test). I don't have the steps or fee for enrolling in a second internship confirmed. Fees can change, so please confirm on the official site before paying. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-060: Can I pay the program fee in installments? — Internship is free; the fee covers training. I don't have an installment option or schedule confirmed. Fees can change, so please confirm on the official site before paying. Would you like me to connect you with the support team?
- CAT-061: How do I join the campus ambassador referral program? — The iStudio help center has a Referral section for the campus ambassador program. I don't have the current application steps confirmed; check the section here: https://internshipstudio.tawk.help/category/referral.
- CAT-062: What referral benefit or reward is available? — The iStudio help center has a Referral section. I don't have the referral reward rules confirmed; check the section here: https://internshipstudio.tawk.help/category/referral, or email contact@internshipstudio.com. Please confirm this on the official site or with the team.
- CAT-063: How do I refer a friend? — The iStudio help center has a Referral section for friend referrals. I don't have the current steps or referral link confirmed; check it here: https://internshipstudio.tawk.help/category/referral, or email contact@internshipstudio.com. Please confirm this on the official site or with the team.
- CAT-064: My referral was not recorded. What should I do? — I understand a missing referral credit is frustrating. I don't have your referral record confirmed. Support hours: 11:00-19:00 IST (operating days not stated). Contact the iStudio support team at contact@internshipstudio.com or 7507869003; would you like me to raise a ticket?
- CAT-065: How is attendance recorded, and what if I miss a day? — For Refund Guarantee Program, After completing the program, refund-program eligibility requires 100% attendance across the 90-day or selected duration, all assignments submitted on time, and the internship project submitted in the last week. I don't have the attendance rule for other batches or the missed-day process confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/curriculum. Please confirm this on the official site or with the team.
- CAT-066: Where is Internship Studio's office? — I don't have iStudio's current office address confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
- CAT-067: What benefits are included in the program? — Training is paired with an internship opportunity for iCAT qualifiers. After completing training and internship, learners get access to the hiring portal to apply for stipend-based internships and jobs. Placement assistance only; no outcome guaranteed. I don't have batch-specific benefits confirmed. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related. Please confirm this on the official site or with the team.
- CAT-068: What does the Refund Guarantee Program enrollment fee cover? — Refund Guarantee Program: The enrollment fee covers structured training, support, placement assistance, and commitment. I don't have your current batch fee confirmed. Please confirm other details with the team; Fees can change, so please confirm on the official site before paying. Would you like me to connect you with the support team?
- CAT-069: Who does Internship Studio serve? — Engineering, commerce/management, pharmaceutical, and psychology learners, plus campus ambassadors. I don't have every current eligibility condition confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.

## Assumptions and limitations

- KB content is assignment sample data and requires team confirmation.
- Test split has limited sample size and is partially seen; evaluation results are not a production guarantee.
- No live WhatsApp delivery, external hosting or real browser/mobile visual check is claimed.
