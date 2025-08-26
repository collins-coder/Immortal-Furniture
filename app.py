from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "immortal_secret_key"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="immortal_db"
        )
        return conn
    except Error as e:
        print("Database connection failed:", e)
        return None

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)",
                (name, email, message),
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("Message sent successfully!", "success")
        else:
            flash("Database connection error!", "danger")

        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/products")
def products():
    conn = get_db_connection()
    products_list = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products_list = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template("products.html", products=products_list)

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(debug=True)
