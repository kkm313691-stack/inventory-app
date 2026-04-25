from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
from io import BytesIO
import uuid

app = Flask(__name__)

# 🔥 메모리 저장소 (엑셀 파일 보관)
shared_store = {}


# =========================
# 🔥 업로드 페이지
# =========================
@app.route('/')
def index():
    return render_template('upload.html')


# =========================
# 🔥 업로드 처리
# =========================
@app.route('/upload', methods=['POST'])
def upload():

    file = request.files.get('file')

    if not file:
        return "파일 없음"

    df = pd.read_excel(file, engine='openpyxl', dtype=str)

    # 기본 컬럼 정리
    df.columns = df.columns.str.strip()

    # 필요한 컬럼만 사용 (없으면 생성)
    for col in ['상품명', '로케이션', '소비기한', '재고수량']:
        if col not in df.columns:
            df[col] = ''

    df = df[['상품명', '로케이션', '소비기한', '재고수량']]

    df['재고수량'] = pd.to_numeric(df['재고수량'], errors='coerce').fillna(0)

    df['실수량'] = ''
    df['차이'] = 0

    data = df.to_dict(orient='records')

    return render_template('inventory.html', data=data)


# =========================
# 🔥 엑셀 다운로드 (일반)
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
# 🔥 공유 생성 (엑셀 생성 + 메모리 저장)
# =========================
@app.route('/generate_link', methods=['POST'])
def generate_link():

    data = request.get_json()

    df = pd.DataFrame(data)

    # 🔥 차이 계산
    if '실수량' in df.columns:
        df['실수량'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0)
    else:
        df['실수량'] = 0

    if '재고수량' in df.columns:
        df['재고수량'] = pd.to_numeric(df['재고수량'], errors='coerce').fillna(0)
    else:
        df['재고수량'] = 0

    df['차이'] = df['실수량'] - df['재고수량']

    # 🔥 엑셀 메모리 생성
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    key = str(uuid.uuid4())

    shared_store[key] = output

    return jsonify({
        "link": f"/share/{key}"
    })


# =========================
# 🔥 공유 다운로드 링크
# =========================
@app.route('/share/<key>')
def share(key):

    file = shared_store.get(key)

    if not file:
        return "공유 데이터가 존재하지 않습니다."

    file.seek(0)

    return send_file(
        file,
        as_attachment=True,
        download_name="재고조사공유.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =========================
# 🔥 실행
# =========================
if __name__ == '__main__':
    app.run()
