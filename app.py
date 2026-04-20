from flask import Flask, render_template, request, send_file, session
import pandas as pd
import os
from io import BytesIO
import uuid

app = Flask(__name__)
app.secret_key = 'secret-key'  # 세션용

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 👉 컬럼 자동 매핑 함수
def map_columns(df):
    df.columns = df.columns.str.strip()

    col_map = {}

    for col in df.columns:
        c = col.lower()

        if '상품' in c or '품명' in c:
            col_map[col] = '상품명'

        elif '로케이션' in c or '랙' in c or '위치' in c:
            col_map[col] = '로케이션'

        elif '소비' in c or '유통' in c:
            col_map[col] = '소비기한'

        elif '재고' in c or '전산' in c or '수량' in c:
            col_map[col] = '재고수량'

    df = df.rename(columns=col_map)

    required = ['상품명', '로케이션', '소비기한', '재고수량']

    for r in required:
        if r not in df.columns:
            raise Exception(f"필수 컬럼 없음: {r}")

    return df


# 메인
@app.route('/')
def index():
    return render_template('upload.html')


# 업로드
@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')

        if not file or file.filename == '':
            return "파일을 선택해주세요."

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)

        # 🔥 컬럼 자동 매핑
        df = map_columns(df)

        # 정렬
        df = df.sort_values(by='로케이션')

        # 초기값
        df['실수량'] = ''
        df['차이'] = 0

        # 👉 세션에 저장 (사용자별)
        session['data'] = df.to_dict(orient='records')

        return render_template('inventory.html', data=session['data'])

    except Exception as e:
        return f"업로드 오류: {str(e)}"


# 다운로드 (동시 사용자 대응)
@app.route('/download', methods=['POST'])
def download():
    try:
        results = request.get_json()

        df = pd.DataFrame(results)

        df['실수량'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0)
        df['재고수량'] = pd.to_numeric(df['재고수량'], errors='coerce').fillna(0)

        df['차이'] = df['실수량'] - df['재고수량']

        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="재고조사결과.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return f"다운로드 오류: {str(e)}"


if __name__ == '__main__':
    app.run()
