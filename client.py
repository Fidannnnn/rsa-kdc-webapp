import requests
from rsa_utils import generate_rsa_keys, rsa_decrypt
from caesar_utils import caesar_encrypt, caesar_decrypt

# Server URL
BASE_URL = "http://127.0.0.1:5000"

# Generate RSA keypair for this client
keys = generate_rsa_keys()
print(f"🔐 Your RSA keys:\nPublic: (e={keys['e']}, n={keys['n']})\nPrivate: d={keys['d']}")

# Register with the server
name = input("\n📝 Enter your name to register: ").strip()

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

# Choose a friend to chat with
partner = input("💬 Enter the name of the person you want to message: ").strip()

# Request Caesar session key from KDC
resp = requests.post(f"{BASE_URL}/request-session-key", json={
    "from": name,
    "to": partner
})

if resp.status_code != 200:
    print(f"❌ Error requesting session key: {resp.json()}")
    exit()

encrypted_key = resp.json()["caesar_key_encrypted"][name]
print(f"🛡️ Encrypted Caesar key received: {encrypted_key}")

# Decrypt Caesar key
caesar_key = rsa_decrypt(encrypted_key, keys['d'], keys['n'])
print(f"🔓 Decrypted Caesar key: {caesar_key}")

# Encrypt message using Caesar
plaintext = input("✉️  Enter a message to send: ")
encrypted_msg = caesar_encrypt(plaintext, caesar_key)
print(f"🔐 Encrypted message: {encrypted_msg}")

# Send message to server
resp = requests.post(f"{BASE_URL}/send-message", json={
    "from": name,
    "to": partner,
    "message": encrypted_msg
})

print(f"📤 Message status: {resp.json()}")

# Check for incoming messages
print("\n📥 Checking for incoming messages...")
resp = requests.get(f"{BASE_URL}/read-message", params={"user": name})
messages = resp.json()

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
