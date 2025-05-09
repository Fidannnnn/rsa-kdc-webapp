# rsa_utils.py

import random
from math import gcd


def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5)+1):
        if n % i == 0:
            return False
    return True

def generate_two_primes():
    primes = [i for i in range(10, 100) if is_prime(i)] # list of primes with 2 digits

    # choose p and q randomly
    p = random.choice(primes)
    q = random.choice(primes)

    #make sure they are not the same
    while q == p:
        q = random.choice(primes)
    return p, q

def modinv(e, phi):
    # function that does extended euclidean algo
    def egcd(a, b):
        # if a is 0, gcd is b and coeffs are (0,1) cuz 0*a + 1*b = b
        if a == 0: # base case
            return (b, 0, 1)
        # recursively call egcd with (b % a, a) until we hit base case
        gcd, y, x = egcd(b % a, a)
        # backtrack and compute the x, y for current step using the previous ones
        return (gcd, x - (b // a) * y, y)

    # get gcd and the modular inverse candidate x
    gcd, x, _ = egcd(e, phi)

    # if gcd isn’t 1, that means e and phi aren't coprime so no inverse
    if gcd != 1:
        raise Exception("Modular inverse does not exist")

    # return x mod phi so it’s in the positive range
    return x % phi

def generate_rsa_keys():
    p, q = generate_two_primes()
    n = p * q
    phi = (p - 1) * (q - 1) # phi(n)

    # Choose e (common values are 3, 5, 17, 257, 65537)
    e = 3
    while gcd(e, phi) != 1: # find e that is coprime with phi(n)
        e += 2

    d = modinv(e, phi) # get priv key
    return {"p": p, "q": q, "e": e, "d": d, "n": n}

def rsa_encrypt(message, e, n):
    return pow(message, e, n) # calculates M^e mod n

def rsa_decrypt(cipher: int, d: int, n: int) -> int:
    return pow(cipher, d, n)  # calculates C^d mod n


if __name__ == "__main__":
    keys = generate_rsa_keys()
    print("Generated keys:", keys)

    msg = 12  # Caesar key to encrypt
    encrypted = rsa_encrypt(msg, keys['e'], keys['n'])
    decrypted = rsa_decrypt(encrypted, keys['d'], keys['n'])

    print(f"\nOriginal Message: {msg}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
