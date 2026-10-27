import os
import json
from cryptography.fernet import Fernet 

from PySide6 import QtCore

from ..Event import Event

class CredentialManager(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.storage_path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/configs/credentials.enc"
        self.key_path = self.storage_path + '.key'
        self.key = self._load_or_generate_key()
        self.cipher_suite = Fernet(self.key)
        self.event = Event("")

    def _load_or_generate_key(self):
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as key_file:
                key_file.write(key)
        return key


    QtCore.Slot(str)
    def save_credentials(self, credentials):
        credentials_json = json.dumps(credentials).encode()
        encrypted_credentials = self.cipher_suite.encrypt(credentials_json)
        with open(self.storage_path, 'wb') as file:
            file.write(encrypted_credentials)
        print("Credentials saved successfully.")
    
    QtCore.Slot()
    def load_credentials(self):
        try:
            with open(self.storage_path, 'rb') as file:
                encrypted_credentials = file.read()
            decrypted_credentials = self.cipher_suite.decrypt(encrypted_credentials).decode()
            credentials = json.loads(decrypted_credentials)
            return credentials
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None

    def get_event(self):
        return self.event
"""
cm = CredentialManager()

credentials = {
    "username": "usuario_ejemplo",
    "password": "contraseña_secreta"
}
cm.save_credentials(credentials)

# Cargar credenciales
loaded_credentials = cm.load_credentials()
print(f"Loaded credentials: {loaded_credentials}")
"""