
---

# MonuBook

A web-based platform for booking tickets to heritage sites across India. This system allows users to book tickets, predict ticket prices, track visits, earn incentives, and offers an admin dashboard for managing bookings and user data.

## System Requirements
- Python 3.7+
- Flask
- SQLite
- Other dependencies listed in `requirements.txt`

## Setup Instructions

### 1. Clone the repository

Clone the repository to your local machine:

```bash
git clone https://github.com/your-repo/monubook.git
cd monubook
```

### 2. Install Dependencies

Install the required Python packages from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 3. Setup the Database

The SQLite databases (`users.db` and `bookings.db`) will be automatically created when the application runs. No manual setup is needed.

### 4. Running the Application

Start the Flask server:

```bash
python app.py
```

The application will be accessible at `http://127.0.0.1:5000`.

### 5. Admin Dashboard

Admin users can access the dashboard by logging in with admin credentials:
- Email: `admin@example.com`
- Password: `test`

The dashboard allows admins to:
- View booking details.
- View statistics about users and bookings.

## API Documentation

### 1. **POST /api/predict-price**
Predicts the ticket price based on monument, date, and time.

**Request:**
```json
{
  "monument": "Taj Mahal",
  "date": "2024-12-25",
  "time": "1000-1100"
}
```

**Response:**
```json
{
  "predicted_price": 102
}
```

### 2. **GET /api/get-incentives**
Returns the user's badge and discount information.

**Response:**
```json
{
  "total_visits": 12
}
```

### 3. **POST /api/insert-booking**
Inserts a new booking into the database after a successful booking.

**Request:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "monument": "Qutb Minar",
  "date": "2024-12-15",
  "time": "1000-1100",
  "adults": 2,
  "children": 1,
  "total_price": 400,
  "special_addons": "",
  "qr_code": "base64-encoded-qr-code"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Booking confirmed"
}
```
