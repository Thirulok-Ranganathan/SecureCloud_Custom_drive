import rsa

public, private = rsa.newkeys(2048)

with open("sample.key",'wb') as f:
    f.write(public.save_pkcs1("PEM"))