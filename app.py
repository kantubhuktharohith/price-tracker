import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Product, PriceHistory

# ==========================================
# APP CONFIGURATION
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'pulse-tracker-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pulse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables on first run
with app.app_context():
    db.create_all()

# ==========================================
# AUTH ROUTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('login.html', mode='register')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('login.html', mode='register')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('login.html', mode='register')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('login.html', mode='register')
        
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
    
    return render_template('login.html', mode='register')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==========================================
# DASHBOARD
# ==========================================

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

# ==========================================
# API ROUTES (all scoped to current_user)
# ==========================================

@app.route('/api/add', methods=['POST'])
@login_required
def add_product():
    data = request.json
    url = data.get('url', '').strip()
    target_price = data.get('target_price')
    
    if not url or not target_price:
        return jsonify({'error': 'Missing url or target_price'}), 400
    
    try:
        target_price = float(target_price)
    except ValueError:
        return jsonify({'error': 'Invalid target_price'}), 400
    
    # Check duplicate for THIS user
    existing = Product.query.filter_by(user_id=current_user.id, url=url).first()
    if existing:
        return jsonify({'error': 'Product already tracked'}), 409
    
    # Try to scrape the title
    try:
        from price import get_product_details
        title, current_price = get_product_details(url)
        if not title or title == 'Unknown Product':
            title = 'New Tracked Product'
    except Exception:
        title = 'New Tracked Product'
    
    new_product = Product(
        user_id=current_user.id,
        name=title,
        url=url,
        target_price=target_price
    )
    db.session.add(new_product)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'product': {'name': new_product.name, 'url': new_product.url, 'target_price': new_product.target_price}
    })

@app.route('/api/products')
@login_required
def list_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {'name': p.name, 'url': p.url, 'target_price': p.target_price}
        for p in products
    ])

@app.route('/api/remove', methods=['POST'])
@login_required
def remove_product():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'Missing url'}), 400
    
    product = Product.query.filter_by(user_id=current_user.id, url=url).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/data')
@login_required
def get_data():
    # Get all products for the current user
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    if not products:
        return jsonify({'labels': [], 'datasets': []})
    
    product_ids = [p.id for p in products]
    
    # Get all price history for these products
    history = PriceHistory.query.filter(
        PriceHistory.product_id.in_(product_ids)
    ).order_by(PriceHistory.timestamp).all()
    
    if not history:
        return jsonify({'labels': [], 'datasets': []})
    
    # Build unified timeline
    timestamps = sorted(set(h.timestamp for h in history))
    labels = [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps]
    
    # Group history by product
    product_prices = {}
    for h in history:
        if h.product_id not in product_prices:
            product_prices[h.product_id] = {}
        product_prices[h.product_id][h.timestamp] = h.price
    
    # Build datasets
    colors = [
        '#00f2fe', '#fa709a', '#fee140', '#43e97b', '#c471ed',
        '#fa0874', '#4facfe', '#fbc2eb', '#a18cd1', '#ff9a9e'
    ]
    
    datasets = []
    for idx, product in enumerate(products):
        prices_dict = product_prices.get(product.id, {})
        prices = []
        last_price = None
        for ts in timestamps:
            if ts in prices_dict:
                last_price = prices_dict[ts]
            prices.append(last_price)
        
        color = colors[idx % len(colors)]
        datasets.append({
            'label': product.name,
            'data': prices,
            'borderColor': color,
            'backgroundColor': color + '33',
            'borderWidth': 3,
            'tension': 0.4,
            'pointRadius': 0,
            'pointHoverRadius': 6,
            'pointHitRadius': 10
        })
    
    return jsonify({'labels': labels, 'datasets': datasets})

if __name__ == '__main__':
    app.run(debug=True, port=5050)
