"""Print the base64 SHA-256 of a certificate's public key (format Edge's --ignore-certificate-errors-spki-list expects)."""
import base64, hashlib, sys
from cryptography import x509
from cryptography.hazmat.primitives import serialization

cert = x509.load_pem_x509_certificate(open(sys.argv[1], "rb").read())
spki = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
print(base64.b64encode(hashlib.sha256(spki).digest()).decode())
