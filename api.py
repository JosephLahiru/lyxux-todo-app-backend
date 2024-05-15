from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

def db_init():
    """Initialize MySQL database connection."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.route('/register', methods=['POST'])
def register():
    """ Route to Register a User """
    data = request.json
    username = data['username']
    password = data['password']
    cnx = db_init()
    cursor = cnx.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        cnx.commit()
        return jsonify({"success": True, "message": "User registered successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cursor.close()
        cnx.close()

@app.route('/login', methods=['POST'])
def login():
    """ Route to Log In a User """
    data = request.json
    username = data['username']
    password = data['password']
    cnx = db_init()
    cursor = cnx.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['id']
            return jsonify({"success": True, "message": "Login successful"}), 200
        else:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401
    finally:
        cursor.close()
        cnx.close()

@app.route('/logout', methods=['GET'])
def logout():
    """ Route to Log Out a User """
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/tasks', methods=['POST'])
def add_task():
    """ Route to Add a Task """
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.json
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
    """ Route to Get All Tasks """
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    cnx = db_init()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (session['user_id'],))
        tasks = cursor.fetchall()
        return jsonify(tasks)
    finally:
        cursor.close()
        cnx.close()

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """ Route to Update a Task """
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.json
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("UPDATE tasks SET title = %s WHERE id = %s AND user_id = %s", (data['title'], task_id, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task updated successfully"})
    finally:
        cursor.close()
        cnx.close()

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """ Route to Delete a Task """
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    cnx = db_init()
    cursor = cnx.cursor()
    try:
        cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
        cnx.commit()
        return jsonify({"success": True, "message": "Task deleted successfully"})
    finally:
        cursor.close()
        cnx.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
