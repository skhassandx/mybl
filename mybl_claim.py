import requests
import json
import os
import random

TOKEN_FILE = "tokens_mybl.json"

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return []

def save_tokens(accounts):
    with open(TOKEN_FILE, "w") as f:
        json.dump(accounts, f, indent=4)
    print("💾 tokens_mybl.json file auto-updated successfully.")

def get_headers(account, is_refresh=False):
    headers = {
        "Accept": "application/json",
        "platform": "android",
        "Accept-Language": "en",
        "version-code": "1207002",
        "app-version": "12.7.2",
        "api-client-pass": "1E6F751EBCD16B4B719E76A34FBA9",
        "msisdn": account.get("phone"),
        "connection-type": "PREPAID",
        "customer-type": "bl",
        "X-Device-Info": "WALTON,Primo H10,11",
        "X-Device-ID": "60f32873-c793-ef2d-eabf-cdc1ed0149c7",
        "X-Entitlements": "PREPAID,BG:1482,BG:1384,FT:FP",
        "Content-Type": "application/json; charset=UTF-8",
        "Host": "myblapi.banglalink.net",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/5.1.0"
    }
    if not is_refresh:
        headers["Authorization"] = f"Bearer {account.get('accessToken')}"
    return headers

def refresh_access_token(account):
    print(f"🔄 Access Token expired for {account.get('phone')}. Attempting to refresh...")
    url = "https://myblapi.banglalink.net/api/v1/refresh"
    
    payload = json.dumps({"refresh_token": account.get("refreshToken")})
    
    try:
        response = requests.post(url, headers=get_headers(account, is_refresh=True), data=payload)
        if response.status_code in [200, 201]:
            data = response.json()
            new_access = data.get("data", {}).get("access_token")
            new_refresh = data.get("data", {}).get("refresh_token", account.get("refreshToken"))
            
            if new_access:
                print("✅ Token refreshed successfully!")
                account["accessToken"] = new_access
                account["refreshToken"] = new_refresh
                return True
        print(f"❌ Token refresh failed. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
    return False

def check_profile(account):
    url = "https://myblapi.banglalink.net/api/loyalty/get-member-profile"
    try:
        response = requests.get(url, headers=get_headers(account))
        if response.status_code == 200:
            print("👤 Profile verified successfully.")
            return True, False
        elif response.status_code == 401:
            return False, True
    except Exception as e:
        print(f"❌ Profile check error: {e}")
    return False, False

def play_daily_quiz(account):
    print("🎯 Attempting to play Daily Quiz...")
    token_url = "https://myblapi.banglalink.net/api/trivia/get-trivia-token"
    
    try:
        # Step 1: MyBL থেকে Gamize এর জন্য টোকেন নেওয়া
        response = requests.post(token_url, headers=get_headers(account))
        if response.status_code == 401:
            return False, True # Token Expired
        
        if response.status_code == 200:
            response_data = response.json()
            
            gamize_token = None
            if "data" in response_data:
                if isinstance(response_data["data"], str):
                    gamize_token = response_data["data"]
                elif isinstance(response_data["data"], dict):
                    gamize_token = response_data["data"].get("token", "")
                    
            if not gamize_token:
                print("❌ Failed to parse Gamize token from response.")
                # সার্ভার কেন টোকেন দিলো না, তা দেখার জন্য ডিবাগ মেসেজ যোগ করা হলো
                print(f"🔍 Debug Info - Server Response: {response_data}")
                return False, False
                
            print("✅ Got Gamize token. Proceeding to submit answers...")
            
            # Gamize API এর জন্য স্পেসিফিক হেডার
            gamize_headers = {
                "x-gamification-api-key": "RQKuhLtyGOq0hppmYbTS",
                "x-gamification-identifier-key": gamize_token,
                "accept": "application/json",
                "user-agent": "Ktor client",
                "content-type": "application/json"
            }
            
            # অ্যাপের মতো একটি ডাইনামিক ২৪ ক্যারেক্টারের Transaction ID তৈরি করা
            transaction_id = os.urandom(12).hex() 
            
            # Step 2: Activity Played (কুইজ শুরু করার সিগন্যাল)
            played_url = "https://api.gamize.com/GamificationUserService/usertransaction/activity/played"
            played_payload = {
                "templateId": "69f399eb0f8d640001f24431",
                "ruleId": "6a5d0b1396115d000143cf07",
                "offerId": "",
                "type": 6,
                "id": transaction_id
            }
            requests.post(played_url, headers=gamize_headers, json=played_payload)
            
            # Step 3: Submit Answer (সঠিক উত্তর সাবমিট)
            submit_url = "https://api.gamize.com/GamificationUserService/reward/get/quiz/reward?lang=en"
            submit_payload = {
                "id": "69f399eb0f8d640001f24431",
                "orgId": "187",
                "questions": [
                    {
                        "correct": True,
                        "correctOption": "1",
                        "questionNo": "75",
                        "selectedOption": "1",
                        "type": "image",
                        "points": 10,
                        "timeOpt": random.randint(4500, 7500) 
                    }
                ],
                "ruleId": "6a5d0b1396115d000143cf07",
                "type": 6,
                "transactionId": transaction_id,
                "scheduleFlag": True,
                "leaderBoardId": "65e08b70cf60160001c3f4c1",
                "leaderBoardScheduleId": "6a5d0b1396115d000143cf09",
                "leaderBoardSelected": True
            }
            requests.post(submit_url, headers=gamize_headers, json=submit_payload)
            
            # Step 4: Claim Reward (রিওয়ার্ড ক্লেইম)
            claim_url = "https://api.gamize.com/GamificationUserService/usertransaction/activity/rewardwon"
            claim_payload = {
                "id": transaction_id,
                "offerId": "6a584fe56c0b0300016bf05c",
                "orgId": "187",
                "ruleId": "6a5d0b1396115d000143cf07",
                "templateId": "69f399eb0f8d640001f24431",
                "type": 6,
                "text": "win",
                "winStatus": True,
                "rewardType": 3,
                "voucher": "",
                "coins": 0,
                "points": 0
            }
            response_claim = requests.post(claim_url, headers=gamize_headers, json=claim_payload)
            
            if response_claim.status_code == 200:
                print("🎉 Daily Quiz Success! Reward claimed.")
            else:
                print(f"⚠️ Quiz submitted but reward claim returned status: {response_claim.status_code}")
                
            return True, False
        else:
            print(f"❌ Failed to get trivia token. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Quiz error: {e}")
        
    return False, False

def main():
    accounts = load_tokens()
    if not accounts:
        print("❌ tokens_mybl.json is empty.")
        return

    tokens_updated_globally = False

    for index, account in enumerate(accounts):
        phone = account.get("phone", f"Account {index+1}")
        print(f"\n{'='*40}\n📱 Processing MyBL Number: {phone}\n{'='*40}")
        
        success, needs_refresh = check_profile(account)
        if needs_refresh:
            if refresh_access_token(account):
                tokens_updated_globally = True
            else:
                continue 
        
        success, needs_refresh = play_daily_quiz(account)
        if needs_refresh:
             if refresh_access_token(account):
                 tokens_updated_globally = True
                 play_daily_quiz(account)

    if tokens_updated_globally:
        print("\n🔄 Updating tokens_mybl.json with new keys...")
        save_tokens(accounts)
    else:
        print("\n✅ All tokens are valid. Done.")

if __name__ == "__main__":
    main()
