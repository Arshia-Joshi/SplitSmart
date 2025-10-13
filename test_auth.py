from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from mongo_db import db_instance

app = Flask(__name__)
app.secret_key = 'test-secret-key-123'

# Simple test routes for authentication only
@app.route('/')
def home():
    if 'user_id' in session:
        return f"Welcome {session['username']}! <a href='/logout'>Logout</a>"
    return "Home - <a href='/login'>Login</a> | <a href='/signup'>Signup</a>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = db_instance.authenticate_user(email, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            flash('Login successful!', 'success')
            return redirect('/')
        else:
            flash('Invalid email or password', 'error')
    
    return '''
    <form method="POST">
        <h2>Login</h2>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
    <a href="/signup">Signup</a>
    '''

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect('/signup')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect('/signup')
        
        user_id, message = db_instance.create_user(username, email, password)
        
        if user_id:
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        else:
            flash(message, 'error')
    
    return '''
    <form method="POST">
        <h2>Sign Up</h2>
        Username: <input type="text" name="username" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        Confirm Password: <input type="password" name="confirm_password" required><br>
        <button type="submit">Sign Up</button>
    </form>
    <a href="/login">Login</a>
    '''

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect('/')

if __name__ == '__main__':
    print("🚀 Testing MongoDB Authentication...")
    app.run(host='0.0.0.0', port=5001, debug=True)