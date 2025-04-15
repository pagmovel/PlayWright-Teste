# Estrutura do Projeto

## Visão Geral da Estrutura

```
projeto/
├── importador_bases.py    # Importação de planilhas
├── main.py               # Execução de processos
├── models/               # Modelos do banco de dados
│   ├── db.py            # Configuração do banco
│   └── tbl_processos.py  # Modelo de processos
├── templates/            # Templates para reconhecimento
├── inputs/              # Planilhas de entrada
├── processed/           # Planilhas processadas
├── error/               # Planilhas com erro
└── logs/                # Logs do sistema
```

## Componentes Principais

### 1. Importador (importador_bases.py)

- **Função**: Importação de planilhas Excel
- **Principais componentes**:
  - `validar_colunas()`: Validação de colunas obrigatórias
  - `importar_planilha()`: Importação de uma planilha
  - `processar_todas_planilhas()`: Processamento em lote

### 2. Executor (main.py)

- **Função**: Automação de processos
- **Principais componentes**:
  - `login()`: Autenticação no sistema
  - `navegar_menu()`: Navegação automatizada
  - `preencher_formulario()`: Preenchimento de campos
  - `processar_processos()`: Processamento de processos

### 3. Modelos (models/)

- **TblProcessos**:
  - Campos:
    - `id`: Identificador único
    - `item`: Número do processo
    - `tipo_sentenca`: Tipo da sentença
    - `valor_contraproposta`: Valor da contraproposta
    - `usuario_serv`: Usuário do serviço
    - `usuario_autojur`: Usuário do autojur
    - `ordem_servico`: Ordem de serviço
    - `atribuido`: Status de atribuição
    - `classificado`: Status de classificação
  - Métodos:
    - `find_by_item()`: Busca por item
    - `find_nao_atribuidos()`: Lista processos não atribuídos
    - `find_nao_classificados()`: Lista processos não classificados
    - `marcar_atribuido()`: Atualiza status de atribuição
    - `marcar_classificado()`: Atualiza status de classificação

### 4. Templates (templates/)

- **Função**: Armazenamento de imagens para reconhecimento
- **Tipos de templates**:
  - Botões
  - Campos de formulário
  - Elementos de interface

### 5. Diretórios de Dados

- **inputs/**: Planilhas a serem processadas
- **processed/**: Planilhas processadas com sucesso
- **error/**: Planilhas com erro no processamento
- **logs/**: Arquivos de log do sistema

## Fluxo de Dados

### 1. Importação

```
Planilha Excel (inputs/)
    ↓
Validação de Colunas
    ↓
Processamento
    ↓
Banco de Dados
    ↓
Arquivo Processado (processed/)
```

### 2. Execução

```
Banco de Dados
    ↓
Login no Sistema
    ↓
Navegação
    ↓
Processamento
    ↓
Atualização do Banco
```

## Configurações

### 1. Banco de Dados (.env)

```env
DB_USER=usuario
DB_PASS=senha
DB_HOST=host
DB_PORT=porta
DB_NAME=banco
```

### 2. Sistema (config.json)

```json
{
  "ambiente": "dev",
  "database": {
    "prod": {
      "database": "pgsql",
      "dbname": "smart",
      "user": "usuario_prod",
      "password": "senha_prod",
      "host": "host_prod",
      "port": "5433",
      "schema": "servicenow"
    },
    "dev": {
      "database": "pgsql",
      "dbname": "smart",
      "user": "usuario_dev",
      "password": "senha_dev",
      "host": "host_dev",
      "port": "54320",
      "schema": "servicenow"
    },
    "autokit": {
      "database": "pgsql",
      "dbname": "autojur_consulta",
      "user": "usuario_autokit",
      "password": "senha_autokit",
      "host": "host_autokit",
      "port": "5433",
      "schema": "autokit"
    }
  },
  "ldap": {
    "server": "ldap://servidor",
    "user": "usuario_ldap",
    "password": "senha_ldap",
    "base_dn": "OU=RMS,DC=rochamarinho,DC=adv,DC=br"
  },
  "require_email": true,
  "email": {
    "host": "smtp.office365.com",
    "port": 587,
    "secure": true,
    "user": "email@dominio.com",
    "password": "senha_email"
  }
}
```

## Logs

### 1. Importador

- Nome: `importador_bases_YYYYMMDD_HHMMSS.log`
- Conteúdo:
  - Início/fim da importação
  - Erros de validação
  - Status de processamento

### 2. Executor

- Nome: `atribuicao_YYYYMMDD_HHMMSS.log`
- Conteúdo:
  - Status de login
  - Navegação
  - Processamento de processos
  - Erros e avisos

## Manutenção

### 1. Banco de Dados

- Backup regular
- Verificação de integridade
- Limpeza de dados antigos

### 2. Templates

- Atualização periódica
- Verificação de qualidade
- Backup de versões

### 3. Logs

- Rotação de arquivos
- Arquivamento
- Limpeza de logs antigos
