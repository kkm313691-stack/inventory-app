from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import re

app = Flask(__name__)

# 🔥 업로드 제한 (10MB)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ===== 숫자 정리 =====
def clean_number_series(series):
    return (
        series.astype(str)
        .str.replace(r'[^0-9.-]', '', regex=True)
        .replace('', None)
    )


# ===== 날짜 정리 =====
def clean_date_series(series):
    return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d')


# ===== 자연 정렬 =====
def natural_sort_key(s):
    if pd.isna(s):
        return []
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', str(s))]


# ===== 컬럼 매핑 =====
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
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)

    if '상품명' not in df.columns or '로케이션' not in df.columns:
        raise Exception("상품명 / 로케이션 컬럼 필수")

    return df


# ===== 메인 =====
@app.route('/')
def index():
    return render_template('upload.html')


# ===== 업로드 =====
@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')

        if not file:
            return "파일 없음"

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # 🔥 빠른 읽기
        df = pd.read_excel(filepath, engine='openpyxl', dtype=str)

        # 🔥 컬럼 정리
        df = map_columns(df)

        # 🔥 필수 컬럼 생성
        for col in ['상품명','로케이션','소비기한','재고수량']:
            if col not in df.columns:
                df[col] = ''

        # 🔥 컬럼 최소화
        df = df[['상품명','로케이션','소비기한','재고수량']]

        # 🔥 데이터 제한
        if len(df) > 5000:
            df = df.head(5000)

        # 🔥 숫자 처리
        df['재고수량'] = pd.to_numeric(
            clean_number_series(df['재고수량']),
            errors='coerce'
        ).fillna(0)

        # 🔥 날짜 처리
        df['소비기한'] = clean_date_series(df['소비기한'])

        # 🔥 기본 컬럼
        df['실수량'] = None
        df['차이'] = 0

        # 🔥 정렬
        df = df.sort_values(
            by='로케이션',
            key=lambda col: col.map(natural_sort_key)
        )

        # 🔥 JSON 안정화
        data = df.where(pd.notnull(df), None).to_dict(orient='records')

        return render_template('inventory.html', data=data)

    except Exception as e:
        print("🔥 ERROR:", str(e))
        return f"업로드 오류: {str(e)}"


# ===== 다운로드 =====
@app.route('/download', methods=['POST'])
def download():
    df = pd.DataFrame(request.get_json())

    df['차이'] = df['실수량'].fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사결과.xlsx")


# ===== 링크 생성 =====
@app.route('/generate_link', methods=['POST'])
def generate_link():
    df = pd.DataFrame(request.get_json())

    filename = f"result_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    df.to_excel(filepath, index=False)

    return jsonify({"link": f"/file/{filename}"})


# ===== 파일 다운로드 =====
@app.route('/file/<filename>')
def file_download(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
