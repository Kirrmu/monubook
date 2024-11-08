import sqlite3

from tensorflow import keras
import numpy as np
import holidays
import requests

keras.backend.clear_session()
price_model = keras.models.load_model('model/predict_price.keras')
price_model.load_weights('model/model.weights.h5')

in_holidays = holidays.India()


def predict_price(monument, visit_date, time_slot):
    is_holiday = 1 if (visit_date.date() in in_holidays) or (visit_date.weekday() >= 5) else 0

    if monument == 'qutb':
        city = 'Delhi'
        base_price = 80
        max_traffic = 692
        avg_traffic = 300
    else:
        city = 'Agra'
        base_price = 100
        max_traffic = 4000
        avg_traffic = 2000

    weather_api_key = '5CNLFSTDVQH4QKX6CQ7BNBKED'
    weather_url = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/{visit_date.date()}?unitGroup=metric&key={weather_api_key}&include=days'

    try:
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        forecast = weather_data['days'][0]
        temperature = forecast['temp']
        is_rainy = 1 if 'rain' in forecast['conditions'].lower() else 0
        is_sunny = 1 if 'clear' in forecast['conditions'].lower() else 0


    except:
        temperature = 25
        is_rainy = 0
        is_sunny = 1

    time_9_10 = 1 if time_slot in ["0900-1000"] else 0
    time_5_6 = 1 if time_slot in ["1700-1800"] else 0

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
            SELECT traffic FROM traffic
            WHERE monument = ? AND date = ? AND time = ?
        ''', (monument, visit_date.date(), time_slot))
    result = 0 if cursor.fetchone() is None else cursor.fetchone()

    conn.close()

    visitors = avg_traffic if avg_traffic >= result else result

    print(visitors)

    predicted_price = price_model.predict(
        np.array(
            [[visitors, base_price, is_holiday, time_9_10, time_5_6, temperature, is_rainy, is_sunny, max_traffic]]))

    return predicted_price[0][0]


def insert_booking(email, name, monument, date, time, adults, children, total_price, qr_code, special_addons):
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    cursor.execute(''' 
    INSERT INTO bookings (email, name, monument, date, time, adults, children, total_price, qr_code, special_additions)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (email, name, monument, date, time, adults, children, total_price, qr_code, special_addons))

    cursor.execute('''
    INSERT INTO traffic (monument, time, date, traffic)
    VALUES (?, ?, ?, ?)
    ON CONFLICT (monument, time, date) 
    DO UPDATE SET traffic = traffic + ?;
    ''', (monument, time, date, adults + children, adults + children))

    conn.commit()
    conn.close()


def get_db_connection():
    conn_users = sqlite3.connect('users.db')
    conn_users.row_factory = sqlite3.Row
    return conn_users
