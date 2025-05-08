#flask py
# app.py

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from models import db, User, Message, Session
from rsa_utils import rsa_encrypt, generate_rsa_keys
from caesar_utils import caesar_encrypt
from caesar_utils import caesar_decrypt
import random
from rsa_utils import rsa_decrypt


app = Flask(__name__)
app.secret_key = 'supersecretkey'  # required for flash messages


app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

with app.app_context():
    db.create_all()
# In your app.py or a test file:
with app.app_context():
    users = User.query.all()
    for user in users:
        print(user.name, user.e, user.n)


# Just to check it's working
@app.route("/")
def home():
    return render_template("home.html")


# 📝 Register Page (GET + POST)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")

        if not name:
            flash("⚠️ Please enter your name.")
            return render_template("register.html")

        if User.query.filter_by(name=name).first():
            flash("⚠️ User already exists!")
            return render_template("register.html")

        # 🔐 Generate keys
        keys = generate_rsa_keys()
        e = keys['e']
        d = keys['d']  # This will be shown to user
        n = keys['n']

        # Store only (name, e, n)
        new_user = User(name=name, e=e, n=n)
        db.session.add(new_user)
        db.session.commit()

        flash(f"✅ Registered user: {name}")
        return render_template("register.html", d=d, e=e, n=n, generated=True)

    return render_template("register.html")

@app.route("/create-session", methods=["GET", "POST"])
def create_session():
    if request.method == "POST":
        from_user = request.form.get("from_user")
        to_user = request.form.get("to_user")
        session_label = request.form.get("session_label")

        if not from_user or not to_user or not session_label:
            flash("⚠️ Please fill out all fields.")
            return render_template("create_session.html")

        if from_user == to_user:
            flash("⚠️ Cannot create a session with yourself.")
            return render_template("create_session.html")

        sender = User.query.filter_by(name=from_user).first()
        receiver = User.query.filter_by(name=to_user).first()

        if not sender or not receiver:
            flash("❌ One or both users were not found.")
            return render_template("create_session.html")

        # 🧠 Check if session already exists
        existing = Session.query.filter_by(
            from_user=from_user,
            to_user=to_user,
            label=session_label
        ).first()
        if existing:
            flash("⚠️ A session with this label already exists.")
            return render_template("create_session.html")

        # ✅ Generate Caesar key
        session_key = random.randint(0, 25)

        # 🔐 Encrypt Caesar key with both public keys
        encrypted_for_sender = rsa_encrypt(session_key, sender.e, sender.n)
        encrypted_for_receiver = rsa_encrypt(session_key, receiver.e, receiver.n)

        # 💾 Save session in DB
        new_session = Session(
            from_user=from_user,
            to_user=to_user,
            label=session_label,
            encrypted_for_sender=encrypted_for_sender,
            encrypted_for_receiver=encrypted_for_receiver
        )
        db.session.add(new_session)
        db.session.commit()

        encrypted_keys = {
            from_user: encrypted_for_sender,
            to_user: encrypted_for_receiver
        }

        flash(f"✅ Session created! Caesar key encrypted below.")
        return render_template("create_session.html",
                               from_user=from_user,
                               to_user=to_user,
                               session_label=session_label,
                               encrypted_keys=encrypted_keys)

    return render_template("create_session.html")


'''
@app.route("/decrypt-key", methods=["GET", "POST"])
def decrypt_key():
    if request.method == "POST":
        username = request.form.get("username")
        encrypted_key = request.form.get("encrypted_key")
        d = request.form.get("d")

        if not username or not encrypted_key or not d:
            flash("⚠️ All fields are required.")
            return render_template("decrypt_key.html", decrypted_key=None)

        user = User.query.filter_by(name=username).first()

        if not user:
            flash("❌ User not found.")
            return render_template("decrypt_key.html", decrypted_key=None)

        try:
            caesar_key = rsa_decrypt(int(encrypted_key), int(d), user.n)
            flash("✅ Caesar key decrypted successfully.")
            return render_template("decrypt_key.html", decrypted_key=caesar_key)
        except Exception as e:
            flash(f"❌ Error decrypting Caesar key: {e}")
            return render_template("decrypt_key.html", decrypted_key=None)

    return render_template("decrypt_key.html", decrypted_key=None)
'''

@app.route("/send-message", methods=["GET", "POST"])
def send_message():
    if request.method == "POST":
        username = request.form.get("username")
        d = request.form.get("d")
        target_user = request.form.get("target_user")
        session_label = request.form.get("session_label")
        plaintext = request.form.get("plaintext")

        # ✅ Step 1: User provides their name and private key
        if username and d and not target_user:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("send_message.html", step=1)

            # Fetch all users the person has sessions with
            partners = db.session.query(Session.to_user).filter_by(from_user=username).distinct().all()
            from_other_side = db.session.query(Session.from_user).filter_by(to_user=username).distinct().all()
            all_users = list(set([p[0] for p in partners + from_other_side if p[0] != username]))

            return render_template("send_message.html", step=2, username=username, d=d, users=all_users)

        # ✅ Intermediate Step: User selected target_user but not session_label yet
        elif username and d and target_user and not session_label:
            session_labels_raw = db.session.query(Session.label).filter(
                ((Session.from_user == username) & (Session.to_user == target_user)) |
                ((Session.from_user == target_user) & (Session.to_user == username))
            ).distinct().all()
            session_labels = [row[0] for row in session_labels_raw]

            return render_template("send_message.html", step=2, username=username, d=d,
                                   users=[], target_user=target_user, session_labels=session_labels)

        # ✅ Step 2: User selected both target and session
        elif username and d and target_user and session_label and not plaintext:
            session = Session.query.filter(
                ((Session.from_user == username) & (Session.to_user == target_user)) |
                ((Session.from_user == target_user) & (Session.to_user == username)),
                Session.label == session_label
            ).first()

            if not session:
                flash("❌ Session not found.")
                return render_template("send_message.html", step=1)

            try:
                d = int(d)
                user = User.query.filter_by(name=username).first()
                enc_key = session.encrypted_for_sender if session.from_user == username else session.encrypted_for_receiver
                caesar_key = rsa_decrypt(enc_key, d, user.n)
                return render_template("send_message.html", step=3, username=username, d=d,
                                       target_user=target_user, session_label=session_label, caesar_key=caesar_key)
            except Exception as e:
                flash(f"❌ Failed to decrypt session key: {e}")
                return render_template("send_message.html", step=1)

        # ✅ Step 3: User submits plaintext to send
        elif username and target_user and session_label and plaintext and d:
            msg = caesar_encrypt(plaintext, int(request.form.get("caesar_key")))
            new_msg = Message(sender=username, receiver=target_user,
                              encrypted_text=msg, session_label=session_label)
            db.session.add(new_msg)
            db.session.commit()
            flash("✅ Message sent!")
            return redirect(url_for('send_message'))

        flash("⚠️ Please fill out required fields.")
        return render_template("send_message.html", step=1)

    # Initial GET request
    return render_template("send_message.html", step=1)




@app.route("/read-messages", methods=["GET", "POST"])
def read_messages():
    if request.method == "POST":
        username = request.form.get("username")
        from_user = request.form.get("from_user")
        session_label = request.form.get("session_label")
        d = request.form.get("d")

        # Step 1 → Step 2: Username entered
        if username and not from_user:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("read_messages.html", step=1)

            senders_raw = db.session.query(Message.sender).filter_by(receiver=username).distinct().all()
            senders = [s[0] for s in senders_raw]

            if not senders:
                flash("📭 No messages found.")
                return render_template("read_messages.html", step=1)

            return render_template("read_messages.html", step=2, username=username, senders=senders)

        # Step 2 → Step 3: Sender chosen
        elif username and from_user and not session_label:
            sessions = Session.query.filter(
                ((Session.from_user == username) & (Session.to_user == from_user)) |
                ((Session.from_user == from_user) & (Session.to_user == username))
            ).all()

            labels = [s.label for s in sessions]

            if not labels:
                flash("❌ No session found between you and this user.")
                return render_template("read_messages.html", step=2, username=username, senders=[from_user])

            return render_template("read_messages.html", step=3,
                                   username=username, from_user=from_user,
                                   session_labels=labels)

        # Step 3 → Step 4: Decrypt messages
        elif username and from_user and session_label and d:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("read_messages.html", step=1)

            session = Session.query.filter_by(label=session_label).filter(
                ((Session.from_user == username) & (Session.to_user == from_user)) |
                ((Session.from_user == from_user) & (Session.to_user == username))
            ).first()

            if not session:
                flash("❌ Session not found.")
                return render_template("read_messages.html", step=3,
                                       username=username, from_user=from_user, session_labels=[])

            try:
                d = int(d)
                enc_key = session.encrypted_for_sender if session.from_user == username else session.encrypted_for_receiver
                caesar_key = rsa_decrypt(enc_key, d, user.n)

                msgs = Message.query.filter_by(receiver=username, sender=from_user, session_label=session_label).all()
                messages_list = []
                for msg in msgs:
                    decrypted = caesar_decrypt(msg.encrypted_text, caesar_key)
                    messages_list.append({
                        "encrypted": msg.encrypted_text,
                        "decrypted": decrypted
                    })

                return render_template("read_messages.html", step=4,
                                       username=username,
                                       session_label=session_label,
                                       messages_list=messages_list)

            except Exception as e:
                flash(f"❌ Decryption error: {e}")
                return render_template("read_messages.html", step=3,
                                       username=username, from_user=from_user, session_labels=[session_label])

    # Default step = 1
    return render_template("read_messages.html", step=1)
