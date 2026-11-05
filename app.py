"""
Interface Gráfica (GUI) para Download em Lote de Vídeos do YouTube.
Permite colar múltiplos links, escolher pasta de destino e qualidade,
salvando cada vídeo com seu título original.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess

from downloader import YouTubeDownloader, is_ffmpeg_installed


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Baixador de Vídeos do YouTube - Download em Lote")
        self.root.geometry("820x760")
        self.root.minsize(720, 640)

        # Configura estilo geral
        self._setup_style()

        # Variáveis de controle
        default_download_dir = os.path.join(os.getcwd(), "downloads")
        self.dest_folder_var = tk.StringVar(value=default_download_dir)
        self.format_type_var = tk.StringVar(value="video")
        self.quality_var = tk.StringVar(value="best")
        self.status_var = tk.StringVar(value="Pronto para baixar.")
        self.link_count_var = tk.StringVar(value="0 links detectados")

        self.current_downloader = None
        self.is_downloading = False

        # Construção da interface
        self._create_widgets()
        self._update_link_count()

    def _setup_style(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Cores e fontes modernas
        self.bg_color = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.primary_color = "#e52d27"  # YouTube Red
        self.primary_hover = "#b31217"
        self.success_color = "#28a745"
        self.text_color = "#2c3e50"

        self.root.configure(bg=self.bg_color)
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        self.style.configure("TLabelframe", background=self.card_bg, foreground=self.text_color)
        self.style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background=self.card_bg, foreground=self.text_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        self.style.configure("Card.TLabel", background=self.card_bg, foreground=self.text_color)
        self.style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#cc181e")
        self.style.map("Primary.TButton", background=[("active", "#a01015"), ("disabled", "#cccccc")])
        self.style.configure("Secondary.TButton", font=("Segoe UI", 9))
        self.style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background="#dc3545")
        self.style.map("Danger.TButton", background=[("active", "#bd2130"), ("disabled", "#cccccc")])

    def _create_widgets(self):
        # Container principal com scroll caso a janela fique pequena
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Cabeçalho
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 12))

        title_lbl = tk.Label(
            header_frame,
            text="▶ Baixador de Vídeos do YouTube",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg="#b31217"
        )
        title_lbl.pack(anchor="w")

        ffmpeg_status = "Detectado ✅ (Alta Resolução + MP3 ativo)" if is_ffmpeg_installed() else "Padrão (Vídeos MP4 diretos)"
        subtitle_lbl = tk.Label(
            header_frame,
            text=f"Cole os links abaixo para baixar tudo automaticamente com o nome original do vídeo. | FFmpeg: {ffmpeg_status}",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg="#555555"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # 2. Área de Links (Card)
        links_card = ttk.LabelFrame(main_frame, text=" 🔗 Links dos Vídeos (um por linha) ", padding=10)
        links_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Barra de botões rápidos para os links
        btn_bar = tk.Frame(links_card, bg=self.card_bg)
        btn_bar.pack(fill=tk.X, pady=(0, 6))

        paste_btn = tk.Button(
            btn_bar, text="📋 Colar da Área de Transferência", font=("Segoe UI", 9),
            relief="groove", command=self._paste_clipboard
        )
        paste_btn.pack(side=tk.LEFT, padx=(0, 5))

        load_file_btn = tk.Button(
            btn_bar, text="📄 Carregar de Arquivo .txt", font=("Segoe UI", 9),
            relief="groove", command=self._load_from_file
        )
        load_file_btn.pack(side=tk.LEFT, padx=(0, 5))

        clear_btn = tk.Button(
            btn_bar, text="🧹 Limpar Links", font=("Segoe UI", 9),
            relief="groove", command=self._clear_links
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.link_count_lbl = tk.Label(
            btn_bar, textvariable=self.link_count_var, font=("Segoe UI", 9, "italic"),
            bg=self.card_bg, fg="#666666"
        )
        self.link_count_lbl.pack(side=tk.RIGHT)

        # Caixa de Texto dos Links
        text_frame = tk.Frame(links_card)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.links_text = tk.Text(
            text_frame, height=8, font=("Consolas", 10), wrap="none",
            relief="solid", borderwidth=1
        )
        self.links_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.links_text.bind("<KeyRelease>", lambda e: self._update_link_count())

        text_scroll_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.links_text.yview)
        text_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.links_text.config(yscrollcommand=text_scroll_y.set)

        # 3. Configurações: Pasta de Destino e Formato (Card)
        opts_card = ttk.LabelFrame(main_frame, text=" ⚙️ Opções de Download ", padding=10)
        opts_card.pack(fill=tk.X, pady=(0, 10))

        # Linha: Pasta de Destino
        dest_row = tk.Frame(opts_card, bg=self.card_bg)
        dest_row.pack(fill=tk.X, pady=(0, 8))

        dest_lbl = tk.Label(dest_row, text="Salvar em:", font=("Segoe UI", 9, "bold"), bg=self.card_bg)
        dest_lbl.pack(side=tk.LEFT, padx=(0, 6))

        dest_entry = ttk.Entry(dest_row, textvariable=self.dest_folder_var, font=("Segoe UI", 9))
        dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        browse_btn = tk.Button(
            dest_row, text="Procurar...", font=("Segoe UI", 9), relief="groove",
            command=self._browse_folder
        )
        browse_btn.pack(side=tk.LEFT, padx=(0, 4))

        open_folder_btn = tk.Button(
            dest_row, text="📂 Abrir Pasta", font=("Segoe UI", 9), relief="groove",
            command=self._open_folder
        )
        open_folder_btn.pack(side=tk.LEFT)

        # Linha: Qualidade / Formato
        fmt_row = tk.Frame(opts_card, bg=self.card_bg)
        fmt_row.pack(fill=tk.X)

        fmt_lbl = tk.Label(fmt_row, text="Qualidade / Formato:", font=("Segoe UI", 9, "bold"), bg=self.card_bg)
        fmt_lbl.pack(side=tk.LEFT, padx=(0, 10))

        r1 = tk.Radiobutton(
            fmt_row, text="Melhor Qualidade (MP4)", variable=self.quality_var, value="best",
            bg=self.card_bg, command=lambda: self.format_type_var.set("video")
        )
        r1.pack(side=tk.LEFT, padx=(0, 12))

        r2 = tk.Radiobutton(
            fmt_row, text="1080p Full HD (MP4)", variable=self.quality_var, value="1080p",
            bg=self.card_bg, command=lambda: self.format_type_var.set("video")
        )
        r2.pack(side=tk.LEFT, padx=(0, 12))

        r3 = tk.Radiobutton(
            fmt_row, text="720p HD (Rápido)", variable=self.quality_var, value="720p",
            bg=self.card_bg, command=lambda: self.format_type_var.set("video")
        )
        r3.pack(side=tk.LEFT, padx=(0, 12))

        r4 = tk.Radiobutton(
            fmt_row, text="Apenas Áudio (MP3)", variable=self.quality_var, value="audio",
            bg=self.card_bg, command=lambda: self.format_type_var.set("audio")
        )
        r4.pack(side=tk.LEFT)

        # 4. Botões de Ação Principal & Progresso
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = tk.Button(
            action_frame, text="▶ INICIAR DOWNLOAD DE TODOS OS VÍDEOS",
            font=("Segoe UI", 11, "bold"), bg="#28a745", fg="#ffffff",
            activebackground="#218838", activeforeground="#ffffff",
            relief="raised", height=2, command=self._start_download_thread
        )
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.cancel_btn = tk.Button(
            action_frame, text="⏹ CANCELAR",
            font=("Segoe UI", 11, "bold"), bg="#dc3545", fg="#ffffff",
            activebackground="#c82333", activeforeground="#ffffff",
            relief="raised", height=2, state=tk.DISABLED, command=self._cancel_download
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 0))

        # Barra de Progresso e Status
        prog_frame = ttk.Frame(main_frame)
        prog_frame.pack(fill=tk.X, pady=(0, 10))

        self.prog_bar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.prog_bar.pack(fill=tk.X, pady=(0, 4))

        self.status_lbl = tk.Label(
            prog_frame, textvariable=self.status_var, font=("Segoe UI", 9, "bold"),
            bg=self.bg_color, fg="#1a252f", anchor="w"
        )
        self.status_lbl.pack(fill=tk.X)

        # 5. Registro / Log de Atividades
        log_card = ttk.LabelFrame(main_frame, text=" 📜 Relatório de Download ", padding=8)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_frame = tk.Frame(log_card)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame, height=6, font=("Segoe UI", 9), wrap="word",
            bg="#ffffff", relief="solid", borderwidth=1
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Tags coloridas no log
        self.log_text.tag_config("SUCCESS", foreground="#28a745", font=("Segoe UI", 9, "bold"))
        self.log_text.tag_config("ERROR", foreground="#dc3545", font=("Segoe UI", 9, "bold"))
        self.log_text.tag_config("WARNING", foreground="#e67e22")
        self.log_text.tag_config("INFO", foreground="#2c3e50")

        self.log("Sistema pronto. Insira os links acima e clique em 'Iniciar Download'.", "INFO")

    def _get_links(self):
        content = self.links_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.splitlines()]
        valid_links = [l for l in lines if l and not l.startswith("#") and ("youtube.com" in l or "youtu.be" in l)]
        return valid_links

    def _update_link_count(self):
        links = self._get_links()
        count = len(links)
        if count == 0:
            self.link_count_var.set("0 links detectados")
        elif count == 1:
            self.link_count_var.set("1 link detectado")
        else:
            self.link_count_var.set(f"{count} links detectados")

    def _paste_clipboard(self):
        try:
            clipboard_text = self.root.clipboard_get()
            if clipboard_text:
                current_text = self.links_text.get("1.0", tk.END).strip()
                if current_text:
                    self.links_text.insert(tk.END, "\n" + clipboard_text.strip())
                else:
                    self.links_text.insert(tk.END, clipboard_text.strip())
                self._update_link_count()
        except Exception:
            pass

    def _load_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo com links",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                current_text = self.links_text.get("1.0", tk.END).strip()
                if current_text:
                    self.links_text.insert(tk.END, "\n" + content)
                else:
                    self.links_text.insert(tk.END, content)
                self._update_link_count()
                self.log(f"Links carregados do arquivo: {os.path.basename(file_path)}", "INFO")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo: {e}")

    def _clear_links(self):
        self.links_text.delete("1.0", tk.END)
        self._update_link_count()

    def _browse_folder(self):
        selected_dir = filedialog.askdirectory(
            title="Selecione a pasta para salvar os vídeos",
            initialdir=self.dest_folder_var.get()
        )
        if selected_dir:
            self.dest_folder_var.set(selected_dir)

    def _open_folder(self):
        dest_dir = self.dest_folder_var.get()
        os.makedirs(dest_dir, exist_ok=True)
        try:
            os.startfile(dest_dir)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {e}")

    def log(self, message, level="INFO"):
        def _do_log():
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
            self.log_text.insert(tk.END, f"{message}\n", level)
            self.log_text.see(tk.END)

        self.root.after(0, _do_log)

    def _format_bytes(self, size):
        if not size:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _format_time(self, seconds):
        if not seconds:
            return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _on_progress(self, data):
        def _update():
            status = data.get("status")
            if status == "downloading":
                percent = data.get("percent", 0)
                speed = data.get("speed", 0)
                eta = data.get("eta", 0)
                filename = data.get("filename", "")

                self.prog_bar["value"] = percent
                speed_str = f"{self._format_bytes(speed)}/s"
                eta_str = self._format_time(eta)

                self.status_var.set(
                    f"Baixando: {percent:.1f}% | {speed_str} | Tempo restante: {eta_str} | \"{filename}\""
                )
            elif status == "finished":
                self.prog_bar["value"] = 100
                filename = data.get("filename", "")
                self.status_var.set(f"Download concluído: \"{filename}\"")

        self.root.after(0, _update)

    def _cancel_download(self):
        if self.current_downloader and self.is_downloading:
            self.current_downloader.cancel()
            self.status_var.set("Cancelando downloads...")
            self.cancel_btn.config(state=tk.DISABLED)

    def _start_download_thread(self):
        links = self._get_links()
        if not links:
            messagebox.showwarning(
                "Nenhum Link Válido",
                "Por favor, cole ao menos um link válido do YouTube na caixa de texto."
            )
            return

        out_dir = self.dest_folder_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Pasta Inválida", "Por favor, selecione uma pasta de destino.")
            return

        self.is_downloading = True
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.prog_bar["value"] = 0

        # Dispara thread para não travar a interface
        thread = threading.Thread(target=self._run_download_batch, args=(links, out_dir), daemon=True)
        thread.start()

    def _run_download_batch(self, links, out_dir):
        total = len(links)
        quality = self.quality_var.get()
        format_type = "audio" if quality == "audio" else "video"

        self.current_downloader = YouTubeDownloader(
            output_dir=out_dir,
            quality=quality,
            format_type=format_type,
            progress_callback=self._on_progress,
            log_callback=self.log
        )

        def on_video_start(idx, tot, url):
            self.root.after(0, lambda: self.status_var.set(f"Iniciando vídeo {idx} de {tot}..."))
            self.root.after(0, lambda: self.prog_bar.configure(value=0))

        def on_video_complete(idx, tot, url, success, info):
            percent_batch = (idx / tot) * 100
            if success:
                self.root.after(0, lambda: self.status_var.set(f"Concluído {idx}/{tot}: {info}"))
            else:
                self.root.after(0, lambda: self.status_var.set(f"Falha no vídeo {idx}/{tot}: {info}"))

        try:
            results = self.current_downloader.download_batch(
                links,
                on_video_start=on_video_start,
                on_video_complete=on_video_complete
            )

            # Relatório final
            sucessos = len(results["success"])
            falhas = len(results["failed"])

            if not self.current_downloader.is_cancelled:
                msg = f"Processo finalizado com sucesso!\n\nVídeos baixados: {sucessos}\nFalhas: {falhas}\n\nSalvos em:\n{out_dir}"
                self.root.after(0, lambda: messagebox.showinfo("Concluído", msg))
                self.root.after(0, lambda: self.status_var.set(f"Concluído! {sucessos} baixados com sucesso."))
            else:
                self.root.after(0, lambda: messagebox.showwarning("Cancelado", "O download foi interrompido."))
                self.root.after(0, lambda: self.status_var.set("Download cancelado."))

        except Exception as e:
            self.log(f"Erro inesperado durante o download: {e}", "ERROR")
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro: {e}"))
        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cancel_btn.config(state=tk.DISABLED))


def main():
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
