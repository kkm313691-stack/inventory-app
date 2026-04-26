from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import pandas as pd
from io import BytesIO
import uuid
import time
import re

app = Flask(__name__)
app.secret_key = "ourbox-secret-key"

shared_store = {}

USER_ID = "김경민"
USER_PW = "ourbox"


def login_required(func):
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("id")
        pw = request.form.get("pw")

        if user == USER_ID and pw == USER_PW:
            session["login"] = True
            return redirect("/")
        else:
            return "로그인 실패"

    return """
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body{text-align:center;padding:50px;}
    input{width:80%;padding:15px;margin:10px;font-size:18px;}
    button{width:85%;padding:15px;font-size:18px;background:#4CAF50;color:white;border:none;}
    </style>
    </head>
    <body>
    <h2>재고조사 로그인</h2>
    <form method="post">
    <input name="id" placeholder="ID"><br>
    <input name="pw" type="password" placeholder="PW"><br>
    <button>로그인</button>
    </form>
    </body>
    </html>
    """


@app.route("/")
@login_required
def index():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
@login_required
def upload():

    file = request.files.get("file")

    df = pd.read_excel(file, engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()

    for col in ["상품명", "로케이션", "소비기한", "재고수량", "바코드"]:
        if col not in df.columns:
            df[col] = ""

    df = df[["상품명", "재고수량", "바코드", "로케이션", "소비기한"]]

    df["재고수량"] = pd.to_numeric(df["재고수량"], errors="coerce").fillna(0)

    df["박스수"] = ""
    df["낱개수량"] = ""
    df["실수량"] = ""
    df["차이"] = 0

    data = df.to_dict(orient="records")

    return render_template("inventory.html", data=data)


@app.route("/download", methods=["POST"])
@login_required
def download():
    df = pd.DataFrame(request.get_json())

    df["차이"] = pd.to_numeric(df["실수량"], errors="coerce").fillna(0) - df["재고수량"]

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사결과.xlsx")


@app.route("/generate_link", methods=["POST"])
@login_required
def generate_link():
    data = request.get_json()

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    key = str(uuid.uuid4())

    shared_store[key] = {
        "file": output,
        "time": time.time()
    }

    return jsonify({"link": f"/share/{key}"})


@app.route("/share/<key>")
def share(key):

    item = shared_store.get(key)

    if not item:
        return "없음"

    item["file"].seek(0)

    return send_file(item["file"], as_attachment=True, download_name="재고.xlsx")


if __name__ == "__main__":
    app.run()
