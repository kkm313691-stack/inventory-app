from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def clean_number_series(series):
    return (
        series.astype(str)
        .str.replace(r'[^0-9.-]', '', regex=True)
        .replace('', None)
    )


def clean_date_series(series):
    return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d')


def natural_sort_key(s):
    if pd.isna(s):
        return []
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', str(s))]


def map_columns(df):
    df.columns = df.columns.str.strip()

    col_map = {}

    for col in df.columns:
        c = col.lower().replace(" ", "")

        if '코드' in c or '바코드' in c:
            continue
        elif '상품' in c or '품명' in c:
            col_map[col] = '상품명'
        elif '로케이션' in c or '랙' in c or '위치' in c:
            col_map[col] = '로케이션'
        elif '소비' in c or '유통' in c:
            col_map[col] = '소비기한'
        elif '재고수량' in c:
            col_map[col] = '재고수량'
        elif '실수량' in c:
            col_map[col] = '실수량'
        elif '차이' in c:
            col_map[col] = '차이'
        elif '입수' in c:
            col_map[col] = '입수'

    df = df.rename(columns=col_map)

    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)

    required = ['상품명', '로케이션']
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

        if not file:
            return "파일 없음"

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)
        df = map_columns(df)

        # 재고수량
        if '재고수량' in df.columns:
            df['재고수량'] = pd.to_numeric(clean_number_series(df['재고수량']), errors='coerce').fillna(0)
        else:
            df['재고수량'] = 0

        # 소비기한
        if '소비기한' in df.columns:
            df['소비기한'] = clean_date_series(df['소비기한'])
        else:
            df['소비기한'] = ''

        # 🔥 이어하기 핵심
        if '실수량' in df.columns:
            df['실수량'] = pd.to_numeric(clean_number_series(df['실수량']), errors='coerce')
        else:
            df['실수량'] = None

        # 차이 재계산
        df['차이'] = df['실수량'].fillna(0) - df['재고수량']

        # 정렬
        if '로케이션' in df.columns:
            df = df.sort_values(
                by='로케이션',
                key=lambda col: col.map(natural_sort_key)
            )

        return render_template('inventory.html', data=df.to_dict(orient='records'))

    except Exception as e:
        return f"오류: {str(e)}"


@app.route('/download', methods=['POST'])
def download():
    df = pd.DataFrame(request.get_json())
    df['차이'] = df['실수량'].fillna(0) - df['재고수량']

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사결과.xlsx")


@app.route('/generate_link', methods=['POST'])
def generate_link():
    df = pd.DataFrame(request.get_json())

    filename = f"result_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    df.to_excel(filepath, index=False)

    return jsonify({"link": f"/file/{filename}"})


@app.route('/file/<filename>')
def file_download(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
