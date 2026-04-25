from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
from io import BytesIO
import re
import uuid
import time

app = Flask(__name__)

# 🔥 공유 저장소
shared_store = {}


# =========================
# 🔥 로케이션 자연 정렬 핵심 함수
# =========================
def location_sort_key(value):
    """
    A-01-01 형태를 문자 + 숫자 분리해서 정렬
    """
    if pd.isna(value):
        return []

    # 문자열 통일
    value = str(value).upper().strip()

    # A-01-01 → ['A', 1, 1]
    parts = re.split(r'(\d+)', value)

    return [int(p) if p.isdigit() else p for p in parts]


# =========================
# 업로드 페이지
# =========================
@app.route('/')
def index():
    return render_template('upload.html')


# =========================
# 업로드 처리
# =========================
@app.route('/upload', methods=['POST'])
def upload():

    file = request.files.get('file')

    if not file:
        return "파일 없음"

    df = pd.read_excel(file, engine='openpyxl', dtype=str)

    df.columns = df.columns.str.strip()

    # 필수 컬럼 보정
    for col in ['상품명', '로케이션', '소비기한', '재고수량']:
        if col not in df.columns:
            df[col] = ''

    df = df[['상품명','로케이션','소비기한','재고수량']]

    df['재고수량'] = pd.to_numeric(df['재고수량'], errors='coerce').fillna(0)

    df['실수량'] = ''
    df['차이'] = 0

    # =========================
    # 🔥 핵심: 로케이션 정렬
    # =========================
    df = df.sort_values(
        by='로케이션',
        key=lambda col: col.map(location_sort_key)
    )

    data = df.to_dict(orient='records')

    return render_template('inventory.html', data=data)


# =========================
# 다운로드
# =========================
@app.route('/download', methods=['POST'])
def download():

    df = pd.DataFrame(request.get_json())

    df['차이'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="재고조사결과.xlsx"
    )


# =========================
# 공유 생성 (엑셀 생성)
# =========================
@app.route('/generate_link', methods=['POST'])
def generate_link():

    data = request.get_json()

    df = pd.DataFrame(data)

    df['차이'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    key = str(uuid.uuid4())

    shared_store[key] = {
        "file": output,
        "time": time.time()
    }

    return jsonify({
        "link": f"/share/{key}"
    })


# =========================
# 공유 다운로드
# =========================
@app.route('/share/<key>')
def share(key):

    item = shared_store.get(key)

    if not item:
        return "공유 데이터 없음"

    item["file"].seek(0)

    return send_file(
        item["file"],
        as_attachment=True,
        download_name="재고조사.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =========================
# 실행
# =========================
if __name__ == '__main__':
    app.run()
