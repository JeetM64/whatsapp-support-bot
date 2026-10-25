# Conversation replay logs

> SAMPLE DATA. Customer values are masked before persistence.

## Smooth resolution — fees and domains

**Customer:** What are the listed program fees?
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** The August 2026 iCAT page lists Rs 880 for an iCAT-qualified student and Rs 8,500 for a regular student. I can connect a team member. fees can change, please confirm on the official site before paying.
**Debug:** decision=CONTINUE reason=high_risk_answer_threshold_met KB ids=['CAT-011', 'CAT-017'] priority=None

**Customer:** Which domains are listed?
**Bot:** List: Artificial Intelligence, AutoCAD, AWS, CPP and Data Structures, Data Analytics, Data Science, Java, Digital Marketing, Energy Conservation and Management, Ethical Hacking, Excel Automation, Machine Learning, RCC Structure Design, Software Testing, UI/UX Design, Website Design and Development, Human Resource, Finance, Video Editing, Graphic Design, Pharmaceutical, Psychology, International Business, and DevOps. The list can change. Please confirm this on the official site or with the team.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-002', 'CAT-008'] priority=None

## Follow-up — certificates after a domain

**Customer:** Which domains are listed?
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** List: Artificial Intelligence, AutoCAD, AWS, CPP and Data Structures, Data Analytics, Data Science, Java, Digital Marketing, Energy Conservation and Management, Ethical Hacking, Excel Automation, Machine Learning, RCC Structure Design, Software Testing, UI/UX Design, Website Design and Development, Human Resource, Finance, Video Editing, Graphic Design, Pharmaceutical, Psychology, International Business, and DevOps. The list can change. Please confirm this on the official site or with the team.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-002', 'CAT-008'] priority=None

**Customer:** certificate types?
**Bot:** SAMPLE DATA — This detail is not verified yet. I can connect you with the team. I can connect a team member.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-053', 'CAT-017'] priority=None

## Out-of-KB — college partnership and accepted human handoff

**Customer:** We want a partnership for our college.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I don't have confirmed information about this. I can connect you with a human; would you like me to?
**Debug:** decision=OFFER_HUMAN reason=out_of_scope KB ids=['CAT-061', 'CAT-005', 'CAT-059'] priority=None

**Customer:** Yes, please connect me with a human.
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-8E9F165F. We aim to reply by Tue 27 Oct, 01:20 PM IST; this is a target, not a promise.
**Debug:** decision=ESCALATE reason=human_offer_accepted KB ids=[] priority=P3
Ticket: IS-8E9F165F

## Payment done — dashboard access missing

**Customer:** I paid, money was debited, and I cannot access the dashboard.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I understand this is worrying. The dashboard can take up to 24 hours to update after payment. If it is still missing after that, After 24 hours, email the payment receipt or screenshot, registered email, and contact details to [EMAIL] or call [PHONE]; also check spam for the confirmation email. I can connect a team member.
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-0205D137. We aim to reply by Tue 27 Oct, 01:30 PM IST; this is a target, not a promise.
**Debug:** decision=KB_FIRST_AID_TICKET reason=payment_issue KB ids=['CAT-013', 'CAT-033'] priority=P2
Ticket: IS-0205D137

## Hinglish — certificate and payment access

**Customer:** Btech web dev internship ka certificate milega kya?
**Bot:** Yeh Internship Studio ke Founder Office assignment ke liye demo bot hai: jawaab public help-center information aur labeled SAMPLE DATA par based hain. Messages log hote hain (masked).
**Bot:** Certificate ke teen types hain: iCAT dene wale sabhi learners ko iCAT Participation; training phase ke baad Training; aur mentor review aur project approval ke baad Internship certificate milta hai.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-017', 'CAT-018'] priority=None

**Customer:** Payment cut gaya par access nahi aaya.
**Bot:** Paisa debit ho gaya hai, samajh sakta hoon. Payment ke baad dashboard update hone mein 24 ghante tak lag sakte hain. Uske baad bhi update na ho, toh payment receipt ya screenshot, registered email aur contact details [EMAIL] par bhejein ya [PHONE] par call karein; confirmation email ka spam folder bhi dekhein. Main aapko support team se connect kar sakta hoon.
**Bot:** Samajh raha hoon ki yeh pareshaani ki baat hai. Maine aapka message support team ko ticket IS-C8B6AC77 ke through bheja hai. Hum Tue 27 Oct, 01:40 PM IST tak jawab dene ki koshish karenge; yeh pakka vaada nahi hai.
**Debug:** decision=KB_FIRST_AID_TICKET reason=payment_issue KB ids=['CAT-013', 'CAT-033'] priority=P2
Ticket: IS-C8B6AC77

## Refund dispute — identify batch, then apply the program conditions

**Customer:** Refund milega?
**Bot:** Yeh Internship Studio ke Founder Office assignment ke liye demo bot hai: jawaab public help-center information aur labeled SAMPLE DATA par based hain. Messages log hote hain (masked).
**Bot:** Jawab dene se pehle batayein: aap Regular batch mein hain ya Refund program batch mein?
**Debug:** decision=CLARIFY reason=refund_batch_type KB ids=[] priority=None

**Customer:** Refund program batch.
**Bot:** Program poora karne ke baad refund program ki shartein: 90 din ya chuni hui duration mein 100% attendance, saare assignments time par, aur internship project aakhri hafte mein submit karna. Nayi jaankari mein 100% attendance hai; purane URL mein 75% hai, team se is shart ki pushti karein. Main aapko support team se connect kar sakta hoon.
**Debug:** decision=CONTINUE reason=high_risk_answer_threshold_met KB ids=['CAT-048', 'CAT-015'] priority=None

**Customer:** Main Refund program batch mein hoon. Attendance aur assignments poore kiye, aur last week internship project submit kiya. Kya yahi program conditions hain?
**Bot:** Program poora karne ke baad refund program ki shartein: 90 din ya chuni hui duration mein 100% attendance, saare assignments time par, aur internship project aakhri hafte mein submit karna. Nayi jaankari mein 100% attendance hai; purane URL mein 75% hai, team se is shart ki pushti karein. Main aapko support team se connect kar sakta hoon.
**Debug:** decision=CONTINUE reason=high_risk_answer_threshold_met KB ids=['CAT-048', 'CAT-067'] priority=None

## One-word message — unclear request

**Customer:** Refund
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** Which detail do you need: I need to cancel and ask about getting my money back. Which batch am I in or I need a refund. Which batch am I in or What are the Refund Guarantee Program conditions?
**Debug:** decision=CONTINUE reason=query_too_vague KB ids=['CAT-015', 'CAT-046', 'CAT-048'] priority=None

## Out-of-hours — human request

**Customer:** Please connect me to a human.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-4E64FB0C. We aim to reply by Wed 28 Oct, 11:00 AM IST; this is a target, not a promise.
**Debug:** decision=ESCALATE reason=human_request KB ids=[] priority=P3
Ticket: IS-4E64FB0C
