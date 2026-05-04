from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'smart_campus_secret_key'

# MongoDB Configuration
MONGO_URI = 'mongodb://localhost:27017/'

def get_db():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return client['smart_campus']
    except ConnectionFailure:
        print("Error: Could not connect to MongoDB.")
        return None

# Context processor to inject user role into templates
@app.context_processor
def inject_user():
    return dict(session=session)

# ----------------- ROUTES -----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        if db is not None:
            user = db.users.find_one({"username": username, "password": password})
            if user:
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['role'] = user.get('role', 'student')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        else:
            # Fallback for demo without DB
            if username == 'admin' and password == 'admin':
                session['user_id'] = 'mock_admin_id'
                session['username'] = 'admin'
                session['role'] = 'admin'
                return redirect(url_for('dashboard'))
            elif username == 'student' and password == 'student':
                session['user_id'] = 'mock_student_id'
                session['username'] = 'student'
                session['role'] = 'student'
                return redirect(url_for('dashboard'))
            flash('Database connection failed. Used fallback credentials (admin/admin or student/student). Invalid.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'student')
        
        db = get_db()
        if db is not None:
            if db.users.find_one({"username": username}):
                flash('Username already exists.', 'error')
            else:
                db.users.insert_one({
                    "username": username,
                    "password": password,
                    "role": role,
                    "created_at": datetime.now()
                })
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
        else:
            flash('Database connection failed. Cannot register.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/parking')
def parking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    slots = []
    db = get_db()
    if db is not None:
        slots_cursor = db.parking_slots.find()
        # Convert ObjectId to string for HTML template
        for slot in slots_cursor:
            slot['id'] = str(slot['_id'])
            slots.append(slot)
    else:
        # Mock Data
        slots = [
            {'id': '1', 'slot_name': 'P1', 'status': 'Free'},
            {'id': '2', 'slot_name': 'P2', 'status': 'Occupied'},
            {'id': '3', 'slot_name': 'P3', 'status': 'Free'}
        ]
    return render_template('parking.html', slots=slots)

@app.route('/reserve_parking', methods=['POST'])
def reserve_parking():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.json
    slot_id = data.get('slot_id')
    
    db = get_db()
    if db is not None:
        result = db.parking_slots.update_one(
            {'_id': ObjectId(slot_id)},
            {'$set': {'status': 'Occupied', 'reserved_by': session['user_id']}}
        )
        if result.modified_count > 0:
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Slot not found or already occupied.'})
    return jsonify({'success': True, 'message': 'Mock reserved'})

@app.route('/classroom')
def classroom():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    rooms = []
    db = get_db()
    if db is not None:
        rooms_cursor = db.classrooms.find()
        for room in rooms_cursor:
            room['id'] = str(room['_id'])
            rooms.append(room)
    else:
        rooms = [
            {'id': '1', 'room_number': 'Room 101', 'usage_status': 'Occupied', 'lights_status': 'ON', 'fans_status': 'ON'},
            {'id': '2', 'room_number': 'Room 102', 'usage_status': 'Free', 'lights_status': 'OFF', 'fans_status': 'OFF'}
        ]
    return render_template('classroom.html', rooms=rooms)

@app.route('/toggle_device', methods=['POST'])
def toggle_device():
    # Simulated IoT control endpoint
    data = request.json
    room_id = data.get('room_id')
    device = data.get('device')
    new_status = data.get('status')
    
    db = get_db()
    if db is not None:
        field = 'lights_status' if device == 'lights' else 'fans_status'
        db.classrooms.update_one(
            {'_id': ObjectId(room_id)},
            {'$set': {field: new_status}}
        )
    # In a real scenario, we would also call ESP8266/Blynk API here.
    return jsonify({'success': True, 'message': f'{device} turned {new_status}'})

@app.route('/irrigation')
def irrigation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    data = []
    db = get_db()
    if db is not None:
        areas_cursor = db.irrigation_data.find()
        for area in areas_cursor:
            area['id'] = str(area['_id'])
            data.append(area)
    else:
        data = [
            {'id': '1', 'area_name': 'Main Garden', 'moisture_level': 45, 'pump_status': 'OFF', 'mode': 'Auto'}
        ]
    return render_template('irrigation.html', areas=data)

@app.route('/garbage')
def garbage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    bins = []
    db = get_db()
    if db is not None:
        bins_cursor = db.garbage_bins.find()
        for bin_doc in bins_cursor:
            bin_doc['id'] = str(bin_doc['_id'])
            bins.append(bin_doc)
    else:
        bins = [
            {'id': '1', 'location': 'Main Gate', 'fill_level': 30, 'status': 'Normal'},
            {'id': '2', 'location': 'Canteen', 'fill_level': 95, 'status': 'Full'}
        ]
    return render_template('garbage.html', bins=bins)

@app.route('/canteen')
def canteen():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    categories = {}
    db = get_db()
    if db is not None:
        items_cursor = db.food_items.find({"available": True})
        for item in items_cursor:
            item['id'] = str(item['_id'])
            cat = item.get('category', 'Others')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
    else:
        categories = {
            "Starters": [
                {"id": "s1", "category": "Starters", "name": "Paneer Tikka", "price": 120.00, "description": "Grilled cottage cheese cubes marinated in spices"},
                {"id": "s2", "category": "Starters", "name": "Chicken 65", "price": 150.00, "description": "Spicy, deep-fried chicken bites"}
            ],
            "Main Course": [
                {"id": "m1", "category": "Main Course", "name": "Veg Biryani", "price": 180.00, "description": "Aromatic rice dish cooked with mixed vegetables and spices"},
                {"id": "m2", "category": "Main Course", "name": "Chicken Biryani", "price": 220.00, "description": "Classic Hyderabadi style chicken dum biryani"}
            ],
            "Fast Food": [
                {"id": "f1", "category": "Fast Food", "name": "Veg Burger", "price": 60.00, "description": "Classic veg patty burger with cheese"},
                {"id": "f2", "category": "Fast Food", "name": "French Fries", "price": 50.00, "description": "Crispy golden potato fries"}
            ],
            "Beverages": [
                {"id": "b1", "category": "Beverages", "name": "Cold Coffee", "price": 60.00, "description": "Refreshing iced coffee with a scoop of ice cream"}
            ],
            "Desserts": [
                {"id": "d1", "category": "Desserts", "name": "Gulab Jamun (2 pcs)", "price": 40.00, "description": "Soft milk-solid dumplings soaked in sugar syrup"}
            ]
        }
    return render_template('canteen.html', categories=categories)

@app.route('/seat_reservation', methods=['GET', 'POST'])
def seat_reservation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        venue = request.form['venue']
        seat_number = request.form['seat_number']
        res_time = request.form['reservation_time']
        
        db = get_db()
        if db is not None:
            db.seat_reservations.insert_one({
                "user_id": session['user_id'],
                "venue": venue,
                "seat_number": seat_number,
                "reservation_time": res_time,
                "created_at": datetime.now()
            })
            flash('Seat reserved successfully!', 'success')
        else:
            flash('Mock reserved!', 'success')
        return redirect(url_for('seat_reservation'))
        
    return render_template('seat_reservation.html')

@app.route('/library')
def library():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    books = []
    borrowings = []
    db = get_db()
    if db is not None:
        books_cursor = db.library_books.find()
        for b in books_cursor:
            b['id'] = str(b['_id'])
            books.append(b)
            
        borrowings_cursor = db.library_borrowings.find({"status": "Borrowed"})
        for bw in borrowings_cursor:
            bw['id'] = str(bw['_id'])
            borrowings.append(bw)
    else:
        books = [
            {"id": "1", "title": "Clean Code", "author": "Robert C. Martin", "total_copies": 3, "available_copies": 3}
        ]
        borrowings = [
            {"student_name": "mock_student", "book_title": "Clean Code", "borrow_date": "Today"}
        ]
        
    return render_template('library.html', books=books, borrowings=borrowings)

@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('admin_panel.html')

# IoT API Endpoint (for ESP8266 to send data)
@app.route('/api/update_sensor', methods=['POST'])
def update_sensor():
    """
    Endpoint for IoT devices (e.g., ESP8266) to POST sensor data.
    Expected JSON: {"sensor_type": "garbage", "id": "mongo_object_id_string", "value": 85}
    """
    data = request.json
    sensor_type = data.get('sensor_type')
    item_id = data.get('id')
    value = data.get('value')
    
    db = get_db()
    if db is not None:
        try:
            if sensor_type == 'garbage':
                status = 'Full' if int(value) > 90 else 'Normal'
                db.garbage_bins.update_one(
                    {'_id': ObjectId(item_id)},
                    {'$set': {'fill_level': int(value), 'status': status}}
                )
            elif sensor_type == 'irrigation':
                db.irrigation_data.update_one(
                    {'_id': ObjectId(item_id)},
                    {'$set': {'moisture_level': int(value), 'last_updated': datetime.now()}}
                )
            elif sensor_type == 'parking':
                status = 'Occupied' if int(value) == 1 else 'Free'
                db.parking_slots.update_one(
                    {'_id': ObjectId(item_id)},
                    {'$set': {'status': status}}
                )
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
            
    return jsonify({'status': 'error', 'message': 'DB connection failed'})

# --- Real-time Data Fetch Endpoints for Frontend Polling ---
@app.route('/api/data/parking')
def api_get_parking():
    db = get_db()
    if db is None: return jsonify([])
    return jsonify([{**slot, '_id': str(slot['_id'])} for slot in db.parking_slots.find()])

@app.route('/api/data/classrooms')
def api_get_classrooms():
    db = get_db()
    if db is None: return jsonify([])
    return jsonify([{**room, '_id': str(room['_id'])} for room in db.classrooms.find()])

@app.route('/api/data/irrigation')
def api_get_irrigation():
    db = get_db()
    if db is None: return jsonify([])
    # Remove datetime objects as they aren't JSON serializable by default easily
    data = []
    for area in db.irrigation_data.find():
        area['_id'] = str(area['_id'])
        if 'last_updated' in area:
            area['last_updated'] = str(area['last_updated'])
        data.append(area)
    return jsonify(data)

@app.route('/api/data/garbage')
def api_get_garbage():
    db = get_db()
    if db is None: return jsonify([])
    return jsonify([{**bin, '_id': str(bin['_id'])} for bin in db.garbage_bins.find()])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
