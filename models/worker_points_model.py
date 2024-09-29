from . import db  # Import db từ __init__.py

# Định nghĩa bảng worker_points
class WorkerPoints(db.Model):
    __tablename__ = 'worker_points'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False)
    points_gain = db.Column(db.Float, nullable=False)
    pre_date = db.Column(db.Date, nullable=False)
    next_date = db.Column(db.Date, nullable=False)
