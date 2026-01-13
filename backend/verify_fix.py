import requests
import sys

BASE_URL = "http://localhost:5001/config"

def test_upsert():
    print("Step 1: Create initial config")
    payload1 = [{"site": "verify_test_site", "email_address": "initial@test.com"}]
    try:
        resp1 = requests.post(f"{BASE_URL}/add/address", json=payload1)
        resp1.raise_for_status()
        data1 = resp1.json()
        print(f"Response 1: {data1}")
        
        # Check if saved
        saved = next((x for x in data1 if x['site'] == 'verify_test_site'), None)
        if not saved:
            print("FAILED: initial save not returned in response")
            # return
        
    except Exception as e:
        print(f"Error in step 1: {e}")
        return

    print("\nStep 2: Update existing config")
    payload2 = [{"site": "verify_test_site", "email_address": "updated@test.com"}]
    try:
        resp2 = requests.post(f"{BASE_URL}/add/address", json=payload2)
        resp2.raise_for_status()
        data2 = resp2.json()
        print(f"Response 2: {data2}")
        
        # Check if updated in response
        # Note: The backend returns all PROCESSED configs (inserted or updated)
        updated_in_resp = next((x for x in data2 if x['site'] == 'verify_test_site'), None)
        
        if not updated_in_resp:
             print("FAILED: Updated config NOT returned in response (Wait, did it return empty list?)")
             if len(data2) == 0:
                 print("CRITICAL FAIL: Returned empty list on update! Fix not working.")
             return
             
        if updated_in_resp['email_address'] != "updated@test.com":
            print(f"FAILED: Response has wrong email: {updated_in_resp['email_address']}")
            return
            
        print("SUCCESS: Response contains updated email.")

    except Exception as e:
        print(f"Error in step 2: {e}")
        return

    print("\nStep 3: Verify with GET")
    try:
        resp3 = requests.get(f"{BASE_URL}/get/address")
        data3 = resp3.json()
        saved_final = next((x for x in data3 if x['site'] == 'verify_test_site'), None)
        
        if saved_final and saved_final['email_address'] == "updated@test.com":
             print("SUCCESS: GET confirms update.")
        else:
             print(f"FAILED: GET data mismatch. Got: {saved_final}")
             
    except Exception as e:
        print(f"Error in step 3: {e}")

    # Cleanup
    requests.delete(f"{BASE_URL}/delete/address/verify_test_site")

if __name__ == "__main__":
    test_upsert()
