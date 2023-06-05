from ccakem import kem_keygen512, kem_encaps512, kem_decaps512

priv, pub = kem_keygen512()
secret1, cipher = kem_encaps512(pub)
secret2 = kem_decaps512(priv, cipher)
