from flask import Flask, redirect
from models import db, User, Transaction
from routes.auth import auth_bp
from routes.transactions import transactions_bp
from werkzeug.security import generate_password_hash
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(transactions_bp)

@app.route('/')
def index():
    return redirect('/dashboard')

def seed():
    if User.query.filter_by(username='test').first():
        return
    user = User(username='test', password_hash=generate_password_hash('1234'))
    db.session.add(user)
    db.session.flush()

    today = date.today()
    samples = [
        Transaction(user_id=user.id, type='income', amount=3000, category='salary', date=today - timedelta(days=20), note='Monthly salary'),
        Transaction(user_id=user.id, type='expense', amount=500, category='food', date=today - timedelta(days=15), note='Groceries'),
        Transaction(user_id=user.id, type='expense', amount=100, category='transport', date=today - timedelta(days=10), note='Bus pass'),
        Transaction(user_id=user.id, type='expense', amount=200, category='entertainment', date=today - timedelta(days=5), note='Movie night'),
        Transaction(user_id=user.id, type='income', amount=500, category='other', date=today - timedelta(days=2), note='Freelance work'),
    ]
    db.session.add_all(samples)
    db.session.commit()

with app.app_context():
    db.create_all()
    seed()

if __name__ == '__main__':
    app.run(debug=True)
