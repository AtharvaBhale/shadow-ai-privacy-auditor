# tests/test_cases.py
from src.engine import PrivacyAuditorEngine

# Each risky case now asserts the *category* expected, not just a nonzero count,
# so a mislabeled finding (e.g. a phone number flagged as MEDICAL_INFO) fails loudly.
TEST_CASES = [
    # ---- SAFE cases: must produce zero findings ----
    ("The project meeting is scheduled for 3:00 PM tomorrow in room 4B.", []),
    ("Please note that our quarterly growth surpassed historical performance metrics by 12%.", []),
    ("We should emphasize general wellness programs during our next cross-department gathering.", []),
    ("May will present the roadmap update at Monday's stand-up.", []),  # common name-as-word, no salutation context
    ("The password policy requires at least 12 characters, but no password is shared here.", []),

    # ---- RISKY cases: must trigger the listed category(ies) ----
    ("Regards, Alice Smith - let me know if you received the document.", ["NAME"]),
    ("Send the invoice update tracking log over to realuser@fictionalcompany.org immediately.", ["CONTACT_INFO"]),
    ("Reach out to my desk line directly at 555-829-1042 for verification.", ["CONTACT_INFO"]),
    ("Employee payroll setup requires verification of SSN 000-12-3456.", ["GOVT_IDENTIFIER"]),
    ("Do not share the master AWS database key: api_key='amzn-p29K_mQx+v83=L' with internal teams.", ["CREDENTIALS"]),
    ("He was recently diagnosed with severe asthma according to the file.", ["MEDICAL_INFO"]),
    ("The checkout terminal accepted payment card 4000-1234-5678-9009.", ["FINANCIAL_IDENTIFIER"]),
]


def run_suite():
    engine = PrivacyAuditorEngine()
    passed, failed = 0, 0

    print("Running Privacy Auditor Synthetic Validation Suite...\n")
    for i, (text, expected_categories) in enumerate(TEST_CASES, start=1):
        found = engine.audit_text(text)
        found_categories = sorted(f["category"] for f in found)
        expected_sorted = sorted(expected_categories)

        ok = found_categories == expected_sorted
        status = "PASSED" if ok else "FAILED"
        passed += ok
        failed += not ok

        print(f"Test #{i}: {status}")
        print(f"  Input:    {text}")
        print(f"  Expected: {expected_sorted or 'no findings'}")
        print(f"  Found:    {found_categories or 'no findings'}\n")

    print(f"Summary: {passed} passed, {failed} failed, {len(TEST_CASES)} total")
    return failed == 0


if __name__ == "__main__":
    import sys
    ok = run_suite()
    sys.exit(0 if ok else 1)
