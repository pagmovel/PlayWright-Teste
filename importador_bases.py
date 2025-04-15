import os
import pandas as pd
import glob
import logging
from datetime import datetime
from models.tbl_processos import TblProcessos
from models.db import SessionLocal
import traceback

# Definição de diretórios
LOGS_DIR = 'logs'

# Configuração de logging
def setup_logging():
    """
    Configura o sistema de logging com rotação de arquivos.
    """
    # Cria o diretório de logs se não existir
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    
    # Nome do arquivo de log com data e hora
    log_filename = os.path.join(LOGS_DIR, f'importador_bases_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configuração do logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )
    
    # Obtém o logger específico para este módulo
    logger = logging.getLogger(__name__)
    
    # Adiciona um handler de arquivo específico para este módulo
    file_handler = logging.FileHandler(log_filename, encoding='utf-8', mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    return logger

# Inicializa o logger
logger = setup_logging()

def validar_colunas(df):
    """
    Valida se todas as colunas necessárias estão presentes no DataFrame
    
    Args:
        df (pandas.DataFrame): DataFrame a ser validado
        
    Returns:
        bool: True se todas as colunas estão presentes, False caso contrário
    """
    # Lista de colunas esperadas
    colunas_esperadas = [
        'item',
        'Tipo de Sentença',
        'Valor Contraproposta',
        'Usuário Serv',
        'Usuário Autojur'
    ]
    
    # Verifica quais colunas estão faltando
    colunas_faltantes = [col for col in colunas_esperadas if col not in df.columns]
    
    if colunas_faltantes:
        print("\nERRO: Colunas obrigatórias ausentes na planilha:")
        print("-" * 50)
        for coluna in colunas_faltantes:
            print(f"- {coluna}")
        print("\nColunas esperadas:")
        print("-" * 50)
        for coluna in colunas_esperadas:
            print(f"- {coluna}")
        return False
        
    return True

def importar_planilha(arquivo):
    """Importa dados da aba Planilha1 de uma planilha para o banco de dados"""
    try:
        logger.info(f"Importando planilha: {arquivo}")
        
        # Lê a planilha, especificando a aba Planilha1
        df = pd.read_excel(arquivo, sheet_name="Planilha1")
        
        # Valida as colunas antes de prosseguir
        if not validar_colunas(df):
            logger.error(f"Planilha {arquivo} não possui todas as colunas necessárias")
            return False
        
        # Gera a ordem de serviço única para toda a planilha
        ordem_servico = datetime.now().strftime("%Y%m%d%H%M%S")
        logger.info(f"Ordem de serviço gerada para a planilha: {ordem_servico}")
        
        # Processa cada linha da planilha
        for _, row in df.iterrows():
            # Verifica se o processo já existe pelo item
            processo_existente = TblProcessos.find_by_item(str(row['item']))
            
            if processo_existente:
                # Atualiza o processo existente
                dados_atualizacao = {
                    'tipo_sentenca': str(row['Tipo de Sentença']) if 'Tipo de Sentença' in row else None,
                    'valor_contraproposta': str(row['Valor Contraproposta']) if 'Valor Contraproposta' in row else None,
                    'usuario_serv': str(row['Usuário Serv']) if 'Usuário Serv' in row else None,
                    'usuario_autojur': str(row['Usuário Autojur']) if 'Usuário Autojur' in row else None,
                    'ordem_servico': ordem_servico
                }
                processo_existente.update(**dados_atualizacao)
                logger.info(f"Processo atualizado: {row['item']}")
            else:
                # Cria um novo processo
                dados_processo = {
                    'item': str(row['item']),
                    'tipo_sentenca': str(row['Tipo de Sentença']) if 'Tipo de Sentença' in row else None,
                    'valor_contraproposta': str(row['Valor Contraproposta']) if 'Valor Contraproposta' in row else None,
                    'usuario_serv': str(row['Usuário Serv']) if 'Usuário Serv' in row else None,
                    'usuario_autojur': str(row['Usuário Autojur']) if 'Usuário Autojur' in row else None,
                    'ordem_servico': ordem_servico
                }
                TblProcessos.insert(dados_processo)
                logger.info(f"Novo processo adicionado: {row['item']}")
        
        logger.info(f"Importação concluída: {arquivo}")
        
    except Exception as e:
        logger.error(f"Erro ao importar planilha {arquivo}: {e}")

def processar_todas_planilhas():
    """Processa todas as planilhas na pasta inputs"""
    try:
        # Lista todos os arquivos Excel na pasta inputs
        arquivos = glob.glob("inputs/*.xlsx")
        
        if not arquivos:
            logger.warning("Nenhuma planilha encontrada na pasta inputs")
            return
        
        # Processa cada arquivo
        for arquivo in arquivos:
            importar_planilha(arquivo)
            
        logger.info("Processamento de todas as planilhas concluído")
        
    except Exception as e:
        logger.error(f"Erro durante o processamento: {e}")

def obter_processos_nao_atribuidos(usuario=None):
    """
    Retorna todos os processos não atribuídos.
    Se um usuário for fornecido, retorna apenas os processos não atribuídos desse usuário.
    
    Args:
        usuario (str, optional): Nome do usuário para filtrar os processos
        
    Returns:
        list: Lista de processos não atribuídos
    """
    try:
        logger.info(f"Buscando processos não atribuídos{f' para o usuário {usuario}' if usuario else ''}")
        
        session = SessionLocal()
        try:
            if usuario:
                query = session.query(TblProcessos).filter(
                    TblProcessos.usuario_serv == usuario,
                    TblProcessos.atribuido == False
                )
            else:
                query = session.query(TblProcessos).filter(
                    TblProcessos.atribuido == False
                )
            
            processos = query.all()
            logger.info(f"Encontrados {len(processos)} processos não atribuídos{f' para o usuário {usuario}' if usuario else ''}")
            return processos
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Erro ao obter processos não atribuídos: {e}")
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        return []

def obter_processos_nao_classificados():
    """Retorna todos os processos não classificados"""
    try:
        processos = TblProcessos.find_nao_classificados()
        # Verifica se processos é um objeto QueryChain e executa a consulta
        if hasattr(processos, 'all'):
            return processos.all()
        else:
            return list(processos)
    except Exception as e:
        logger.error(f"Erro ao obter processos não classificados: {e}")
        return []
    
def listar_usuarios():
    """Retorna todos os usuários cadastrados"""
    try:
        usuarios = TblProcessos.listar_usuarios_serv()
        # Verifica se usuarios é um objeto QueryChain e executa a consulta
        if hasattr(usuarios, 'all'):
            return usuarios.all()
        else:
            return list(usuarios)
    except Exception as e:
        logger.error(f"Erro ao obter lista de usuários: {e}")
        return []


if __name__ == "__main__":
    processar_todas_planilhas() 