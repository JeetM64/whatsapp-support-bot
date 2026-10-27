# Conversation replay logs

> SAMPLE DATA. Customer values are masked before persistence.

## Smooth resolution — fees and domains

**Customer:** What are the listed program fees?
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** Rs 880 for an iCAT-qualified student; Rs 8,500 for a regular student. Fees can change, so please confirm on the official site before paying.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-011'] priority=None

**Customer:** Which domains are listed?
**Bot:** Some listed iStudio domains are Artificial Intelligence, Data Science, Java, Digital Marketing, UI/UX Design, and DevOps. I don't have current batch availability confirmed; please check with the iStudio support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-002'] priority=None

## Follow-up — certificates after a domain

**Customer:** Which domains are listed?
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** Some listed iStudio domains are Artificial Intelligence, Data Science, Java, Digital Marketing, UI/UX Design, and DevOps. I don't have current batch availability confirmed; please check with the iStudio support team. See the iStudio help center: https://internshipstudio.tawk.help/category/internship-related.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-002'] priority=None

**Customer:** certificate types?
**Bot:** Yes. iStudio describes three certificate types: iCAT Participation for everyone who takes iCAT; Training after the training phase; and Internship after mentors review and approve the project. I don't have the exact issue date confirmed; please check with the support team. See the iStudio help center: https://internshipstudio.tawk.help/category/certificates.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-017'] priority=None

## Out-of-KB — college partnership and accepted human handoff

**Customer:** We want a partnership for our college.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I don't have details on college partnerships. I can help with iCAT, fees, certificates, refunds, and the training or internship dashboard. Help center: https://internshipstudio.tawk.help/. Would you like me to connect you with a human?
**Debug:** decision=OFFER_HUMAN reason=out_of_scope KB ids=['CAT-061', 'CAT-018', 'CAT-005'] priority=None

**Customer:** Yes, please connect me with a human.
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-F591EE46. We aim to reply by Tue 27 Oct, 01:20 PM IST.
**Debug:** decision=ESCALATE reason=human_offer_accepted KB ids=[] priority=P3
Ticket: IS-F591EE46

## Payment done — dashboard access missing

**Customer:** I paid, money was debited, and I cannot access the dashboard.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I understand the debit is worrying. The dashboard can take up to 24 hours to update after payment. If access is still missing, email the payment receipt or screenshot, registered email, and contact details to contact@internshipstudio.com or call 7507869003; also check spam for the confirmation email. See the iStudio help center: https://internshipstudio.tawk.help/category/payment-related
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-8EADB22E. We aim to reply by Tue 27 Oct, 01:30 PM IST.
**Debug:** decision=KB_FIRST_AID_TICKET reason=payment_issue KB ids=['CAT-013'] priority=P2
Ticket: IS-8EADB22E

## Hinglish — certificate and payment access

**Customer:** Btech web dev internship ka certificate milega kya?
**Bot:** Yeh Internship Studio ke Founder Office assignment ke liye demo bot hai: jawaab public help-center information aur labeled SAMPLE DATA par based hain. Messages log hote hain (masked).
**Bot:** Haan. iStudio teen certificate types batata hai: iCAT dene wale sabhi learners ko iCAT Participation; training phase ke baad Training; aur mentor review aur project approval ke baad Internship certificate milta hai. Issue date confirm nahi hai. iStudio help center dekhein: https://internshipstudio.tawk.help/category/certificates.
**Debug:** decision=CONTINUE reason=answer_threshold_met KB ids=['CAT-017'] priority=None

**Customer:** Payment cut gaya par access nahi aaya.
**Bot:** Paisa debit ho gaya hai, samajh sakta hoon. Payment ke baad dashboard update hone mein 24 ghante tak lag sakte hain. Access na aaye toh payment receipt ya screenshot, registered email aur contact details contact@internshipstudio.com par bhejein ya 7507869003 par call karein; confirmation email ka spam folder bhi dekhein. iStudio help center dekhein: https://internshipstudio.tawk.help/category/payment-related
**Bot:** Samajh raha hoon ki yeh pareshaani ki baat hai. Maine aapka message support team ko ticket IS-5496D4BA ke through bheja hai. Hum Tue 27 Oct, 01:40 PM IST tak jawab dene ki koshish karenge.
**Debug:** decision=KB_FIRST_AID_TICKET reason=payment_issue KB ids=['CAT-013'] priority=P2
Ticket: IS-5496D4BA

## Refund dispute — identify batch, then apply the program conditions

**Customer:** Refund milega?
**Bot:** Yeh Internship Studio ke Founder Office assignment ke liye demo bot hai: jawaab public help-center information aur labeled SAMPLE DATA par based hain. Messages log hote hain (masked).
**Bot:** Jawab dene se pehle batayein: aap Regular batch mein hain ya Refund program batch mein?
**Debug:** decision=CLARIFY reason=refund_batch_type KB ids=[] priority=None

**Customer:** Refund program batch.
**Bot:** Program poora karne ke baad refund program ki shartein: 90 din ya chuni hui duration mein 100% attendance, saare assignments time par, aur internship project aakhri hafte mein submit karna. Aapki eligibility ya batch record yahan confirm nahi kar sakta. Kya main aapko support team se connect kar doon?
**Debug:** decision=CONTINUE reason=high_risk_answer_threshold_met KB ids=['CAT-048'] priority=None

**Customer:** Main Refund program batch mein hoon. Attendance aur assignments poore kiye, aur last week internship project submit kiya. Kya yahi program conditions hain?
**Bot:** Update dene ke liye shukriya. Team aapke batch conditions ke mutabik eligibility check kar sakti hai. Kya main ticket raise kar doon?
**Debug:** decision=CONTINUE reason=high_risk_answer_threshold_met KB ids=['CAT-048'] priority=None

## One-word message — unclear request

**Customer:** Refund
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** Which detail do you need: What are the Refund Guarantee Program conditions or How do I submit a refund request after cancelling a course or How many students can join the Refund Guarantee Program?
**Debug:** decision=CONTINUE reason=query_too_vague KB ids=['CAT-048', 'CAT-015', 'CAT-049'] priority=None

## Out-of-hours — human request

**Customer:** Please connect me to a human.
**Bot:** Demo bot built for Internship Studio's Founder Office assignment: answers use public help-center information plus labeled SAMPLE DATA. Messages are logged (masked).
**Bot:** I understand this is concerning. I've sent your message to our support team as ticket IS-97E8DB41. We aim to reply by Wed 28 Oct, 11:00 AM IST.
**Debug:** decision=ESCALATE reason=human_request KB ids=[] priority=P3
Ticket: IS-97E8DB41
