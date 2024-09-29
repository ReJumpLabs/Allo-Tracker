from . import db  # Import db từ __init__.py

# Định nghĩa bảng wallet_points
class WalletPoints(db.Model):
    __tablename__ = 'wallet_points'

    wallet = db.Column(db.String(100), primary_key=True)
    points_total = db.Column(db.Float, nullable=False, default=0.0)
    ip_address = db.Column(db.String(50), nullable=False)
    mnemonics = db.Column(db.String(200), nullable=False)

    # Các cột khác liên quan đến points...
