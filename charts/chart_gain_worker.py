import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import numpy as np
from datetime import datetime

def load_data(db_path):
    conn = sqlite3.connect(db_path)
    query = """
    SELECT ip_address, points_gain, pre_date, next_date
    FROM worker_points
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def process_data(df):
    # Chuyển đổi next_date thành kiểu datetime nếu chưa
    df['next_date'] = pd.to_datetime(df['next_date']).dt.date
    return df

def plot_data(df):
    # Nhóm dữ liệu theo ip_address và next_date, tính trung bình và tổng points_gain cho mỗi IP và ngày
    pivot_df = df.groupby(['ip_address', 'next_date']).agg({
        'points_gain': ['mean', 'sum']
    }).reset_index()
    pivot_df.columns = ['ip_address', 'next_date', 'avg_points_gain', 'total_points_gain']

    # Lọc ra dữ liệu của ngày hôm nay
    today = datetime.now().date()  # Sử dụng datetime để lấy ngày hôm nay
    today_data = pivot_df[pivot_df['next_date'] == today]

    # Sắp xếp today_data theo total_points_gain từ lớn đến nhỏ
    today_data = today_data.sort_values(by='total_points_gain', ascending=False)

    # Tạo một figure mới
    fig, ax = plt.subplots(figsize=(14, 8))

    # Lấy danh sách các ngày unique
    unique_dates = sorted(pivot_df['next_date'].unique())

    # Tạo color map cho biểu đồ
    colors = plt.get_cmap('tab20', len(unique_dates))  # Hoặc plasma, inferno, etc.

    # Tính tổng giá trị points_gain theo next_date
    total_points_per_date = df.groupby('next_date')['points_gain'].sum()

    # Vẽ biểu đồ cho mỗi ngày
    for idx, date_ in enumerate(unique_dates):
        # Lọc dữ liệu theo từng ngày
        daily_data = pivot_df[pivot_df['next_date'] == date_]

        # Vẽ biểu đồ cột cho từng ngày
        ax.bar(daily_data['ip_address'], daily_data['avg_points_gain'], color=colors(idx), label=f'{date_} (Tổng: {total_points_per_date[date_]})', alpha=0.7)

    # Đặt nhãn cho trục X và Y
    ax.set_xlabel('IP Address')
    ax.set_ylabel('Average Points Gain')
    ax.set_title('Average Points Gain by IP Address Across Dates')
    ax.tick_params(axis='x', rotation=90)

    # Thêm chú thích cho các ngày (giữ nguyên)
    ax.legend(title="Next Date (Tổng Points Gain)", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()

    # Trả về đối tượng figure
    return fig


def generate_chart(db_path):
    df = load_data(db_path)
    processed_df = process_data(df)
    fig = plot_data(processed_df)
    
    # Tạo buffer để lưu trữ biểu đồ dưới dạng hình ảnh
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return output.getvalue()

