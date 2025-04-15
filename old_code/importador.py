import pandas as pd
from sqlalchemy import create_engine
from models.tbl_processos import TblProcessos
from models.db import SessionLocal, get_schema
import os
from dotenv import load_dotenv
import logging
import glob
import traceback
from datetime import datetime
import shutil

load_dotenv()

# Configuração de diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS_DIR = os.path.join(BASE_DIR, 'inputs')
PROCESSED_DIR = os.path.join(BASE_DIR, 'processed')
ERROR_DIR = os.path.join(BASE_DIR, 'error')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Cria diretórios se não existirem
for directory in [INPUTS_DIR, PROCESSED_DIR, ERROR_DIR, LOGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Diretório criado: {directory}")

# Configuração de logging
def setup_logging():
    """
    Configura o sistema de logging com rotação de arquivos.
    """
    # Cria o diretório de logs se não existir
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    
    # Nome do arquivo de log com data e hora
    log_filename = os.path.join(LOGS_DIR, f'importador_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
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
    """Valida se todas as colunas obrigatórias estão presentes"""
    colunas_obrigatorias = [
        'GCPJ',
        'Tipo de Sentença',
        'Valor Contraproposta',
        'Usuário Serv',
        'Usuário Autojur'
    ]
    
    colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
    if colunas_faltantes:
        raise ValueError(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")

def importar_planilha(caminho_arquivo):
    """Importa dados da planilha para o banco de dados"""
    session = None
    try:
        # Lê a planilha
        logger.info(f"Lendo arquivo: {caminho_arquivo}")
        df = pd.read_excel(caminho_arquivo)
        logger.info(f"Arquivo lido com sucesso. Total de linhas: {len(df)}")
        
        # Remove duplicatas de GCPJ
        df = df.drop_duplicates(subset=['GCPJ'], keep='first')
        logger.info(f"Após remoção de duplicatas: {len(df)} linhas")
        
        # Valida colunas
        validar_colunas(df)
        logger.info("Validação de colunas concluída com sucesso")
        
        # Renomeia colunas para o formato do banco
        mapeamento_colunas = {
            'GCPJ': 'gcpj',
            'Tipo de Sentença': 'tipo_sentenca',
            'Valor Contraproposta': 'contra',
            'Usuário Serv': 'usuario_serv',
            'Usuário Autojur': 'usuario_autojur'
        }
        df = df.rename(columns=mapeamento_colunas)
        logger.info("Colunas renomeadas com sucesso")
        
        # Cria sessão do banco
        session = SessionLocal()
        logger.info(f"Conectado ao banco de dados. Schema: {get_schema()}")
        
        # Contadores para estatísticas
        total_registros = len(df)
        registros_atualizados = 0
        registros_inseridos = 0
        erros = 0
        
        # Processa cada linha
        for index, row in df.iterrows():
            try:
                # Converte GCPJ para string
                gcpj = str(row['gcpj']) if pd.notna(row['gcpj']) else None
                if not gcpj:
                    logger.warning(f"Linha {index + 1}: GCPJ vazio ou inválido")
                    erros += 1
                    continue
                
                # Trunca campos de texto se necessário
                tipo_sentenca = str(row['tipo_sentenca'])[:100] if pd.notna(row['tipo_sentenca']) else None
                contra = str(row['contra'])[:100] if pd.notna(row['contra']) else None
                usuario_serv = str(row['usuario_serv'])[:250] if pd.notna(row['usuario_serv']) else None
                usuario_autojur = str(row['usuario_autojur'])[:250] if pd.notna(row['usuario_autojur']) else None
                
                processo = TblProcessos(
                    gcpj=gcpj,
                    tipo_sentenca=tipo_sentenca,
                    contra=contra,
                    usuario_serv=usuario_serv,
                    usuario_autojur=usuario_autojur,
                    atribuido=False,
                    classificado=False
                )
                
                # Verifica se processo já existe
                existente = session.query(TblProcessos).filter_by(gcpj=gcpj).first()
                if existente:
                    # Atualiza dados mantendo o estado de atribuição e classificação
                    if tipo_sentenca:
                        existente.tipo_sentenca = tipo_sentenca
                    if contra:
                        existente.contra = contra
                    if usuario_serv:
                        existente.usuario_serv = usuario_serv
                    if usuario_autojur:
                        existente.usuario_autojur = usuario_autojur
                    registros_atualizados += 1
                    logger.info(f"Processo {gcpj} atualizado")
                else:
                    # Insere novo
                    session.add(processo)
                    registros_inseridos += 1
                    logger.info(f"Novo processo {gcpj} inserido")
                
                # Commit a cada 50 registros para evitar transações muito longas
                if (index + 1) % 50 == 0:
                    session.commit()
                    logger.info(f"Commit parcial: {index + 1} de {total_registros} registros processados")
            
            except Exception as e:
                erros += 1
                logger.error(f"Erro ao processar linha {index + 1} (GCPJ: {row.get('gcpj', 'N/A')}): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Rollback da transação atual e continua para a próxima linha
                session.rollback()
                continue
        
        # Commit final
        try:
            session.commit()
            logger.info(f"Importação do arquivo {caminho_arquivo} concluída com sucesso")
            logger.info(f"Estatísticas: {registros_inseridos} novos registros, {registros_atualizados} registros atualizados, {erros} erros")
            
            # Move o arquivo para a pasta processed
            nome_arquivo = os.path.basename(caminho_arquivo)
            novo_caminho = os.path.join(PROCESSED_DIR, nome_arquivo)
            shutil.move(caminho_arquivo, novo_caminho)
            logger.info(f"Arquivo movido para: {novo_caminho}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro no commit final: {str(e)}")
            # Move o arquivo para a pasta error
            nome_arquivo = os.path.basename(caminho_arquivo)
            novo_caminho = os.path.join(ERROR_DIR, nome_arquivo)
            shutil.move(caminho_arquivo, novo_caminho)
            logger.info(f"Arquivo com erro movido para: {novo_caminho}")
            raise
        
    except Exception as e:
        logger.error(f"Erro na importação do arquivo {caminho_arquivo}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        if session:
            session.rollback()
        # Move o arquivo para a pasta error
        nome_arquivo = os.path.basename(caminho_arquivo)
        novo_caminho = os.path.join(ERROR_DIR, nome_arquivo)
        shutil.move(caminho_arquivo, novo_caminho)
        logger.info(f"Arquivo com erro movido para: {novo_caminho}")
        raise
    finally:
        if session:
            session.close()
            logger.info("Sessão do banco de dados fechada")

def processar_arquivos_inputs():
    """Processa todos os arquivos Excel na pasta inputs/"""
    # Lista todos os arquivos Excel na pasta inputs
    arquivos = glob.glob(os.path.join(INPUTS_DIR, '*.xlsx')) + glob.glob(os.path.join(INPUTS_DIR, '*.xls'))
    
    if not arquivos:
        logger.warning("Nenhum arquivo Excel encontrado na pasta 'inputs'")
        return
    
    logger.info(f"Encontrados {len(arquivos)} arquivos para processar")
    
    # Processa cada arquivo
    for arquivo in arquivos:
        try:
            logger.info(f"Iniciando importação do arquivo: {arquivo}")
            importar_planilha(arquivo)
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {arquivo}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    try:
        logger.info("Iniciando processamento de arquivos")
        processar_arquivos_inputs()
        logger.info("Processamento concluído")
    except Exception as e:
        logger.error(f"Erro durante o processamento: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}") 