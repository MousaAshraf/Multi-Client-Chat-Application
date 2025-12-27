from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

KEY = b"this_is_16_bytes"  # 16 bytes = AES-128 (keep simple for project)

def encrypt_message(message: str) -> bytes:
    cipher = AES.new(KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(message.encode("utf-8"))

    # Send nonce + tag + ciphertext together
    return cipher.nonce + tag + ciphertext


def decrypt_message(data: bytes) -> str:
    nonce = data[:16]
    tag = data[16:32]
    ciphertext = data[32:]

    cipher = AES.new(KEY, AES.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    return plaintext.decode("utf-8")
