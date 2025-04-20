# caesar_utils.py

def caesar_encrypt(plaintext: str, shift: int) -> str:
    result = ""
    for char in plaintext:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            # shift letter by shift amount
            shifted = (ord(char) - base + shift) % 26
            result += chr(base + shifted)
        else:
            result += char  # keep punctuation, spaces, numbers
    return result

def caesar_decrypt(ciphertext: str, shift: int) -> str:
    return caesar_encrypt(ciphertext, -shift)


if __name__ == "__main__":
    message = "Hello, World!"
    key = 5

    encrypted = caesar_encrypt(message, key)
    decrypted = caesar_decrypt(encrypted, key)

    print(f"Original:  {message}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
