from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
from io import BytesIO
import re
import uuid

app = Flask(__name__)

# 🔥 공유 데이터 저장 (메모리)
shared_data_store = {}

# ===== 숫자 정리 =====
def clean_number_series(series):
    return (
        series.astype(str)
        .str.replace(r'[^0-9.-]', '', regex=True)
        .replace('', None)
    )

# ===== 날짜 =====
def clean_date_series(series):
    return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d')

# ===== 정렬 =====
def natural_sort_key(s):
    if pd.isna(s):
        return []
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', str(s))]

# ===== 컬럼 =====
def map_columns(df):
    df.columns = df.columns.str.strip()
    col_map = {}

    for col in df.columns:
        c = col.lower().replace(" ", "")

        if '코드' in c or '바코드' in c:
            continue
        elif ('상품' in c or '품명' in c):
            col_map[col] = '상품명'
        elif '로케이션' in c or '랙' in c or '위치' in c:
            col_map[col] = '로케이션'
        elif '소비' in c or '유통' in c:
            col_map[col] = '소비기한'
        elif '재고' in c:
            col_map[col] = '재고수량'

    df = df.rename(columns=col_map)
    df = df.reset_index(drop=True)

    if '상품명' not in df.columns or '로케이션' not in df.columns:
        raise Exception("상품명 / 로케이션 필수")

    return df

# ===== 메인 =====
@app.route('/')
def index():
    return render_template('upload.html')

# ===== 업로드 =====
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    df = pd.read_excel(file, dtype=str)

    df = map_columns(df)

    df = df[['상품명','로케이션','소비기한','재고수량']]

    if len(df) > 2000:
        df = df.head(2000)

    df['재고수량'] = pd.to_numeric(clean_number_series(df['재고수량']), errors='coerce').fillna(0)
    df['소비기한'] = clean_date_series(df['소비기한'])

    df['실수량'] = None
    df['차이'] = 0

    data = df.to_dict(orient='records')

    return render_template('inventory.html', data=data)

# ===== 다운로드 =====
@app.route('/download', methods=['POST'])
def download():
    df = pd.DataFrame(request.get_json())

    df['차이'] = df['실수량'].fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사결과.xlsx")

# ===== 🔥 공유 생성 =====
@app.route('/generate_link', methods=['POST'])
def generate_link():
    data = request.get_json()

    key = str(uuid.uuid4())
    shared_data_store[key] = data

    return jsonify({"link": f"/share/{key}"})

# ===== 🔥 공유 접속 =====
@app.route('/share/<key>')
def load_shared(key):
    data = shared_data_store.get(key)

    if not data:
        return "공유 데이터가 만료되었습니다."

    return render_template('inventory.html', data=data)


if __name__ == '__main__':
    app.run()
