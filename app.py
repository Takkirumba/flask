from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cholachat_atm_secret_key"
# เชื่อมต่อ MySQL (ตรวจสอบชื่อ database ให้ตรงกับใน phpMyAdmin)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/atm_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class Account(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return Account.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        acc_num = request.form.get('account_number')
        name = request.form.get('username')
        pw = request.form.get('password')
        if Account.query.filter_by(account_number=acc_num).first():
            flash('เลขบัญชีนี้ถูกใช้งานแล้ว', 'danger')
        else:
            # ยอดเงินเริ่มต้นเป็น 0.0 บาท
            new_user = Account(account_number=acc_num, username=name, password=pw, balance=0.0)
            db.session.add(new_user)
            db.session.commit()
            flash('สมัครสมาชิกสำเร็จ! ยอดเงินเริ่มต้นคือ 0 บาท', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        acc_num = request.form.get('account_number')
        pw = request.form.get('password')
        user = Account.query.filter_by(account_number=acc_num, password=pw).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('เลขบัญชีหรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html')

@app.route('/index')
@login_required
def index():
    # ดึงประวัติธุรกรรมเฉพาะของ User ที่ Login อยู่
    txs = Transaction.query.filter_by(account_number=current_user.account_number).order_by(Transaction.timestamp.desc()).all()
    # ส่งแค่ข้อมูล user และ transactions ไปที่หน้าเว็บ
    return render_template('index.html', user=current_user, transactions=txs)

@app.route('/process', methods=['POST'])
@login_required
def process():
    try:
        amount = float(request.form.get('amount'))
        action = request.form.get('action')

        # เงื่อนไขตรวจสอบ: ห้ามใส่ค่าติดลบหรือศูนย์
        if amount <= 0:
            flash('จำนวนเงินไม่ถูกต้อง', 'danger')
            return redirect(url_for('index'))

        if action == 'withdraw' and current_user.balance < amount:
            flash('ยอดเงินในบัญชีไม่เพียงพอ', 'danger')
        else:
            if action == 'deposit':
                current_user.balance += amount
                t_type = "ฝากเงิน"
            else:
                current_user.balance -= amount
                t_type = "ถอนเงิน"
            
            db.session.add(Transaction(account_number=current_user.account_number, type=t_type, amount=amount))
            db.session.commit()
            flash(f'ทำรายการ {t_type} สำเร็จ', 'success')
            
    except ValueError:
        flash('กรุณาระบุจำนวนเงินเป็นตัวเลขที่ถูกต้อง', 'danger')

    return redirect(url_for('index'))

@app.route('/delete_account')
@login_required
def delete_account():
    acc_num = current_user.account_number
    user = Account.query.get(current_user.id)
    Transaction.query.filter_by(account_number=acc_num).delete()
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash('บัญชีของคุณถูกลบถาวรแล้ว', 'info')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)