import requests
from rsa_utils import generate_rsa_keys, rsa_decrypt
from caesar_utils import caesar_encrypt, caesar_decrypt

# Server URL (this is local for now)
BASE_URL = "http://127.0.0.1:5000"

# generate RSA keys for this client (public + private pair)
keys = generate_rsa_keys()
print(f"🔐 Your RSA keys:\nPublic: (e={keys['e']}, n={keys['n']})\nPrivate: d={keys['d']}")

# ask user to register a name (used for sending/receiving)
name = input("\n📝 Enter your name to register: ").strip()

# register with the server by sending public key
resp = requests.post(f"{BASE_URL}/register", json={
    "name": name,
    "e": keys['e'],
    "n": keys['n']
})

if resp.status_code == 201:
    print(f"✅ Registered as {name}!")
else:
    print(f"⚠️ Registration error: {resp.json()}")
    exit()

# pick someone to talk to
partner = input("💬 Enter the name of the person you want to message: ").strip()

# ask the server (KDC) to send you a session key for Caesar
resp = requests.post(f"{BASE_URL}/request-session-key", json={
    "from": name,
    "to": partner
})

if resp.status_code != 200:
    print(f"❌ Error requesting session key: {resp.json()}")
    exit()

# get the encrypted Caesar key (encrypted with my public RSA key)
encrypted_key = resp.json()["caesar_key_encrypted"][name]
print(f"🛡️ Encrypted Caesar key received: {encrypted_key}")

# decrypt the Caesar key using my private RSA key
caesar_key = rsa_decrypt(encrypted_key, keys['d'], keys['n'])
print(f"🔓 Decrypted Caesar key: {caesar_key}")

# get a message from the user and encrypt it with the Caesar key
plaintext = input("✉️  Enter a message to send: ")
encrypted_msg = caesar_encrypt(plaintext, caesar_key)
print(f"🔐 Encrypted message: {encrypted_msg}")

# send the encrypted message to the server to deliver to partner
resp = requests.post(f"{BASE_URL}/send-message", json={
    "from": name,
    "to": partner,
    "message": encrypted_msg
})

print(f"📤 Message status: {resp.json()}")

# now check for any new messages for this user
print("\n📥 Checking for incoming messages...")
resp = requests.get(f"{BASE_URL}/read-message", params={"user": name})
messages = resp.json()

# if there are messages, decrypt and show them
if isinstance(messages, list) and messages:
    print(f"\n🧾 You have {len(messages)} message(s):")
    for msg in messages:
        sender = msg['from']
        ciphertext = msg['message']
        decrypted = caesar_decrypt(ciphertext, caesar_key)
        print(f"From {sender}:")
        print(f"🔒 {ciphertext}")
        print(f"🔓 {decrypted}\n")
else:
    print("📭 No new messages.")
