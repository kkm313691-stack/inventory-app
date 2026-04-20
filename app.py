from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 🔥 컬럼 자동 매핑 (재고수량은 정확히 일치만 허용)
def map_columns(df):
    df.columns = df.columns.str.strip()

    col_map = {}

    for col in df.columns:
        c = col.lower().replace(" ", "")

        # 상품명
        if '상품' in c or '품명' in c:
            col_map[col] = '상품명'

        # 로케이션
        elif '로케이션' in c or '랙' in c or '위치' in c:
            col_map[col] = '로케이션'

        # 소비기한
        elif '소비' in c or '유통' in c:
            col_map[col] = '소비기한'

        # 🔥 재고수량 (정확히 일치할 때만)
        elif c == '재고수량':
            col_map[col] = '재고수량'

    df = df.rename(columns=col_map)

    # 필수 컬럼 체크
    required = ['상품명', '로케이션', '소비기한', '재고수량']

    for r in required:
        if r not in df.columns:
            raise Exception(f"필수 컬럼 없음: {r}")

    return df


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')

        if not file or file.filename == '':
            return "파일을 선택해주세요."

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)

        # 🔥 컬럼 매핑 적용
        df = map_columns(df)

        # 로케이션 순 정렬
        df = df.sort_values(by='로케이션')

        # 초기값
        df['실수량'] = ''
        df['차이'] = 0

        return render_template('inventory.html', data=df.to_dict(orient='records'))

    except Exception as e:
        return f"업로드 오류: {str(e)}"


# 🔥 엑셀 다운로드 (메모리 처리)
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
