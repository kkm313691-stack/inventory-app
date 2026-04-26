from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import pandas as pd
from io import BytesIO
import uuid
import time

app = Flask(__name__)
app.secret_key = "ourbox-secret-key"

shared_store = {}

# 계정
WORKER_ID = "김경민"
WORKER_PW = "ourbox"

ADMIN_ID = "김경민"
ADMIN_PW = "ourbox123"


def login_required(role=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not session.get("login"):
                return redirect("/login")

            if role and session.get("role") != role:
                return "권한 없음"

            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        role = request.form.get("role")
        user = request.form.get("id")
        pw = request.form.get("pw")

        # 관리자
        if role == "admin" and user == ADMIN_ID and pw == ADMIN_PW:
            session["login"] = True
            session["role"] = "admin"
            return redirect("/")

        # 재고조사
        if role == "worker" and user == WORKER_ID and pw == WORKER_PW:
            session["login"] = True
            session["role"] = "worker"
            return redirect("/")

        return "로그인 실패"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required()
def index():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
@login_required()
def upload():

    file = request.files.get("file")

    df = pd.read_excel(file, engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()

    for col in ["상품명", "재고수량", "바코드", "로케이션", "소비기한"]:
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
@login_required()
def download():
    df = pd.DataFrame(request.get_json())

    df["차이"] = pd.to_numeric(df["실수량"], errors="coerce").fillna(0) - df["재고수량"]

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사.xlsx")


@app.route("/generate_link", methods=["POST"])
@login_required("admin")
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
