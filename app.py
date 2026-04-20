from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FILE = 'result.xlsx'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

data_df = None

@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    global data_df

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

        data_df = df

        return render_template('inventory.html', data=df.to_dict(orient='records'))

    except Exception as e:
        return f"에러 발생: {str(e)}"


@app.route('/save', methods=['POST'])
def save():
    try:
        results = request.json
        df = pd.DataFrame(results)

        df['차이'] = df['실수량'] - df['전산수량']
        df.to_excel(RESULT_FILE, index=False)

        return {'status': 'success'}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.route('/download')
def download():
    return send_file(RESULT_FILE, as_attachment=True)


if __name__ == '__main__':
    app.run()
