# Bot de acertar musiquinha

Este projeto é um bot automatizado que interage com um jogo de musiquinha. O bot é capaz de jogar automaticamente, capturando e armazenando os IDs das aberturas de animes em um banco de dados, a partir dos logs e requisições do site.

## Pré-requisitos

Antes de executar o programa, você precisa ter:

- **Python 3.x** instalado.
- **MySQL Server** instalado e em execução.
- **Git** instalado (para clonar o repositório).

## Instalação
### 1. **Clone o repositório:**
   
No cmd digite:
   ```bash
   git clone https://github.com/cauancesar/musiquinha.git
   cd <NOME_DO_DIRETÓRIO>
   ```


### 2. **Crie um ambiente virtual e ative:**
   
No diretório do projeto, digite:
   ```bash
   python -m venv venv
   ```
Depois de criado, ative o ambiente virtual:

#### Windows
   ```bash
   venv\Scripts\activate
   ```
#### macOS/Linux
   ```bash
   source venv/bin/activate
   ```


### 3. **Instale as dependências necessárias:**

Ainda no diretório do projeto, digite:
   ```bash
   pip install -r requirements.txt
   ```


### 4. **Configure o arquivo .env:**

Crie um arquivo chamado .env na raiz do projeto com as seguintes variáveis de ambiente:
   ```bash
LOGIN=seu_login
PASSWORD=sua_senha
DB_PASSWORD=sua_senha_do_mysql
   ```


## Executando o programa

Para executar o programa, digite:
   ```bash
python main.py
   ```
Caso você não tenha preenchido LOGIN e PASSWORD no arquivo .env, o programa abrirá um prompt para perguntar seu login e senha antes de iniciar o navegador. Em seguida, perguntará se você deseja logar automaticamente ou não:

* N: O programa abrirá o site para que você possa logar e criar ou entrar em uma partida.
* Y: O programa logará automaticamente no jogo, criará uma sala e iniciará o jogo.
