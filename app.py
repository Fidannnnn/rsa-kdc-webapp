#flask py
# app.py

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from models import db, User, Message
from rsa_utils import rsa_encrypt
from caesar_utils import caesar_encrypt
from caesar_utils import caesar_decrypt
import random
from rsa_utils import rsa_decrypt


app = Flask(__name__)
app.secret_key = 'supersecretkey'  # required for flash messages

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

# Just to check it's working
@app.route("/")
def home():
    return """
        <h2>Welcome to the KDC Web App</h2>
        <ul>
            <li><a href='/register'>Register a user</a></li>
            <li><a href='/request-session-key'>Request session key</a></li>
            <li><a href='/decrypt-key'>Decrypt Caesar key</a></li>
            <li><a href='/send-message'>Send a message</a></li>
            <li><a href='/read-messages'>Read your messages</a></li>
        </ul>
    """


# 📝 Register Page (GET + POST)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        e = request.form.get("e")
        n = request.form.get("n")

        if not name or not e or not n:
            flash("⚠️ Please fill out all fields.")
            return render_template("register.html")

        if User.query.filter_by(name=name).first():
            flash("⚠️ User already exists!")
            return render_template("register.html")

        new_user = User(name=name, e=int(e), n=int(n))
        db.session.add(new_user)
        db.session.commit()

        flash(f"✅ Registered user: {name}")
        return redirect(url_for('register'))

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


@app.route("/decrypt-key", methods=["GET", "POST"])
def decrypt_key():
    if request.method == "POST":
        encrypted_key = request.form.get("encrypted_key")
        d = request.form.get("d")
        n = request.form.get("n")

        if not encrypted_key or not d or not n:
            flash("⚠️ All fields are required.")
            return render_template("decrypt_key.html", decrypted_key=None)

        try:
            caesar_key = rsa_decrypt(int(encrypted_key), int(d), int(n))
            flash("✅ Caesar key decrypted successfully.")
            return render_template("decrypt_key.html", decrypted_key=caesar_key)
        except Exception as e:
            flash(f"❌ Error decrypting Caesar key: {e}")
            return render_template("decrypt_key.html", decrypted_key=None)

    return render_template("decrypt_key.html", decrypted_key=None)

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
        caesar_key = request.form.get("caesar_key")

        if not username or not caesar_key:
            flash("⚠️ Please fill out both fields.")
            return render_template("read_messages.html", messages_list=None)

        user = User.query.filter_by(name=username).first()

        if not user:
            flash("❌ User not found.")
            return render_template("read_messages.html", messages_list=None)

        caesar_key = int(caesar_key)

        # Fetch all messages sent to this user
        received_msgs = Message.query.filter_by(receiver=username).all()

        if not received_msgs:
            flash("📭 No messages found.")
            return render_template("read_messages.html", messages_list=None)

        messages_list = []
        for msg in received_msgs:
            decrypted_text = caesar_decrypt(msg.encrypted_text, caesar_key)
            messages_list.append({
                "sender": msg.sender,
                "encrypted": msg.encrypted_text,
                "decrypted": decrypted_text
            })

        return render_template("read_messages.html", messages_list=messages_list)

    return render_template("read_messages.html", messages_list=None)
