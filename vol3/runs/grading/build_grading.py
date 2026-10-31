"""Builds the strict hand-grading sheet from the 2026-10-27 llama3.2 grading sheet.
Grades are human judgements typed in below (Grok Bot draft for Prateek's review)."""
import csv
from pathlib import Path
SRC = Path(__file__).resolve().parent.parent / "2026-10-27-llama3.2-grading-sheet.csv"
# key -> (strict, lenient, borderline, reason, citation_note)
G = {}
def g(key, strict, lenient, bl, reason, cite=""):
    G[key] = (strict, lenient, "yes" if bl else "no", reason, cite)
N, D = "no", "yes"
# ---- q1 return window: expected 30 days of delivery, full refund (ret-window)
g(("q1",2,N),"wrong","wrong",0,"gives 2-day courier collection and 21-day intl transit as 'return windows'; 30 days absent (ret-window not in pack)","no [Sn] labels -> escalate")
g(("q1",3,N),"wrong","wrong",0,"lists courier 2 days and international 21 days as return windows next to 30 days; two false windows","no [Sn] labels -> escalate")
g(("q1",5,N),"wrong","wrong",0,"same three-window answer; 2 days is courier collection, 21 days is parcel transit","no [Sn] labels -> escalate")
g(("q1",10,N),"wrong","wrong",0,"says window varies; presents 2-day courier window and 21 days as windows; 30 days only as one of several","labels valid -> sent")
g(("q1",2,D),"wrong","wrong",0,"states return window is two days domestic, 21 days international; 30 days absent","labels valid -> sent")
g(("q1",3,D),"wrong","wrong",0,"two-day domestic window and 21 days international asserted; also lists shop-window display","parenthesised (S1) not [S1] -> escalate")
g(("q1",5,D),"wrong","correct",1,"30 days of delivery for a full refund is stated, but prefixed with 'varies depending on the item and location'; nothing in the pack makes the window depend on location","no labels -> escalate")
g(("q1",10,D),"wrong","wrong",0,"same false 2-day/21-day windows; cites the distractor twice (store-window was already in the k=10 pack)","labels valid -> sent")
# ---- q2 broken mug: expected send a photo, refunded once seen (mug-dmg; ret-damaged adds 7 days)
g(("q2",2,N),"correct","correct",0,"photo within 7 days, then refund; every claim in mug-dmg/ret-damaged","labels valid -> sent; cites ret-damaged not mug-dmg")
g(("q2",3,N),"wrong","correct",1,"photo-then-refund is right, but invents a step: contact customer service with order number and description, 'we will review your case'","no labels -> escalate")
g(("q2",5,N),"wrong","correct",1,"photo within 7 days is right, but invents US/outside-US rules and a 30-day return for the mug and a mug-care warning","labels valid -> sent")
g(("q2",10,N),"wrong","correct",1,"photo within 7 days is right, but 'international customers allow 21 days for the parcel' implies the mug must be shipped back; mug-dmg needs only a photo","labels valid -> sent")
g(("q2",2,D),"wrong","correct",1,"same invented contact-customer-service step as k=3 no-distractor","no labels -> escalate")
g(("q2",3,D),"wrong","correct",1,"invented contact step plus speculation that breakage was due to misuse (from mug-care)","labels valid -> sent")
g(("q2",5,D),"wrong","correct",1,"photo within 7 days is right, but 'follow the return process and provide the required documentation' adds a return/documentation requirement not in the pack","labels valid -> sent")
g(("q2",10,D),"wrong","correct",1,"same as k=10 no-distractor: implies the mug is shipped back (21 days international)","labels valid -> sent")
# ---- q3 clearance jacket: expected no, final sale and final sale cannot be returned (ret-final never in pack)
g(("q3",2,N),"correct","correct",0,"no, final sale; matches expected (the 'final sale = no returns' step is not in the pack: ret-final missing)","no labels -> escalate")
g(("q3",3,N),"correct","correct",0,"identical reply to k=2","no labels -> escalate")
g(("q3",5,N),"correct","correct",0,"'No, the clearance jacket is final sale [S2]'","labels valid -> sent")
g(("q3",10,N),"abstained","abstained",0,"opens 'No direct information...' and the reply is cut off mid-sentence in the log; no answer given","no labels -> escalate")
g(("q3",2,D),"correct","correct",0,"no, final sale [S2]","labels valid -> sent")
g(("q3",3,D),"wrong","correct",1,"concludes not returnable, but says 'no direct information is provided' (jacket-sale is S2) and adds 'or exchanges', which no passage says","labels valid -> sent")
g(("q3",5,D),"abstained","abstained",1,"only says final sale 'implies that returns may not be accepted' after 'no direct information'; never commits; also says S4 (ret-courier) does not address returns","no labels -> escalate")
g(("q3",10,D),"abstained","abstained",0,"same truncated reply as k=10 no-distractor","no labels -> escalate")
# ---- q4 cash on delivery: expected yes, under Rs 10,000 (pay-cod never in pack)
for k in (2,3,5,10):
    for d in (N,D):
        g(("q4",k,d),"wrong","wrong",0,"answers 'No' by misreading ret-intl (international returns, 21 days); pay-cod says COD is available under Rs 10,000","labels valid -> sent (a wrong answer passes the citation check)")
# ---- q5 refund to card: expected 5 to 7 days (pay-refund)
g(("q5",2,N),"wrong","correct",1,"5 to 7 days is given, but opens 'the refund timeline varies depending on the type of refund' and treats the 7-day photo deadline as a refund timing; pay-refund is unconditional","labels valid -> sent")
g(("q5",3,N),"abstained","abstained",0,"quotes 5 to 7 days but says no definitive answer is possible because 'card' is not named","parenthesised (S1) -> escalate")
g(("q5",5,N),"correct","correct",0,"'within 5 to 7 days [S1]'","labels valid -> sent")
g(("q5",10,N),"correct","correct",0,"'within 5 to 7 days [S1]'","labels valid -> sent")
g(("q5",2,D),"wrong","wrong",0,"says there is no information, then quotes 5-7 days, and misstates S2 as 'refunds processed within 7 days of receiving a photo'","labels valid -> sent")
g(("q5",3,D),"abstained","abstained",0,"says it is unclear; quotes 5-7 days without committing","labels valid -> sent")
g(("q5",5,D),"abstained","abstained",0,"says the timeframe cannot be determined","no labels -> escalate")
g(("q5",10,D),"abstained","abstained",0,"says no specific information; quotes 5-7 days without committing","labels valid -> sent")
# ---- q6 NW-500 battery warranty: expected send order number + photo of the fault; replacement free within the 12-month warranty
g(("q6",2,N),"wrong","wrong",0,"invents a manufacturer website form and submission process; 12-month/free never stated","no labels -> escalate")
g(("q6",3,N),"wrong","correct",1,"order number + photo and free within 12 months are both right; only fault: 'send ... to the manufacturer', a recipient no passage names","labels valid -> sent")
g(("q6",5,N),"correct","correct",0,"free within the 12-month warranty; send the order number and a photo of the fault; extra pair/reset lines are true and marked unrelated","bare S1/S2 without brackets -> escalate")
g(("q6",10,N),"wrong","correct",1,"order number + photo is right, but 'to the manufacturer' is unsupported and the free-within-12-months part is missing","labels valid -> sent; mis-cites [S1] (nw500-batt) for the warranty-claim text")
g(("q6",2,D),"wrong","wrong",0,"says there is no information that replacement is free within the 12-month warranty while S1 says exactly that","labels valid -> sent")
g(("q6",3,D),"wrong","correct",1,"same as k=3 no-distractor ('to the manufacturer')","labels valid -> sent")
g(("q6",5,D),"wrong","wrong",0,"'follow steps S1 and S2' without stating them; never says order number or photo","bare S-labels -> escalate")
g(("q6",10,D),"wrong","correct",1,"same as k=10 no-distractor ('to the manufacturer', no 12-month point)","labels valid -> sent; mis-cites [S1]")
# ---- Ch 16 (7 of 16 BENCH cases). content grade; pipeline outcome treats escalate as abstained
C16 = {
 "eu-withdrawal": ("correct","14 days from delivery, without giving a reason: matches S5 exactly","no labels -> escalate","abstained (escalated)","critical answerable case not answered"),
 "old-vs-new-window": ("correct","30 days: matches the kept clause R1@2026-09-15","no labels -> escalate","abstained (escalated)","critical answerable case not answered"),
 "refund-vs-ticket": ("correct","'No... 30 days, not 7 [S1]': precedence kept R1@2026-09-15 over ticket-8812","labels valid -> sent","correct",""),
 "bundle-charger": ("wrong","says not covered and that S4 (ear-tip exclusion) excludes the charger; expected covered via charger PART_OF bundle, bundle COVERED_BY W2. The charger edge was not in the pack: assemble() dropped it as a near-duplicate of the case edge (dupes=1)","labels valid -> sent","wrong",""),
 "final-sale-refund": ("correct","no refund, final sale [S2]; ret-final not in pack, inference is the model's","labels valid -> sent","correct",""),
 "lifetime-warranty": ("abstained","says no direct information about a lifetime warranty; mentions the 12-month battery warranty, which is true; expected abstain","parenthesised (S1) -> escalate","abstained (escalated)","expected abstain: right outcome"),
 "unknown-part": ("wrong","claims the cable is excluded under W2.3 (W2.3 excludes ear tips) and that its bundle is covered; expected unknown/abstain","no labels -> escalate","abstained (escalated)","right outcome only because the citation check escalated a wrong reply"),
}
rows = list(csv.DictReader(open(SRC)))
F = ["chapter","case","k","distractor","question","expected_answer","pack_ids","needed_in_pack","citations_in_pack","action","reply","strict_grade","lenient_grade","borderline","reason","citation_note","pipeline_outcome","grader"]
EXP = {"q1":"30 days of delivery for a full refund (most items)","q2":"send a photo; the mug is refunded once it is seen (photo within 7 days per ret-damaged)","q3":"No: it is final sale, and final sale items cannot be returned or refunded","q4":"Yes: cash on delivery for orders under Rs 10,000","q5":"5 to 7 days, to the original payment method","q6":"send the order number and a photo of the fault; NW-500 battery replacement is free within the 12-month warranty",
 "eu-withdrawal":"14 days from delivery, no reason needed","old-vs-new-window":"30 days (R1@2026-09-15)","refund-vs-ticket":"No: 30 days, the agent's 7 days is superseded","bundle-charger":"Yes: charger is part of the Travel Bundle, which W2 covers","final-sale-refund":"No: final sale, cannot be refunded","lifetime-warranty":"abstain: no lifetime warranty in the evidence","unknown-part":"abstain / unknown: no evidence about the cable"}
out = []
for r in rows:
    act = "send" if r["citations_in_pack"] == "yes" else "escalate"
    base = dict(chapter=r["chapter"], case=r["case"], k=r["k"], distractor=r["distractor"], question=r["question"],
                expected_answer=EXP[r["case"]], pack_ids=r["pack_ids"], needed_in_pack=r["needed_in_pack"],
                citations_in_pack=r["citations_in_pack"], action=act, reply=r["reply"], grader="Grok Bot draft, strict; for Prateek's review")
    if r["chapter"] == "11":
        s, l, b, why, cite = G[(r["case"], int(r["k"]), r["distractor"])]
        po = s if act == "send" else "abstained (escalated)"
        base.update(strict_grade=s, lenient_grade=l, borderline=b, reason=why, citation_note=cite, pipeline_outcome=po)
    else:
        s, why, cite, po, note = C16[r["case"]]
        base.update(strict_grade=s, lenient_grade=s, borderline="no", reason=why + (f"; {note}" if note else ""), citation_note=cite, pipeline_outcome=po)
    out.append(base)
assert len(G) == 48 and len(out) == 55
dst = Path(__file__).resolve().parent / "2026-10-28-llama3.2-strict-grading.csv"
with dst.open("w", newline="") as f:
    w = csv.DictWriter(f, F); w.writeheader(); w.writerows(out)
print("wrote", dst)
# summary
from collections import defaultdict
for d in (N, D):
    for col in ("strict_grade","lenient_grade"):
        line=[]
        for k in ("2","3","5","10"):
            rs=[o for o in out if o["chapter"]=="11" and o["k"]==k and o["distractor"]==d]
            c=sum(o[col]=="correct" for o in rs); a=sum(o[col]=="abstained" for o in rs); wr=sum(o[col]=="wrong" for o in rs)
            line.append(f"k={k}: {c}/6 (wrong {wr}, abst {a})")
        print(f"distractor={d} {col}: " + "; ".join(line))
    line=[]
    for k in ("2","3","5","10"):
        rs=[o for o in out if o["chapter"]=="11" and o["k"]==k and o["distractor"]==d]
        line.append(f"k={k}: {sum(o['strict_grade']=='correct' and o['action']=='send' for o in rs)}/6")
    print(f"distractor={d} strict correct AND sent: " + "; ".join(line))
