from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from io import BytesIO

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 메인 페이지
@app.route('/')
def index():
    return render_template('upload.html')


# 엑셀 업로드
@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')

        if not file or file.filename == '':
            return "파일을 선택해주세요."

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # 엑셀 읽기
        df = pd.read_excel(filepath)

        # 컬럼 공백 제거 (중요)
        df.columns = df.columns.str.strip()

        # 필수 컬럼 체크
        required_columns = ['랙번호', '품명', '소비기한', '전산수량']
        for col in required_columns:
            if col not in df.columns:
                return f"엑셀 컬럼 오류: '{col}' 컬럼이 없습니다."

        # 정렬
        df = df.sort_values(by='랙번호')

        # 초기값 세팅
        df['실수량'] = ''
        df['차이'] = 0

        # HTML로 데이터 전달
        return render_template('inventory.html', data=df.to_dict(orient='records'))

    except Exception as e:
        return f"업로드 오류: {str(e)}"


# 🔥 엑셀 다운로드 (파일 저장 없이 메모리 처리)
@app.route('/download', methods=['POST'])
def download():
    try:
        results = request.get_json()

        if not results:
            return "데이터가 없습니다."

        df = pd.DataFrame(results)

        # 숫자 변환 (안전 처리)
        df['실수량'] = pd.to_numeric(df['실수량'], errors='coerce').fillna(0)
        df['전산수량'] = pd.to_numeric(df['전산수량'], errors='coerce').fillna(0)

        # 차이 계산
        df['차이'] = df['실수량'] - df['전산수량']

        # 메모리 엑셀 생성
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


# 서버 실행
if __name__ == '__main__':
    app.run()
