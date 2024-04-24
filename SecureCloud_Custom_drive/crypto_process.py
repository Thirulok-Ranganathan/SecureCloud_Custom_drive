from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Util.Padding import pad, unpad
import rsa

salt = b'Q\x13\xdc\xb0p\x0e\xdd\xe0\xe4\xf6i\xd5\xb6\xdc\xbdg\x88\x05\xef\xb0\\9\xf4q^\x14\x0e\xaa\\\x97\x1fr'
password = 'Valueisworth'

key = PBKDF2(password, salt, dkLen=32)

""" with open("public_key.pem",'rb') as f:
    public_key = rsa.PublicKey.load_pkcs1(f.read())

with open("private_key.pem",'rb') as s:
    private_key = rsa.PrivateKey.load_pkcs1(s.read()) """

def key_creation():
    public_key, private_key = rsa.newkeys(2048)
    private_ky = private_key.save_pkcs1().decode()
    pub_ky = public_key.save_pkcs1().decode()
    return (private_ky, pub_ky)

def encryption_process(message, public_key_str):

    public_key = rsa.PublicKey.load_pkcs1(public_key_str.encode())
    cipher = AES.new(key, AES.MODE_CBC) 
    padded_message = pad(message, AES.block_size)
    cipher_data = cipher.encrypt(padded_message)
    cipher_iv = cipher.iv
    ciphertext = cipher_iv + cipher_data
    encrypted_data = b''
    chunk_size = 214  # Define your desired chunk size

    # Chunk the data and encrypt each chunk
    for i in range(0, len(ciphertext), chunk_size):
        chunk = ciphertext[i:i+chunk_size]
        encrypted_chunk = rsa.encrypt(chunk, public_key)
        encrypted_data += encrypted_chunk

    return encrypted_data

    #with open("protected_data.bin",'wb') as pro:
        #pro.write(cipher.iv)
        #pro.write(cipher_data)
    #return combined_encrypted


def decryption_process(encrypted_data, private_key_str):
    
    private_key = rsa.PrivateKey.load_pkcs1(private_key_str.encode())
    decrypted_data = b''

    # Decrypt each chunk of the encrypted data
    for i in range(0, len(encrypted_data), 256):  # Assuming 256 bytes per chunk
        decrypted_chunk = rsa.decrypt(encrypted_data[i:i + 256], private_key)
        decrypted_data += decrypted_chunk

    rsa_decrypt = decrypted_data
    iv = rsa_decrypt[:16]
    cipher_text = rsa_decrypt[16:]

    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    Original_data = unpad(cipher.decrypt(cipher_text), AES.block_size)
    return Original_data

