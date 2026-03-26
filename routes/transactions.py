from flask import Blueprint, render_template, request, redirect, session
from models import db, Transaction
from datetime import date, timedelta
from functools import wraps

transactions_bp = Blueprint('transactions', __name__)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/auth/login')
        return f(*args, **kwargs)
    return wrapper

@transactions_bp.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    txns = Transaction.query.filter_by(user_id=uid).order_by(Transaction.date.desc()).limit(5).all()
    all_txns = Transaction.query.filter_by(user_id=uid).all()
    income = sum(t.amount for t in all_txns if t.type == 'income')
    expense = sum(t.amount for t in all_txns if t.type == 'expense')
    balance = income - expense
    return render_template('dashboard.html',
        income=income, expense=expense, balance=balance,
        recent=txns, username=session.get('username'))

@transactions_bp.route('/transactions/add', methods=['POST'])
@login_required
def add():
    try:
        t = Transaction(
            user_id=session['user_id'],
            type=request.form['type'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            date=date.fromisoformat(request.form['date']),
            note=request.form.get('note', '')
        )
        db.session.add(t)
        db.session.commit()
    except Exception:
        pass
    return redirect('/dashboard')

@transactions_bp.route('/transactions')
@login_required
def list_transactions():
    uid = session['user_id']
    f = request.args.get('filter')
    today = date.today()

    q = Transaction.query.filter_by(user_id=uid)
    if f == 'daily':
        q = q.filter(Transaction.date == today)
    elif f == 'weekly':
        q = q.filter(Transaction.date >= today - timedelta(days=7))
    elif f == 'monthly':
        q = q.filter(Transaction.date >= today.replace(day=1))

    txns = q.order_by(Transaction.date.desc()).all()
    income = sum(t.amount for t in txns if t.type == 'income')
    expense = sum(t.amount for t in txns if t.type == 'expense')
    return render_template('history.html', transactions=txns, active_filter=f,
        income=income, expense=expense)

@transactions_bp.route('/transactions/<int:tid>', methods=['DELETE'])
@login_required
def delete(tid):
    t = Transaction.query.filter_by(id=tid, user_id=session['user_id']).first()
    if t:
        db.session.delete(t)
        db.session.commit()
    return ('', 204)
