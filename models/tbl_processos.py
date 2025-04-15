from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Text, distinct, text
from sqlalchemy.sql import func
from .db import Base, SessionLocal, get_schema, engine
from .crud import CRUDMixin
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

class TblProcessos(Base, CRUDMixin):
    """
    Modelo para armazenar os processos do Bradesco importados das planilhas.
    """
    __tablename__ = 'tbl_processos'
    __table_args__ = {'schema': get_schema()}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    item = Column(String(20), nullable=False, unique=True, index=True)
    tipo_sentenca = Column(String(100))
    contra = Column(String(100))
    usuario_serv = Column(String(250))
    usuario_autojur = Column(String(250))
    ordem_servico = Column(BigInteger)
    atribuido = Column(Boolean, default=False)
    classificado = Column(Boolean, default=False)    
    ja_atribuido = Column(Boolean, default=False)
    ja_classificado = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __init__(self, **kwargs):
        # Converte item para string se for número
        if 'item' in kwargs and kwargs['item'] is not None:
            kwargs['item'] = str(kwargs['item'])
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<TblProcessos(item='{self.item}', tipo_sentenca='{self.tipo_sentenca}')>"
    
    @classmethod
    def find_by_item(cls, item):
        """
        Encontra um processo pelo número do item.
        """
        return cls.get(where=[('item', item)])
    
    
    @classmethod
    def find_by_id(cls, id):
        """
        Encontra um processo pelo número do ID.
        """
        return cls.get(where=[('id', id)])
    
    
    @classmethod
    def find_nao_atribuidos(cls):
        """
        Retorna todos os processos não atribuídos.
        """
        return cls.all(where=[('atribuido', False)])
    
    @classmethod
    def find_nao_classificados(cls):
        """
        Retorna todos os processos não classificados.
        """
        return cls.all(where=[('classificado', False)])
    
    @classmethod
    def marcar_atribuido(cls, id):
        """
        Marca um processo como atribuído.
        """
        session = SessionLocal()
        try:
            processo = cls.find_by_id(id)
            if processo:
                processo.atribuido = True
                session.merge(processo)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    @classmethod
    def marcar_classificado(cls, item):
        """
        Marca um processo como classificado.
        """
        processo = cls.find_by_item(item)
        if processo:
            processo.update(classificado=True)
            return True
        return False

    @classmethod
    def listar_usuarios_serv(cls):
        """
        Retorna uma lista única de todos os usuários_serv cadastrados.
        """
        session = SessionLocal()
        try:
            usuarios = session.query(distinct(cls.usuario_serv)).filter(cls.usuario_serv.isnot(None)).all()
            return [usuario[0] for usuario in usuarios]
        finally:
            session.close()

    @classmethod
    def processos_nao_atribuidos_por_usuario(cls, usuario_serv, valor=False):
        """
        Retorna todos os processos não atribuídos de um usuário específico.
        
        Args:
            usuario_serv (str): Nome do usuário para filtrar
            
        Returns:
            list: Lista de processos não atribuídos do usuário
        """
        return cls.all(where=[
            ('usuario_serv', usuario_serv),
            ('atribuido', valor)
        ])

    @classmethod
    def processos_atribuidos_nao_classificados_por_usuario(cls, usuario_serv):
        """
        Retorna todos os processos atribuídos mas não classificados de um usuário específico.
        
        Args:
            usuario_serv (str): Nome do usuário para filtrar
            
        Returns:
            list: Lista de processos atribuídos mas não classificados do usuário
        """
        return cls.all(where=[
            ('usuario_serv', usuario_serv),
            ('atribuido', True),
            ('classificado', False)
        ])

    @classmethod
    def listar_usuarios_com_processos_pendentes(cls):
        """
        Retorna uma lista única de usuários que possuem processos não atribuídos 
        ou não classificados.
        
        Returns:
            list: Lista de usuários com processos pendentes
        """
        session = SessionLocal()
        try:
            usuarios = session.query(distinct(cls.usuario_serv))\
                .filter(cls.usuario_serv.isnot(None))\
                .filter(
                    ((cls.atribuido == False) | (cls.classificado == False))
                ).all()
            return [usuario[0] for usuario in usuarios]
        finally:
            session.close()

    @classmethod
    def listar_usuarios_atribuidos_pendentes(cls):
        """
        Retorna uma lista única de usuários que possuem processos não atribuídos.
        
        Returns:
            list: Lista de usuários com processos pendentes de atribuição
        """
        session = SessionLocal()
        try:
            usuarios = session.query(distinct(cls.usuario_serv))\
                .filter(cls.usuario_serv.isnot(None))\
                .filter(cls.atribuido == False)\
                .all()
            return [usuario[0] for usuario in usuarios]
        finally:
            session.close()

    @classmethod
    def listar_usuarios_classificacao_pendente(cls):
        """
        Retorna uma lista única de usuários que possuem processos atribuídos mas não classificados.
        
        Returns:
            list: Lista de usuários com processos pendentes de classificação
        """
        session = SessionLocal()
        try:
            usuarios = session.query(distinct(cls.usuario_serv))\
                .filter(cls.usuario_serv.isnot(None))\
                .filter(cls.atribuido == True)\
                .filter(cls.classificado == False)\
                .all()
            return [usuario[0] for usuario in usuarios]
        finally:
            session.close()

    @classmethod
    def atualizar_status_processo(cls, processo, **kwargs):
        """
        Atualiza o status de atribuição e/ou classificação de um processo.
        
        Args:
            processo (TblProcessos): Objeto do processo a ser atualizado
            **kwargs: Campos a serem atualizados (atribuido e/ou classificado)
            
        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        session = SessionLocal()
        try:
            if processo:
                # Atualiza apenas os campos fornecidos
                if 'atribuido' in kwargs:
                    processo.atribuido = kwargs['atribuido']
                if 'classificado' in kwargs:
                    processo.classificado = kwargs['classificado']
                if 'ja_atribuido' in kwargs:
                    processo.ja_atribuido = kwargs['ja_atribuido']
                if 'ja_classificado' in kwargs:
                    processo.ja_classificado = kwargs['ja_classificado']
                
                session.merge(processo)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Cria a tabela se ela não existir
def criar_tabela():
    """
    Cria a tabela no banco de dados se ela não existir.
    """
    try:
        # Verifica se o schema existe
        schema = get_schema()
        if schema:
            # Tenta criar o schema se não existir
            with engine.connect() as conn:
                # Verifica se a tabela já existe
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = '{schema}'
                        AND table_name = '{TblProcessos.__tablename__}'
                    )
                """))
                tabela_existe = result.scalar()
                
                if not tabela_existe:
                    # Cria o schema se não existir
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                    conn.commit()
                    
                    # Cria a tabela
                    Base.metadata.create_all(engine)
    except Exception as e:
        print(f"Erro ao verificar/criar tabela: {str(e)}")

# Executa a criação da tabela ao importar o módulo
criar_tabela() 