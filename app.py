from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, abort
)
from decimal import Decimal, ROUND_HALF_UP
import uuid
import datetime

app = Flask(__name__)
app.secret_key = "replace_this_with_a_secure_random_value"

PRODUCTS = [
    {"id": 1, "name": "Classic Oak Sofa", "price": 49999.00, "description": "Comfortable 3-seater sofa crafted in solid oak with premium cushions.", "image": "sofa.jpg", "category": "Living Room"},
    {"id": 2, "name": "Mid-Century Dining Chair", "price": 7999.00, "description": "Stylish dining chair with walnut legs and upholstered seat.", "image": "chair.jpg", "category": "Dining"},
    {"id": 3, "name": "Rustic Coffee Table", "price": 14900.00, "description": "Solid wood coffee table with natural finish and storage shelf.", "image": "table.jpg", "category": "Living Room"},
    {"id": 4, "name": "Scandinavian Bed Frame", "price": 39950.00, "description": "Minimalist bed frame in pine with sturdy slats.", "image": "bed.jpg", "category": "Bedroom"},
]

ORDERS = []

def get_product(product_id):
    for p in PRODUCTS:
        if int(p["id"]) == int(product_id):
            return p
    return None

def money(v):
    return f"{Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"

def cart_items_and_total():
    cart = session.get("cart", {})  # {product_id: qty}
    items = []
    total = Decimal("0.00")
    for pid_str, qty in cart.items():
        prod = get_product(pid_str)
        if not prod:
            continue
        price = Decimal(str(prod["price"]))
        q = int(qty)
        subtotal = (price * q).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        items.append({"product": prod, "quantity": q, "subtotal": float(subtotal)})
        total += subtotal
    return items, float(total)

@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    count = sum(cart.values()) if cart else 0
    return {"cart_count": count}

# ------------------------
# Routes
# ------------------------
@app.route("/")
def index():
    featured = PRODUCTS[:3]
    return render_template("index.html", featured=featured)

@app.route("/products")
def products():
    return render_template("products.html", products=PRODUCTS)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    prod = get_product(product_id)
    if not prod:
        abort(404)
    return render_template("product_detail.html", product=prod)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = request.form.get("product_id")
    qty = request.form.get("quantity", 1)
    try:
        qty = max(1, int(qty))
    except ValueError:
        qty = 1

    prod = get_product(product_id)
    if not prod:
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    cart = session.get("cart", {})
    cart_key = str(prod["id"])
    cart[cart_key] = cart.get(cart_key, 0) + qty
    session["cart"] = cart
    session.modified = True
    flash(f'Added {qty} x {prod["name"]} to cart.', "success")
    next_url = request.form.get("next") or url_for("cart")
    return redirect(next_url)

@app.route("/update_cart", methods=["POST"])
def update_cart():
    cart = session.get("cart", {})
    for key, val in request.form.items():
        if key.startswith("qty-"):
            pid = key.split("-", 1)[1]
            try:
                q = int(val)
            except ValueError:
                q = 0
            if q <= 0:
                cart.pop(pid, None)
            else:
                cart[pid] = q
    session["cart"] = cart
    session.modified = True
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))

@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session.modified = True
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))

@app.route("/clear_cart")
def clear_cart():
    session.pop("cart", None)
    session.modified = True
    flash("Cart cleared.", "info")
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    items, total = cart_items_and_total()
    return render_template("cart.html", items=items, total=total, money=money)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_items_and_total()
    if not items:
        flash("Your cart is empty. Add items before checkout.", "warning")
        return redirect(url_for("products"))

    if request.method == "POST":
        street = request.form.get("street", "").strip()
        house_number = request.form.get("house_number", "").strip()
        city = request.form.get("city", "").strip()
        if not (street and house_number and city):
            flash("Please fill street, house number and city.", "danger")
            return render_template("checkout.html", items=items, total=total, money=money)

        payment_method = request.form.get("payment_method")
        payment_info = {}

        if payment_method == "mpesa":
            mpesa_number = request.form.get("mpesa_number", "").strip()
            if not mpesa_number:
                flash("Please enter your M-Pesa number.", "danger")
                return render_template("checkout.html", items=items, total=total, money=money)
            payment_info["mpesa_number"] = mpesa_number

        elif payment_method == "credit_card":
            card_number = request.form.get("card_number", "").strip()
            expiry_date = request.form.get("expiry_date", "").strip()
            cvv = request.form.get("cvv", "").strip()
            if not (card_number and expiry_date and cvv):
                flash("Please fill all credit card details.", "danger")
                return render_template("checkout.html", items=items, total=total, money=money)
            payment_info.update({"card_number": card_number, "expiry_date": expiry_date})

        elif payment_method == "cash":
            pass
        else:
            flash("Please select a payment method.", "danger")
            return render_template("checkout.html", items=items, total=total, money=money)

        order_id = str(uuid.uuid4()).split("-")[0].upper()
        order = {
            "id": order_id,
            "items": items,
            "total": total,
            "address": {"street": street, "house_number": house_number, "city": city},
            "payment_method": payment_method,
            "payment_info": payment_info,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        ORDERS.append(order)

        session.pop("cart", None)
        session.modified = True

        flash("Order placed successfully.", "success")
        return redirect(url_for("order_confirmation", order_id=order_id))

    return render_template("checkout.html", items=items, total=total, money=money)

@app.route("/order/<order_id>")
def order_confirmation(order_id):
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        abort(404)
    return render_template("order_confirmation.html", order=order, money=money)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not (name and email and message):
            flash("Please fill all fields.", "danger")
            return render_template("contact.html")
    
        print(f"[Contact] {name} <{email}>: {message}")
        flash("Thanks — message received. We'll contact you soon.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(debug=True)
