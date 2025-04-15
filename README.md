# Sistema Automação WEB

Sistema para importação de processos do Bradesco para o WEB.

## Estrutura do Projeto

```
.
├── inputs/              # Pasta para arquivos Excel a serem importados
├── processed/           # Pasta para arquivos processados com sucesso
├── error/              # Pasta para arquivos com erro
├── logs/               # Pasta para arquivos de log
├── models/             # Modelos do banco de dados
│   ├── db.py          # Configuração do banco de dados
│   └── tbl_processos.py  # Modelo da tabela de processos
├── importador.py       # Script principal de importação
├── config.json         # Configurações do sistema
└── .env               # Variáveis de ambiente
```

## Requisitos

- Python 3.9 ou superior
- PostgreSQL
- Bibliotecas Python (instalar via `pip install -r requirements.txt`):
  - pandas>=1.5.0
  - openpyxl>=3.1.0
  - python-dotenv>=1.0.0
  - SQLAlchemy>=2.0.0
  - psycopg2-binary>=2.9.0

## Configuração

1. Instalar dependências:

```bash
pip install -r requirements.txt
```

2. Configurar arquivo `.env`:

```
DB_HOST=seu_host
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

3. Configurar `config.json`:

```json
{
  "ambiente": "dev",
  "schema": "public"
}
```

## Estrutura da Tabela

A tabela `tbl_processos` possui os seguintes campos:

- `id`: BigInteger, chave primária
- `gcpj`: String(20), único, índice
- `tipo_sentenca`: String(100)
- `contra`: String(100)
- `usuario_serv`: String(250)
- `usuario_autojur`: String(250)
- `atribuido`: Boolean
- `classificado`: Boolean
- `created_at`: DateTime
- `updated_at`: DateTime

## Uso

1. Coloque os arquivos Excel na pasta `inputs/`
2. Execute o script:

```bash
python importador.py
```

O script irá:

- Validar as colunas obrigatórias
- Remover duplicatas de GCPJ
- Importar os dados para o banco
- Mover o arquivo para `processed/` em caso de sucesso
- Mover o arquivo para `error/` em caso de falha
- Gerar logs detalhados em `logs/`

## Logs

Os logs são gerados na pasta `logs/` com o formato:

- Nome: `importador_YYYYMMDD_HHMMSS.log`
- Contém informações detalhadas sobre:
  - Início e fim do processamento
  - Validação de colunas
  - Registros processados
  - Erros encontrados
  - Estatísticas de importação

## Tratamento de Erros

O sistema trata os seguintes casos:

- Duplicatas de GCPJ (mantém o primeiro registro)
- Campos de texto excedendo o limite (trunca automaticamente)
- Erros de conexão com o banco
- Arquivos inválidos ou mal formatados

## Manutenção

Para alterar o tamanho dos campos ou adicionar novas colunas:

1. Atualizar o modelo em `models/tbl_processos.py`
2. Recriar a tabela no banco de dados
3. Atualizar a documentação
