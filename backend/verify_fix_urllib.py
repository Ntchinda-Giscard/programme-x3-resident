import urllib.request
import json
import sys

BASE_URL = "http://localhost:5001/config"

def make_request(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_upsert():
    print("Step 1: Create initial config")
    payload1 = [{"site": "verify_test_site", "email_address": "initial@test.com"}]
    data1 = make_request(f"{BASE_URL}/add/address", method="POST", data=payload1)
    
    if data1:
        print(f"Response 1: {data1}")
        # Check if saved
        saved = next((x for x in data1 if x['site'] == 'verify_test_site'), None)
        if not saved:
            print("FAILED: initial save not returned in response")
    else:
        print("FAILED: No response for step 1")
        return

    print("\nStep 2: Update existing config")
    payload2 = [{"site": "verify_test_site", "email_address": "updated@test.com"}]
    data2 = make_request(f"{BASE_URL}/add/address", method="POST", data=payload2)
    
    if data2 is not None:
        print(f"Response 2: {data2}")
        
        # Check if updated in response
        if len(data2) == 0:
             print("CRITICAL FAIL: Returned empty list on update! Fix not working.")
             return

        updated_in_resp = next((x for x in data2 if x['site'] == 'verify_test_site'), None)
        
        if not updated_in_resp:
             print("FAILED: Updated config NOT returned in response")
             return
             
        if updated_in_resp['email_address'] != "updated@test.com":
            print(f"FAILED: Response has wrong email: {updated_in_resp['email_address']}")
            return
            
        print("SUCCESS: Response contains updated email.")
    else:
        print("FAILED: No response for step 2")
        return

    print("\nStep 3: Verify with GET")
    data3 = make_request(f"{BASE_URL}/get/address", method="GET")
    if data3:
        saved_final = next((x for x in data3 if x['site'] == 'verify_test_site'), None)
        
        if saved_final and saved_final['email_address'] == "updated@test.com":
             print("SUCCESS: GET confirms update.")
        else:
             print(f"FAILED: GET data mismatch. Got: {saved_final}")
    else:
        print("FAILED: No response for step 3")

    # Cleanup
    make_request(f"{BASE_URL}/delete/address/verify_test_site", method="DELETE")

if __name__ == "__main__":
    test_upsert()
