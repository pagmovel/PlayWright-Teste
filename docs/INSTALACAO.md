# Instalação do Sistema

## Pré-requisitos

### 1. Python

- Instale o Python 3.x do site oficial: https://www.python.org/downloads/
- Certifique-se de marcar a opção "Add Python to PATH" durante a instalação

### 2. PostgreSQL

- Instale o PostgreSQL: https://www.postgresql.org/download/
- Crie um banco de dados para o projeto
- Anote as credenciais de acesso (usuário, senha, host, porta)

### 3. Tesseract OCR

- Baixe o instalador do Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Execute o instalador e anote o caminho de instalação
- Adicione o caminho ao PATH do sistema

### 4. Navegador

- Instale o Google Chrome ou Microsoft Edge
- Certifique-se de que está atualizado

## Instalação do Projeto

1. Clone o repositório:

```bash
git clone [URL_DO_REPOSITÓRIO]
cd [NOME_DO_PROJETO]
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure o arquivo .env:

```env
DB_USER=seu_usuario
DB_PASS=sua_senha
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nome_do_banco
USER=seu_usuario_bradesco
PASS=sua_senha_bradesco
```

5. Configure o arquivo config.json:

```json
{
  "tesseract_path": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
  "templates_dir": "templates",
  "inputs_dir": "inputs",
  "processed_dir": "processed",
  "error_dir": "error",
  "logs_dir": "logs"
}
```

6. Crie os diretórios necessários:

```bash
mkdir inputs processed error logs templates
```

## Verificação da Instalação

1. Teste a conexão com o banco:

```bash
python -c "from models.db import SessionLocal; SessionLocal()"
```

2. Teste o Tesseract:

```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

3. Teste o Playwright:

```bash
playwright install
```

## Solução de Problemas

### Erro de Conexão com o Banco

- Verifique se o PostgreSQL está rodando
- Confirme as credenciais no arquivo .env
- Verifique se o banco de dados existe

### Erro do Tesseract

- Verifique se o caminho no config.json está correto
- Confirme se o Tesseract está no PATH do sistema
- Tente reinstalar o Tesseract

### Erro do Playwright

- Execute `playwright install` novamente
- Verifique se o navegador está instalado
- Limpe o cache do navegador

## Próximos Passos

Após a instalação, consulte a documentação de [Uso do Sistema](USO.md) para começar a utilizar o sistema.
