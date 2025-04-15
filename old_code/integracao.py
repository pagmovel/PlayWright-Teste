import asyncio
import os
import logging
from datetime import datetime
from models.tbl_processos import TblProcessos
from importador_bases import processar_todas_planilhas, obter_processos_nao_atribuidos, obter_processos_nao_classificados
from atribuicao import run as run_atribuicao
from classificacao_pre import run as run_classificacao
import traceback

# Definição de diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

def setup_logging(module_name):
    """
    Configura o sistema de logging com arquivos separados para cada módulo.
    
    Args:
        module_name (str): Nome do módulo para o arquivo de log
    """
    # Cria o diretório de logs se não existir
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    
    # Nome do arquivo de log apenas com a data
    log_filename = os.path.join(LOGS_DIR, f'{module_name}_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Configuração do logging
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)
    
    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_filename, encoding='utf-8', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

# Inicializa os loggers para cada módulo
logger_integracao = setup_logging('integracao')
logger_atribuicao = setup_logging('atribuicao')
logger_classificacao = setup_logging('classificacao')

async def executar_atribuicao():
    """Executa o processo de atribuição para processos não atribuídos"""
    try:
        # Obtém usuários com processos pendentes
        usuarios = TblProcessos.listar_usuarios_com_processos_pendentes()
        
        if not usuarios:
            logger_atribuicao.info("Não há usuários com processos pendentes")
            return
            
        logger_atribuicao.info(f"Encontrados {len(usuarios)} usuários com processos pendentes")
        
        # aqui eu preciso de um loop para cada usuario
        for usuario in usuarios:
            logger_atribuicao.info("-" * 65)
            logger_atribuicao.info(f"Atribuindo gcpj(s) para o usuario: {usuario}")
            
            # Obtém processos não atribuídos
            processos = obter_processos_nao_atribuidos(usuario)
            
            if not processos:
                logger_atribuicao.info(f"Nenhum processo pendente de atribuição encontrado para o usuário {usuario}.")
                continue  # Continua para o próximo usuário em vez de retornar
            
            logger_atribuicao.info(f"Iniciando atribuição para {len(processos)} processos do usuário {usuario}")
            
            # Executa o script de atribuição
            await run_atribuicao(usuario=usuario, processos=processos)
            
            # # Marca os processos como atribuídos
            # for processo in processos:
            #     TblProcessos.marcar_atribuido(processo.gcpj)
                
            logger_atribuicao.info(f"Processo de atribuição concluído para o usuário {usuario}")
        
        logger_atribuicao.info("Processo de atribuição concluído para todos os usuários")
        
    except Exception as e:
        logger_atribuicao.error(f"Erro durante o processo de atribuição: {e}")
        logger_atribuicao.error(f"Traceback completo: {traceback.format_exc()}")

async def executar_classificacao():
    """Executa o processo de classificação para processos não classificados"""
    try:
        # Obtém processos não classificados
        processos = obter_processos_nao_classificados()
        
        if not processos:
            logger_classificacao.info("Não há processos para classificação")
            return
        
        logger_classificacao.info(f"Iniciando classificação para {len(processos)} processos")
        
        # Executa o script de classificação
        await run_classificacao()
        
        # Marca os processos como classificados
        for processo in processos:
            TblProcessos.marcar_classificado(processo.gcpj)
            
        logger_classificacao.info("Processo de classificação concluído")
        
    except Exception as e:
        logger_classificacao.error(f"Erro durante o processo de classificação: {e}")
        logger_classificacao.error(f"Traceback completo: {traceback.format_exc()}")

async def executar_fluxo_completo():
    """Executa o fluxo completo: importação, atribuição e classificação"""
    try:
        logger_integracao.info("Iniciando fluxo completo de integração")
        
        # Importa as planilhas
        logger_integracao.info("Iniciando importação de planilhas")
        processar_todas_planilhas()
        logger_integracao.info("Importação de planilhas concluída")
        
        # Executa atribuição
        logger_integracao.info("Iniciando processo de atribuição")
        await executar_atribuicao()
        logger_integracao.info("Processo de atribuição concluído")
        
        # Executa classificação
        # logger_integracao.info("Iniciando processo de classificação")
        # await executar_classificacao()
        # logger_integracao.info("Processo de classificação concluído")
        
        # logger_integracao.info("Fluxo completo executado com sucesso")
        
    except Exception as e:
        logger_integracao.error(f"Erro durante o fluxo completo: {e}")
        logger_integracao.error(f"Traceback completo: {traceback.format_exc()}")

if __name__ == "__main__":
    try:
        logger_integracao.info("Iniciando execução do script de integração")
        asyncio.run(executar_fluxo_completo())
        logger_integracao.info("Script de integração finalizado com sucesso")
    except Exception as e:
        logger_integracao.error(f"Erro fatal durante a execução do script: {e}")
        logger_integracao.error(f"Traceback completo: {traceback.format_exc()}") 