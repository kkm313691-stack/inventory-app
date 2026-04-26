from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import pandas as pd
from io import BytesIO
import uuid
import time

app = Flask(__name__)
app.secret_key = "ourbox-secret-key"

WORKER_ID = "김경민"
WORKER_PW = "ourbox"

ADMIN_ID = "김경민"
ADMIN_PW = "ourbox123"

current_data = []


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

        if role == "admin" and user == ADMIN_ID and pw == ADMIN_PW:
            session["login"] = True
            session["role"] = "admin"
            return redirect("/admin")

        if role == "worker" and user == WORKER_ID and pw == WORKER_PW:
            session["login"] = True
            session["role"] = "worker"
            return redirect("/")

        return "로그인 실패"

    return render_template("login.html")


@app.route("/")
@login_required("worker")
def index():
    return render_template("upload.html")


@app.route("/admin")
@login_required("admin")
def admin_page():
    return render_template("admin.html")


@app.route("/upload", methods=["POST"])
@login_required("worker")
def upload():
    global current_data

    file = request.files.get("file")

    df = pd.read_excel(file, engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()

    for col in ["상품명", "재고수량", "바코드", "로케이션", "소비기한"]:
        if col not in df.columns:
            df[col] = ""

    df = df[["상품명", "재고수량", "바코드", "로케이션", "소비기한"]]

    df["재고수량"] = pd.to_numeric(df["재고수량"], errors="coerce").fillna(0)

    df["박스수"] = 0
    df["낱개수량"] = 0
    df["실수량"] = 0
    df["차이"] = 0

    current_data = df.to_dict(orient="records")

    return render_template("inventory.html", data=current_data)


@app.route("/sync", methods=["POST"])
@login_required("worker")
def sync():
    global current_data
    current_data = request.get_json()
    return "ok"


@app.route("/current_data")
@login_required("admin")
def current_data_view():
    return jsonify(current_data)


@app.route("/admin_download", methods=["POST"])
@login_required("admin")
def admin_download():
    global current_data

    df = pd.DataFrame(current_data)
    df["차이"] = df["실수량"] - df["재고수량"]

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    current_data = []

    return send_file(output, as_attachment=True, download_name="재고조사_최종.xlsx")


if __name__ == "__main__":
    app.run()
