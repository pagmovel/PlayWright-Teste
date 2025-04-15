# Sistema de Importação e Execução de Processos BancoX

## Visão Geral

Este sistema é responsável por automatizar o processo de importação e execução de processos do BancoX. Ele consiste em dois módulos principais:

1. **Importador**: Responsável por importar dados de planilhas Excel para o banco de dados
2. **Executor**: Responsável por automatizar a execução dos processos no sistema

## Funcionalidades Principais

### Importador

- Importação de planilhas Excel
- Validação de colunas obrigatórias
- Geração automática de ordem de serviço
- Inserção e atualização de processos no banco de dados

### Executor

- Login automático no sistema
- Navegação automatizada no menu
- Preenchimento automático de formulários
- Processamento de processos pendentes

## Tecnologias Utilizadas

- Python 3.x
- SQLAlchemy (ORM)
- Pandas (Processamento de planilhas)
- Playwright (Automação web)
- OpenCV (Processamento de imagens)
- Tesseract OCR (Reconhecimento de texto)

## Estrutura do Projeto

```
projeto/
├── importador_bases.py    # Importação de planilhas
├── main.py               # Execução de processos
├── models/               # Modelos do banco de dados
├── templates/            # Templates para reconhecimento
├── inputs/              # Planilhas de entrada
├── processed/           # Planilhas processadas
├── error/               # Planilhas com erro
└── logs/                # Logs do sistema
```

## Documentação

- [Instalação](INSTALACAO.md)
- [Uso do Sistema](USO.md)
- [Estrutura do Projeto](ESTRUTURA.md)

## Requisitos

- Python 3.x
- PostgreSQL
- Tesseract OCR
- Navegador Chrome/Edge

## Suporte

Para suporte ou dúvidas, entre em contato com a equipe de desenvolvimento.
