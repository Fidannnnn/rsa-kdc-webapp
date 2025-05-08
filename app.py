#flask py
# app.py

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from models import db, User, Message
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
        return render_template("register.html", private_key=d)

    return render_template("register.html")

# POST /request-session-key
@app.route("/request-session-key", methods=["GET", "POST"])
def request_session_key():
    if request.method == "POST":
        from_user = request.form.get("from_user")
        to_user = request.form.get("to_user")

        if not from_user or not to_user:
            flash("⚠️ Please fill out both names.")
            return render_template("request_key.html")

        if from_user == to_user:
            flash("⚠️ You cannot request a key with yourself.")
            return render_template("request_key.html")

        sender = User.query.filter_by(name=from_user).first()
        receiver = User.query.filter_by(name=to_user).first()

        if not sender or not receiver:
            flash("❌ One or both users were not found.")
            return render_template("request_key.html")

        # Generate random Caesar key
        session_key = random.randint(0, 25)

        # Encrypt Caesar key with both users' public keys
        encrypted_for_sender = rsa_encrypt(session_key, sender.e, sender.n)
        encrypted_for_receiver = rsa_encrypt(session_key, receiver.e, receiver.n)

        encrypted_keys = {
            from_user: encrypted_for_sender,
            to_user: encrypted_for_receiver
        }

        flash(f"✅ Session key generated (Caesar shift = {session_key}) — encrypted below.")
        return render_template("request_key.html", encrypted_keys=encrypted_keys)

    return render_template("request_key.html")

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
        from_user = request.form.get("from_user")
        to_user = request.form.get("to_user")
        caesar_key = request.form.get("caesar_key")
        plaintext = request.form.get("plaintext")

        if not from_user or not to_user or not caesar_key or not plaintext:
            flash("⚠️ Please fill out all fields.")
            return render_template("send_message.html")

        sender = User.query.filter_by(name=from_user).first()
        receiver = User.query.filter_by(name=to_user).first()

        if not sender or not receiver:
            flash("❌ Sender or receiver not found.")
            return render_template("send_message.html")

        try:
            caesar_key = int(caesar_key)
            encrypted_msg = caesar_encrypt(plaintext, caesar_key)
        except Exception as e:
            flash(f"❌ Error encrypting message: {e}")
            return render_template("send_message.html")

        msg = Message(sender=from_user, receiver=to_user, encrypted_text=encrypted_msg)
        db.session.add(msg)
        db.session.commit()

        flash(f"✅ Message sent to {to_user}! Encrypted as: {encrypted_msg}")
        return render_template("send_message.html")

    return render_template("send_message.html")

@app.route("/read-messages", methods=["GET", "POST"])
def read_messages():
    if request.method == "POST":
        username = request.form.get("username")

        if not username:
            flash("⚠️ Please enter your username.")
            return render_template("read_messages.html", show_decrypt_form=False)

        user = User.query.filter_by(name=username).first()
        if not user:
            flash("❌ User not found.")
            return render_template("read_messages.html", show_decrypt_form=False)

        from_user = request.form.get("from_user")
        encrypted_key = request.form.get("caesar_key")  # this is still RSA-encrypted Caesar key
        d = request.form.get("d")

        if from_user and encrypted_key and d:
            try:
                encrypted_key = int(encrypted_key)
                d = int(d)

                # Decrypt Caesar key with RSA
                caesar_key = rsa_decrypt(encrypted_key, d, user.n)

                # Now decrypt messages from selected sender
                msgs = Message.query.filter_by(receiver=username, sender=from_user).all()
                messages_list = []
                for msg in msgs:
                    decrypted_text = caesar_decrypt(msg.encrypted_text, caesar_key)
                    messages_list.append({
                        "encrypted": msg.encrypted_text,
                        "decrypted": decrypted_text
                    })

                return render_template("read_messages.html", show_decrypt_form=True,
                                       username=username, senders=[], messages_list=messages_list)

            except Exception as e:
                flash(f"❌ Decryption error: {e}")
                return render_template("read_messages.html", show_decrypt_form=True,
                                       username=username, senders=[], messages_list=None)

        # Step 1 completed: get senders
        sender_names = db.session.query(Message.sender).filter_by(receiver=username).distinct().all()
        senders = [s[0] for s in sender_names]

        if not senders:
            flash("📭 No messages found.")
            return render_template("read_messages.html", show_decrypt_form=False)

        return render_template("read_messages.html", show_decrypt_form=True, username=username, senders=senders)

    return render_template("read_messages.html", show_decrypt_form=False)

