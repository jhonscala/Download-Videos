"""
Módulo responsável pelo download dos vídeos do YouTube utilizando yt-dlp.
Otimizado para:
1. Downloads simultâneos em paralelo (Multi-threading / Worker Pool).
2. Aceleração de velocidade via fragmentos concorrentes (concurrent_fragment_downloads).
3. Salvamento garantido com o título original do vídeo.
4. Suporte a upload simultâneo/sequencial no Google Drive.
"""

import glob
import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp


def find_ffmpeg():
    """Localiza o executável do FFmpeg no PATH, na pasta local ou nos pacotes do WinGet."""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg

    local_bin_ffmpeg = os.path.join(os.getcwd(), "bin", "ffmpeg.exe")
    if os.path.exists(local_bin_ffmpeg):
        return local_bin_ffmpeg

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*ffmpeg*", "**", "bin", "ffmpeg.exe")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

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
    def __init__(
        self,
        output_dir=None,
        quality="best",
        format_type="video",
        max_workers=3,
        progress_callback=None,
        log_callback=None,
        gdrive_uploader=None,
        gdrive_folder_id=None,
        delete_local_after_upload=False
    ):
        """
        :param output_dir: Diretório onde os vídeos serão salvos.
        :param quality: 'best', '1080p', '720p', '480p'
        :param format_type: 'video' (MP4) ou 'audio' (MP3/M4A)
        :param max_workers: Quantidade de downloads simultâneos (padrão: 3)
        :param progress_callback: Função chamada com dados de progresso combinado
        :param log_callback: Função chamada para registrar mensagens de log (msg, level)
        :param gdrive_uploader: Instância opcional de GoogleDriveUploader para upload em nuvem
        :param gdrive_folder_id: ID da pasta no Google Drive (se None, usa 'YouTube Downloads')
        :param delete_local_after_upload: Se True, apaga o arquivo local após upload no Drive
        """
        self.output_dir = output_dir or os.path.join(os.getcwd(), "downloads")
        self.quality = quality
        self.format_type = format_type
        self.max_workers = max(1, int(max_workers))
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.gdrive_uploader = gdrive_uploader
        self.gdrive_folder_id = gdrive_folder_id
        self.delete_local_after_upload = delete_local_after_upload

        self.is_cancelled = False
        self.progress_lock = threading.Lock()
        self.active_downloads = {}   # url -> dict com percent, speed, eta, title
        self.completed_count = 0
        self.executor = None
        self.gdrive_lock = threading.Lock()

        # Garante que a pasta de destino exista
        os.makedirs(self.output_dir, exist_ok=True)

    def log(self, message, level="INFO"):
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")

    def cancel(self):
        """Sinaliza para cancelar os downloads pendentes imediatamente."""
        self.is_cancelled = True
        self.log("Cancelamento solicitado. Interrompendo tarefas ativas...", "WARNING")
        if self.executor:
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def _build_ydl_opts(self, progress_hook=None):
        ffmpeg_exe = find_ffmpeg()
        ffmpeg_available = ffmpeg_exe is not None
        node_available = has_node_js()

        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "windowsfilenames": True,
            "restrictfilenames": False,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,

            # ========================================================
            # OTIMIZAÇÕES DE VELOCIDADE TURBO:
            # ========================================================
            "concurrent_fragment_downloads": 4,  # Baixa até 4 pedaços do vídeo ao mesmo tempo
            "http_chunk_size": 10485760,         # Buffer de 10 MB para máxima largura de banda
            "buffersize": 1024 * 64,             # Buffer de leitura de 64 KB
            "retries": 10,
            "fragment_retries": 10,
            "skip_unavailable_fragments": True,
        }

        if progress_hook:
            ydl_opts["progress_hooks"] = [progress_hook]

        if ffmpeg_available:
            ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_exe)

        if node_available:
            ydl_opts["js_runtimes"] = {"node": {}}
            ydl_opts["remote_components"] = ["ejs:github"]

        # Configurações de Formato e Qualidade
        if self.format_type == "audio":
            if ffmpeg_available:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            else:
                ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
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

    def _emit_combined_progress(self, total_videos):
        """Calcula o progresso combinado de todos os downloads simultâneos."""
        if not self.progress_callback:
            return

        with self.progress_lock:
            active_count = len(self.active_downloads)
            active_sum_percent = sum(item.get("percent", 0) for item in self.active_downloads.values())
            total_speed = sum(item.get("speed", 0) for item in self.active_downloads.values())

            # Porcentagem total ponderada
            if total_videos > 0:
                overall_percent = ((self.completed_count * 100.0) + active_sum_percent) / total_videos
                overall_percent = min(100.0, max(0.0, overall_percent))
            else:
                overall_percent = 0.0

            # Monta lista de nomes dos vídeos em download no momento
            active_titles = [f"\"{item.get('title', '')}\" ({item.get('percent', 0):.0f}%)" for item in self.active_downloads.values() if item.get('title')]
            active_str = ", ".join(active_titles[:2])
            if len(active_titles) > 2:
                active_str += f" +{len(active_titles) - 2} outro(s)"

            self.progress_callback({
                "status": "downloading",
                "percent": overall_percent,
                "speed": total_speed,
                "completed": self.completed_count,
                "total": total_videos,
                "active_count": active_count,
                "active_detail": active_str or "Processando..."
            })

    def _download_single_video(self, url, idx, total_videos, resolved_folder_id=None):
        """Executado em uma thread trabalhadora individual para cada vídeo."""
        if self.is_cancelled:
            return False, "Cancelado", url

        url = url.strip()
        if not url:
            return False, "Link vazio", url

        title = self.extract_title(url)
        self.log(f"[{idx}/{total_videos}] Iniciando: \"{title}\"")

        # Inicializa o estado desta thread no monitor de progresso
        with self.progress_lock:
            self.active_downloads[url] = {
                "percent": 0.0,
                "speed": 0,
                "eta": 0,
                "title": title
            }
        self._emit_combined_progress(total_videos)

        def worker_hook(d):
            if self.is_cancelled:
                raise yt_dlp.utils.DownloadCancelled("Download cancelado.")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = (downloaded / total * 100) if total > 0 else 0
                spd = d.get("speed") or 0
                eta = d.get("eta") or 0
                fn = os.path.basename(d.get("filename", "")) or title

                with self.progress_lock:
                    self.active_downloads[url] = {
                        "percent": pct,
                        "speed": spd,
                        "eta": eta,
                        "title": fn
                    }
                self._emit_combined_progress(total_videos)

            elif status == "finished":
                with self.progress_lock:
                    if url in self.active_downloads:
                        self.active_downloads[url]["percent"] = 100.0

        ydl_opts = self._build_ydl_opts(progress_hook=worker_hook)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

                # Localiza o arquivo exato após merge ou extração de áudio
                if ydl_opts.get("merge_output_format"):
                    merged_candidate = os.path.splitext(downloaded_file)[0] + "." + ydl_opts["merge_output_format"]
                    if os.path.exists(merged_candidate):
                        downloaded_file = merged_candidate
                elif self.format_type == "audio":
                    audio_candidate = os.path.splitext(downloaded_file)[0] + ".mp3"
                    if os.path.exists(audio_candidate):
                        downloaded_file = audio_candidate

            self.log(f"✔ Download concluído: \"{title}\"", "SUCCESS")

            # Upload opcional para o Google Drive
            if self.gdrive_uploader and os.path.exists(downloaded_file):
                self.log(f"☁️ Enviando \"{title}\" para o Google Drive...")
                with self.gdrive_lock:
                    folder_id = resolved_folder_id or self.gdrive_folder_id
                    if not folder_id:
                        folder_id = self.gdrive_uploader.get_or_create_folder("YouTube Downloads")

                def drive_progress(percent, msg):
                    if self.progress_callback:
                        self.progress_callback({
                            "status": "uploading",
                            "percent": percent,
                            "filename": f"Drive: {os.path.basename(downloaded_file)}",
                            "active_detail": f"Upload Drive: {percent}%"
                        })

                self.gdrive_uploader.upload_file(downloaded_file, folder_id=folder_id, progress_callback=drive_progress)
                self.log(f"☁️ Salvo no Google Drive: \"{title}\"", "SUCCESS")

                if self.delete_local_after_upload:
                    try:
                        os.remove(downloaded_file)
                        self.log(f"Cópia local removida para poupar espaço: \"{os.path.basename(downloaded_file)}\"", "INFO")
                    except Exception as del_err:
                        self.log(f"Aviso ao remover arquivo local: {del_err}", "WARNING")

            with self.progress_lock:
                self.completed_count += 1
                if url in self.active_downloads:
                    del self.active_downloads[url]
            self._emit_combined_progress(total_videos)

            return True, title, url

        except yt_dlp.utils.DownloadCancelled:
            self.log(f"Download de \"{title}\" cancelado.", "WARNING")
            with self.progress_lock:
                if url in self.active_downloads:
                    del self.active_downloads[url]
            return False, "Cancelado", url
        except Exception as e:
            err_msg = str(e)
            self.log(f"Erro ao baixar \"{title}\": {err_msg}", "ERROR")
            with self.progress_lock:
                if url in self.active_downloads:
                    del self.active_downloads[url]
            return False, err_msg, url

    def download_batch(self, urls, on_video_start=None, on_video_complete=None):
        """
        Baixa múltiplos vídeos simultaneamente utilizando ThreadPoolExecutor.
        :param urls: Lista de URLs
        :param on_video_start: Callback (index, total, url)
        :param on_video_complete: Callback (index, total, url, success, info)
        :return: Dicionário com {success: [...], failed: [...]}
        """
        self.is_cancelled = False
        valid_urls = [u.strip() for u in urls if u and u.strip() and not u.strip().startswith("#")]
        total = len(valid_urls)

        results = {"success": [], "failed": []}

        if total == 0:
            self.log("Nenhum link válido fornecido.", "WARNING")
            return results

        concurrency = min(self.max_workers, total)
        self.log(f"⚡ Iniciando lote de {total} vídeo(s) com {concurrency} download(s) simultâneo(s)...", "INFO")

        # Pré-cria a pasta no Google Drive caso ativado para evitar concorrência
        resolved_folder_id = None
        if self.gdrive_uploader:
            try:
                resolved_folder_id = self.gdrive_folder_id or self.gdrive_uploader.get_or_create_folder("YouTube Downloads")
            except Exception as e:
                self.log(f"Aviso ao verificar pasta no Google Drive: {e}", "WARNING")

        self.completed_count = 0
        self.active_downloads.clear()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            self.executor = executor
            future_to_url = {
                executor.submit(self._download_single_video, url, idx, total, resolved_folder_id): url
                for idx, url in enumerate(valid_urls, 1)
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    success, info, orig_url = future.result()
                    if success:
                        results["success"].append({"url": orig_url, "title": info})
                    else:
                        results["failed"].append({"url": orig_url, "error": info})

                    if on_video_complete:
                        on_video_complete(self.completed_count, total, orig_url, success, info)
                except Exception as ex:
                    results["failed"].append({"url": url, "error": str(ex)})

        # Garante progresso final em 100%
        if self.progress_callback and not self.is_cancelled:
            self.progress_callback({
                "status": "finished",
                "percent": 100.0,
                "completed": len(results["success"]),
                "total": total,
                "speed": 0,
                "active_detail": "Lote finalizado com sucesso!"
            })

        self.log(
            f"Finalizado! {len(results['success'])} baixado(s) com sucesso, "
            f"{len(results['failed'])} falha(s).",
            "SUCCESS" if len(results["failed"]) == 0 else "WARNING"
        )
        return results
