# ☁️ Como Conectar o Sistema ao Google Drive

O sistema oferece **duas formas** de salvar seus vídeos diretamente no Google Drive:

---

## 🟢 Opção 1: Usando o Google Drive para Desktop (Mais Simples)

Se você já utiliza o aplicativo oficial do **Google Drive para Desktop** instalado no seu Windows (que cria uma unidade `G:\` ou uma pasta sincronizada no seu computador):

1. Abra o **Baixador de Vídeos**.
2. No campo **"Salvar em"**, clique no botão **"Procurar..."**.
3. Selecione a sua pasta do Google Drive (por exemplo: `G:\Meu Drive\Vídeos` ou `C:\Users\SeuUsuario\Google Drive`).
4. Clique em **Iniciar Download**.
5. **Pronto!** Os vídeos serão baixados diretamente nessa pasta e o próprio aplicativo do Google Drive fará o upload automático para a nuvem em segundo plano.

---

## 🔵 Opção 2: Upload Direto via Nuvem (Google Drive API)

Se você deseja que o programa faça o upload diretamente pela internet para a sua conta do Google Drive (mesmo sem o aplicativo de desktop instalado) e tenha a opção de **apagar os vídeos do computador após o envio** para economizar espaço:

### Passo a Passo para Obter o `credentials.json` (Gratuito e feito uma única vez):

1. Acesse o **Google Cloud Console**:
   👉 [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Crie um projeto novo (ex: *"Baixador YouTube"*).
3. No menu lateral, vá em **APIs e Serviços** > **Biblioteca**.
4. Pesquise por **Google Drive API** e clique em **Ativar**.
5. Vá em **APIs e Serviços** > **Credenciais** > clique em **Criar Credenciais** > **ID do cliente OAuth**.
   - *Se for a primeira vez, clique em "Configurar Tela de Consentimento", escolha "Externo", dê um nome e adicione seu próprio e-mail como usuário de teste.*
   - Em "Tipo de aplicativo", escolha **Aplicativo para Computador** (Desktop App).
6. Clique em **Criar** e depois em **Baixar JSON**.
7. Renomeie o arquivo baixado para **`credentials.json`** e coloque-o na mesma pasta do programa (onde fica o `BaixadorYoutube.exe`).

### Conectando no Aplicativo:
1. No aplicativo, marque a opção **"☁️ Fazer upload automático para o Google Drive"**.
2. Clique no botão **"🔑 Conectar Conta Google"**.
3. Uma página do seu navegador padrão se abrirá para você fazer login na sua conta Google e autorizar.
4. O sistema salvará o acesso com segurança e criará automaticamente a pasta **"YouTube Downloads"** no seu Google Drive!
5. Se marcar a opção **"🗑️ Excluir cópia local após upload"**, o vídeo é enviado para a nuvem e o arquivo local é excluído para não lotar seu disco rígido.
