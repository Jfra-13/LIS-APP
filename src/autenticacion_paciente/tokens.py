from django.contrib.auth.tokens import PasswordResetTokenGenerator

class MagicLinkTokenGenerator(PasswordResetTokenGenerator):
    """
    Generador de tokens para enlaces mágicos de un solo uso.
    Hereda de PasswordResetTokenGenerator para aprovechar la lógica de seguridad
    y expiración de Django.
    """
    def _make_hash_value(self, user, timestamp):
        # Aseguramos que el token se invalide si el email cambia o el usuario se desactiva
        return (
            str(user.pk) + str(timestamp) + str(user.email) + str(user.is_active)
        )

account_activation_token = MagicLinkTokenGenerator()
