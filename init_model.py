from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Cấu hình database của bạn
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///I:/AlloraPoints/allora.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from models.worker_points_model import WorkerPoints
from models.wallet_points_model import WalletPoints
# Hàm khởi tạo database và bảng
def init_db():
    with app.app_context():
        db.create_all()  # Tạo tất cả các bảng trong model
        print("Database initialized with table 'worker_points'.")

if __name__ == '__main__':
    init_db()
