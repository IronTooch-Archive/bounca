import arrow
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import ExtensionOID, RFC822Name

# noinspection PyUnresolvedReferences
from cryptography.x509.extensions import ExtensionNotFound

# noinspection PyUnresolvedReferences
from cryptography.x509.oid import ExtendedKeyUsageOID
from django.db.models import signals
from django.utils import timezone
from factory.django import mute_signals

from certificate_engine.ssl.certificate import Certificate, CertificateError
from certificate_engine.ssl.key import Key
from certificate_engine.tests.helpers import CertificateTestCase
from certificate_engine.types import CertificateTypes
from x509_pki.models import KeyStore
from x509_pki.tests.factories import CertificateFactory, DistinguishedNameFactory


class EmailCertificateTest(CertificateTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root_key = Key().create_key("ed25519", None)
        subject = DistinguishedNameFactory(
            countryName="NL", stateOrProvinceName="Noord Holland", organizationName="Repleo"
        )

        cls.root_certificate = CertificateFactory(
            dn=subject, name="test client root certificate", expires_at=arrow.get(timezone.now()).shift(days=+30).date()
        )

        with mute_signals(signals.post_save):
            cls.root_certificate.save()
        root_certhandler = Certificate()
        root_certhandler.create_certificate(cls.root_certificate, cls.root_key.serialize())
        keystore = KeyStore(certificate=cls.root_certificate)
        keystore.crt = root_certhandler.serialize()
        keystore.key = cls.root_key.serialize()
        keystore.save()

        cls.int_key = Key().create_key("ed25519", None)
        subject = DistinguishedNameFactory(
            countryName=cls.root_certificate.dn.countryName,
            stateOrProvinceName=cls.root_certificate.dn.stateOrProvinceName,
            organizationName=cls.root_certificate.dn.organizationName,
        )
        cls.int_certificate = CertificateFactory(
            expires_at=arrow.get(timezone.now()).shift(days=+5).date(),
            name="test client intermediate certificate",
            type=CertificateTypes.INTERMEDIATE,
            parent=cls.root_certificate,
            dn=subject,
            crl_distribution_url="https://example.com/crl/cert.crl.pem",
            ocsp_distribution_host="https://example.com/ocsp/",
        )

        with mute_signals(signals.post_save):
            cls.int_certificate.save()

        int_certhandler = Certificate()
        int_certhandler.create_certificate(cls.int_certificate, cls.int_key.serialize())

        keystore = KeyStore(certificate=cls.int_certificate)
        keystore.crt = int_certhandler.serialize()
        keystore.key = cls.int_key.serialize()
        keystore.save()

        cls.key = Key().create_key("ed25519", None)

    def test_generate_client_certificate(self):
        client_subject = DistinguishedNameFactory(subjectAltNames=["jeroen", "info@bounca.org"])
        certificate = CertificateFactory(
            type=CertificateTypes.CLIENT_CERT, parent=self.int_certificate, dn=client_subject
        )
        certhandler = Certificate()
        certhandler.create_certificate(certificate, self.key.serialize())

        crt = certhandler.certificate

        # basicConstraints = CA:FALSE
        # keyUsage = critical, digitalSignature, keyEncipherment
        self.assert_user_certificate(crt, content_commitment=True)

        # authorityKeyIdentifier = keyid:always, issuer
        self.assert_authority_key(crt, self.int_key, issuer_certificate=self.int_certificate, critical=False)

        # subjectKeyIdentifier = hash
        self.assert_hash(crt, critical=False)

        # extendedKeyUsage = clientAuth, emailProtection
        self.assert_extension(
            crt,
            ExtensionOID.EXTENDED_KEY_USAGE,
            [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.EMAIL_PROTECTION],
        )

        # subjectAltName = @alt_names
        self.assert_extension(
            crt, ExtensionOID.SUBJECT_ALTERNATIVE_NAME, [RFC822Name("jeroen"), RFC822Name("info@bounca.org")]
        )

        # crlDistributionPoints
        self.assert_crl_distribution(crt, self.int_certificate)

        # OCSP
        # authorityInfoAccess = OCSP;URI:{{cert.ocsp_distribution_host}}
        self.assert_oscp(crt, self.int_certificate)

        # subject
        self.assert_subject(crt.subject, certificate)
        # issuer
        self.assert_subject(crt.issuer, self.int_certificate)

    def test_generate_client_certificate_minimal(self):
        client_subject = DistinguishedNameFactory(
            countryName=None,
            stateOrProvinceName=None,
            localityName=None,
            organizationName=None,
            organizationalUnitName=None,
            emailAddress=None,
            subjectAltNames=None,
            commonName="client cert",
        )
        certificate = CertificateFactory(
            type=CertificateTypes.CLIENT_CERT,
            name="test_generate_client_certificate_minimal",
            parent=self.int_certificate,
            dn=client_subject,
            crl_distribution_url=None,
            ocsp_distribution_host=None,
        )
        certificate.save()
        certhandler = Certificate()
        certhandler.create_certificate(certificate, self.key.serialize())

        crt = certhandler.certificate

        # basicConstraints = CA:FALSE
        # keyUsage = critical, digitalSignature, keyEncipherment
        self.assert_user_certificate(crt, content_commitment=True)

        # authorityKeyIdentifier = keyid:always, issuer
        self.assert_authority_key(crt, self.int_key, issuer_certificate=self.int_certificate, critical=False)

        # subjectKeyIdentifier = hash
        self.assert_hash(crt)

        # extendedKeyUsage = serverAuth
        self.assert_extension(
            crt,
            ExtensionOID.EXTENDED_KEY_USAGE,
            [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.EMAIL_PROTECTION],
        )

        # crlDistributionPoints
        self.assert_crl_distribution(crt, self.int_certificate)

        # OCSP
        # authorityInfoAccess = OCSP;URI:{{cert.ocsp_distribution_host}}
        self.assert_oscp(crt, self.int_certificate)

        # subject
        self.assert_subject(crt.subject, certificate)
        # issuer
        self.assert_subject(crt.issuer, self.int_certificate)

    def test_generate_client_certificate_no_subject_altnames(self):
        client_subject = DistinguishedNameFactory(subjectAltNames=None)
        certificate = CertificateFactory(
            type=CertificateTypes.CLIENT_CERT, parent=self.int_certificate, dn=client_subject
        )
        certhandler = Certificate()
        certhandler.create_certificate(certificate, self.key.serialize())

        crt = certhandler.certificate

        self.assertEqual(crt.serial_number, int(certificate.serial))
        self.assertEqual(
            crt.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw),
            self.key.key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            ),
        )

        with self.assertRaises(ExtensionNotFound):
            crt.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

    def test_generate_client_certificate_no_intermediate_ca(self):
        client_subject = DistinguishedNameFactory(subjectAltNames=None)
        certificate = CertificateFactory(
            type=CertificateTypes.CLIENT_CERT, parent=self.root_certificate, dn=client_subject
        )

        certhandler = Certificate()
        certhandler.create_certificate(certificate, self.key.serialize())

        crt = certhandler.certificate

        self.assertEqual(crt.serial_number, int(certificate.serial))
        self.assertEqual(
            crt.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw),
            self.key.key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            ),
        )

        # extendedKeyUsage = serverAuth
        self.assert_extension(
            crt,
            ExtensionOID.EXTENDED_KEY_USAGE,
            [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.EMAIL_PROTECTION],
        )

        # subject
        self.assert_subject(crt.subject, certificate)

        # issuer
        self.assert_subject(crt.issuer, self.root_certificate)

        # authorityKeyIdentifier = keyid:always, issuer
        self.assert_authority_key(crt, self.root_key, issuer_certificate=self.root_certificate, critical=False)

        # subjectKeyIdentifier = hash
        self.assert_hash(crt, critical=False)

    def test_generate_client_certificate_parent_client_cert(self):
        client_subject = DistinguishedNameFactory(subjectAltNames=None)
        certificate = CertificateFactory(
            type=CertificateTypes.CLIENT_CERT,
            name="test_generate_client_certificate_parent_client_cert_1",
            parent=self.int_certificate,
            dn=client_subject,
            crl_distribution_url=None,
            ocsp_distribution_host=None,
        )
        certificate.save()
        certhandler = Certificate()
        certhandler.create_certificate(certificate, self.key.serialize())

        client_subject = DistinguishedNameFactory()
        with self.assertRaises(CertificateError) as context:
            certificate_request = CertificateFactory(
                type=CertificateTypes.CLIENT_CERT,
                name="test_generate_client_certificate_parent_client_cert_2",
                parent=certificate,
                dn=client_subject,
            )
            certhandler = Certificate()
            certhandler.create_certificate(certificate_request, self.key.serialize())

        self.assertEqual("A root or intermediate parent is expected", str(context.exception))
