from flask import Flask, render_template, request, redirect, session
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "secret"

TOWNS = [
    "未選択",
    "パサパサこうやの街",
    "ゴツゴツやまの街",
    "ドンヨリうみべの街",
    "キラキラうきしまの街",
    "まっさらな街"
]

def get_db():
    conn = sqlite3.connect("pokemon.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS pokemon_master (
        id INTEGER PRIMARY KEY,
        name TEXT,
        skill1 TEXT,
        skill2 TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_pokemon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pokemon_id INTEGER,
        town TEXT
    )
    """)

    count = conn.execute("SELECT COUNT(*) FROM pokemon_master").fetchone()[0]
    if count == 0:
        for i in range(1, 308):
            conn.execute(
                "INSERT INTO pokemon_master VALUES (?, ?, ?, ?)",
                (i, f"ポケモン{i}", "すばやさ", "ちから")
            )

    conn.commit()
    conn.close()

# バリデーション関数追加
def is_valid(text):
    return re.match(r'^[a-zA-Z0-9]{4,10}$', text)

# ---------------- ログイン ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        # ★ バリデーション追加
        if not is_valid(user) or not is_valid(pw):
            error = "半角英数字4文字から10文字で入力してください"
            return render_template("login.html", error=error)

        conn = get_db()
        u = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (user, pw)
        ).fetchone()

        if u:
            session["user_id"] = u["id"]
            return redirect("/manage")
        else:
            error = "ユーザー名またはパスワードが違います"

    return render_template("login.html", error=error)

# ---------------- 管理画面 ----------------
@app.route("/manage", methods=["GET", "POST"])
def manage():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]
    conn = get_db()

    # 検索
    result = None
    if request.method == "POST":
        name = request.form["name"]
        result = conn.execute(
            "SELECT * FROM pokemon_master WHERE name LIKE ?",
            (f"%{name}%",)
        ).fetchone()

    # 一覧（街 + 出現有無）
    all_pokemon = conn.execute("""
    SELECT pm.id, pm.name, pm.skill1, pm.skill2,
       up.town,
       IFNULL(up.is_active, 0) as is_active
    FROM pokemon_master pm
    LEFT JOIN user_pokemon up
    ON pm.id = up.pokemon_id AND up.user_id=?
    """, (user_id,)).fetchall()

    # 街ごとのカウント
    data = conn.execute("""
    SELECT town, COUNT(*) as cnt
    FROM user_pokemon
    WHERE user_id=?
    GROUP BY town
    """, (user_id,)).fetchall()

    counts = {t: 0 for t in TOWNS}
    for d in data:
        counts[d["town"]] = d["cnt"]

    conn.close()

    return render_template(
        "manage.html",
        result=result,
        towns=TOWNS,
        all_pokemon=all_pokemon,
        counts=counts
    )

# 保存
@app.route("/bulk_update", methods=["POST"])
def bulk_update():
    user_id = session["user_id"]
    conn = get_db()

    for key in request.form:
        if key.startswith("town_"):
            pokemon_id = key.split("_")[1]
            town = request.form.get(f"town_{pokemon_id}")
            is_active = request.form.get(f"active_{pokemon_id}", "0")

            exists = conn.execute(
                "SELECT * FROM user_pokemon WHERE user_id=? AND pokemon_id=?",
                (user_id, pokemon_id)
            ).fetchone()

            if exists:
                conn.execute("""
                UPDATE user_pokemon
                SET town=?, is_active=?
                WHERE id=?
                """, (town, is_active, exists["id"]))
            else:
                conn.execute("""
                INSERT INTO user_pokemon(user_id,pokemon_id,town,is_active)
                VALUES (?,?,?,?)
                """, (user_id, pokemon_id, town, is_active))

    conn.commit()
    conn.close()

    return redirect("/manage")

# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# register
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        # ★ バリデーション追加
        if not is_valid(user) or not is_valid(pw):
            error = "半角英数字4文字から10文字で入力してください"
            return render_template("register.html", error=error)

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(username, password) VALUES (?, ?)",
                (user, pw)
            )
            conn.commit()
        except:
            error = "ユーザー名は既に存在します"
            return render_template("register.html", error=error)
        finally:
            conn.close()

        return redirect("/")

    return render_template("register.html", error=error)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)