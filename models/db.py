# db.py

import os
import json
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def find_config_file():
    current_dir = os.path.dirname(__file__)
    # Verifica em 1 e 2 níveis acima
    for levels in range(1, 3):
        directory = os.path.abspath(os.path.join(current_dir, *[".."] * levels))
        config_file = os.path.join(directory, 'config.json')
        if os.path.isfile(config_file):
            return config_file
    return None

config_path = find_config_file()
if config_path:
    print(f"Arquivo encontrado em: {config_path}")
else:
    raise FileNotFoundError("config.json não foi encontrado em até 2 níveis acima.")

# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# config_path = os.path.join(BASE_DIR, 'config.json')

with open(config_path, 'r') as f:
    config = json.load(f)

def get_engine(dbKey =  None):
    """
    Lê config["ambiente"] (ex.: 'dev', 'prod') e monta a conexão com base nisso.
    """
    # environment = config.get("environment", "dev")  # Pega "environment" ou usa 'dev' como padrão
    environment = dbKey if dbKey is not None else config.get("ambiente", "dev")
    db_params = config['database'].get(environment)
    
    if not db_params:
        raise ValueError(f"Environment '{environment}' não encontrado em config['database'].")
    
    if db_params['database'].lower() == 'pgsql':
        connection_string = (
            f"postgresql://{db_params['user']}:{db_params['password']}"
            f"@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
        )
    else:
        # Fallback se não for pgsql
        connection_string = 'sqlite:///meu_banco.db'
    
    return create_engine(connection_string, echo=False)

def get_schema():
    """
    Retorna o schema definido no config.json para o environment atual.
    """
    environment = config.get("ambiente", "dev")
    
    db_params = config['database'].get(environment)
    if not db_params:
        raise ValueError(f"Environment '{environment}' não encontrado em config['database'].")
    return db_params.get('schema', None)

# Inicializa engine e SessionLocal para uso geral
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
