from savings_ledger import classify_savings_transactions, extract_merchant, _parse_all_lines

# Verbatim from pdf_decrypt.extract_text() output on the real July 2026
# Kotak savings account statement (dump/kotak/*_40XXXXXXX437*) — every one
# of its 53 transactions, including the mid-statement page-break header
# (lines 86-89 below) pdftotext inserts. Kept as one contiguous, unmodified
# excerpt on purpose: this parser derives each row's signed amount from the
# delta between consecutive printed balances, so a hand-trimmed subset
# (skipping transactions) breaks those deltas — this was caught while
# writing this test and is exactly the kind of bug a synthetic fixture
# would hide, per this project's standing fixture convention.
RAW_EXCERPT = """Savings Account Transactions
# Date Description Chq/Ref. No. Withdrawal (Dr.) Deposit (Cr.) Balance
- - Opening Balance - - - 1,49,505.48
1 01 Jul 2026 UPI/CHANDRAMANIAM
/TNSC/654899676356/UPI
UPI-618257480055 2,000.00 1,47,505.48
2 01 Jul 2026 UPI/CHANDRAMANIAM
/TNSC/654825775938/UPI
UPI-618257494744 1,500.00 1,46,005.48
3 01 Jul 2026 NACH-MUT-DR-TP ACH NIPPON IND MF-
2242314054
NACHDR010726001510
03
500.00 1,45,505.48
4 01 Jul 2026 NACH-MUT-DR-TP ACH NIPPON IND MF-
2242317978
NACHDR010726001512
63
500.00 1,45,005.48
5 01 Jul 2026 NACH-MUT-DR-TP ACH NIPPON IND MF-
2242310486
NACHDR010726001570
37
500.00 1,44,505.48
6 01 Jul 2026 NACH-MUT-DR-TP ACH NIPPON IND MF-
2242325082
NACHDR010726001433
00
500.00 1,44,005.48
7 01 Jul 2026 UPI/MARIMUTHU B/IOBA/654806738194/Paid
via CRE
UPI-618273966395 40.00 1,43,965.48
8 01 Jul 2026 UPI/VIGNESH S/KVBL/654826753733/Paid via
CRE
UPI-618277238103 50.00 1,43,915.48
9 01 Jul 2026 UPI/CRED Club/UTIB/654826780426/payment
on C
UPI-618288224759 42,625.00 1,01,290.48
10 03 Jul 2026 NACH-MUT-DR-TP ACH NIPPON IND MF-
2254854047
NACHDR030726008489
96
500.00 1,00,790.48
11 03 Jul 2026 UPI/CRED Club/UTIB/655015128768/payment
on C
UPI-618437106229 3,997.02 96,793.46
12 05 Jul 2026 Ins Debit A\\c GLN 4228809 dt 05/07/26 CORE-2372960620 3,891.00 92,902.46
13 05 Jul 2026 UPI/GoodScore/YESB/618669273727/Subscrip
tion
UPI-618652046594 99.00 92,803.46
14 05 Jul 2026 UPI/CRED Club/UTIB/655231398314/payment
on C
UPI-618654743825 8,344.00 84,459.46
15 05 Jul 2026 UPI/K SWATHITHRA/UTIB/655222404457/Paid
via CRE
UPI-618654772597 15,000.00 69,459.46
16 05 Jul 2026 UPI/JAI MEDICALS/UTIB/655209402522/Paid
via CRE
UPI-618660335139 20.00 69,439.46
17 06 Jul 2026 UPI/CRED Club/UTIB/655331625513/payment
on C
UPI-618749609109 14,550.74 54,888.72
18 07 Jul 2026 UPI/Chai Kings KNK/YESB/655424778766/Paid
via CRE
UPI-618820410152 115.00 54,773.72
19 07 Jul 2026 UPI/KANDASAMY G/HDFC/655431779387/Paid
via CRE
UPI-618821283700 50.00 54,723.72
20 10 Jul 2026 UPI/SMOKY DOCKY/YESB/655702250908/Paid UPI-619151735128 543.00 54,180.72
Statement Generated on 01 Aug 2026, 12:48 Page 1 of
5Savings Account Transactions
# Date Description Chq/Ref. No. Withdrawal (Dr.) Deposit (Cr.) Balance
via CRE
21 12 Jul 2026 UPI/RANI M/UCBA/655905515442/Paid via CRE UPI-619372970748 250.00 53,930.72
22 14 Jul 2026 UPI/K RADHA GOURI/KKBK/656133992203/UPI UPI-619585968052 2,000.00 55,930.72
23 14 Jul 2026 UPI/K RADHA GOURI/KKBK/619593804316/UPI UPI-619587645948 1,400.00 57,330.72
24 14 Jul 2026 UPI/CRED Club/UTIB/656108745988/payment
on C
UPI-619587715594 3,389.00 53,941.72
25 15 Jul 2026 UPI/SANTHOSH S/O
S/HDFC/656216881756/Paid via CRE
UPI-619653530121 100.00 53,841.72
26 15 Jul 2026 UPI/K RADHA GOURI/KKBK/656217615419/UPI UPI-619656645328 3,000.00 56,841.72
27 15 Jul 2026 UPI/CRED Club/UTIB/656221879546/payment
on C
UPI-619656775190 3,000.00 53,841.72
28 16 Jul 2026 Pyt Loan A\\c GLN 4805528 dt 16/07/26 CORE-2767720141 4,57,829.00 5,11,670.72
29 19 Jul 2026 UPI/K RADHA GOURI/KKBK/656667739773/UPI UPI-620037313469 2,185.00 5,13,855.72
30 19 Jul 2026 UPI/AMURA
NUTRITIO/UTIB/656616444822/Paid via CRE
UPI-620037316567 2,185.00 5,11,670.72
31 19 Jul 2026 UPI/RANI M/UCBA/656628476420/Paid via CRE UPI-620059908434 250.00 5,11,420.72
32 19 Jul 2026 UPI/Mr R SIVASANGA/IDIB/656622499445/Paid
via CRE
UPI-620061477030 50.00 5,11,370.72
33 19 Jul 2026 UPI/Mr R SIVASANGA/IDIB/656618503493/Paid
via CRE
UPI-620063119578 330.00 5,11,040.72
34 19 Jul 2026 UPI/SAVUTHA K/BARB/656608491423/Paid via
CRE
UPI-620063171046 330.00 5,10,710.72
35 19 Jul 2026 UPI/MINOR P
VELMUR/IOBA/656622513910/Paid via CRE
UPI-620068006948 1,183.00 5,09,527.72
36 22 Jul 2026 UPI/CRED Club/UTIB/656927825510/payment
on C
UPI-620328701484 31,250.00 4,78,277.72
37 23 Jul 2026 UPI/ARYAN  S  JAIN/UBIN/657020638442/UPI UPI-620407919803 1,200.00 4,79,477.72
38 23 Jul 2026 UPI/K RADHA GOURI/KKBK/657098045060/UPI UPI-620418004589 1,200.00 4,78,277.72
39 24 Jul 2026 UPI/K RADHA GOURI/KKBK/620588328805/UPI UPI-620579839950 4,200.00 4,82,477.72
40 24 Jul 2026 UPI/CRED Club/UTIB/657115128470/payment
on C
UPI-620579959237 4,200.00 4,78,277.72
41 24 Jul 2026 UPI/VASUDEVAN R/HDFC/657117146760/Paid
via CRE
UPI-620587721085 5,000.00 4,73,277.72
42 25 Jul 2026 UPI/SUBHATHRA
VENK/ICIC/620668388249/UPI
UPI-620626143900 1,500.00 4,74,777.72
43 25 Jul 2026 UPI/KAMALRAJ  M/SBIN/657228215711/Paid
via CRE
UPI-620630299096 30.00 4,74,747.72
44 25 Jul 2026 UPI/MUTHUKUMARAN
M/KARB/657226233291/Paid via CRE
UPI-620633167151 90.00 4,74,657.72
45 25 Jul 2026 UPI/KANDASAMY G/HDFC/657227261163/Paid
via CRE
UPI-620642981910 50.00 4,74,607.72
46 25 Jul 2026 UPI/VASUDEVAN R/HDFC/657230261075/Paid
via CRE
UPI-620649014448 5,000.00 4,69,607.72
47 26 Jul 2026 UPI/RANI M/UCBA/657306417784/Paid via CRE UPI-620720511061 250.00 4,69,357.72
48 27 Jul 2026 Ins Debit A\\c GLN 4228809 dt 27/07/26 CORE-2379220750 4,37,770.00 31,587.72
49 29 Jul 2026 Pyt Loan A\\c GLN 4228809 dt 29/07/26 CORE-2772901550 1.00 31,588.72
50 30 Jul 2026 UPI/Zee5/YESB/621100990488/Oidzee5240ee UPI-621150310355 99.00 31,489.72
51 30 Jul 2026 UPI/NITHYANANDA
PR/IBKL/657728933815/Paid via CRE
UPI-621174418373 782.00 30,707.72
52 30 Jul 2026 UPI/VASUDEVAN R/HDFC/657725007490/Paid
via CRE
UPI-621102673224 1,000.00 29,707.72
53 31 Jul 2026 NEFT HDFCH01159246906 KALS BREWERIES
PVT LTD HDFC
NEFTINW-1667589570 1,83,842.00 2,13,549.72
"""


def test_parses_all_53_transactions():
    rows = _parse_all_lines(RAW_EXCERPT)
    assert len(rows) == 53


def test_ledger_reconciles_to_statement_totals():
    rows = _parse_all_lines(RAW_EXCERPT)
    assert round(sum(r["amount"] for r in rows), 2) == round(213549.72 - 149505.48, 2)


def test_classifies_into_correct_buckets():
    b = classify_savings_transactions(RAW_EXCERPT)
    assert len(b["salary"]) == 1
    assert len(b["sip"]) == 5
    assert len(b["cred_club"]) == 8
    assert len(b["family"]) == 6
    assert len(b["loan"]) == 4
    assert len(b["unmatched"]) == 0


def test_cred_club_is_always_a_debit():
    b = classify_savings_transactions(RAW_EXCERPT)
    assert all(r["amount"] < 0 for r in b["cred_club"])
    first = next(r for r in b["cred_club"] if r["date"] == "2026-07-01")
    assert first["amount"] == -42625.0


def test_family_transfers_can_be_either_direction():
    b = classify_savings_transactions(RAW_EXCERPT)
    amounts = sorted(r["amount"] for r in b["family"])
    assert amounts[0] < 0  # 23 Jul: money went out to her
    assert amounts[-1] > 0  # 14 Jul: she sent money in


def test_salary_credit_correct():
    b = classify_savings_transactions(RAW_EXCERPT)
    assert b["salary"][0]["amount"] == 183842.0


def test_loan_lines_not_double_counted_as_spend():
    b = classify_savings_transactions(RAW_EXCERPT)
    descriptions = [r["description"] for r in b["loan"]]
    assert all("GLN" in d for d in descriptions)
    assert sum(r["amount"] for r in b["loan"]) == 457829.0 - 3891.0 - 437770.0 + 1.0


def test_extract_merchant():
    assert extract_merchant("UPI/Chai Kings KNK/YESB/655424778766/Paid via CRE UPI-618820410152") == "Chai Kings KNK"
    assert extract_merchant("UPI/MARIMUTHU B/IOBA/654806738194/Paid via CRE") == "MARIMUTHU B"
