from poly import generate_new_polyvec, get_noise_poly, polyvec_ntt, polyvec_reduce, polyvec_pointwise_acc_mont, \
    poly_to_mont, polyvec_add, poly_from_data, poly_inv_ntt_mont, polyvec_inv_ntt, poly_add, poly_reduce, poly_sub, \
    poly_to_msg
from params import KYBER_SYM_BYTES
from Crypto.Hash import SHA3_512
from Crypto.Random import get_random_bytes
from util import cast_to_byte
from indcpa import generate_matrix, pack_private_key, pack_public_key, unpack_public_key, pack_ciphertext, unpack_ciphertext, \
    unpack_private_key

def generate_kyber_keys(params_k, seed = None):
    """
    generate public and private keys for cpa-secure pubkey encryption
    scheme underlying Kyber
    :param params_k: int
    :return: tuple of (byte array privkey, byte array pubkey)
    """
    skpv = generate_new_polyvec(params_k)                       # genereowanie nowego wielomianu
    pkpv = generate_new_polyvec(params_k)                       # genereowanie nowego wielomianu
    e = generate_new_polyvec(params_k)                          # genereowanie nowego wielomianu
    public_seed = [ 0 for x in range(0, KYBER_SYM_BYTES)]       # wprowadzanie błędów?
    noise_seed = [ 0 for x in range(0, KYBER_SYM_BYTES)]        # --||--
    h = SHA3_512.new()
    public_seed = get_random_bytes(KYBER_SYM_BYTES)
    if(seed != None):
        public_seed = bytearray([x & 0xFF for x in seed])
    h.update(public_seed)
    full_seed = h.digest()
    full_seed = [ cast_to_byte(x) for x in full_seed ]
    public_seed = [ full_seed[i] for i in range(0, KYBER_SYM_BYTES)]
    noise_seed = [ full_seed[KYBER_SYM_BYTES + i] for i in range(0, KYBER_SYM_BYTES)]
    a = generate_matrix(public_seed, False, params_k)
    nonce = 0
    for i in range(0, params_k):
        skpv[i] = get_noise_poly(noise_seed, nonce, params_k)
        nonce = cast_to_byte(nonce + 1)
    for i in range(0, params_k):
        e[i] = get_noise_poly(noise_seed, nonce, params_k)
        nonce = cast_to_byte(nonce + 1)
    skpv = polyvec_ntt(skpv, params_k)
    skpv = polyvec_reduce(skpv, params_k)
    e = polyvec_ntt(e, params_k)
    for i in range(0, params_k):
        #print(a[i])
        #print(skpv)
        temp = polyvec_pointwise_acc_mont(a[i], skpv, params_k)
        pkpv[i] = poly_to_mont(temp)
    pkpv = polyvec_add(pkpv, e, params_k)
    pkpv = polyvec_reduce(pkpv, params_k)
    #print("pubkey_reduced")
    #print(pkpv)
    packed_priv_key = pack_private_key(skpv, params_k)
    #print("public_seed: " + str(public_seed))
    packed_pub_key = pack_public_key(pkpv, public_seed, params_k)
    return (packed_priv_key, packed_pub_key)


def encrypt(m, pubkey, coins, params_k):
    """
    encrypt the given message using Kyber
    :param m: message, byte array
    :param pubkey: public key, byte array
    :param coins: randomness, byte array
    :param params_k: int
    :return: ciphertext, byte array
    """

    # Generate new polynomial vectors
    r_daszek = generate_new_polyvec(params_k)  # Secret polynomial vector       # wektor
    e1 = generate_new_polyvec(params_k)  # Error polynomial vector
    u = generate_new_polyvec(params_k)  # Encrypted polynomial vector ??

    # Unpack the public key and retrieve the pubkey seed
    unpacked_public_key, pubkey_seed = unpack_public_key(pubkey, params_k)      # chyba t_daszek, czy transp ??
                                                                                # public_seed to moze byc ρ ??

    # Convert the message to a polynomial
    mess = poly_from_data(m)

    # Generate the matrix A (used in encryption) from the pubkey seed
    A = generate_matrix(pubkey_seed[0:KYBER_SYM_BYTES], True, params_k)         # linie 4-8, czy transp??

    # Generate noise polynomials for sp and ep
    for i in range(0, params_k):
        r_daszek[i] = get_noise_poly(coins, cast_to_byte(i), params_k)          # linie 9-12
        e1[i] = get_noise_poly(coins, cast_to_byte(i + params_k), 3)            # linie 13-16

    # Generate noise polynomial for epp
    e2 = get_noise_poly(coins, cast_to_byte(params_k * 2), 3)                   # linia 17 - generowanie wielomianu

    # Perform NTT (Number Theoretic Transform) on sp
    r_daszek = polyvec_ntt(r_daszek, params_k)                                  # linia 18 docs

    # Reduce the coefficients of sp
    r_daszek = polyvec_reduce(r_daszek, params_k)                                # to chyba tez w ramach linii 18

    # Mnozenie ^A^T @ ^r
    for i in range(0, params_k):                                                # linia 19
        u[i] = polyvec_pointwise_acc_mont(A[i], r_daszek, params_k)             # do czego jest to potrzebne
    # chyba jest to realizacja operacji kółka w nawiasach NTT

    # wykonanie NTT^-1 nad u

    u = polyvec_inv_ntt(u, params_k)                                            # linia 19 (czesc z ntt) (ta funkcja bo to wektor wielomianów)
    # dodanie szumow e1 do wektora u
    u = polyvec_add(u, e1, params_k)                                            # linia 19 + e1

    # Redukcja wspolczynikow wektora wielomianow
    u = polyvec_reduce(u, params_k)                                             # na wektorach wielomianów trzeba wywolywac te funkcje recznie po kazdym mnozeniu



    # chyba jest to realizacja operacji kółka w nawiasach NTT
    v = polyvec_pointwise_acc_mont(unpacked_public_key, r_daszek, params_k)     # linia 20

    # Perform inverse NTT on bp and v
    v = poly_inv_ntt_mont(v)                                                    # linia 20 docs (czesci z NTT^-1) (ta funkcja bo to jeden wielomian)

    # Dodanie szumu e2 i WIADOMOSCI
    v = poly_add(poly_add(v, e2), mess)                                         # linia 20  +e2 + Decompressed(Decode(m), 1)


    # Pack the ciphertext
    ret = pack_ciphertext(u, poly_reduce(v), params_k)     # linia 23 docs

    return ret



def decrypt(packed_ciphertext, private_key, params_k):
    """
    decrypt given byte array using Kyber
    :param packed_ciphertext: array of bytes
    :param private_key: array of bytes
    :param params_k: int
    :return: array of bytes
    """
    bp, v = unpack_ciphertext(packed_ciphertext, params_k)
    unpacked_privkey = unpack_private_key(private_key, params_k)
    bp = polyvec_ntt(bp, params_k)
    mp = polyvec_pointwise_acc_mont(unpacked_privkey, bp, params_k)
    mp = poly_inv_ntt_mont(mp)
    mp = poly_sub(v, mp)
    mp = poly_reduce(mp)
    ret = poly_to_msg(mp)
    return ret
