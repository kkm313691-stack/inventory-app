from flask import Flask, render_template, request, send_file, jsonify, redirect, session
import pandas as pd
from io import BytesIO
import uuid
import time

app = Flask(__name__)
app.secret_key = "ourbox-secret-key"

# 계정
WORKER_ID = "김경민"
WORKER_PW = "ourbox"

ADMIN_ID = "김경민"
ADMIN_PW = "ourbox123"

# 데이터
current_data = []
shared_store = {}


# =========================
# 로그인 체크
# =========================
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


# =========================
# 로그인
# =========================
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


# =========================
# 페이지
# =========================
@app.route("/")
@login_required("worker")
def index():
    return render_template("upload.html")


@app.route("/admin")
@login_required("admin")
def admin_page():
    return render_template("admin.html")


# =========================
# 업로드
# =========================
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


# =========================
# 실시간 저장
# =========================
@app.route("/sync", methods=["POST"])
@login_required("worker")
def sync():
    global current_data
    current_data = request.get_json()
    return "ok"


# =========================
# 다운로드
# =========================
@app.route("/download", methods=["POST"])
@login_required()
def download():
    df = pd.DataFrame(request.get_json())
    df["차이"] = df["실수량"] - df["재고수량"]

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="재고조사.xlsx")


# =========================
# 공유 생성 (30분)
# =========================
@app.route("/generate_link", methods=["POST"])
@login_required()
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


# =========================
# 공유 다운로드 (만료 체크)
# =========================
@app.route("/share/<key>")
def share(key):

    item = shared_store.get(key)

    if not item:
        return "링크 없음"

    # 30분 = 1800초
    if time.time() - item["time"] > 1800:
        del shared_store[key]
        return "링크 만료"

    item["file"].seek(0)

    return send_file(
        item["file"],
        as_attachment=True,
        download_name="재고공유.xlsx"
    )


# =========================
# 관리자 재고 조회
# =========================
@app.route("/current_data")
@login_required("admin")
def current_data_view():
    return jsonify(current_data)


# =========================
# 관리자 다운로드 + 초기화
# =========================
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

    return send_file(output, as_attachment=True, download_name="최종.xlsx")


# =========================
# 공유 목록 (관리자)
# =========================
@app.route("/shared_list")
@login_required("admin")
def shared_list():

    now = time.time()
    result = []

    for key, item in list(shared_store.items()):

        remain = 1800 - (now - item["time"])

        if remain <= 0:
            del shared_store[key]
            continue

        result.append({
            "key": key,
            "remain": int(remain)
        })

    return jsonify(result)


# =========================
# 공유 삭제 (관리자)
# =========================
@app.route("/delete_share/<key>", methods=["POST"])
@login_required("admin")
def delete_share(key):

    if key in shared_store:
        del shared_store[key]

    return "ok"


# =========================
# 실행
# =========================
if __name__ == "__main__":
    app.run()
