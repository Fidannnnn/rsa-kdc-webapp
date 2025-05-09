# caesar_utils.py

# function to encrypt a string using Caesar Cipher
def caesar_encrypt(plaintext, shift):
    result = ""
    for char in plaintext:
        if char.isalpha():
            # decide if we’re working with uppercase or lowercase
            base = ord('A') if char.isupper() else ord('a')
            # shift the letter by 'shift' positions, wrap around with mod 26
            shifted = (ord(char) - base + shift) % 26
            result += chr(base + shifted)
        else:
            # if it’s not a letter (like punctuation or space), just keep it
            result += char
    return result

# decryption is just shifting backwards (negative shift)
def caesar_decrypt(ciphertext, shift):
    return caesar_encrypt(ciphertext, -shift)


if __name__ == "__main__":
    message = "Hello, World!"  # sample text
    key = 5  # Caesar key

    encrypted = caesar_encrypt(message, key)
    decrypted = caesar_decrypt(encrypted, key)

    print(f"Original:  {message}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
