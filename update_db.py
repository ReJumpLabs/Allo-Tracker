import sqlite3
from models import db  # Import db từ models

# Hàm đọc dữ liệu từ tệp txt và phân tích cú pháp
def read_data_from_txt(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            # Loại bỏ khoảng trắng và phân tách theo dấu |
            line = line.strip()
            if line:
                ip_address, wallet, mnemonics = line.split('|')
                data.append((ip_address, wallet, mnemonics))
    return data

# Kết nối đến cơ sở dữ liệu SQLite
conn = sqlite3.connect('allora.db')
cursor = conn.cursor()

# Đọc dữ liệu từ file txt
data = read_data_from_txt('data.txt')

batch_size = 1000  # Chia thành lô 1000 dòng một
for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]

    # Cập nhật nếu wallet đã tồn tại
    update_query = """
        UPDATE wallet_points 
        SET ip_address = ?, mnemonics = ?
        WHERE wallet = ?;
    """
    cursor.executemany(update_query, [(ip, mnemonic, wallet) for ip, wallet, mnemonic in batch])

    # Chèn dữ liệu mới nếu wallet không tồn tại và points_total > 0.0
    insert_query = """
        INSERT INTO wallet_points (ip_address, wallet, mnemonics)
        SELECT ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM wallet_points WHERE wallet = ?)
          AND (SELECT points_total FROM wallet_points WHERE wallet = ?) > 0.0;
    """
    cursor.executemany(insert_query, [(ip, wallet, mnemonic, wallet, wallet) for ip, wallet, mnemonic in batch])

    # Commit sau mỗi lô
    conn.commit()

# Đóng kết nối cơ sở dữ liệu
conn.close()
