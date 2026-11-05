# 📥 Baixador de Vídeos do YouTube em Lote

Sistema completo para download de vídeos do YouTube em lote (múltiplos links simultâneos ou sequenciais), garantindo que **cada arquivo seja salvo automaticamente com o título original do vídeo**.

---

## 🚀 Como Usar (Mais Fácil)

Basta dar **duplo clique** direto no executável:
👉 **`BaixadorYoutube.exe`**

Ele abrirá imediatamente a **Interface Gráfica** (sem precisar de terminal ou instalar Python):

1. **Cole os links** na caixa de texto (um por linha). Você também pode clicar no botão **"📋 Colar da Área de Transferência"** ou **"📄 Carregar de Arquivo .txt"**.
2. **Escolha a pasta de destino** onde deseja salvar os vídeos (por padrão, os arquivos vão para a pasta `downloads`).
3. **Escolha a qualidade/formato**:
   - *Melhor Qualidade (MP4)* (1080p, 1440p, 4K)
   - *1080p Full HD (MP4)*
   - *720p HD (MP4)*
   - *Apenas Áudio (MP3)*
4. Clique no botão verde **"▶ INICIAR DOWNLOAD DE TODOS OS VÍDEOS"**.
5. Quando terminar, clique em **"📂 Abrir Pasta"** para ver seus vídeos baixados com os nomes originais!

---

## 📁 Estrutura de Arquivos do Projeto

```text
Abaixa video do Youtube/
│
├── BaixadorYoutube.exe           # EXECUTÁVEL PRINCIPAL (Basta dar duplo clique)
├── ffmpeg.exe                    # Processador de áudio/vídeo integrado para alta resolução
│
├── links.txt                     # Arquivo de texto opcional para listar links
├── Iniciar_Baixador.bat          # Atalho alternativo via script
├── Iniciar_Via_Terminal.bat      # Versão de terminal (CLI)
│
├── app.py                        # Código-fonte da Interface Gráfica
├── downloader.py                 # Código-fonte do mecanismo de download
├── cli.py                        # Código-fonte da versão CLI
│
└── csharp_version/               # Versão alternativa em C# (.NET 10 + YoutubeExplode)
```

---

## 🛠️ Outras Formas de Execução

### 1. Linha de Comando (Python)
Você pode executar diretamente via terminal do Windows (PowerShell ou Prompt de Comando):

```powershell
# Abrir a interface gráfica
py app.py

# Baixar usando a lista do arquivo links.txt
py cli.py links.txt

# Baixar passando links diretamente
py cli.py "https://www.youtube.com/watch?v=EXEMPLO1" "https://www.youtube.com/watch?v=EXEMPLO2"

# Baixar apenas áudio (MP3)
py cli.py --audio links.txt
```

### 2. Versão em C# (.NET)
Para quem prefere utilizar a solução em **C#**:

```powershell
cd csharp_version\YoutubeDownloader
dotnet run
```
Ou dê um duplo clique em `csharp_version\Iniciar_CSharp.bat`.

---

## ✨ Recursos do Sistema

- **Nomeação Automática**: O nome do arquivo no disco é exatamente o título original do vídeo no YouTube.
- **Sanitização de Caracteres**: Caracteres especiais proibidos no Windows (`\ / : * ? " < > |`) são tratados automaticamente para evitar erros.
- **Download em Lote**: Baixe dezenas ou centenas de links de uma só vez.
- **Barra de Progresso em Tempo Real**: Exibe porcentagem, velocidade de download (MB/s) e tempo restante (ETA).
- **Controle de Cancelamento**: Botão para cancelar a qualquer momento sem corromper arquivos.
- **Suporte a FFmpeg**: FFmpeg integrado para combinar vídeo de alta resolução (1080p, 4K) e áudio em MP4 perfeito ou converter para MP3.
