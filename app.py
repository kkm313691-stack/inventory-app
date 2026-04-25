from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
from io import BytesIO
import uuid
import time

app = Flask(__name__)

# 🔥 메모리 저장소
shared_store = {}


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

    for col in ['상품명','로케이션','소비기한','재고수량']:
        if col not in df.columns:
            df[col] = ''

    df = df[['상품명','로케이션','소비기한','재고수량']]

    df['재고수량'] = pd.to_numeric(df['재고수량'], errors='coerce').fillna(0)

    df['실수량'] = ''
    df['차이'] = 0

    data = df.to_dict(orient='records')

    return render_template('inventory.html', data=data)


# =========================
# 일반 다운로드
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


# =====================================================
# 🔥 공유 생성 (링크 생성)
# =====================================================
@app.route('/generate_link', methods=['POST'])
def generate_link():

    data = request.get_json()

    key = str(uuid.uuid4())

    shared_store[key] = {
        "data": data,
        "time": time.time()
    }

    return jsonify({
        "link": f"/share/{key}"
    })


# =====================================================
# 🔥 공유 페이지 (다운로드 버튼 페이지)
# =====================================================
@app.route('/share/<key>')
def share_page(key):

    if key not in shared_store:
        return "공유 데이터가 없습니다."

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>재고조사 다운로드</title>
        <style>
            body {{
                font-family: Arial;
                text-align: center;
                padding: 50px;
            }}
            button {{
                font-size: 20px;
                padding: 15px;
                width: 80%;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
            }}
        </style>
    </head>
    <body>

        <h2>재고조사 파일 다운로드</h2>

        <p>아래 버튼을 눌러 엑셀 파일을 다운로드하세요</p>

        <button onclick="location.href='/download_file/{key}'">
            엑셀 다운로드
        </button>

        <script>
            // 🔥 자동 다운로드 (모바일 대응)
            setTimeout(()=>{
                window.location.href = "/download_file/{key}";
            }, 800);
        </script>

    </body>
    </html>
    """


# =====================================================
# 🔥 실제 파일 다운로드
# =====================================================
@app.route('/download_file/<key>')
def download_file(key):

    item = shared_store.get(key)

    if not item:
        return "파일이 존재하지 않습니다."

    df = pd.DataFrame(item["data"])

    df['차이'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="재고조사.xlsx"
    )


# =========================
# 실행
# =========================
if __name__ == '__main__':
    app.run()
