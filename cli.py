"""
Interface de Linha de Comando (CLI) para baixar vídeos do YouTube em lote.
Pode ser executado diretamente pelo terminal ou recebendo arquivos/links como parâmetros.

Exemplos de uso:
    py cli.py
    py cli.py links.txt
    py cli.py --audio links.txt
    py cli.py "https://www.youtube.com/watch?v=..."
"""

import os
import sys
import argparse
from downloader import YouTubeDownloader, is_ffmpeg_installed


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Baixador de Vídeos do YouTube em Lote (salva com o nome original do vídeo)"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Links do YouTube ou caminhos para arquivos .txt contendo links (um por linha)"
    )
    parser.add_argument(
        "-o", "--output",
        default=os.path.join(os.getcwd(), "downloads"),
        help="Pasta de destino onde os arquivos serão salvos (padrão: ./downloads)"
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["best", "1080p", "720p"],
        default="best",
        help="Qualidade do vídeo (padrão: best)"
    )
    parser.add_argument(
        "-a", "--audio",
        action="store_true",
        help="Baixar apenas o áudio (MP3/M4A)"
    )
    return parser.parse_args()


def load_urls(inputs):
    urls = []
    for item in inputs:
        item = item.strip()
        if not item:
            continue
        if os.path.isfile(item):
            print(f"Lendo links do arquivo: {item}")
            with open(item, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and ("youtube.com" in line or "youtu.be" in line):
                        urls.append(line)
        elif "youtube.com" in item or "youtu.be" in item:
            urls.append(item)
    return urls


def progress_printer(data):
    status = data.get("status")
    if status == "downloading":
        percent = data.get("percent", 0)
        speed = (data.get("speed") or 0) / (1024 * 1024)
        eta = data.get("eta") or 0
        m, s = divmod(int(eta), 60)
        sys.stdout.write(f"\r  -> Progresso: {percent:5.1f}% | Velocidade: {speed:5.2f} MB/s | Restante: {m:02d}:{s:02d}   ")
        sys.stdout.flush()
    elif status == "finished":
        sys.stdout.write("\r  -> Concluído! Finalizando processamento...                    \n")
        sys.stdout.flush()


def main():
    args = parse_arguments()
    urls = load_urls(args.inputs)

    # Se nenhum link foi passado pela linha de comando, tenta verificar links.txt ou pede ao usuário
    if not urls:
        default_file = "links.txt"
        if os.path.exists(default_file):
            print(f"Nenhum argumento fornecido. Lendo automaticamente do arquivo '{default_file}'...")
            urls = load_urls([default_file])

    if not urls:
        print("=" * 60)
        print("          BAIXADOR DE VÍDEOS DO YOUTUBE (CLI)")
        print("=" * 60)
        print("Cole os links abaixo (digite uma linha em branco ou 'fim' para iniciar):")
        while True:
            try:
                line = input("> ").strip()
                if not line or line.lower() == "fim":
                    break
                if "youtube.com" in line or "youtu.be" in line:
                    urls.append(line)
                else:
                    print("  [Aviso] O link digitado não parece ser do YouTube.")
            except (KeyboardInterrupt, EOFError):
                break

    if not urls:
        print("\nNenhum link válido fornecido. Encerrando.")
        return

    format_type = "audio" if args.audio else "video"
    print("\n" + "=" * 60)
    print(f"Total de links a baixar: {len(urls)}")
    print(f"Pasta de destino: {os.path.abspath(args.output)}")
    print(f"Formato: {'Áudio' if args.audio else f'Vídeo ({args.quality})'}")
    print(f"FFmpeg instalado: {'Sim' if is_ffmpeg_installed() else 'Não (usando modo compatível)'}")
    print("=" * 60 + "\n")

    downloader = YouTubeDownloader(
        output_dir=args.output,
        quality=args.quality,
        format_type=format_type,
        progress_callback=progress_printer,
        log_callback=lambda msg, lvl: print(f"[{lvl}] {msg}")
    )

    results = downloader.download_batch(urls)

    print("\n" + "=" * 60)
    print("RESUMO DO PROCESSAMENTO:")
    print(f"  Total de Sucessos: {len(results['success'])}")
    for item in results['success']:
        print(f"    ✔ {item['title']}")

    if results['failed']:
        print(f"  Total de Falhas: {len(results['failed'])}")
        for item in results['failed']:
            print(f"    ✖ {item['url']} -> {item['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
