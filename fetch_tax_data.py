import sys
import os
import json
import time

# Add root dir to sys.path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.api_client import APIClient
from app.services.captcha_solver import get_captcha_solver

def main():
    mst = "0310510716"
    password = "XiRT1aA@"
    
    api = APIClient()
    solver = get_captcha_solver()
    
    logged_in = False
    for i in range(5):
        print(f"Login attempt {i+1}...")
        capt_res = api.get_captcha()
        if not capt_res.success:
            print("Failed to get captcha")
            time.sleep(2)
            continue
            
        captcha_text = solver.solve(capt_res.image_bytes)
        print(f"Solved captcha: {captcha_text}")
        if not captcha_text:
            print("Captcha solve failed or invalid. Retrying.")
            time.sleep(1)
            continue
            
        login_res = api.login(mst, password, captcha_text, capt_res.captcha_key)
        if login_res.success:
            print("Logged in successfully!")
            logged_in = True
            break
        else:
            print(f"Login failed: {login_res.error_msg}")
            time.sleep(2)
            
    if not logged_in:
        print("Could not login. Exiting.")
        return
        
    endpoints = {
        "sold_list": "/query/invoices/sold?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59",
        "sold_sco_list": "/sco-query/invoices/sold?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59",
        "purchase_list_status_5": "/query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=01/03/2026T00:00:00;tdlap=le=22/03/2026T23:59:59;ttxly==5",
        "purchase_detail_status_5": "/query/invoices/detail?nbmst=0309532497&khhdon=C26TKV&shdon=41142&khmshdon=1",
        "purchase_list_status_6": "/query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=01/03/2026T00:00:00;tdlap=le=22/03/2026T23:59:59;ttxly==6",
        "purchase_detail_status_6": "/query/invoices/detail?nbmst=0305358801&khhdon=K26TDS&shdon=11224&khmshdon=1",
        "purchase_list_status_8": "/query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59;ttxly==8",
        "purchase_sco_list_status_5": "/sco-query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59;ttxly==5",
        "purchase_sco_list_status_6": "/sco-query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59;ttxly==6",
        "purchase_sco_list_status_8": "/sco-query/invoices/purchase?sort=tdlap:desc&size=5&search=tdlap=ge=06/03/2026T00:00:00;tdlap=le=05/04/2026T23:59:59;ttxly==8",
        "purchase_sco_detail_status_8": "/sco-query/invoices/detail?nbmst=0312650437&khhdon=C26MGA&shdon=2736943&khmshdon=1",
    }
    
    results = {}
    base_url = "https://hoadondientu.gdt.gov.vn:30000"
    
    for name, path in endpoints.items():
        print(f"Fetching {name}...")
        url = base_url + path
        try:
            resp = api.client.get(url, headers=api._get_auth_headers())
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                results[name] = resp.json()
            else:
                results[name] = {"error": f"HTTP {resp.status_code}", "text": resp.text[:200]}
        except Exception as e:
            results[name] = {"error": str(e)}
        time.sleep(1)
        
    with open("Reference/api_responses.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Done! Results saved to Reference/api_responses.json")

if __name__ == "__main__":
    main()
