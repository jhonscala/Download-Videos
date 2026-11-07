"""
Módulo de Integração com o Google Drive.
Oferece suporte a:
1. Detecção automática de pasta sincronizada do Google Drive Desktop / Nuvem local.
2. Upload direto para o Google Drive na nuvem via Google Drive API v3 (OAuth 2.0).
3. Criação automática da pasta de destino no Drive.
4. Upload resumável com barra de progresso em tempo real.
"""

import os
import string
import mimetypes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_FILE = os.path.join(os.getcwd(), "token.json")
CREDENTIALS_FILE = os.path.join(os.getcwd(), "credentials.json")


def detect_local_google_drive():
    """
    Detecta se o Google Drive para Desktop está instalado e mapeado em alguma unidade (G:\\, H:\\, etc.)
    ou dentro da pasta do usuário.
    """
    candidates = ["Meu Drive", "My Drive", "Google Drive"]

    # 1. Verifica letras de unidade (G:, H:, etc.)
    for letter in string.ascii_uppercase:
        drive_root = f"{letter}:\\"
        if os.path.exists(drive_root):
            for cand in candidates:
                full_path = os.path.join(drive_root, cand)
                if os.path.exists(full_path):
                    return full_path

    # 2. Verifica pasta do usuário
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        for cand in candidates:
            full_path = os.path.join(user_profile, cand)
            if os.path.exists(full_path):
                return full_path

    return None


class GoogleDriveUploader:
    def __init__(self, credentials_path=None, token_path=None, log_callback=None):
        self.credentials_path = credentials_path or CREDENTIALS_FILE
        self.token_path = token_path or TOKEN_FILE
        self.log_callback = log_callback
        self.service = None
        self.user_email = None

    def log(self, message, level="INFO"):
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] [Google Drive] {message}")

    def is_authenticated(self):
        """Verifica se há um token salvo e válido."""
        if not os.path.exists(self.token_path):
            return False
        try:
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            if creds and creds.valid:
                return True
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                return True
        except Exception:
            return False
        return False

    def authenticate(self):
        """
        Realiza o fluxo de autenticação OAuth 2.0.
        Abre o navegador padrão para o usuário autorizar o acesso.
        """
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Arquivo '{os.path.basename(self.credentials_path)}' não encontrado na pasta do programa.\n"
                        "Consulte as instruções no app para obter o arquivo gratuitamente no Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Salva o token para as próximas execuções
            with open(self.token_path, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        self.service = build("drive", "v3", credentials=creds)
        self.get_user_info()
        return True

    def get_service(self):
        if not self.service:
            if not self.authenticate():
                raise RuntimeError("Falha ao autenticar com o Google Drive.")
        return self.service

    def get_user_info(self):
        """Obtém o e-mail da conta conectada."""
        try:
            service = self.get_service()
            about = service.about().get(fields="user(emailAddress,displayName)").execute()
            user = about.get("user", {})
            self.user_email = user.get("emailAddress", "Conta Conectada")
            return self.user_email
        except Exception:
            return "Conta Conectada"

    def disconnect(self):
        """Remove o token salvo desvinculando a conta."""
        if os.path.exists(self.token_path):
            try:
                os.remove(self.token_path)
            except Exception:
                pass
        self.service = None
        self.user_email = None

    def get_or_create_folder(self, folder_name="YouTube Downloads", parent_id=None):
        """
        Localiza uma pasta pelo nome no Google Drive ou cria uma nova se não existir.
        Retorna o ID da pasta.
        """
        service = self.get_service()
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        response = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = response.get("files", [])

        if files:
            return files[0]["id"]

        # Cria a pasta
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            folder_metadata["parents"] = [parent_id]

        folder = service.files().create(body=folder_metadata, fields="id").execute()
        self.log(f"Pasta '{folder_name}' criada com sucesso no Google Drive (ID: {folder.get('id')}).", "SUCCESS")
        return folder.get("id")

    def upload_file(self, file_path, folder_id=None, progress_callback=None):
        """
        Faz upload de um arquivo para o Google Drive com suporte a arquivos grandes (resumable upload).
        :param file_path: Caminho completo do arquivo no disco
        :param folder_id: ID da pasta destino no Google Drive (opcional)
        :param progress_callback: Função callback(percent, speed_str)
        :return: Dicionário com informações do arquivo criado (id, name, webViewLink)
        """
        service = self.get_service()
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "video/mp4" if file_path.endswith(".mp4") else "audio/mpeg"

        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        # Chunk size de 5 MB para uploads estáveis
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True, chunksize=5 * 1024 * 1024)
        request = service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink")

        self.log(f"Iniciando upload de \"{file_name}\" para o Google Drive...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                if progress_callback:
                    progress_callback(percent, f"{percent}% enviado")

        if progress_callback:
            progress_callback(100, "Upload concluído")

        self.log(f"Upload concluído! \"{file_name}\" salvo no Google Drive.", "SUCCESS")
        return response
