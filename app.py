from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
import mysql.connector
import os
import json
from datetime import datetime, timedelta
import calendar
import bcrypt
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from matplotlib.colors import LinearSegmentedColormap
import threading
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'expense_tracker')
    )

# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create expenses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        date DATE NOT NULL,
        category VARCHAR(50) NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        description VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create funds table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS funds (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        date DATE NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create monthly_savings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monthly_savings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        month INT NOT NULL,
        year INT NOT NULL,
        total_expenses DECIMAL(10, 2) NOT NULL,
        total_funds DECIMAL(10, 2) NOT NULL,
        savings DECIMAL(10, 2) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE KEY (user_id, month, year)
    )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Initialize database on startup
init_db()

# Helper functions
def get_user_data():
    if 'user_id' not in session:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return user

def get_current_month_expenses(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    last_day = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    cursor.execute(
        "SELECT * FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY date DESC",
        (user_id, first_day, last_day)
    )
    expenses = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return expenses

def get_current_month_funds(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    last_day = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    cursor.execute(
        "SELECT * FROM funds WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY date DESC",
        (user_id, first_day, last_day)
    )
    funds = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return funds

def get_monthly_summary(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    month = today.month
    year = today.year
    
    cursor.execute(
        "SELECT * FROM monthly_savings WHERE user_id = %s AND month = %s AND year = %s",
        (user_id, month, year)
    )
    summary = cursor.fetchone()
    
    if not summary:
        # Calculate summary if not exists
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month, calendar.monthrange(year, month)[1])
        
        # Get total expenses
        cursor.execute(
            "SELECT SUM(amount) as total FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s",
            (user_id, first_day, last_day)
        )
        total_expenses_result = cursor.fetchone()
        total_expenses = total_expenses_result['total'] if total_expenses_result['total'] else 0
        
        # Get total funds
        cursor.execute(
            "SELECT SUM(amount) as total FROM funds WHERE user_id = %s AND date BETWEEN %s AND %s",
            (user_id, first_day, last_day)
        )
        total_funds_result = cursor.fetchone()
        total_funds = total_funds_result['total'] if total_funds_result['total'] else 0
        
        # Calculate savings
        savings = float(total_funds) - float(total_expenses)
        
        summary = {
            'month': month,
            'year': year,
            'total_expenses': float(total_expenses),
            'total_funds': float(total_funds),
            'savings': savings
        }
    
    cursor.close()
    conn.close()
    
    # Get month name
    month_name = calendar.month_name[month if isinstance(month, int) else int(month)]
    
    return {
        'month': month_name,
        'year': summary['year'],
        'total_expenses': float(summary['total_expenses']),
        'total_funds': float(summary['total_funds']),
        'savings': float(summary['savings'])
    }

def get_previous_month_savings(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    previous_month = today.month - 1
    year = today.year
    
    if previous_month == 0:
        previous_month = 12
        year -= 1
    
    cursor.execute(
        "SELECT * FROM monthly_savings WHERE user_id = %s AND month = %s AND year = %s",
        (user_id, previous_month, year)
    )
    savings = cursor.fetchone()
    
    if not savings:
        # Calculate if not exists
        first_day = datetime(year, previous_month, 1)
        last_day = datetime(year, previous_month, calendar.monthrange(year, previous_month)[1])
        
        # Get total expenses
        cursor.execute(
            "SELECT SUM(amount) as total FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s",
            (user_id, first_day, last_day)
        )
        total_expenses_result = cursor.fetchone()
        total_expenses = total_expenses_result['total'] if total_expenses_result['total'] else 0
        
        # Get total funds
        cursor.execute(
            "SELECT SUM(amount) as total FROM funds WHERE user_id = %s AND date BETWEEN %s AND %s",
            (user_id, first_day, last_day)
        )
        total_funds_result = cursor.fetchone()
        total_funds = total_funds_result['total'] if total_funds_result['total'] else 0
        
        # Calculate savings
        savings_amount = float(total_funds) - float(total_expenses)
        
        cursor.close()
        conn.close()
        
        return savings_amount
    
    cursor.close()
    conn.close()
    
    return float(savings['savings'])

def generate_category_chart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    last_day = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    cursor.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s GROUP BY category",
        (user_id, first_day, last_day)
    )
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not categories:
        return None
    
    # Create pie chart
    labels = [category['category'] for category in categories]
    sizes = [float(category['total']) for category in categories]
    
    # Custom colors
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF']
    
    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    plt.axis('equal')
    plt.title('Expenses by Category')
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    
    return graphic

def generate_monthly_chart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    year = today.year
    
    monthly_data = []
    
    for month in range(1, 13):
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month, calendar.monthrange(year, month)[1])
        
        # Skip future months
        if first_day > today:
            monthly_data.append({
                'month': calendar.month_abbr[month],
                'amount': 0
            })
            continue
        
        # Get total expenses
        cursor.execute(
            "SELECT SUM(amount) as total FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s",
            (user_id, first_day, last_day)
        )
        total_expenses_result = cursor.fetchone()
        total_expenses = total_expenses_result['total'] if total_expenses_result['total'] else 0
        
        monthly_data.append({
            'month': calendar.month_abbr[month],
            'amount': float(total_expenses)
        })
    
    cursor.close()
    conn.close()
    
    # Create bar chart
    months = [data['month'] for data in monthly_data]
    amounts = [data['amount'] for data in monthly_data]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(months, amounts, color='#3b82f6')
    
    # Add data labels
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width()/2., height + 50,
                    f'₹{int(height)}', ha='center', va='bottom')
    
    plt.title('Monthly Expenses')
    plt.xlabel('Month')
    plt.ylabel('Amount (₹)')
    plt.ylim(0, max(amounts) * 1.2 if max(amounts) > 0 else 1000)
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    
    return graphic

def generate_balance_chart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    month = today.month
    year = today.year
    
    # Get all days in the current month
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    
    # Get all funds and expenses for the month
    cursor.execute(
        "SELECT date, amount FROM funds WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY date",
        (user_id, first_day, last_day)
    )
    funds = cursor.fetchall()
    
    cursor.execute(
        "SELECT date, amount FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY date",
        (user_id, first_day, last_day)
    )
    expenses = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Combine funds and expenses
    transactions = []
    for fund in funds:
        transactions.append({
            'date': fund['date'],
            'amount': float(fund['amount']),
            'type': 'fund'
        })
    
    for expense in expenses:
        transactions.append({
            'date': expense['date'],
            'amount': float(expense['amount']),
            'type': 'expense'
        })
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x['date'])
    
    # Calculate running balance
    dates = []
    balances = []
    running_balance = 0
    
    current_date = first_day
    while current_date <= min(last_day, today):
        # Calculate balance for this date
        for transaction in transactions:
            if transaction['date'].strftime('%Y-%m-%d') == current_date.strftime('%Y-%m-%d'):
                if transaction['type'] == 'fund':
                    running_balance += transaction['amount']
                else:
                    running_balance -= transaction['amount']
        
        # Add to balance trend
        dates.append(current_date.strftime('%b %d'))
        balances.append(running_balance)
        
        # Move to next date
        current_date += timedelta(days=1)
    
    # Create line chart
    plt.figure(figsize=(10, 6))
    plt.plot(dates, balances, marker='o', linestyle='-', color='#10b981')
    
    # Add data labels for first and last points
    if balances:
        plt.text(0, balances[0], f'₹{int(balances[0])}', ha='left', va='bottom')
        plt.text(len(dates)-1, balances[-1], f'₹{int(balances[-1])}', ha='right', va='bottom')
    
    plt.title('Balance Trend')
    plt.xlabel('Date')
    plt.ylabel('Balance (₹)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    
    return graphic

def generate_top_expenses_chart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    last_day = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    
    cursor.execute(
        "SELECT category, description, amount FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY amount DESC LIMIT 5",
        (user_id, first_day, last_day)
    )
    expenses = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not expenses:
        return None
    
    # Create bar chart
    labels = []
    amounts = []
    
    for expense in expenses:
        description = expense['description'] if expense['description'] else expense['category']
        labels.append(description[:15] + '...' if len(description) > 15 else description)
        amounts.append(float(expense['amount']))
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(labels, amounts, color='#f43f5e')
    
    # Add data labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        plt.text(width + 50, bar.get_y() + bar.get_height()/2, f'₹{int(width)}', ha='left', va='center')
    
    plt.title('Top Expenses')
    plt.xlabel('Amount (₹)')
    plt.ylabel('Description')
    plt.tight_layout()
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    graphic = base64.b64encode(image_png).decode('utf-8')
    
    return graphic

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            error = 'Email and password are required'
        else:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                
                cursor.close()
                conn.close()
                
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid email or password'
            
            cursor.close()
            conn.close()
    
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not name or not email or not password:
            error = 'All fields are required'
        else:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                error = 'User with this email already exists'
            else:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password.decode('utf-8'))
                )
                conn.commit()
                
                user_id = cursor.lastrowid
                
                session['user_id'] = user_id
                session['user_name'] = name
                session['user_email'] = email
                
                cursor.close()
                conn.close()
                
                return redirect(url_for('dashboard'))
            
            cursor.close()
            conn.close()
    
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_data()
    expenses = get_current_month_expenses(session['user_id'])
    funds = get_current_month_funds(session['user_id'])
    monthly_summary = get_monthly_summary(session['user_id'])
    previous_month_savings = get_previous_month_savings(session['user_id'])
    
    # Calculate totals
    total_expenses = sum(float(expense['amount']) for expense in expenses)
    total_funds = sum(float(fund['amount']) for fund in funds)
    remaining_balance = total_funds - total_expenses
    
    # Calculate daily spendable amount
    today = datetime.now()
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    remaining_days = last_day_of_month - today.day + 1
    daily_spendable = remaining_balance / remaining_days if remaining_days > 0 else 0
    
    # Generate charts
    category_chart = generate_category_chart(session['user_id'])
    monthly_chart = generate_monthly_chart(session['user_id'])
    balance_chart = generate_balance_chart(session['user_id'])
    top_expenses_chart = generate_top_expenses_chart(session['user_id'])
    
    return render_template(
        'dashboard.html',
        user=user,
        expenses=expenses,
        funds=funds,
        total_expenses=total_expenses,
        total_funds=total_funds,
        remaining_balance=remaining_balance,
        daily_spendable=daily_spendable,
        remaining_days=remaining_days,
        monthly_summary=monthly_summary,
        previous_month_savings=previous_month_savings,
        category_chart=category_chart,
        monthly_chart=monthly_chart,
        balance_chart=balance_chart,
        top_expenses_chart=top_expenses_chart
    )

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    category = request.form.get('category')
    amount = request.form.get('amount')
    description = request.form.get('description', '')
    
    if not category or not amount:
        flash('Category and amount are required', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        amount = float(amount)
    except ValueError:
        flash('Amount must be a number', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO expenses (user_id, date, category, amount, description) VALUES (%s, %s, %s, %s, %s)",
        (session['user_id'], datetime.now().strftime('%Y-%m-%d'), category, amount, description)
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Expense added successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_fund', methods=['POST'])
def add_fund():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    amount = request.form.get('amount')
    
    if not amount:
        flash('Amount is required', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        amount = float(amount)
    except ValueError:
        flash('Amount must be a number', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO funds (user_id, date, amount) VALUES (%s, %s, %s)",
        (session['user_id'], datetime.now().strftime('%Y-%m-%d'), amount)
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Fund added successfully', 'success')
    return redirect(url_for('dashboard'))

# Monthly cleanup task
def cleanup_old_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current date
        today = datetime.now()
        
        # Calculate date two months ago
        two_months_ago = today.replace(day=1)
        if two_months_ago.month <= 2:
            two_months_ago = two_months_ago.replace(year=two_months_ago.year - 1)
            two_months_ago = two_months_ago.replace(month=two_months_ago.month + 10)
        else:
            two_months_ago = two_months_ago.replace(month=two_months_ago.month - 2)
        
        # Before deleting, ensure monthly savings are calculated and stored
        cursor.execute("SELECT DISTINCT user_id FROM expenses WHERE date < %s", (two_months_ago,))
        users = cursor.fetchall()
        
        for user in users:
            user_id = user[0]
            
            # Get month and year for data to be deleted
            cursor.execute(
                "SELECT DISTINCT MONTH(date) as month, YEAR(date) as year FROM expenses WHERE user_id = %s AND date < %s",
                (user_id, two_months_ago)
            )
            periods = cursor.fetchall()
            
            for period in periods:
                month = period[0]
                year = period[1]
                
                # Check if monthly savings already exist
                cursor.execute(
                    "SELECT * FROM monthly_savings WHERE user_id = %s AND month = %s AND year = %s",
                    (user_id, month, year)
                )
                if not cursor.fetchone():
                    # Calculate and store monthly savings
                    first_day = datetime(year, month, 1)
                    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
                    
                    # Get total expenses
                    cursor.execute(
                        "SELECT SUM(amount) as total FROM expenses WHERE user_id = %s AND date BETWEEN %s AND %s",
                        (user_id, first_day, last_day)
                    )
                    total_expenses_result = cursor.fetchone()
                    total_expenses = total_expenses_result[0] if total_expenses_result[0] else 0
                    
                    # Get total funds
                    cursor.execute(
                        "SELECT SUM(amount) as total FROM funds WHERE user_id = %s AND date BETWEEN %s AND %s",
                        (user_id, first_day, last_day)
                    )
                    total_funds_result = cursor.fetchone()
                    total_funds = total_funds_result[0] if total_funds_result[0] else 0
                    
                    # Calculate savings
                    savings = float(total_funds) - float(total_expenses)
                    
                    # Store monthly savings
                    cursor.execute(
                        "INSERT INTO monthly_savings (user_id, month, year, total_expenses, total_funds, savings) VALUES (%s, %s, %s, %s, %s, %s)",
                        (user_id, month, year, total_expenses, total_funds, savings)
                    )
                    conn.commit()
        
        # Delete expenses older than two months
        cursor.execute(
            "DELETE FROM expenses WHERE date < %s",
            (two_months_ago,)
        )
        
        # Delete funds older than two months
        cursor.execute(
            "DELETE FROM funds WHERE date < %s",
            (two_months_ago,)
        )
        
        conn.commit()
        print(f"Cleaned up data older than {two_months_ago}")
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        cursor.close()
        conn.close()

# Run cleanup task daily
def schedule_cleanup():
    def run_cleanup():
        while True:
            cleanup_old_data()
            # Sleep for 24 hours
            time.sleep(24 * 60 * 60)
    
    cleanup_thread = threading.Thread(target=run_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()

# Start cleanup scheduler
schedule_cleanup()

if __name__ == '__main__':
    app.run(debug=True)