from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']

        if file.filename == '':
            return "파일이 없습니다."

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)

        # 컬럼 공백 제거
        df.columns = df.columns.str.strip()

        # 필수 컬럼 체크
        required_columns = ['랙번호', '품명', '소비기한', '전산수량']
        for col in required_columns:
            if col not in df.columns:
                return f"엑셀 컬럼 오류: '{col}' 컬럼이 없습니다."

        # 정렬
        df = df.sort_values(by='랙번호')

        df['실수량'] = 0
        df['차이'] = 0

        return render_template('inventory.html', data=df.to_dict(orient='records'))

    except Exception as e:
        return f"에러 발생: {str(e)}"


# 🔥 파일 저장 없이 바로 엑셀 다운로드
@app.route('/download', methods=['POST'])
def download():
    try:
        results = request.json
        df = pd.DataFrame(results)

        df['차이'] = df['실수량'] - df['전산수량']

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
