#flask py
# app.py

from flask import Flask, request, jsonify
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from models import db, User, Message
from rsa_utils import rsa_encrypt
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

# Just to check it's working
@app.route("/")
def home():
    return "🔐 KDC Flask App is Running!"

# Register a user (POST /register)
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    name = data.get("name")
    e = data.get("e")
    n = data.get("n")

    if not name or not e or not n:
        return jsonify({"error": "Missing name, e, or n"}), 400

    # Check if user already exists
    if User.query.filter_by(name=name).first():
        return jsonify({"error": "User already exists"}), 409

    # Create and store user
    new_user = User(name=name, e=e, n=n)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": f"✅ User '{name}' registered successfully!"}), 201


# POST /request-session-key
@app.route("/request-session-key", methods=["POST"])
def request_session_key():
    data = request.get_json()
    from_user = data.get("from")
    to_user = data.get("to")

    if not from_user or not to_user:
        return jsonify({"error": "Missing 'from' or 'to' field"}), 400

    if from_user == to_user:
        return jsonify({"error": "Cannot generate session key with self"}), 400

    # Get both users from DB
    sender = User.query.filter_by(name=from_user).first()
    receiver = User.query.filter_by(name=to_user).first()

    if not sender or not receiver:
        return jsonify({"error": "User not found"}), 404

    # Generate Caesar session key (0–25)
    session_key = random.randint(0, 25)

    # Encrypt session key for both users
    encrypted_for_sender = rsa_encrypt(session_key, sender.e, sender.n)
    encrypted_for_receiver = rsa_encrypt(session_key, receiver.e, receiver.n)

    return jsonify({
        "caesar_key_encrypted": {
            from_user: encrypted_for_sender,
            to_user: encrypted_for_receiver
        },
        "note": f"Both users received the same Caesar key encrypted with their public keys."
    }), 200

@app.route("/send-message", methods=["POST"])
def send_message():
    data = request.get_json()
    sender = data.get("from")
    receiver = data.get("to")
    encrypted_message = data.get("message")

    if not sender or not receiver or not encrypted_message:
        return jsonify({"error": "Missing sender, receiver, or message"}), 400

    # Optional: check if both users exist
    if not User.query.filter_by(name=sender).first():
        return jsonify({"error": "Sender not found"}), 404
    if not User.query.filter_by(name=receiver).first():
        return jsonify({"error": "Receiver not found"}), 404

    msg = Message(sender=sender, receiver=receiver, encrypted_text=encrypted_message)
    db.session.add(msg)
    db.session.commit()

    return jsonify({"message": "Encrypted message sent!"}), 201

@app.route("/read-message", methods=["GET"])
def read_message():
    user = request.args.get("user")

    if not user:
        return jsonify({"error": "Missing 'user' query parameter"}), 400

    messages = Message.query.filter_by(receiver=user).all()

    if not messages:
        return jsonify({"message": "No messages found."}), 200

    return jsonify([
        {
            "from": msg.sender,
            "to": msg.receiver,
            "message": msg.encrypted_text
        }
        for msg in messages
    ]), 200
