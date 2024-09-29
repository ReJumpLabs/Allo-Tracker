import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from app import update_wallet
from colorama import Fore, Style
import sqlite3

# Hàm ngủ tạm thời
def sleep(ms):
    time.sleep(ms / 1000)

# Hàm tạo ngẫu nhiên User-Agent
def random_user_agent():
    os_versions = f"{random.randint(10, 20)}_{random.randint(0, 14)}"
    platforms = ["Windows", "Macintosh", "X11", "iPhone", "iPad", "Linux"]
    platform = random.choice(platforms)

    if platform == "Windows":
        os = f"Windows NT {random.randint(6, 10)}.{random.randint(0, 3)}; Win64; x64"
    elif platform == "Macintosh":
        os = f"Macintosh; Intel Mac OS X 10_{os_versions}"
    elif platform == "X11":
        os = "X11; Linux x86_64"
    elif platform == "iPhone":
        os = f"iPhone; CPU iPhone OS {os_versions} like Mac OS X"
    elif platform == "iPad":
        os = f"iPad; CPU OS {os_versions} like Mac OS X"
    else:
        os = f"Linux; Android {random.randint(4, 12)}.{random.randint(0, 4)}"

    web_kits = [f"AppleWebKit/{random.randint(500, 900)}.36 (KHTML, like Gecko)", "Gecko/20100101"]
    browsers = [f"Chrome/{random.randint(60, 90)}.0.{random.randint(1000, 4000)}.{random.randint(0, 199)}",
                f"Safari/{random.randint(500, 1100)}.15",
                f"Firefox/{random.randint(60, 90)}.0"]

    web_kit = random.choice(web_kits)
    browser = random.choice(browsers)
    return f"Mozilla/5.0 ({os}) {web_kit} {browser}"


            
# Hàm kiểm tra số dư
def check_balance(wallet):
    url = f"https://allora-api.testnet-1.testnet.allora.network/cosmos/bank/v1beta1/balances/{wallet}"
    headers = {
        'accept': '*/*',
        'user-agent': random_user_agent(),
    }
    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        if response_data.get('balances') and response_data['balances'][0]:
            print(wallet, response_data['balances'][0]['amount'])
        else:
            print(wallet, 'error')
    except Exception as e:
        print(f"Error checking balance for {wallet}: {str(e)}")

# Hàm lấy điểm từ API
def signin(wallet):
    url = 'https://api.upshot.xyz/v2/allora/users/connect'
    data = {
        'allora_address': wallet,
        'evm_address': None
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'user-agent': random_user_agent(),
        'x-api-key': 'UP-0d9ed54694abdac60fd23b74'
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        points_data = check_points(response.json().get('data', {}).get('id'), wallet)
        return points_data
    except Exception as e:
        print(f"Error signing in {wallet}: {str(e)}")

# Hàm kiểm tra điểm
def check_points(walletID, wallet):
    url = f"https://api.upshot.xyz/v2/allora/points/{walletID}"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'user-agent': random_user_agent(),
        'x-api-key': 'UP-0d9ed54694abdac60fd23b74'
    }
    try:
        response = requests.get(url, headers=headers)
        points_data = response.json().get('data', {})
        return {
            'total_points': points_data['allora_leaderboard_stats']['total_points'],
            'campaign_points': points_data.get('campaign_points', [])
        }
    except Exception as e:
        
        print(Fore.RED + f"Checking points for {wallet} with points is 0" + Style.RESET_ALL)
        return {'total_points': 0, 'campaign_points': []}

# Hàm gửi dữ liệu POST tới API Python
def post_data(data):
    try:
        update_wallet(data)
    except Exception as e:
        print(f"Failed to update wallet: {str(e)}")

# Hàm xử lý hàng loạt
def mass_check(wallet_list):
    with ThreadPoolExecutor(max_workers=50) as executor:
        for wallet in wallet_list:
            executor.submit(handle_wallet, wallet)

# Hàm xử lý từng ví
def handle_wallet(wallet):
    try:
        points_data = signin(wallet)
        result_point = f"{points_data['total_points']:.3f}".replace('.', '.')
        data = {
            'wallet': wallet,
            'points': result_point
        }
        if(points_data['total_points'] > 0):
            post_data(data)

    except Exception as e:
        print(f"Error processing wallet {wallet}: {str(e)}")

# Đọc ví từ file
def read_wallets(file_path):
    with open(file_path, 'r') as file:
        wallets = [line.strip() for line in file.readlines() if line.strip()]
    return wallets

def get_wallets_from_db():
    """
    Lấy danh sách ví từ bảng wallet_points trong cơ sở dữ liệu SQLite.
    """
    conn = sqlite3.connect('allora.db')
    
    if conn is None:
        return []

    wallet_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT wallet FROM wallet_points")
        wallet_list = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Lỗi khi truy vấn cơ sở dữ liệu: {e}")
    finally:
        # Đảm bảo đóng kết nối
        conn.close()
    
    return wallet_list
if __name__ == "__main__":
    # wallet_list = get_wallets_from_db()
    wallet_list = read_wallets('allora.txt')

    mass_check(wallet_list)
