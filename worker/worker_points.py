from datetime import datetime, timedelta
from sqlalchemy import text
from models.worker_points_model import WorkerPoints  # Import WorkerPoints từ models
from models import db  # Import db từ models

def read_tracking_from_db():
    with db.engine.connect() as conn:
        # Lấy tất cả các ip_address khác NULL và không rỗng
        result = conn.execute(text("""
            SELECT DISTINCT ip_address 
            FROM wallet_points 
            WHERE ip_address IS NOT NULL 
              AND ip_address != ''
              AND ip_address != 'null'
        """))
        
        # Lấy danh sách tất cả các ip_address
        ip_addresses = [row[0] for row in result.fetchall()]
    
    return ip_addresses


def calculate_points(wallets):
    today_column = f"points_{datetime.now().strftime('%d%m')}"
    yesterday_column = f"points_{(datetime.now() - timedelta(days=1)).strftime('%d%m')}"

    # Nếu không có wallets, trả về 0 ngay lập tức
    if not wallets:
        return 0, 0

    wallets_str = ', '.join(f"'{wallet}'" for wallet in wallets)  # Chuẩn bị danh sách ví cho truy vấn SQL

    with db.engine.connect() as conn:
        # Truy vấn cho tất cả wallets
        result = conn.execute(text(f"""
            SELECT SUM(COALESCE({today_column}, 0)), SUM(COALESCE({yesterday_column}, 0)) 
            FROM wallet_points 
            WHERE wallet IN ({wallets_str})
        """))

        # Lấy tổng điểm cho ngày hôm nay và hôm qua
        today_total, yesterday_total = result.fetchone()

    return today_total or 0, yesterday_total or 0

def save_worker_points(ip_address, points_gain, pre_date, next_date):
    worker_entry = WorkerPoints(
        ip_address=ip_address,
        points_gain=points_gain,
        pre_date=pre_date,
        next_date=next_date
    )
    db.session.add(worker_entry)
    db.session.commit()

def update_worker_points_from_tracking_file(file_path):
    ip_addresses = read_tracking_from_db()
    
    if not ip_addresses:
        print("No IP addresses found")
        return

    for ip_address in ip_addresses:
        with db.engine.connect() as conn:
            # Lấy tất cả các wallet liên quan đến ip_address
            result = conn.execute(text("""
                SELECT wallet 
                FROM wallet_points 
                WHERE ip_address = :ip_address
            """), {'ip_address': ip_address})
        
            wallets = [row[0] for row in result.fetchall()]

        if not wallets:
            print(f"No wallets found for IP address {ip_address}")
            continue

        today_total, yesterday_total = calculate_points(wallets)
        points_gain = round((today_total - yesterday_total), 3)

        pre_date = (datetime.now() - timedelta(days=1)).date()
        next_date = datetime.now().date()

        # Kiểm tra xem đã tồn tại bản ghi hay chưa
        existing_entry = WorkerPoints.query.filter_by(ip_address=ip_address, pre_date=pre_date, next_date=next_date).first()

        if existing_entry:
            existing_entry.points_gain = points_gain
        else:
            save_worker_points(ip_address, points_gain, pre_date, next_date)

        # Lưu thay đổi
        db.session.commit()

