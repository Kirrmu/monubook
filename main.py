from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
from contextlib import closing
import os
import re
import qrcode
import qrcode.image.svg
import base64
from io import BytesIO
from utils import predict_price, insert_booking, get_db_connection

app = Flask(__name__)
app.secret_key = os.urandom(24)

monuments = [
    {"name": "Taj Mahal", "url": "/taj"},
    {"name": "Qutb Minar", "url": "/qutb"},
]


# First page to log in, signup or continue as guest
@app.route("/")
def signup_login():
    return render_template("login_signup/signup_login.html")


@app.route("/continue_as_guest")
def continue_as_guest():
    session['guest'] = True
    return redirect(url_for("home"))


# Route for signing up a new user
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        with closing(get_db_connection()) as conn_users:
            try:
                conn_users.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
                conn_users.commit()
                return redirect(url_for("signup_login"))
            except sqlite3.IntegrityError:
                return "Email already exists. Please try a different one."
    return render_template("login_signup/signup.html")


# Route for login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        with closing(get_db_connection()) as conn_users:
            user = conn_users.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['is_admin'] = user['is_admin']
                session.pop('guest', None)
                if user['is_admin']:
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("home"))
            else:
                error = "Invalid email or password."
                return render_template("login.html", error=error)

    return render_template("login_signup/login.html")


# Route to log out the user
@app.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("signup_login"))
    response.set_cookie(app.config['SESSION_COOKIE_NAME'], '', expires=0)  # Expire the session cookie
    return response


# Route to home page
@app.route("/home")
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("index.html")
    elif session.get('guest'):
        return render_template("index.html")
    else:
        return redirect(url_for("signup_login"))


# Route for monument booking pages
@app.route('/taj')
def taj():
    return render_template('monuments/taj.html')


@app.route('/qutb')
def qutb():
    return render_template('monuments/qutb.html')


# Direct route to monument booking pages
@app.route("/book")
def book():
    monument = request.args.get('monument')
    if monument == 'qutb':
        return redirect(url_for('qutb'))
    else:
        return redirect(url_for('taj'))


# Route through search bar
@app.route('/search')
def search():
    query = request.args.get('query')
    if query:
        results = [m for m in monuments if re.search(query, m['name'], re.IGNORECASE)]
        return jsonify(results)
    else:
        return jsonify([])


# Route to confirmation page
@app.route('/confirmation')
def confirmation():
    if session.get('guest'):
        flash("Please sign up or log in to make a purchase.", "info")
        return redirect(url_for('signup_login'))
    booking_data = request.args

    email = session['email']
    name = booking_data.get('name')
    monument = booking_data.get("monument")
    date = booking_data.get('date')
    time = booking_data.get('time')
    adults = int(booking_data.get('adults'))
    children = int(booking_data.get('children'))
    total_price = float(booking_data.get('total_price'))
    special_addons = booking_data.get("special_addons")

    # Generate a unique QR code for the booking
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f'Booking for {name} at {monument} on {date} at {time}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert the image to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Insert booking into database, including the QR code
    insert_booking(email, name, monument, date, time, adults, children, total_price, qr_code_base64, special_addons)

    return render_template('confirmation_page.html', booking_data=booking_data, qr_code=qr_code_base64)


# Display booking data on booking page
@app.route('/bookings')
def bookings():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    user_email = session.get('email')
    c.execute("SELECT * FROM bookings WHERE email = ?", (user_email,))
    bookings = c.fetchall()
    conn.close()

    bookings_data = []

    for booking in bookings:
        bookings_data.append({
            'name': booking[2],
            'monument': booking[3],
            'date': booking[4],
            'time': booking[5],
            'adults': booking[6],
            'children': booking[7],
            'total_price': booking[8],
            'qr_code': booking[9],
            'special_addons': booking[10]
        })

    return render_template('dropdown/bookings.html', bookings=bookings_data)


# Route to incentive page
@app.route('/incentive')
def incentive_page():
    return render_template('dropdown/incentives.html')


# Route to admin home page
@app.route("/admin")
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    with closing(get_db_connection()) as conn:
        total_users = conn.execute("SELECT COUNT(DISTINCT email) FROM users").fetchone()[0]

    with sqlite3.connect('bookings.db') as conn_bookings:
        conn_bookings.row_factory = sqlite3.Row
        bookings = conn_bookings.execute("SELECT * FROM bookings").fetchall()
        total_bookings = conn_bookings.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

    return render_template("admin/home.html", total_users=total_users, recent_bookings=bookings, total_bookings=total_bookings)


# Route for predicting the price
@app.route('/api/predict-price', methods=['POST'])
def get_predicted_price():
    try:
        data = request.json
        visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d')
        monument = data['monument']
        time_slot = data['time_slot']
        predicted_price = predict_price(monument, visit_date, time_slot)
        return jsonify({
            'success': True,
            'predicted_price': round(predicted_price)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# Route for getting traffic estimation
@app.route('/api/get-traffic', methods=['POST'])
def get_traffic():
    data = request.json

    monument = data.get('monument')
    date = data.get('visit_date')
    time_slot = data.get('time_slot')

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT traffic FROM traffic
        WHERE monument = ? AND date = ? AND time = ?
    ''', (monument, date, time_slot))
    result = cursor.fetchone()

    conn.close()

    print(result)

    if result:
        traffic = result[0]
        return jsonify({"success": True, "traffic": traffic})
    else:
        return jsonify({"success": True, "traffic": 0})


@app.route('/api/get-incentives', methods=['GET'])
def get_incentives():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Query total visits
    cursor.execute('SELECT COUNT(DISTINCT monument) FROM bookings WHERE email = ?', (session['email'],))
    total_visits = cursor.fetchone()[0]

    # Define badges and discounts based on visit milestones
    badges = []
    discount = 0

    if total_visits >= 5:
        badges.append({"name": "Explorer", "icon": "/static/icons/explorer.png"})
        discount = max(discount, 5)
    if total_visits >= 10:
        badges.append({"name": "Adventurer", "icon": "/static/icons/adventurer.png"})
        discount = max(discount, 10)
    if total_visits >= 20:
        badges.append({"name": "Globetrotter", "icon": "/static/icons/globetrotter.png"})
        discount = max(discount, 20)

    conn.close()

    return jsonify({
        "success": True,
        "totalVisits": total_visits,
        "badges": badges,
        "discount": discount
    })


if __name__ == "__main__":
    app.run(debug=True)
