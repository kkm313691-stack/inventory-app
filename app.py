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

    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)

    df = df.sort_values(by='랙번호')

    df['실수량'] = 0
    df['차이'] = 0

    data_df = df

    return render_template('inventory.html', data=df.to_dict(orient='records'))


@app.route('/save', methods=['POST'])
def save():
    global data_df

    results = request.json

    df = pd.DataFrame(results)

    df['차이'] = df['실수량'] - df['전산수량']

    df.to_excel(RESULT_FILE, index=False)

    return {'status': 'success'}


@app.route('/download')
def download():
    return send_file(RESULT_FILE, as_attachment=True)


if __name__ == '__main__':
    app.run()