"""
Módulo responsável pelo download dos vídeos do YouTube utilizando yt-dlp.
Garante que o arquivo seja salvo com o nome original do vídeo e limpo de caracteres inválidos.
"""

import glob
import os
import re
import shutil
import yt_dlp


def find_ffmpeg():
    """Localiza o executável do FFmpeg no PATH, na pasta local ou nos pacotes do WinGet."""
    # 1. Verifica se já está no PATH
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    # 2. Verifica na pasta do próprio projeto
    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg

    local_bin_ffmpeg = os.path.join(os.getcwd(), "bin", "ffmpeg.exe")
    if os.path.exists(local_bin_ffmpeg):
        return local_bin_ffmpeg

    # 3. Verifica nas instalações comuns do WinGet no Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*ffmpeg*", "**", "bin", "ffmpeg.exe")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

        # Verifica pasta WindowsApps
        winapps_ffmpeg = os.path.join(local_app_data, "Microsoft", "WindowsApps", "ffmpeg.exe")
        if os.path.exists(winapps_ffmpeg):
            return winapps_ffmpeg

    return None


def is_ffmpeg_installed():
    """Verifica se o FFmpeg está instalado e acessível."""
    return find_ffmpeg() is not None


def has_node_js():
    """Verifica se o Node.js está instalado para suporte à descriptografia JS."""
    return shutil.which("node") is not None


class YouTubeDownloader:
    def __init__(self, output_dir=None, quality="best", format_type="video", progress_callback=None, log_callback=None):
        """
        :param output_dir: Diretório onde os vídeos serão salvos.
        :param quality: 'best', '1080p', '720p', '480p'
        :param format_type: 'video' (MP4) ou 'audio' (MP3/M4A)
        :param progress_callback: Função chamada com dados de progresso (percent, speed, eta, filename)
        :param log_callback: Função chamada para registrar mensagens de log (msg, level)
        """
        self.output_dir = output_dir or os.path.join(os.getcwd(), "downloads")
        self.quality = quality
        self.format_type = format_type
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.is_cancelled = False
        self.current_title = ""

        # Garante que a pasta de destino exista
        os.makedirs(self.output_dir, exist_ok=True)

    def log(self, message, level="INFO"):
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")

    def cancel(self):
        """Sinaliza para cancelar os downloads pendentes."""
        self.is_cancelled = True
        self.log("Cancelamento solicitado pelo usuário.", "WARNING")

    def _progress_hook(self, d):
        if self.is_cancelled:
            raise yt_dlp.utils.DownloadCancelled("Download cancelado pelo usuário.")

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            filename = os.path.basename(d.get("filename", ""))

            if self.progress_callback:
                self.progress_callback({
                    "status": "downloading",
                    "percent": percent,
                    "downloaded": downloaded,
                    "total": total,
                    "speed": speed,
                    "eta": eta,
                    "filename": filename or self.current_title
                })
        elif status == "finished":
            filename = os.path.basename(d.get("filename", ""))
            if self.progress_callback:
                self.progress_callback({
                    "status": "finished",
                    "percent": 100.0,
                    "filename": filename or self.current_title
                })

    def _build_ydl_opts(self):
        ffmpeg_exe = find_ffmpeg()
        ffmpeg_available = ffmpeg_exe is not None
        node_available = has_node_js()

        # O modelo outtmpl garante que o arquivo seja salvo com o título exato do vídeo!
        # %(title)s = Nome do vídeo no YouTube
        # %(ext)s = Extensão do arquivo (mp4, mp3, etc.)
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "windowsfilenames": True,      # Remove caracteres inválidos para o Windows (: * ? " < > |)
            "restrictfilenames": False,    # Preserva espaços e caracteres acentuados em português
            "noplaylist": True,            # Se o link tiver &list=, baixa apenas o vídeo individual
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
        }

        if ffmpeg_available:
            ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_exe)

        if node_available:
            ydl_opts["js_runtimes"] = {"node": {}}
            ydl_opts["remote_components"] = ["ejs:github"]

        # Configuração de Formato e Qualidade
        if self.format_type == "audio":
            if ffmpeg_available:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            else:
                # Sem ffmpeg, baixa o melhor áudio nativo (m4a/webm)
                ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            # Formato de Vídeo
            if self.quality == "720p":
                if ffmpeg_available:
                    ydl_opts["format"] = (
                        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo[height<=720]+bestaudio/"
                        "best[height<=720][ext=mp4]/best[height<=720]/best"
                    )
                    ydl_opts["merge_output_format"] = "mp4"
                else:
                    ydl_opts["format"] = "best[height<=720][ext=mp4]/best[ext=mp4]/best"

            elif self.quality == "1080p":
                if ffmpeg_available:
                    ydl_opts["format"] = (
                        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo[height<=1080]+bestaudio/"
                        "best[height<=1080][ext=mp4]/best[height<=1080]/best"
                    )
                    ydl_opts["merge_output_format"] = "mp4"
                else:
                    # Sem ffmpeg não é possível juntar trilhas separadas 1080p, pega o melhor disponível
                    ydl_opts["format"] = "best[height<=1080][ext=mp4]/best[ext=mp4]/best"

            else:  # 'best'
                if ffmpeg_available:
                    ydl_opts["format"] = (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo+bestaudio/"
                        "best[ext=mp4]/best"
                    )
                    ydl_opts["merge_output_format"] = "mp4"
                else:
                    ydl_opts["format"] = "best[ext=mp4]/best"

        return ydl_opts

    def extract_title(self, url):
        """Obtém o título do vídeo rapidamente antes de baixar."""
        try:
            ydl_opts = {"quiet": True, "extract_flat": True}
            if has_node_js():
                ydl_opts["js_runtimes"] = {"node": {}}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("title", "Vídeo sem título")
        except Exception:
            return "Vídeo do YouTube"

    def download_url(self, url):
        """Baixa um único vídeo garantindo o nome do vídeo no arquivo final."""
        if self.is_cancelled:
            return False, "Operação cancelada"

        url = url.strip()
        if not url:
            return False, "Link vazio"

        self.log(f"Consultando informações: {url}...")
        title = self.extract_title(url)
        self.current_title = title
        self.log(f"Título identificado: \"{title}\"")

        ydl_opts = self._build_ydl_opts()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log(f"Baixando \"{title}\"...")
                ydl.download([url])
            self.log(f"Sucesso! Concluído: \"{title}\"", "SUCCESS")
            return True, title
        except yt_dlp.utils.DownloadCancelled:
            self.log(f"Download de \"{title}\" cancelado.", "WARNING")
            return False, "Cancelado"
        except Exception as e:
            err_msg = str(e)
            self.log(f"Erro ao baixar \"{title}\": {err_msg}", "ERROR")
            return False, err_msg

    def download_batch(self, urls, on_video_start=None, on_video_complete=None):
        """
        Baixa uma lista de URLs sequencialmente.
        :param urls: Lista ou iterável de URLs
        :param on_video_start: Callback (index, total, url)
        :param on_video_complete: Callback (index, total, url, success, info)
        :return: Dicionário com resumo dos downloads {sucessos: [...], falhas: [...]}
        """
        self.is_cancelled = False
        valid_urls = [u.strip() for u in urls if u and u.strip() and not u.strip().startswith("#")]
        total = len(valid_urls)

        results = {"success": [], "failed": []}

        if total == 0:
            self.log("Nenhum link válido fornecido.", "WARNING")
            return results

        self.log(f"Iniciando download de {total} vídeo(s)...")

        for idx, url in enumerate(valid_urls, 1):
            if self.is_cancelled:
                self.log("Processamento do lote interrompido pelo usuário.", "WARNING")
                break

            if on_video_start:
                on_video_start(idx, total, url)

            success, info = self.download_url(url)

            if success:
                results["success"].append({"url": url, "title": info})
            else:
                results["failed"].append({"url": url, "error": info})

            if on_video_complete:
                on_video_complete(idx, total, url, success, info)

        self.log(
            f"Finalizado! {len(results['success'])} baixado(s) com sucesso, "
            f"{len(results['failed'])} falha(s).",
            "SUCCESS" if len(results["failed"]) == 0 else "WARNING"
        )
        return results
