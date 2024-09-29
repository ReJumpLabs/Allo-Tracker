from flask import Flask, render_template, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from colorama import Fore, Style
from flask_paginate import Pagination, get_page_args
from models import db  # Import đối tượng db từ models/__init__.py
from models.worker_points_model import WorkerPoints  # Import model WorkerPoints từ models
from worker.worker_points import update_worker_points_from_tracking_file
from models.wallet_points_model import WalletPoints  # Import model WorkerPoints từ models
from charts.chart_gain_worker import generate_chart

app = Flask(__name__)

# Cấu hình đường dẫn đến SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///I:/AlloraPoints/allora.db?timeout=30'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 100,
    'max_overflow': 20,
    'pool_timeout': 300,
    'connect_args': {'timeout': 30}
}
db.init_app(app)

            
# Hàm kiểm tra cột có tồn tại hay không
def column_exists(column_name):
    with db.engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info(wallet_points)")).fetchall()
        return any(col[1] == column_name for col in result)

# Hàm lấy tất cả các cột 'points_' có trong database
def get_existing_point_columns():
    with db.engine.connect() as conn:
        columns_query = conn.execute(text("PRAGMA table_info(wallet_points)")).fetchall()
    # Lọc các cột bắt đầu bằng 'points_' để lấy các cột tương ứng với các ngày
    point_columns = [col[1] for col in columns_query if col[1].startswith('points_')]
    return point_columns

# Hàm cập nhật hoặc thêm mới cột points theo ngày
def update_or_add_column(wallet, points):
    with app.app_context():
        today_column = f"points_{datetime.now().strftime('%d%m')}"  # Định dạng ngày cho hôm nay

        # Sử dụng một kết nối duy nhất cho toàn bộ hàm
        with db.engine.connect() as conn:
            # Kiểm tra nếu cột hôm nay không tồn tại, thì tạo mới cột
            if not column_exists(today_column):
                conn.execute(text(f'ALTER TABLE wallet_points ADD COLUMN {today_column} FLOAT DEFAULT 0.0'))

            # Lấy tất cả các cột ngày 'points_' hiện có trong database
            point_columns = get_existing_point_columns()

            # Lấy thông tin của ví từ cơ sở dữ liệu
            wallet_entry = WalletPoints.query.filter_by(wallet=wallet).first()

            if wallet_entry:
                # Kiểm tra và cập nhật điểm cho tất cả các ngày trước đó nếu giá trị bằng 0
                for col in point_columns:
                    if col < today_column:  # Chỉ kiểm tra các cột ngày trước đó
                        previous_value = conn.execute(
                            text(f"SELECT {col} FROM wallet_points WHERE wallet = :wallet"), 
                            {'wallet': wallet}
                        ).fetchone()

                        if previous_value and previous_value[0] == 0:
                            # Cập nhật điểm của ngày trước đó bằng điểm của hôm nay nếu giá trị bằng 0
                            conn.execute(
                                text(f"UPDATE wallet_points SET {col} = :points WHERE wallet = :wallet"),
                                {'points': points, 'wallet': wallet}
                            )

                # Cập nhật điểm cho cột ngày hôm nay
                conn.execute(
                    text(f"UPDATE wallet_points SET {today_column} = :points WHERE wallet = :wallet"),
                    {'points': points, 'wallet': wallet}
                )
            else:
                # Nếu ví chưa tồn tại, thêm mới ví
                new_wallet = WalletPoints(wallet=wallet, points_total=points)
                db.session.add(new_wallet)
                db.session.commit()

                # Cập nhật điểm cho ngày hôm nay
                conn.execute(
                    text(f"UPDATE wallet_points SET {today_column} = :points WHERE wallet = :wallet"),
                    {'points': points, 'wallet': wallet}
                )

            # Hàm tính lại tổng số điểm
            recalculate_points_total(wallet_entry if wallet_entry else new_wallet)

            # Commit lại sau khi tất cả các thay đổi đã được thực hiện
            conn.commit()
            
            
# Hàm tính toán lại points_total từ các cột points_{ngày}
def recalculate_points_total(wallet_entry):
    total_points = 0.0
    for col in WalletPoints.__table__.columns:
        if col.name.startswith('points_'):
            total_points += getattr(wallet_entry, col.name) or 0.0
    wallet_entry.points_total = total_points

# API cập nhật hoặc thêm mới wallet và điểm

@app.route('/update_wallet', methods=['POST'])
def update_wallet(data):
    # Không cần lấy data từ request, data đã được truyền từ hàm post_data
    if 'wallet' not in data or 'points' not in data:
        return {"error": "wallet and points are required"}, 400

    wallet = data.get('wallet')
    points = data.get('points')
    
    if not wallet or points is None or points == 0.0 or points == 0:
        return {"error": "Invalid input"}, 400

    # Giả sử bạn có hàm update_or_add_column để xử lý việc cập nhật
    update_or_add_column(wallet, points)

    # In ra console với màu cho log
    print(Fore.GREEN + f"Wallet {wallet} updated successfully" + Style.RESET_ALL)

    # Trả về chỉ mã trạng thái 200 mà không có nội dung
    return '', 200

# Tạo filter cho Jinja2 để sử dụng getattr
@app.template_filter('getattr')
def getattr_filter(obj, attr):
    return getattr(obj, attr, 0)


# Hàm lấy danh sách các cột 'points_'
def get_columns():
    with db.engine.connect() as conn:
        columns_query = conn.execute(text("PRAGMA table_info(wallet_points)")).fetchall()
    columns = [col[1] for col in columns_query if col[1].startswith('points_')]
    return columns

# Hàm tính tổng cho các cột 'points_'
def calculate_column_sums(columns):
    sums = {col: 0 for col in columns}
    with db.engine.connect() as conn:
        for col in columns:
            total_query = text(f"SELECT SUM({col}) FROM wallet_points")
            result = conn.execute(total_query).fetchone()
            if result is not None and result[0] is not None:
                sums[col] = round(result[0] + 2647.506, 3)  # Thêm giá trị 2647.506 như yêu cầu
            else:
                sums[col] = 0
    return sums

# Hàm lấy dữ liệu 'wallets' với sắp xếp, phân trang, và tìm kiếm
def get_filtered_wallets(search_wallet, sort_by, order, offset, per_page, columns):
    query = WalletPoints.query

    # Áp dụng tìm kiếm theo wallet nếu có
    if search_wallet:
        query = query.filter(WalletPoints.wallet.ilike(f"%{search_wallet}%"))

    # Kiểm tra nếu cột sắp xếp là cột động (dạng text) thì dùng text() của SQLAlchemy
    if sort_by in columns or sort_by == 'wallet':
        sort_column = text(sort_by)
    else:
        sort_column = 'wallet'

    # Sắp xếp và phân trang
    if order == 'asc':
        wallets = query.order_by(db.asc(sort_column)).offset(offset).limit(per_page).all()
    else:
        wallets = query.order_by(db.desc(sort_column)).offset(offset).limit(per_page).all()

    total_wallets = query.count()  # Tổng số wallets sau khi tìm kiếm và sắp xếp

    return wallets, total_wallets

# Hàm lấy dữ liệu của từng ví (wallet)
def get_wallet_data(wallets, columns):
    results = []
    for wallet in wallets:
        wallet_data = {'wallet': wallet.wallet}
        with db.engine.connect() as conn:
            for col in columns:
                query = text(f"SELECT {col} FROM wallet_points WHERE wallet = :wallet")
                result = conn.execute(query, {'wallet': wallet.wallet}).fetchone()
                wallet_data[col] = result[0] if result else 0  # Gán giá trị mặc định là 0 nếu không có dữ liệu
        results.append(wallet_data)
    return results

# Hàm format lại tên cột
def format_column_names(columns):
    return [(col, format_column_name(col)) for col in columns]

# Hàm format tên cột thành dạng mong muốn
def format_column_name(col_name):
    if col_name == 'points_total':
        return 'Points first time'
    elif col_name.startswith('points_'):
        date_part = col_name.split('_')[1]
        return f'Points {date_part[:2]}T{date_part[2:]}'
    return col_name

def get_total_points():
    """
    Lấy tổng points_gain theo danh sách IP cho ngày hôm nay từ bảng worker_points
    """
    # Lấy ngày hôm nay và chuyển sang định dạng chuỗi YYYY-MM-DD
    today = datetime.now().strftime('%Y-%m-%d')

    query = """
    SELECT ip_address, SUM(points_gain) as total_points
    FROM worker_points
    WHERE next_date = :today
    GROUP BY ip_address
    ORDER BY total_points DESC
    """

    # Kết nối đến database và thực hiện query, truyền giá trị 'today' vào
    with db.engine.connect() as conn:
        result = conn.execute(text(query), {'today': today})
        # Chuyển kết quả thành danh sách các dictionary {ip_address: ..., total_points: ...}
        points_data = [{"ip_address": row[0], "total_points": row[1]} for row in result]
    
    return points_data

# Hàm chính xử lý view wallets với tìm kiếm
@app.route('/view_wallets', methods=['GET'])
def view_wallets():
    # Lấy thông tin tìm kiếm và phân trang từ request
    search_wallet = request.args.get('search_wallet', '')  # Lấy từ khóa tìm kiếm
    sort_by = request.args.get('sort_by', 'wallet')
    order = request.args.get('order', 'asc')
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page', per_page=50)
    
    total_points = get_total_points()
    # Lấy danh sách cột 'points_'
    columns = get_columns()

    # Lấy danh sách wallets sau khi tìm kiếm và phân trang
    wallets, total_wallets = get_filtered_wallets(search_wallet, sort_by, order, offset, per_page, columns)

    # Tính tổng cho các cột 'points_'
    sums = calculate_column_sums(columns)

    # Lấy dữ liệu từng ví
    results = get_wallet_data(wallets, columns)

    # Format lại tên cột để hiển thị
    formatted_columns = format_column_names(columns)

    # Tạo đối tượng phân trang
    pagination = Pagination(page=page, per_page=per_page, total=total_wallets, css_framework='bootstrap4')

    return render_template('wallets.html', wallets=results, columns=formatted_columns, sums=sums, sort_by=sort_by, order=order, pagination=pagination, search_wallet=search_wallet, total_points=total_points)

@app.route('/track_wallets', methods=['POST'])
def track_wallets():
    # Đường dẫn tới file tracking.txt (bạn có thể thay đổi theo yêu cầu)
    file_path = 'tracking.txt'

    # Gọi hàm để cập nhật điểm từ file
    update_worker_points_from_tracking_file(file_path)
    
    # Trả về chỉ mã trạng thái 200 mà không có nội dung
    return '', 200
    
@app.route('/chart')
def show_chart():
    # Tạo biểu đồ và nhận dữ liệu hình ảnh từ canvas
    chart_data = generate_chart('allora.db')

    # Trả về dữ liệu hình ảnh dưới dạng nội dung image/png
    response = make_response(chart_data)
    response.headers['Content-Type'] = 'image/png'
    return response

if __name__ == '__main__':
    
    app.run(debug=True)
