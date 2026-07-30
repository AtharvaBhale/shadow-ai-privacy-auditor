# tests/test_cases.py
from src.engine import PrivacyAuditorEngine

def run_suite():
    engine = PrivacyAuditorEngine()
    
    test_cases = [
        # 3 SAFE Cases (Must NOT redact anything)
        ("The project meeting is scheduled for 3:00 PM tomorrow in room 4B.", 0),
        ("Please note that our quarterly growth surpassed historical performance metrics by 12%.", 0),
        ("We should emphasize general wellness programs during our next cross-department gathering.", 0),
        
        # 7 RISKY Cases (Must trigger specific categories)
        ("Regards, Alice Smith - let me know if you received the document.", 1), # Context Name
        ("Send the invoice update tracking log over to realuser@fictionalcompany.org immediately.", 1), # Email
        ("Reach out to my desk line directly at 555-829-1042 for verification.", 1), # Phone
        ("Employee payroll setup requires verification of SSN 000-12-3456.", 1), # SSN
        ("Do not share the master AWS database key: api_key='amzn-p29K_mQx+v83=L' with internal teams.", 1), # API Credential
        ("He was recently diagnosed with severe asthma according to the file.", 1), # Medical Context
        ("The checkout terminal accepted payment card 4000-1234-5678-9010.", 1) # Credit Card (Luhn Validated)
    ]
    
    print("🚀 Running Privacy Auditor Synthetic Validation Suite...")
    for i, (text, expected_count) in enumerate(test_cases):
        found = engine.audit_text(text)
        status = "PASSED" if (len(found) >= expected_count if expected_count > 0 else len(found) == 0) else "FAILED"
        print(f"Test #{i+1}: {status} | Found: {len(found)} flags | Input: '{text[:40]}...'")

if __name__ == "__main__":
    run_suite()