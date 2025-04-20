# rsa_utils.py

import random
from math import gcd

# ---------------------------
# Prime checking (for p and q)
# ---------------------------
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5)+1):
        if n % i == 0:
            return False
    return True

# ---------------------------
# Generate two random prime numbers (double-digit)
# ---------------------------
def generate_two_primes():
    primes = [i for i in range(10, 100) if is_prime(i)]
    p = random.choice(primes)
    q = random.choice(primes)
    while q == p:
        q = random.choice(primes)
    return p, q

# ---------------------------
# Extended Euclidean Algorithm to find modular inverse
# ---------------------------
def modinv(e, phi):
    def egcd(a, b):
        if a == 0:
            return (b, 0, 1)
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)

    g, x, _ = egcd(e, phi)
    if g != 1:
        raise Exception("Modular inverse does not exist")
    return x % phi

# ---------------------------
# RSA Key Generation
# ---------------------------
def generate_rsa_keys():
    p, q = generate_two_primes()
    n = p * q
    phi = (p - 1) * (q - 1)

    # Choose e (common values are 3, 5, 17, 257, 65537)
    e = 3
    while gcd(e, phi) != 1:
        e += 2

    d = modinv(e, phi)
    return {"p": p, "q": q, "e": e, "d": d, "n": n}

# ---------------------------
# RSA Encryption and Decryption
# ---------------------------
def rsa_encrypt(message: int, e: int, n: int) -> int:
    return pow(message, e, n)

def rsa_decrypt(cipher: int, d: int, n: int) -> int:
    return pow(cipher, d, n)


if __name__ == "__main__":
    keys = generate_rsa_keys()
    print("Generated keys:", keys)

    msg = 12  # Caesar key to encrypt
    encrypted = rsa_encrypt(msg, keys['e'], keys['n'])
    decrypted = rsa_decrypt(encrypted, keys['d'], keys['n'])

    print(f"\nOriginal Message: {msg}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
