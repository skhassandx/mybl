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
        # Step 1: Gamize Token সংগ্রহ করা
        response = requests.post(token_url, headers=get_headers(account))
        if response.status_code == 401:
            return False, True 
        
        if response.status_code == 200:
            response_data = response.json()
            
            gamize_token = None
            if "data" in response_data:
                if isinstance(response_data["data"], str):
                    gamize_token = response_data["data"]
                elif isinstance(response_data["data"], dict):
                    gamize_token = response_data["data"].get("access_token")
                    if not gamize_token:
                        gamize_token = response_data["data"].get("token", "")
                    
            if not gamize_token:
                print("❌ Failed to parse Gamize token from response.")
                return False, False
                
            print("✅ Got Gamize token. Fetching today's quiz data...")
            
            gamize_headers = {
                "x-gamification-api-key": "RQKuhLtyGOq0hppmYbTS",
                "x-gamification-identifier-key": gamize_token,
                "accept": "application/json",
                "user-agent": "Ktor client",
                "content-type": "application/json"
            }
            
            # Step 2: আজকের নতুন রুল এবং আইডিগুলো সার্ভার থেকে বের করা
            rule_url = "https://api.gamize.com/GamificationUserService/reward/get/rule/reward?ruleName=SeasonHome0coin&lang=en"
            rule_response = requests.get(rule_url, headers=gamize_headers)
            
            if rule_response.status_code != 200:
                print(f"❌ Failed to get quiz rule. Status: {rule_response.status_code}")
                return False, False
                
            rule_data = rule_response.json()
            spin_wheel = rule_data.get("widget", {}).get("spinWheel", {})
            
            if not spin_wheel:
                print("❌ Quiz data not found in response.")
                return False, False
            
            # ডাইনামিক ডেটা এক্সট্র্যাক্ট করা
            template_id = spin_wheel.get("id")
            rule_id = spin_wheel.get("ruleId")
            lb_id = spin_wheel.get("leaderBoardId")
            lb_schedule_id = spin_wheel.get("leaderBoardScheduleId")
            questions = spin_wheel.get("questions", [])
            
            if not questions:
                print("❌ No questions found for today.")
                return False, False
                
            q_no = questions[0].get("questionNo")
            correct_opt = questions[0].get("correctOption")
            q_points = questions[0].get("points", 10)
            q_type = questions[0].get("type", "image")
            
            print(f"🔍 Extracted Data -> Question: {q_no}, Answer: {correct_opt}, Rule: {rule_id}")
            
            transaction_id = os.urandom(12).hex() 
            
            # Step 3: Activity Played
            played_url = "https://api.gamize.com/GamificationUserService/usertransaction/activity/played"
            played_payload = {
                "templateId": template_id,
                "ruleId": rule_id,
                "offerId": "",
                "type": 6,
                "id": transaction_id
            }
            res_played = requests.post(played_url, headers=gamize_headers, json=played_payload)
            
            # Step 4: Submit Answer
            submit_url = "https://api.gamize.com/GamificationUserService/reward/get/quiz/reward?lang=en"
            submit_payload = {
                "id": template_id,
                "orgId": "187",
                "questions": [
                    {
                        "correct": True,
                        "correctOption": correct_opt,
                        "questionNo": q_no,
                        "selectedOption": correct_opt,
                        "type": q_type,
                        "points": q_points,
                        "timeOpt": random.randint(12000, 19500) 
                    }
                ],
                "ruleId": rule_id,
                "type": 6,
                "transactionId": transaction_id,
                "scheduleFlag": True,
                "leaderBoardId": lb_id,
                "leaderBoardScheduleId": lb_schedule_id,
                "leaderBoardSelected": True
            }
            res_submit = requests.post(submit_url, headers=gamize_headers, json=submit_payload)
            
            # Step 5: Claim Reward
            claim_url = "https://api.gamize.com/GamificationUserService/usertransaction/activity/rewardwon"
            claim_payload = {
                "id": transaction_id,
                "offerId": "6a584fe56c0b0300016bf05c", # এটি ফিক্সড থাকে সাধারণত
                "orgId": "187",
                "ruleId": rule_id,
                "templateId": template_id,
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
                print(f"⚠️ Reward claim returned status: {response_claim.status_code} | Debug Info: {response_claim.text}")
                
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
