@app.route("/download", methods=["POST"])
@login_required()
def download():

    raw = request.get_json()

    log_rows = []

    # =========================
    # 1️⃣ 상세 로그 생성
    # =========================
    for item in raw:

        logs = item.get("logs", [])
        in_qty = int(item.get("입수량") or 1)

        for log in logs:

            box = int(log.get("박스수", 0))
            each = int(log.get("낱개수량", 0))

            if box == 0 and each == 0:
                continue

            total = (in_qty * box) + each

            row = {
                "바코드": item.get("바코드", ""),
                "상품명": item.get("상품명", ""),
                "입수량": in_qty,
                "재고수량": item.get("재고수량", 0),
                "박스수": box,
                "낱개수량": each,
                "총수량": total
            }

            if item.get("로케이션"):
                row["로케이션"] = item.get("로케이션")

            if item.get("소비기한"):
                row["소비기한"] = item.get("소비기한")

            log_rows.append(row)

    df_log = pd.DataFrame(log_rows)

    if df_log.empty:
        df_log = pd.DataFrame(columns=[
            "바코드","상품명","입수량","재고수량",
            "박스수","낱개수량","총수량"
        ])

    # 컬럼 순서
    base_cols = ["바코드","상품명","입수량","재고수량","박스수","낱개수량","총수량"]
    extra_cols = [c for c in df_log.columns if c not in base_cols]
    df_log = df_log[base_cols + extra_cols]

    # =========================
    # 2️⃣ 집계 시트 생성
    # =========================
    if not df_log.empty:

        df_sum = df_log.groupby(
            ["바코드","상품명","입수량","재고수량"],
            as_index=False
        ).agg({
            "박스수": "sum",
            "낱개수량": "sum"
        })

        df_sum["총수량"] = (df_sum["입수량"] * df_sum["박스수"]) + df_sum["낱개수량"]

    else:
        df_sum = pd.DataFrame(columns=[
            "바코드","상품명","입수량","재고수량",
            "박스수","낱개수량","총수량"
        ])

    # =========================
    # 3️⃣ 엑셀 저장
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_log.to_excel(writer, index=False, sheet_name="상세로그")
        df_sum.to_excel(writer, index=False, sheet_name="집계")

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="재고조사.xlsx"
    )
