from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv
import os
import bcrypt
from waitress import serve

load_dotenv()

start_time = datetime.now().isoformat()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

session = {}


def db_init():
    """Initialize MySQL database connection"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def console(message):
    """Logging the message to the console with timestamp"""
    time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    print(f"{time} [LOG]: Processing {message}")


def validate_json(data, required_fields):
    """Validate JSON data for required fields"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        abort(400, f'Missing fields: {", ".join(missing_fields)}')


def hash_password(password):
    """Hash a password for storing."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def check_password(hashed, password):
    """Check a password against a hashed value."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad Request', 'message': str(error)}), 400


@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized', 'message': str(error)}), 401


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found', 'message': str(error)}), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500


@app.route("/")
def status():
    console("Status Check")
    return jsonify({"project": "lyxux-todo-api", "status": "online", "start_time": start_time})


@app.route('/register', methods=['POST'])
def register():
    console("Registering a new user")
    data = request.json
    validate_json(data, ['username', 'password'])
    username = data['username']
    password = data['password']
    first_name = data['first_name']
    last_name = data['last_name']
    email = data['email']
    hashed_password = hash_password(password)
    cnx = db_init()
    cursor = cnx.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password, first_name, last_name, email) VALUES (%s, %s, %s, %s, %s)",
            (username, password, first_name, last_name, email)
        )
        cnx.commit()
        return jsonify({"success": True, "message": "User registered successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cursor.close()
        cnx.close()


@app.route('/login', methods=['POST'])
def login():
    console("Logging in a user")
    data = request.json
    validate_json(data, ['username', 'password'])
    username = data['username']
    password = data['password']
    cnx = db_init()
    cursor = cnx.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and check_password(user['password'], password):
            session['user_id'] = user['user_id']
            return jsonify({"success": True, "message": "Login successful"}), 200
        else:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401
    finally:
        cursor.close()
        cnx.close()


@app.route('/logout', methods=['GET'])
def logout():
    console("Logging out a user")
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route('/tasks', methods=['POST'])
def add_task():
    console("Adding a new task")
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.json
    validate_json(data, ['title'])
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("INSERT INTO tasks (title, completed, user_id) VALUES (%s, %s, %s)",
                       (data['title'], 0, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task added successfully"}), 201
    finally:
        cursor.close()
        cnx.close()


@app.route('/tasks', methods=['GET'])
def get_tasks():
    console("Getting all tasks")
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    cnx = db_init()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM tasks WHERE user_id = %s",
                       (session['user_id'],))
        tasks = cursor.fetchall()
        return jsonify(tasks)
    finally:
        cursor.close()
        cnx.close()


@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    console("Updating a task")
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.json
    validate_json(data, ['title'])
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("UPDATE tasks SET title = %s WHERE id = %s AND user_id = %s",
                       (data['title'], task_id, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task updated successfully"})
    finally:
        cursor.close()
        cnx.close()


@app.route('/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    console("Completing a task")
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("UPDATE tasks SET completed = 1 WHERE id = %s AND user_id = %s",
                       (task_id, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task completed successfully"})
    finally:
        cursor.close()
        cnx.close()


@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    console("Deleting a task")
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s",
                       (task_id, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task deleted successfully"})
    finally:
        cursor.close()
        cnx.close()


if __name__ == '__main__':
    console("API Started")
    serve(app, host='0.0.0.0', port=5005, threads=10)
