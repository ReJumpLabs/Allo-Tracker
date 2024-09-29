from flask_sqlalchemy import SQLAlchemy

# Khởi tạo đối tượng SQLAlchemy
db = SQLAlchemy()

# Import các models vào __init__.py để có thể sử dụng trong app.py
from .worker_points_model import WorkerPoints
from .wallet_points_model import WalletPoints
