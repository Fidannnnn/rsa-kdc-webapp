# flask py
# app.py

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from models import db, User, Message, Session
from rsa_utils import rsa_encrypt, generate_rsa_keys, rsa_decrypt
from caesar_utils import caesar_encrypt, caesar_decrypt
import random

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # needed for flash messages (yep, classic flask stuff)

# set up DB config from config.py
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

# bind SQLAlchemy to the app
db.init_app(app)

# create tables in DB if they don’t exist yet
with app.app_context():
    db.create_all()

# test: show all users + their public keys
with app.app_context():
    users = User.query.all()
    for user in users:
        print(user.name, user.e, user.n)

# sanity check route — loads home page just to make sure everything's alive
@app.route("/")
def home():
    return render_template("home.html")

# Register Page (GET + POST)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # get the name user typed in
        name = request.form.get("name")

        # if name is empty, just tell them to type smth
        if not name:
            flash("⚠️ Please enter your name.")
            return render_template("register.html")

        # check if the name is already in the DB
        if User.query.filter_by(name=name).first():
            flash("⚠️ User already exists!")
            return render_template("register.html")

        # generate RSA keys for the new user
        keys = generate_rsa_keys()
        e = keys['e']     # public exponent
        d = keys['d']     # private key (only shown to user)
        n = keys['n']     # modulus

        # save only what's public to DB (name, e, n)
        new_user = User(name=name, e=e, n=n)
        db.session.add(new_user)
        db.session.commit()

        # show success msg + the keys to user
        flash(f"✅ Registered user: {name}")
        return render_template("register.html", d=d, e=e, n=n, generated=True)

    # if GET request, just show the register page
    return render_template("register.html")


@app.route("/create-session", methods=["GET", "POST"])
def create_session():
    if request.method == "POST":
        # get all form values
        from_user = request.form.get("from_user")
        to_user = request.form.get("to_user")
        session_label = request.form.get("session_label")

        # check if any field is missing
        if not from_user or not to_user or not session_label:
            flash("⚠️ Please fill out all fields.")
            return render_template("create_session.html")

        # no messaging yourself bruh
        if from_user == to_user:
            flash("⚠️ Cannot create a session with yourself.")
            return render_template("create_session.html")

        # find sender + receiver in DB
        sender = User.query.filter_by(name=from_user).first()
        receiver = User.query.filter_by(name=to_user).first()

        # if one doesn’t exist, abort
        if not sender or not receiver:
            flash("❌ One or both users were not found.")
            return render_template("create_session.html")

        # check if a session with this label already exists
        existing = Session.query.filter_by(
            from_user=from_user,
            to_user=to_user,
            label=session_label
        ).first()
        if existing:
            flash("⚠️ A session with this label already exists.")
            return render_template("create_session.html")

        # generate a Caesar key (just a number between 0-25)
        session_key = random.randint(0, 25)

        # encrypt the Caesar key for both users using their public RSA keys
        encrypted_for_sender = rsa_encrypt(session_key, sender.e, sender.n)
        encrypted_for_receiver = rsa_encrypt(session_key, receiver.e, receiver.n)

        # save this session to the DB
        new_session = Session(
            from_user=from_user,
            to_user=to_user,
            label=session_label,
            encrypted_for_sender=encrypted_for_sender,
            encrypted_for_receiver=encrypted_for_receiver
        )
        db.session.add(new_session)
        db.session.commit()

        # show both encrypted keys (for debugging or just info)
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

    # GET request → just show the session creation form
    return render_template("create_session.html")


@app.route("/send-message", methods=["GET", "POST"])
def send_message():
    if request.method == "POST":
        # get all inputs from form
        username = request.form.get("username")
        d = request.form.get("d")  # private key
        target_user = request.form.get("target_user")
        session_label = request.form.get("session_label")
        plaintext = request.form.get("plaintext")

        # Step 1: User just entered name and private key, nothing else yet
        if username and d and not target_user:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("send_message.html", step=1)

            # get all users this person has sessions with (both directions)
            partners = db.session.query(Session.to_user).filter_by(from_user=username).distinct().all()
            from_other_side = db.session.query(Session.from_user).filter_by(to_user=username).distinct().all()
            all_users = list(set([p[0] for p in partners + from_other_side if p[0] != username]))

            # show them list of possible users to message
            return render_template("send_message.html", step=2, username=username, d=d, users=all_users)

        # User picked who to message, but not the session label yet
        elif username and d and target_user and not session_label:
            session_labels_raw = db.session.query(Session.label).filter(
                ((Session.from_user == username) & (Session.to_user == target_user)) |
                ((Session.from_user == target_user) & (Session.to_user == username))
            ).distinct().all()
            session_labels = [row[0] for row in session_labels_raw]

            # show all labels (in case they have multiple sessions)
            return render_template("send_message.html", step=2, username=username, d=d,
                                   users=[], target_user=target_user, session_labels=session_labels)

        # Step 2 done: user selected target + label → time to decrypt Caesar key
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
                d = int(d)  # private key as int
                user = User.query.filter_by(name=username).first()
                # get correct encrypted key based on direction of session
                enc_key = session.encrypted_for_sender if session.from_user == username else session.encrypted_for_receiver
                # decrypt Caesar key with RSA
                caesar_key = rsa_decrypt(enc_key, d, user.n)

                # now we’re ready to write the message
                return render_template("send_message.html", step=3, username=username, d=d,
                                       target_user=target_user, session_label=session_label, caesar_key=caesar_key)
            except Exception as e:
                flash(f"❌ Failed to decrypt session key: {e}")
                return render_template("send_message.html", step=1)

        # Step 3: all set, user wrote message → encrypt and store it
        elif username and target_user and session_label and plaintext and d:
            msg = caesar_encrypt(plaintext, int(request.form.get("caesar_key")))
            new_msg = Message(sender=username, receiver=target_user,
                              encrypted_text=msg, session_label=session_label)
            db.session.add(new_msg)
            db.session.commit()
            flash("✅ Message sent!")
            return redirect(url_for('send_message'))

        # fallback → something’s missing or not right
        flash("⚠️ Please fill out required fields.")
        return render_template("send_message.html", step=1)

    # GET request → just load step 1
    return render_template("send_message.html", step=1)




@app.route("/read-messages", methods=["GET", "POST"])
def read_messages():
    if request.method == "POST":
        username = request.form.get("username")
        from_user = request.form.get("from_user")
        session_label = request.form.get("session_label")
        d = request.form.get("d")  # private RSA key

        # Step 1 → Step 2: user entered their name
        if username and not from_user:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("read_messages.html", step=1)

            # get all people who sent this user a message
            senders_raw = db.session.query(Message.sender).filter_by(receiver=username).distinct().all()
            senders = [s[0] for s in senders_raw]

            if not senders:
                flash("📭 No messages found.")
                return render_template("read_messages.html", step=1)

            # show list of users who sent msgs
            return render_template("read_messages.html", step=2, username=username, senders=senders)

        # Step 2 → Step 3: user picked a sender, now show session labels
        elif username and from_user and not session_label:
            sessions = Session.query.filter(
                ((Session.from_user == username) & (Session.to_user == from_user)) |
                ((Session.from_user == from_user) & (Session.to_user == username))
            ).all()

            labels = [s.label for s in sessions]

            if not labels:
                flash("❌ No session found between you and this user.")
                return render_template("read_messages.html", step=2, username=username, senders=[from_user])

            # show session label options
            return render_template("read_messages.html", step=3,
                                   username=username, from_user=from_user,
                                   session_labels=labels)

        # Step 3 → Step 4: user picked label, now we decrypt messages
        elif username and from_user and session_label and d:
            user = User.query.filter_by(name=username).first()
            if not user:
                flash("❌ User not found.")
                return render_template("read_messages.html", step=1)

            # find the session based on label + who it’s with
            session = Session.query.filter_by(label=session_label).filter(
                ((Session.from_user == username) & (Session.to_user == from_user)) |
                ((Session.from_user == from_user) & (Session.to_user == username))
            ).first()

            if not session:
                flash("❌ Session not found.")
                return render_template("read_messages.html", step=3,
                                       username=username, from_user=from_user, session_labels=[])

            try:
                d = int(d)  # make sure key is int
                # get the correct encrypted Caesar key based on direction
                enc_key = session.encrypted_for_sender if session.from_user == username else session.encrypted_for_receiver
                caesar_key = rsa_decrypt(enc_key, d, user.n)

                # get all messages from sender for this session
                msgs = Message.query.filter_by(receiver=username, sender=from_user, session_label=session_label).all()
                messages_list = []

                # decrypt them one by one
                for msg in msgs:
                    decrypted = caesar_decrypt(msg.encrypted_text, caesar_key)
                    messages_list.append({
                        "encrypted": msg.encrypted_text,
                        "decrypted": decrypted
                    })

                # show the messages
                return render_template("read_messages.html", step=4,
                                       username=username,
                                       session_label=session_label,
                                       messages_list=messages_list)

            except Exception as e:
                flash(f"❌ Decryption error: {e}")
                return render_template("read_messages.html", step=3,
                                       username=username, from_user=from_user, session_labels=[session_label])

    # GET request or fallback → start at step 1
    return render_template("read_messages.html", step=1)

