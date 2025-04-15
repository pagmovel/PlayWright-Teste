# Uso do Sistema

## Importação de Planilhas

### Preparação das Planilhas

1. As planilhas devem estar no formato Excel (.xlsx)
2. Devem conter a aba "Planilha1"
3. Colunas obrigatórias:
   - item
   - Tipo de Sentença
   - Valor Contraproposta
   - Usuário Serv
   - Usuário Autojur

### Processo de Importação

1. Coloque as planilhas na pasta `inputs/`
2. Execute o importador:

```bash
python importador_bases.py
```

3. Verifique os logs em `logs/importador_bases_YYYYMMDD_HHMMSS.log`
4. Planilhas processadas serão movidas para `processed/`
5. Planilhas com erro serão movidas para `error/`

## Execução de Processos

### Configuração

1. Verifique se as credenciais no `.env` estão corretas
2. Certifique-se que o banco de dados está acessível
3. Verifique se há processos pendentes no banco

### Execução

1. Execute o módulo principal:

```bash
python main.py
```

2. O sistema irá:
   - Fazer login no sistema
   - Navegar até a página de processos
   - Processar cada processo pendente
   - Registrar o progresso nos logs

### Monitoramento

1. Acompanhe os logs em tempo real:

```bash
tail -f logs/atribuicao_YYYYMMDD_HHMMSS.log
```

2. Verifique o status dos processos no banco de dados
3. Monitore a pasta `processed/` para confirmar o processamento

## Logs e Monitoramento

### Estrutura de Logs

- `logs/importador_bases_*.log`: Logs da importação
- `logs/atribuicao_*.log`: Logs da execução
- `logs/integracao_*.log`: Logs da integração

### Níveis de Log

- INFO: Operações normais
- WARNING: Avisos importantes
- ERROR: Erros que precisam de atenção
- DEBUG: Informações detalhadas para debug

### Verificação de Status

1. Importação:

   - Verifique os logs do importador
   - Confira a pasta `processed/`
   - Verifique o banco de dados

2. Execução:
   - Monitore os logs em tempo real
   - Verifique o status no banco
   - Confira a interface do sistema

## Solução de Problemas

### Problemas na Importação

1. Verifique o formato da planilha
2. Confira se todas as colunas obrigatórias estão presentes
3. Verifique os logs de erro
4. Confira as permissões das pastas

### Problemas na Execução

1. Verifique a conexão com o sistema
2. Confira as credenciais
3. Verifique se o navegador está atualizado
4. Monitore os logs de erro

### Erros Comuns

1. "Coluna não encontrada"

   - Verifique o nome da coluna na planilha
   - Confira se está na aba correta

2. "Erro de conexão"

   - Verifique a internet
   - Confira as credenciais
   - Verifique se o sistema está online

3. "Erro de reconhecimento"
   - Verifique os templates
   - Confira a resolução da tela
   - Atualize os templates se necessário

## Manutenção

### Backup

1. Faça backup regular do banco de dados
2. Mantenha cópias das planilhas originais
3. Arquive os logs periodicamente

### Atualização

1. Mantenha as dependências atualizadas
2. Verifique atualizações do sistema
3. Atualize os templates quando necessário

### Limpeza

1. Limpe a pasta `processed/` periodicamente
2. Arquivar logs antigos
3. Remover planilhas processadas
