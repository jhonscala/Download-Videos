"""
Interface Gráfica Moderna (CustomTkinter) para Download em Lote de Vídeos do YouTube.
Inclui:
- Salvamento com título original do vídeo.
- Resoluções até 4K (MP4) e extração de MP3.
- Suporte completo ao Google Drive (Upload direto na Nuvem e Pasta Sincronizada).
- Tema Escuro/Claro no estilo Windows 11 / YouTube Dark Mode.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from downloader import YouTubeDownloader, is_ffmpeg_installed
from gdrive import GoogleDriveUploader, detect_local_google_drive, CREDENTIALS_FILE, TOKEN_FILE


# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ModernYouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da Janela Principal
        self.title("YouTube Downloader Pro • Download em Lote & Google Drive")
        self.geometry("940x920")
        self.minsize(820, 740)

        # Variáveis de Controle
        default_folder = os.path.join(os.getcwd(), "downloads")
        self.dest_folder_var = tk.StringVar(value=default_folder)
        self.status_var = tk.StringVar(value="Pronto para baixar.")
        self.link_count_var = tk.StringVar(value="0 links prontos")
        self.progress_detail_var = tk.StringVar(value="")

        # Variáveis do Google Drive
        self.gdrive_enabled_var = tk.BooleanVar(value=False)
        self.gdrive_status_var = tk.StringVar(value="Não conectado à Nuvem")
        self.gdrive_folder_name_var = tk.StringVar(value="YouTube Downloads")
        self.gdrive_delete_local_var = tk.BooleanVar(value=False)
        self.gdrive_uploader = GoogleDriveUploader(log_callback=self.log)

        self.current_downloader = None
        self.is_downloading = False

        # Criação dos Componentes Visuais
        self._build_interface()
        self._update_link_count()
        self._check_initial_gdrive_status()

    def _build_interface(self):
        # Container com padding geral
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Cartão de links expande
        self.grid_rowconfigure(5, weight=1)  # Log expande

        # ========================================================
        # 1. CABEÇALHO MODERNO
        # ========================================================
        header_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        header_card.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")
        header_card.grid_columnconfigure(1, weight=1)

        # Ícone e Título
        title_box = ctk.CTkFrame(header_card, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        title_lbl = ctk.CTkLabel(
            title_box,
            text="▶ YouTube Downloader Pro",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("#dc2626", "#ef4444")
        )
        title_lbl.pack(anchor="w")

        ffmpeg_ok = is_ffmpeg_installed()
        status_text = "⚡ FFmpeg Ativo (1080p, 4K & MP3)" if ffmpeg_ok else "⚠️ FFmpeg Padrão"
        status_color = ("#16a34a", "#22c55e") if ffmpeg_ok else ("#d97706", "#f59e0b")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text=f"Download em lote com nome original  •  {status_text}  •  ☁️ Suporte a Google Drive",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=status_color
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Seletor de Tema (Claro / Escuro)
        theme_box = ctk.CTkFrame(header_card, fg_color="transparent")
        theme_box.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        theme_lbl = ctk.CTkLabel(theme_box, text="Tema:", font=ctk.CTkFont(family="Segoe UI", size=11))
        theme_lbl.pack(side="left", padx=(0, 6))

        self.theme_switch = ctk.CTkOptionMenu(
            theme_box,
            values=["Escuro", "Claro", "Sistema"],
            width=95,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._change_theme
        )
        self.theme_switch.set("Escuro")
        self.theme_switch.pack(side="left")

        # ========================================================
        # 2. CARTÃO DE LINKS (ENTRADA)
        # ========================================================
        links_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        links_card.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        links_card.grid_columnconfigure(0, weight=1)

        links_header = ctk.CTkFrame(links_card, fg_color="transparent")
        links_header.pack(fill="x", padx=14, pady=(10, 6))

        section_title = ctk.CTkLabel(
            links_header,
            text="🔗 Cole os Links dos Vídeos (um por linha):",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        section_title.pack(side="left")

        self.badge_lbl = ctk.CTkLabel(
            links_header,
            textvariable=self.link_count_var,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=("#e2e8f0", "#27272a"),
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.badge_lbl.pack(side="right")

        self.links_textbox = ctk.CTkTextbox(
            links_card,
            height=100,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=("white", "#09090b"),
            border_width=1,
            border_color=("gray80", "#27272a")
        )
        self.links_textbox.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.links_textbox.bind("<KeyRelease>", lambda e: self._update_link_count())

        links_actions = ctk.CTkFrame(links_card, fg_color="transparent")
        links_actions.pack(fill="x", padx=14, pady=(0, 10))

        paste_btn = ctk.CTkButton(
            links_actions,
            text="📋 Colar da Área de Transferência",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=30,
            fg_color=("#e2e8f0", "#27272a"),
            text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"),
            command=self._paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 8))

        file_btn = ctk.CTkButton(
            links_actions,
            text="📄 Importar de .txt",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=30,
            fg_color=("#e2e8f0", "#27272a"),
            text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"),
            command=self._load_from_file
        )
        file_btn.pack(side="left", padx=(0, 8))

        clear_btn = ctk.CTkButton(
            links_actions,
            text="🧹 Limpar Lista",
            font=ctk.CTkFont(size=12),
            height=30,
            width=90,
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            hover_color=("#fee2e2", "#3f1d1d"),
            command=self._clear_links
        )
        clear_btn.pack(side="left")

        # ========================================================
        # 3. CARTÃO DE DESTINO & QUALIDADE
        # ========================================================
        settings_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        settings_card.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        settings_card.grid_columnconfigure(1, weight=1)

        # Pasta de Destino
        folder_lbl = ctk.CTkLabel(settings_card, text="📁 Salvar em:", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        folder_lbl.grid(row=0, column=0, padx=(14, 8), pady=(12, 6), sticky="w")

        self.dest_entry = ctk.CTkEntry(
            settings_card,
            textvariable=self.dest_folder_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=32,
            corner_radius=8,
            fg_color=("white", "#09090b"),
            border_width=1,
            border_color=("gray80", "#27272a")
        )
        self.dest_entry.grid(row=0, column=1, padx=(0, 8), pady=(12, 6), sticky="ew")

        browse_btn = ctk.CTkButton(
            settings_card, text="Procurar...", width=85, height=32, corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e2e8f0", "#27272a"), text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"), command=self._browse_folder
        )
        browse_btn.grid(row=0, column=2, padx=(0, 8), pady=(12, 6))

        open_folder_btn = ctk.CTkButton(
            settings_card, text="📂 Abrir", width=75, height=32, corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e2e8f0", "#27272a"), text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"), command=self._open_folder
        )
        open_folder_btn.grid(row=0, column=3, padx=(0, 14), pady=(12, 6))

        # Qualidade
        qual_lbl = ctk.CTkLabel(settings_card, text="⚙️ Formato:", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        qual_lbl.grid(row=1, column=0, padx=(14, 8), pady=(4, 6), sticky="w")

        self.quality_segmented = ctk.CTkSegmentedButton(
            settings_card,
            values=[
                "🎬 Melhor Qualidade (MP4)",
                "🎥 1080p Full HD",
                "⚡ 720p HD",
                "🎵 Apenas Áudio (MP3)"
            ],
            corner_radius=8,
            height=32,
            selected_color="#dc2626",
            selected_hover_color="#b91c1c"
        )
        self.quality_segmented.set("🎬 Melhor Qualidade (MP4)")
        self.quality_segmented.grid(row=1, column=1, columnspan=3, padx=(0, 14), pady=(4, 6), sticky="ew")

        # Velocidade / Downloads Simultâneos
        workers_lbl = ctk.CTkLabel(settings_card, text="⚡ Velocidade:", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        workers_lbl.grid(row=2, column=0, padx=(14, 8), pady=(4, 12), sticky="w")

        self.workers_segmented = ctk.CTkSegmentedButton(
            settings_card,
            values=[
                "1 Vídeo (Sequencial)",
                "2 Simultâneos",
                "3 Simultâneos (Recomendado ⚡)",
                "5 Simultâneos (Turbo 🚀)"
            ],
            corner_radius=8,
            height=32,
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8"
        )
        self.workers_segmented.set("3 Simultâneos (Recomendado ⚡)")
        self.workers_segmented.grid(row=2, column=1, columnspan=3, padx=(0, 14), pady=(4, 12), sticky="ew")

        # ========================================================
        # 4. CARTÃO DE INTEGRAÇÃO COM O GOOGLE DRIVE
        # ========================================================
        gdrive_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        gdrive_card.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        gdrive_card.grid_columnconfigure(1, weight=1)

        # Cabeçalho do Cartão Drive
        drive_top = ctk.CTkFrame(gdrive_card, fg_color="transparent")
        drive_top.pack(fill="x", padx=14, pady=(10, 6))

        self.gdrive_switch = ctk.CTkSwitch(
            drive_top,
            text="☁️ Upload Automático para o Google Drive na Nuvem",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            variable=self.gdrive_enabled_var,
            onvalue=True,
            offvalue=False,
            progress_color="#2563eb",
            command=self._on_gdrive_toggle
        )
        self.gdrive_switch.pack(side="left")

        # Botão rápido para Pasta do Desktop (se existir)
        self.local_drive_btn = ctk.CTkButton(
            drive_top,
            text="📁 Usar Pasta do Drive Desktop",
            font=ctk.CTkFont(size=11),
            height=26,
            fg_color=("#e2e8f0", "#27272a"),
            text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"),
            command=self._use_local_gdrive_folder
        )
        self.local_drive_btn.pack(side="right", padx=(8, 0))

        help_btn = ctk.CTkButton(
            drive_top,
            text="❓ Como Configurar",
            font=ctk.CTkFont(size=11),
            height=26,
            width=110,
            fg_color="transparent",
            text_color=("#2563eb", "#60a5fa"),
            hover_color=("#dbeafe", "#1e293b"),
            command=self._show_gdrive_help
        )
        help_btn.pack(side="right")

        # Painel expansível do Google Drive
        self.drive_panel = ctk.CTkFrame(gdrive_card, fg_color=("white", "#09090b"), corner_radius=10)
        self.drive_panel.pack(fill="x", padx=14, pady=(0, 10))

        # Linha de Status da Conta
        drive_row1 = ctk.CTkFrame(self.drive_panel, fg_color="transparent")
        drive_row1.pack(fill="x", padx=12, pady=(10, 6))

        self.drive_status_lbl = ctk.CTkLabel(
            drive_row1,
            textvariable=self.gdrive_status_var,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#475569", "#94a3b8")
        )
        self.drive_status_lbl.pack(side="left")

        self.disconnect_btn = ctk.CTkButton(
            drive_row1,
            text="Desconectar",
            font=ctk.CTkFont(size=11),
            height=26,
            width=90,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._disconnect_gdrive
        )

        self.connect_btn = ctk.CTkButton(
            drive_row1,
            text="🔑 Conectar Conta Google",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=26,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._connect_gdrive
        )
        self.connect_btn.pack(side="right", padx=(6, 0))

        self.import_cred_btn = ctk.CTkButton(
            drive_row1,
            text="📄 Importar credentials.json",
            font=ctk.CTkFont(size=11),
            height=26,
            fg_color=("#e2e8f0", "#27272a"),
            text_color=("gray10", "gray95"),
            hover_color=("#cbd5e1", "#3f3f46"),
            command=self._import_credentials_file
        )
        self.import_cred_btn.pack(side="right")

        # Linha de Opções do Drive
        drive_row2 = ctk.CTkFrame(self.drive_panel, fg_color="transparent")
        drive_row2.pack(fill="x", padx=12, pady=(0, 10))

        folder_name_lbl = ctk.CTkLabel(
            drive_row2,
            text="Pasta no Drive:",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        folder_name_lbl.pack(side="left", padx=(0, 6))

        self.folder_name_entry = ctk.CTkEntry(
            drive_row2,
            textvariable=self.gdrive_folder_name_var,
            font=ctk.CTkFont(size=12),
            width=170,
            height=28
        )
        self.folder_name_entry.pack(side="left", padx=(0, 16))

        self.delete_local_chk = ctk.CTkCheckBox(
            drive_row2,
            text="🗑️ Excluir cópia local após upload no Drive (economiza espaço)",
            font=ctk.CTkFont(size=11),
            variable=self.gdrive_delete_local_var,
            checkbox_width=20,
            checkbox_height=20,
            fg_color="#dc2626",
            hover_color="#b91c1c"
        )
        self.delete_local_chk.pack(side="left")

        # ========================================================
        # 5. BOTÕES DE AÇÃO E PROGRESSO
        # ========================================================
        action_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        action_card.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        action_card.grid_columnconfigure(0, weight=1)

        btn_box = ctk.CTkFrame(action_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=14, pady=(12, 8))

        self.start_btn = ctk.CTkButton(
            btn_box,
            text="▶ INICIAR DOWNLOAD DE TODOS OS VÍDEOS",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._start_download_thread
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_box,
            text="⏹ Cancelar",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=46,
            width=110,
            corner_radius=10,
            fg_color=("gray80", "#27272a"),
            text_color=("gray40", "gray50"),
            hover_color=("#ef4444", "#dc2626"),
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="left")

        prog_box = ctk.CTkFrame(action_card, fg_color="transparent")
        prog_box.pack(fill="x", padx=14, pady=(0, 12))

        self.prog_bar = ctk.CTkProgressBar(prog_box, height=10, corner_radius=5, progress_color="#dc2626")
        self.prog_bar.set(0)
        self.prog_bar.pack(fill="x", pady=(0, 6))

        status_row = ctk.CTkFrame(prog_box, fg_color="transparent")
        status_row.pack(fill="x")

        self.status_lbl = ctk.CTkLabel(
            status_row,
            textvariable=self.status_var,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray20", "gray90")
        )
        self.status_lbl.pack(side="left")

        self.detail_lbl = ctk.CTkLabel(
            status_row,
            textvariable=self.progress_detail_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray40", "gray60")
        )
        self.detail_lbl.pack(side="right")

        # ========================================================
        # 6. CARTÃO DE LOG EM TEMPO REAL (CONSOLE)
        # ========================================================
        log_card = ctk.CTkFrame(self, corner_radius=14, fg_color=("gray92", "#18181b"))
        log_card.grid(row=5, column=0, padx=20, pady=(0, 16), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=14, pady=(8, 4))

        log_title = ctk.CTkLabel(log_header, text="📜 Relatório em Tempo Real:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        log_title.pack(side="left")

        clear_log_btn = ctk.CTkButton(
            log_header, text="Limpar Log", font=ctk.CTkFont(size=10),
            height=22, width=70, fg_color="transparent",
            text_color=("gray40", "gray60"), command=self._clear_log
        )
        clear_log_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            height=120,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("white", "#09090b"),
            border_width=1,
            border_color=("gray80", "#27272a")
        )
        self.log_textbox.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.log_textbox._textbox.tag_config("SUCCESS", foreground="#10b981")
        self.log_textbox._textbox.tag_config("ERROR", foreground="#ef4444")
        self.log_textbox._textbox.tag_config("WARNING", foreground="#f59e0b")
        self.log_textbox._textbox.tag_config("INFO", foreground="#60a5fa")
        self.log_textbox._textbox.tag_config("TIME", foreground="#71717a")

        self.log("Sistema pronto. Insira seus links e selecione as opções de download.", "INFO")

    def _change_theme(self, choice):
        mode_map = {"Escuro": "dark", "Claro": "light", "Sistema": "system"}
        ctk.set_appearance_mode(mode_map.get(choice, "dark"))

    def _on_gdrive_toggle(self):
        if self.gdrive_enabled_var.get():
            self._check_initial_gdrive_status()
            if not self.gdrive_uploader.is_authenticated():
                self.log("Google Drive ativado. Conecte sua conta para iniciar os uploads.", "WARNING")

    def _check_initial_gdrive_status(self):
        if self.gdrive_uploader.is_authenticated():
            user = self.gdrive_uploader.get_user_info()
            self.gdrive_status_var.set(f"Conectado como: {user} ✅")
            self.drive_status_lbl.configure(text_color=("#16a34a", "#22c55e"))
            self.connect_btn.pack_forget()
            self.import_cred_btn.pack_forget()
            self.disconnect_btn.pack(side="right")
        else:
            if os.path.exists(CREDENTIALS_FILE):
                self.gdrive_status_var.set("credentials.json encontrado. Clique em 'Conectar' para autorizar.")
                self.drive_status_lbl.configure(text_color=("#d97706", "#f59e0b"))
            else:
                self.gdrive_status_var.set("Não conectado à Nuvem (credentials.json pendente)")
                self.drive_status_lbl.configure(text_color=("#475569", "#94a3b8"))
            self.disconnect_btn.pack_forget()
            self.connect_btn.pack(side="right", padx=(6, 0))
            self.import_cred_btn.pack(side="right")

    def _connect_gdrive(self):
        if not os.path.exists(CREDENTIALS_FILE):
            ans = messagebox.askyesno(
                "Configurar Google Drive",
                "Para conectar à sua conta Google, é necessário o arquivo 'credentials.json' do Google Cloud (gratuito).\n\n"
                "Deseja ver o passo-a-passo de como obter seu credentials.json em 1 minuto?"
            )
            if ans:
                self._show_gdrive_help()
            return

        def do_auth():
            self.gdrive_status_var.set("Aguardando autorização no navegador...")
            try:
                self.gdrive_uploader.authenticate()
                self._check_initial_gdrive_status()
                self.gdrive_enabled_var.set(True)
                self.log("Conta Google conectada com sucesso!", "SUCCESS")
                messagebox.showinfo("Sucesso", "Google Drive conectado com sucesso!")
            except Exception as e:
                self.log(f"Falha na autenticação do Google Drive: {e}", "ERROR")
                self.gdrive_status_var.set("Erro na autenticação")
                messagebox.showerror("Erro", f"Não foi possível conectar: {e}")

        threading.Thread(target=do_auth, daemon=True).start()

    def _import_credentials_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo credentials.json baixado do Google Cloud",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os Arquivos", "*.*")]
        )
        if not file_path:
            return
        try:
            import shutil
            shutil.copy(file_path, CREDENTIALS_FILE)
            self.log("credentials.json importado com sucesso!", "SUCCESS")
            self._check_initial_gdrive_status()
            messagebox.showinfo(
                "Arquivo Importado",
                "Arquivo credentials.json configurado!\nClique agora em 'Conectar Conta Google' para autorizar o acesso."
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao importar arquivo: {e}")

    def _disconnect_gdrive(self):
        self.gdrive_uploader.disconnect()
        self.gdrive_enabled_var.set(False)
        self._check_initial_gdrive_status()
        self.log("Conta do Google Drive desconectada.", "INFO")
        messagebox.showinfo("Desconectado", "Conta do Google Drive desconectada com sucesso.")

    def _use_local_gdrive_folder(self):
        detected = detect_local_google_drive()
        if detected:
            self.dest_folder_var.set(detected)
            self.log(f"Pasta do Google Drive Desktop selecionada: {detected}", "SUCCESS")
            messagebox.showinfo("Google Drive Detectado", f"A pasta do Google Drive foi selecionada:\n{detected}")
        else:
            ans = messagebox.askyesno(
                "Google Drive Desktop",
                "O aplicativo Google Drive Desktop não foi encontrado nas unidades padrão.\n\n"
                "Deseja procurar e selecionar manualmente a pasta sincronizada do Google Drive ou OneDrive?"
            )
            if ans:
                self._browse_folder()

    def _show_gdrive_help(self):
        msg = (
            "COMO CONECTAR O GOOGLE DRIVE:\n\n"
            "Opção 1 (Mais Simples): Se você usa o Google Drive para Desktop no Windows, "
            "clique no botão 'Usar Pasta do Drive Desktop' e selecione sua pasta do Drive!\n\n"
            "Opção 2 (Upload em Nuvem Direto via API):\n"
            "1. Acesse console.cloud.google.com\n"
            "2. Ative a API 'Google Drive API'\n"
            "3. Vá em Credenciais -> Criar ID do cliente OAuth -> Aplicativo para Computador\n"
            "4. Baixe o JSON, renomeie para 'credentials.json' e use o botão 'Importar credentials.json'\n"
            "5. Clique em 'Conectar Conta Google' e pronto!\n\n"
            "Deseja abrir o arquivo de instruções detalhadas?"
        )
        if messagebox.askyesno("Ajuda do Google Drive", msg):
            help_doc = os.path.join(os.getcwd(), "COMO_CONFIGURAR_GOOGLE_DRIVE.md")
            if os.path.exists(help_doc):
                os.startfile(help_doc)

    def _get_links(self):
        content = self.links_textbox.get("1.0", "end").strip()
        lines = [line.strip() for line in content.splitlines()]
        valid_links = [l for l in lines if l and not l.startswith("#") and ("youtube.com" in l or "youtu.be" in l)]
        return valid_links

    def _update_link_count(self):
        count = len(self._get_links())
        if count == 0:
            self.link_count_var.set("0 links prontos")
        elif count == 1:
            self.link_count_var.set("1 link pronto")
        else:
            self.link_count_var.set(f"{count} links prontos")

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                curr = self.links_textbox.get("1.0", "end").strip()
                if curr:
                    self.links_textbox.insert("end", "\n" + text.strip())
                else:
                    self.links_textbox.insert("end", text.strip())
                self._update_link_count()
        except Exception:
            pass

    def _load_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo de links",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                curr = self.links_textbox.get("1.0", "end").strip()
                if curr:
                    self.links_textbox.insert("end", "\n" + content)
                else:
                    self.links_textbox.insert("end", content)
                self._update_link_count()
                self.log(f"Links carregados de: {os.path.basename(file_path)}", "INFO")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o arquivo: {e}")

    def _clear_links(self):
        self.links_textbox.delete("1.0", "end")
        self._update_link_count()

    def _clear_log(self):
        self.log_textbox.delete("1.0", "end")

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            title="Selecione a pasta de destino",
            initialdir=self.dest_folder_var.get()
        )
        if folder:
            self.dest_folder_var.set(folder)

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
            tb = self.log_textbox._textbox
            tb.insert("end", f"[{timestamp}] ", "TIME")
            tb.insert("end", f"{message}\n", level)
            tb.see("end")

        self.after(0, _do_log)

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
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                active_count = data.get("active_count", 0)
                active_detail = data.get("active_detail", "")

                self.prog_bar.set(percent / 100.0)
                speed_str = f"{self._format_bytes(speed)}/s"

                self.status_var.set(
                    f"⚡ Baixando [{active_count} em paralelo] • Concluídos: {completed}/{total} • Total: {percent:.1f}% ({speed_str})"
                )
                self.progress_detail_var.set(active_detail)
            elif status == "uploading":
                percent = data.get("percent", 0)
                filename = data.get("filename", "")
                detail = data.get("active_detail", "")
                self.prog_bar.set(percent / 100.0)
                self.status_var.set(f"☁️ {filename}")
                self.progress_detail_var.set(detail)
            elif status == "finished":
                self.prog_bar.set(1.0)
                total = data.get("total", 0)
                completed = data.get("completed", 0)
                self.status_var.set(f"Concluído! {completed}/{total} vídeo(s) finalizados com sucesso.")
                self.progress_detail_var.set("100% Finalizado")

        self.after(0, _update)

    def _cancel_download(self):
        if self.current_downloader and self.is_downloading:
            self.current_downloader.cancel()
            self.status_var.set("Cancelando downloads...")
            self.cancel_btn.configure(state="disabled")

    def _start_download_thread(self):
        links = self._get_links()
        if not links:
            messagebox.showwarning("Nenhum Link", "Por favor, cole ao menos um link válido do YouTube.")
            return

        out_dir = self.dest_folder_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Pasta Inválida", "Selecione a pasta de destino.")
            return

        # Verifica se Google Drive está habilitado mas não autenticado
        gdrive_uploader = None
        if self.gdrive_enabled_var.get():
            if not self.gdrive_uploader.is_authenticated():
                resp = messagebox.askyesno(
                    "Google Drive Não Conectado",
                    "O upload para o Google Drive está ativado, mas você ainda não conectou sua conta.\n\n"
                    "Deseja continuar baixando apenas localmente no computador?"
                )
                if not resp:
                    return
            else:
                gdrive_uploader = self.gdrive_uploader

        self.is_downloading = True
        self.start_btn.configure(state="disabled", fg_color="gray50")
        self.cancel_btn.configure(state="normal", fg_color="#dc2626", text_color="white", hover_color="#b91c1c")
        self.prog_bar.set(0)
        self.progress_detail_var.set("Iniciando conexões turbo...")

        thread = threading.Thread(
            target=self._run_download_batch,
            args=(links, out_dir, gdrive_uploader),
            daemon=True
        )
        thread.start()

    def _run_download_batch(self, links, out_dir, gdrive_uploader):
        choice = self.quality_segmented.get()
        if "Áudio" in choice:
            quality = "best"
            format_type = "audio"
        elif "1080p" in choice:
            quality = "1080p"
            format_type = "video"
        elif "720p" in choice:
            quality = "720p"
            format_type = "video"
        else:
            quality = "best"
            format_type = "video"

        # Concorrência configurada pelo usuário
        workers_choice = self.workers_segmented.get()
        if "1" in workers_choice:
            max_workers = 1
        elif "2" in workers_choice:
            max_workers = 2
        elif "5" in workers_choice:
            max_workers = 5
        else:
            max_workers = 3

        folder_name = self.gdrive_folder_name_var.get().strip() or "YouTube Downloads"
        delete_local = self.gdrive_delete_local_var.get()

        self.current_downloader = YouTubeDownloader(
            output_dir=out_dir,
            quality=quality,
            format_type=format_type,
            max_workers=max_workers,
            progress_callback=self._on_progress,
            log_callback=self.log,
            gdrive_uploader=gdrive_uploader,
            gdrive_folder_id=None,
            delete_local_after_upload=delete_local
        )

        def on_video_start(idx, tot, url):
            self.after(0, lambda: self.status_var.set(f"[{idx}/{tot}] Baixando vídeo..."))
            self.after(0, lambda: self.prog_bar.set(0))

        def on_video_complete(idx, tot, url, success, info):
            if success:
                self.after(0, lambda: self.status_var.set(f"[{idx}/{tot}] Concluído com sucesso!"))
            else:
                self.after(0, lambda: self.status_var.set(f"[{idx}/{tot}] Falha: {info}"))

        try:
            results = self.current_downloader.download_batch(
                links,
                on_video_start=on_video_start,
                on_video_complete=on_video_complete
            )

            sucessos = len(results["success"])
            falhas = len(results["failed"])

            if not self.current_downloader.is_cancelled:
                extra_drive = "\n☁️ Vídeos também enviados para o seu Google Drive!" if gdrive_uploader else ""
                msg = f"🎉 Processo Concluído!\n\nVídeos salvos com sucesso: {sucessos}\nFalhas: {falhas}\n\nPasta:\n{out_dir}{extra_drive}"
                self.after(0, lambda: messagebox.showinfo("Download Concluído", msg))
                self.after(0, lambda: self.status_var.set(f"Pronto! {sucessos} vídeo(s) baixados com sucesso."))
                self.after(0, lambda: self.progress_detail_var.set(""))
            else:
                self.after(0, lambda: messagebox.showwarning("Cancelado", "O download do lote foi cancelado."))
                self.after(0, lambda: self.status_var.set("Download cancelado pelo usuário."))
                self.after(0, lambda: self.progress_detail_var.set(""))

        except Exception as e:
            self.log(f"Erro inesperado: {e}", "ERROR")
            self.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro: {e}"))
        finally:
            self.is_downloading = False
            self.after(0, lambda: self.start_btn.configure(state="normal", fg_color="#dc2626"))
            self.after(0, lambda: self.cancel_btn.configure(
                state="disabled",
                fg_color=("gray80", "#27272a"),
                text_color=("gray40", "gray50")
            ))


def main():
    app = ModernYouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
