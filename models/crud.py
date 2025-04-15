from .db import SessionLocal
from sqlalchemy import or_
from sqlalchemy.sql.sqltypes import String, Text
from sqlalchemy.orm import sessionmaker
from .utils.validator import validate_or_fail


class QueryChain:
    """
    Permite encadear operações na query antes de executá-la.
    
    Métodos de encadeamento:
      - join(target, onclause=None): Realiza join (inner join).
      - innerJoin(target, onclause=None): Igual ao join.
      - leftJoin(target, onclause=None): Realiza left outer join.
      - rightJoin(target, onclause=None): Não implementado.
      - groupBy(*criteria): Aplica agrupamento.
      - orderBy(*criteria): Ordena os resultados.
          Se os critérios forem strings, devem ser passados em pares
          (nome_da_coluna, 'asc' ou 'desc'). Exemplo: .orderBy('id', 'desc')
      - isTrue(column): Adiciona filtro para que a(s) coluna(s) seja(m) True.
      - isFalse(column): Adiciona filtro para que a(s) coluna(s) seja(m) False.
      - empty(column): Filtra registros onde o valor da coluna é vazio ("") ou nulo (None).
      - notEmpty(column): Filtra registros onde o valor da coluna não é vazio nem nulo.
      - limit(limit_value): Define o limite de registros.
      - offset(offset_value): Define o deslocamento da consulta.
    
    Métodos de execução:
      - toList(): Executa a consulta e retorna a lista de resultados.
      - toDict(): Executa a consulta e retorna os resultados como lista de dicionários.
      - first(): Executa a consulta e retorna o primeiro resultado.
      - firstToDict(): Executa a consulta e retorna o primeiro resultado como dicionário.
    """
    def __init__(self, query, session, model):
        self.query = query
        self.session = session
        self.model = model
        # Se .select() não for chamado, fica None. Se for chamado, vira uma lista de colunas.
        self._selected_columns = None
        
    
    
    def select(self, *columns):
        """
        Pode ser usado com joins para selecionar colunas de múltiplas tabelas.
        Exemplo:
        .select(Modelo.id, Modelo.nome, OutraTabela.coluna)
        .select('id', 'nome')
        """
        selected_columns = []
        column_names = []

        for col in columns:
            if isinstance(col, str):
                # Coluna referindo-se ao modelo principal
                if hasattr(self.model, col):
                    selected_columns.append(getattr(self.model, col))
                    column_names.append(col)
                else:
                    raise AttributeError(f"A coluna '{col}' não existe no modelo {self.model.__name__}")
            else:
                # Se for passado um atributo de outro modelo (usado em joins)
                selected_columns.append(col)
                # Tenta usar col.key como "nome" no dicionário final, ou fallback em str(col)
                if hasattr(col, 'key') and col.key:
                    column_names.append(col.key)
                else:
                    column_names.append(str(col))

        if not selected_columns:
            raise ValueError("O método select() requer pelo menos uma coluna válida.")

        self.query = self.query.with_entities(*selected_columns)
        self._selected_columns = column_names  # para uso no toDict
        return self

    
    
    def where(self, *args):
        """
        Adiciona uma condição WHERE à query.
        
        Se passados 2 argumentos, interpreta como (campo, valor) com operador '='.
        Se passados 3 argumentos, interpreta como (campo, operador, valor).
        
        Exemplo:
        .where('bot_controle_id', bot_controle['id'])
        .where('nome_bot', 'like', '%valor%')
        """
        if len(args) == 2:
            condition = args  # ('campo', valor)
        elif len(args) == 3:
            condition = args  # ('campo', operador, valor)
        else:
            raise ValueError("O método where espera 2 ou 3 argumentos.")
        filters = self.model.build_filters([condition])
        self.query = self.query.filter(*filters)
        return self

    def whereIn(self, column, values):
        """
        Filtra registros onde o valor da coluna está contido na lista de valores.
        
        Exemplo:
        .whereIn('id', [1,2,3])
        """
        if not hasattr(self.model, column):
            raise AttributeError(f"{self.model.__name__} não possui a coluna '{column}'")
        self.query = self.query.filter(getattr(self.model, column).in_(values))
        return self

    def whereNotIn(self, column, values):
        """
        Filtra registros onde o valor da coluna NÃO está contido na lista de valores.
        
        Exemplo:
        .whereNotIn('id', [1,2,3])
        """
        if not hasattr(self.model, column):
            raise AttributeError(f"{self.model.__name__} não possui a coluna '{column}'")
        self.query = self.query.filter(~getattr(self.model, column).in_(values))
        return self


    # Métodos de encadeamento
    def join(self, target, onclause=None):
        self.query = self.query.join(target, onclause=onclause)
        return self

    def innerJoin(self, target, onclause=None):
        return self.join(target, onclause=onclause)

    def leftJoin(self, target, onclause=None):
        self.query = self.query.outerjoin(target, onclause=onclause)
        return self

    def rightJoin(self, target, onclause=None):
        raise NotImplementedError("Right join não implementado.")

    def groupBy(self, *criteria):
        self.query = self.query.group_by(*criteria)
        return self
    
    def count(self):
        """
        Executa a consulta e retorna a quantidade de registros encontrados.
        """
        try:
            quantidade = self.query.count()
        finally:
            self.session.close()
        return quantidade
    
    
    # Métodos de ordenação
    def orderBy(self, *criteria):
        """
        Ordena os resultados da query.
        Se os critérios forem strings, devem ser passados em pares (coluna, direção).
        Exemplo:
          .orderBy('id', 'desc')
          .orderBy(Modelo.nome.asc())
        """
        if all(isinstance(crit, str) for crit in criteria):
            new_criteria = []
            i = 0
            while i < len(criteria):
                col_name = criteria[i]
                direction = criteria[i+1] if i+1 < len(criteria) else 'asc'
                column = getattr(self.model, col_name)
                if direction.lower() == 'desc':
                    new_criteria.append(column.desc())
                else:
                    new_criteria.append(column.asc())
                i += 2
            self.query = self.query.order_by(*new_criteria)
        else:
            self.query = self.query.order_by(*criteria)
        return self

    def isTrue(self, column):
        """
        Adiciona filtro para que a(s) coluna(s) seja(m) True.
        
        Parâmetro:
          column (str ou lista): Nome da coluna ou lista de nomes.
        Exemplo:
          .isTrue('ativo')
          .isTrue(['ativo', 'confirmado'])
        """
        if isinstance(column, list):
            for col in column:
                self.query = self.query.filter(getattr(self.model, col) == True)
        else:
            self.query = self.query.filter(getattr(self.model, column) == True)
        return self

    def isFalse(self, column):
        """
        Adiciona filtro para que a(s) coluna(s) seja(m) False.
        
        Parâmetro:
          column (str ou lista): Nome da coluna ou lista de nomes.
        Exemplo:
          .isFalse('ativo')
          .isFalse(['ativo', 'confirmado'])
        """
        if isinstance(column, list):
            for col in column:
                self.query = self.query.filter(getattr(self.model, col) == False)
        else:
            self.query = self.query.filter(getattr(self.model, column) == False)
        return self

    def empty(self, column):
        """
        Filtra registros onde o valor da coluna é vazio ("") ou nulo (None).
        
        Parâmetro:
          column (str ou lista): Nome da coluna ou lista de nomes.
        Exemplo:
          .empty('encerrado_em')
        """
        if isinstance(column, list):
            for col in column:
                self.query = self.query.filter(
                    or_(getattr(self.model, col) == "", getattr(self.model, col) == None)
                )
        else:
            self.query = self.query.filter(
                or_(getattr(self.model, column) == "", getattr(self.model, column) == None)
            )
        return self

    def notEmpty(self, column):
        """
        Filtra registros onde o valor da coluna não é vazio nem nulo.
        
        Parâmetro:
          column (str ou lista): Nome da coluna ou lista de nomes.
        Exemplo:
          .notEmpty('nome')
        """
        if isinstance(column, list):
            for col in column:
                self.query = self.query.filter(getattr(self.model, col) != "").filter(getattr(self.model, col) != None)
        else:
            self.query = self.query.filter(getattr(self.model, column) != "").filter(getattr(self.model, column) != None)
        return self


    def emptyOrNull(self, column):
        """
        Filtra registros onde o valor da coluna é vazio ("" - para colunas de texto)
        ou nulo (NULL). Se a coluna não for de texto, aplica apenas o teste de NULL.
        
        Parâmetro:
        column (str ou lista): Nome da coluna ou lista de nomes.
        
        Exemplo:
        .emptyOrNull('encerrado_em')
        """
        def build_condition(col_obj):
            # Se a coluna for do tipo String ou Text, verifica se é "" ou NULL.
            if isinstance(col_obj.type, (String, Text)):
                return or_(col_obj == "", col_obj == None)
            else:
                # Para outros tipos, somente NULL faz sentido.
                return col_obj == None

        if isinstance(column, list):
            for col in column:
                col_obj = getattr(self.model, col)
                self.query = self.query.filter(build_condition(col_obj))
        else:
            col_obj = getattr(self.model, column)
            self.query = self.query.filter(build_condition(col_obj))
        return self


    def limit(self, limit_value):
        self.query = self.query.limit(limit_value)
        return self

    def offset(self, offset_value):
        self.query = self.query.offset(offset_value)
        return self

    # Métodos de execução
    def toList(self):
        """
        Executa a consulta e retorna a lista de resultados.
        """
        try:
            results = self.query.all()
        finally:
            self.session.close()
        return results

    def toDict(self):
        """
        Executa a consulta e retorna:
          - Se NENHUMA coluna foi passada a select(), retorna [obj.to_dict(), ...].
          - Se houve select('colA', 'colB'...), retorna uma lista de dicionários
            montados com base nessas colunas selecionadas.
        """
        rows = self.toList()

        # Caso não tenha sido chamado select(), assumimos que cada row é instância do model
        if not self._selected_columns:
            return [item.to_dict() for item in rows]

        # Se houve select(...), então cada 'item' de rows é basicamente uma tupla
        # se várias colunas, ou um valor "simples" se 1 coluna.
        resultado = []
        num_cols = len(self._selected_columns)

        for item in rows:
            # Se a query retorna só 1 coluna, 'item' não é tupla, é um valor
            if num_cols == 1:
                col_name = self._selected_columns[0]
                d = {col_name: item}
            else:
                # Várias colunas => 'item' é uma tupla
                d = {}
                for i, col_name in enumerate(self._selected_columns):
                    d[col_name] = item[i]
            resultado.append(d)

        return resultado

    def first(self):
        """
        Executa a consulta e retorna o primeiro resultado.
        """
        try:
            result = self.query.first()
        finally:
            self.session.close()
        return result

    def firstToDict(self):
        """
        Executa a consulta e retorna o primeiro resultado como dicionário.
        """
        result = self.first()
        return result.to_dict() if result else None


class CRUDMixin:
    """
    Mixin que provê operações CRUD e métodos básicos de filtragem para os models.
    
    Métodos de execução:
      - all(where, or_where): Retorna um QueryChain para encadeamento.
      - get(where, or_where): Retorna o primeiro registro que satisfaça os filtros como dicionário.
      - rawSql(sql_string, params): Executa uma query SQL bruta.
      - insert(**kwargs): Insere um registro.
      - create(records): Insere registros em massa.
      - update(**kwargs): Atualiza o registro.
      - updateWhere(**kwargs): Atualiza registros que satisfaçam os filtros.
      - delete(): Remove o registro.
    """
    @classmethod
    def _filter_fillable(cls, data: dict):
        if hasattr(cls, "fillable"):
            return {k: v for k, v in data.items() if k in cls.fillable}
        elif hasattr(cls, "guarded"):
            return {k: v for k, v in data.items() if k not in cls.guarded}
        return data

    @classmethod
    def _apply_aliases(cls, data: dict):
        """
        Converte apelidos amigáveis (como 'nome') para os nomes reais ('name') com base em cls.aliases.
        """
        if hasattr(cls, "aliases"):
            return {cls.aliases.get(k, k): v for k, v in data.items()}
        return data

    
    @classmethod
    def build_filters(cls, conditions):
        """
        Constrói uma lista de filtros a partir de condições.
        Cada condição pode ser:
          - (campo, valor)        => operador '='
          - (campo, operador, valor)
        
        Exemplo:
          build_filters([('nome', 'like', '%Silva%'), ('idade', '>=', 18)])
        """
        filters = []
        for cond in conditions:
            if not isinstance(cond, tuple):
                raise ValueError("Cada condição deve ser uma tupla")
            if len(cond) == 2:
                field, value = cond
                op = '='
            elif len(cond) == 3:
                field, op, value = cond
            else:
                raise ValueError("A condição deve ter 2 ou 3 elementos")
            if not hasattr(cls, field):
                raise AttributeError(f"{cls.__name__} não possui a coluna '{field}'")
            column = getattr(cls, field)
            if op == '=':
                filters.append(column == value)
            elif op == '!=':
                filters.append(column != value)
            elif op == '>':
                filters.append(column > value)
            elif op == '>=':
                filters.append(column >= value)
            elif op == '<':
                filters.append(column < value)
            elif op == '<=':
                filters.append(column <= value)
            elif op.lower() == 'like':
                filters.append(column.like(value))
            else:
                raise ValueError(f"Operador não suportado: {op}")
        return filters

    @classmethod
    def query(cls, where=None, or_where=None):
        """
        Prepara a query com os filtros aplicados e retorna (query, session).
        """
        session = SessionLocal()
        query = session.query(cls)
        if where:
            if isinstance(where, tuple):
                where = [where]
            filters = cls.build_filters(where)
            query = query.filter(*filters)
        if or_where:
            if isinstance(or_where, tuple):
                or_where = [or_where]
            or_filters = cls.build_filters(or_where)
            query = query.filter(or_(*or_filters))
        return query, session

    def to_dict(self):
        """
        Converte a instância do model em um dicionário.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def all(cls, where=None, or_where=None):
        """
        Retorna todos os registros que satisfaçam os filtros.
        Exemplo:
          registros = Modelo.all(where=("ativo", True))
        """
        query, session = cls.query(where, or_where)
        try:
            result = query.all()
        finally:
            session.close()
        return result

    @classmethod
    def get(cls, where=None, or_where=None):
        """
        Retorna o primeiro registro que satisfaça os filtros, como dicionário.
        Exemplo:
          registro = Modelo.get(where=("email", "=", "alice@example.com"))
        """
        query, session = cls.query(where, or_where)
        try:
            result = query.first()
        finally:
            session.close()
        return result.to_dict() if result else None

    @classmethod
    def rawSql(cls, sql_string, params=None, db_key=None):
        """
        Executa uma query SQL bruta e retorna os resultados.
        
        Parâmetros:
        - sql_string: a consulta SQL (deve ser envolvida com text() se for uma string literal).
        - params: (opcional) dicionário de parâmetros para a consulta.
        - db_key: (opcional) chave do banco de dados a ser utilizado (ex.: 'autokit').
                    Se não for informado, usa o engine padrão.
                    
        Exemplo:
        resultados = Modelo.rawSql(sql, params, db_key='autokit')
        """
        if db_key:
            # Importa a função get_engine do seu db.py para obter o engine desejado
            from models.db import get_engine
            engine = get_engine(db_key)
            Session = sessionmaker(bind=engine)
            session = Session()
        else:
            from models.db import SessionLocal
            session = SessionLocal()
        try:
            result = session.execute(sql_string, params)
            data = result.fetchall()
        finally:
            session.close()
        return data

    @classmethod
    def insert(cls, data=None, **kwargs):
        """
        Insere um ou mais registros no banco de dados, obedecendo regras de validação e permissões.
        
        Pode ser usado de três formas:
        1. Com argumentos nomeados: insert(campo=valor, campo2=valor2, ...)
        2. Com um dicionário: insert({ 'campo': valor, 'campo2': valor2, ... })
        3. Com uma lista de dicionários: insert([{'campo': valor}, {'campo': valor2}, ...])
        
        Retorna a instância inserida (no caso de inserção única) ou o resultado de create() para inserção em massa.
        """
        # Se não for passado o parâmetro 'data', usa os kwargs
        if data is None:
            data = kwargs
        # Se for passado 'data' e também kwargs, mescla os dois (priorizando kwargs)
        elif kwargs:
            if isinstance(data, dict):
                data.update(kwargs)
            else:
                raise ValueError("Quando 'data' é uma lista, não se deve passar argumentos nomeados.")

        # Se 'data' for uma lista, delega à função create()
        if isinstance(data, list):
            return cls.create(data)

        # Se 'data' for um dicionário, prossegue com a inserção única
        if isinstance(data, dict):
            session = SessionLocal()
            clean_data = cls._apply_aliases(data)
            clean_data = cls._filter_fillable(clean_data)

            # Validação automática, se houver regras (rules) definidas no model
            if hasattr(cls, "rules"):
                from utils.validator import validate_or_fail
                validate_or_fail(clean_data, cls.rules())

            try:
                instance = cls(**clean_data)
                session.add(instance)
                session.commit()
                session.refresh(instance)
            except Exception as e:
                session.rollback()
                print(f"[ERRO BD] Falha ao inserir {cls.__name__}: {str(e).splitlines()[0]}")
                raise e
            finally:
                session.close()
            return instance
        else:
            raise ValueError("Formato de dados inválido para insert().")


    @classmethod
    def create(cls, records):
        """
        Insere registros em massa com validação automática.
        Exemplo:
        resultado = Modelo.create([{"nome": "Alice"}, {"nome": "Bob"}])
        """
        session = SessionLocal()
        try:
            instances = []
            for index, data in enumerate(records):
                # Aplica aliases e limpa com fillable
                clean_data = cls._filter_fillable(cls._apply_aliases(data))

                # Validação com feedback claro
                if hasattr(cls, "rules"):
                    from utils.validator import validate_or_fail, ValidationError
                    try:
                        validate_or_fail(clean_data, cls.rules())
                    except ValidationError as ve:
                        print(f"[VALIDAÇÃO] Erro no registro {index + 1}: {ve.errors}")
                        raise ve

                instances.append(cls(**clean_data))

            session.add_all(instances)
            session.commit()
            for instance in instances:
                session.refresh(instance)

        except Exception as e:
            session.rollback()
            print(f"[ERRO BD] Falha ao criar múltiplos {cls.__name__}: {str(e).splitlines()[0]}")
            raise e
        finally:
            session.close()

        return [instance.to_dict() for instance in instances]

    

    def update(self, data=None, **kwargs):
        """
        Atualiza o registro atual com os valores fornecidos.
        
        Pode receber:
        - Um dicionário: update(data={"campo": valor, ...})
        - Uma lista de tuplas: update(data=[("campo", valor), ...])
        - Argumentos nomeados: update(campo=valor, ...)
        - Ou qualquer combinação dos anteriores.

        Exemplo:
        registro.update(data={"nome": "Novo Nome"}, email="novo@email")
        """
        update_data = {}

        if data is not None:
            if isinstance(data, dict):
                update_data.update(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, (tuple, list)) and len(item) == 2:
                        update_data[item[0]] = item[1]
                    else:
                        raise ValueError("Cada item da lista deve ser uma tupla ou lista com 2 elementos")
            else:
                raise ValueError("O parâmetro 'data' deve ser um dicionário ou uma lista de tuplas")

        update_data.update(kwargs)

        update_data = self.__class__._apply_aliases(update_data)
        update_data = self.__class__._filter_fillable(update_data)

        #  Validação automática baseada nas regras do modelo
        if hasattr(self.__class__, "rules"):
            from utils.validator import validate_or_fail, ValidationError
            try:
                validate_or_fail(update_data, self.__class__.rules())
            except ValidationError as ve:
                print(f"[VALIDAÇÃO] Falha na atualização: {ve.errors}")
                raise ve

        session = SessionLocal()
        try:
            for key, value in update_data.items():
                setattr(self, key, value)
            instance = session.merge(self)
            session.commit()
            session.refresh(instance)
        except Exception as e:
            session.rollback()
            print(f"[ERRO BD] Falha ao atualizar {self.__class__.__name__}: {str(e).splitlines()[0]}")
            raise e
        finally:
            session.close()

        return instance


    @classmethod
    def updateWhere(cls, data, where):
        """
        Atualiza registros do modelo no banco de dados que atendam à condição especificada.

        Este método realiza a atualização de um ou mais registros com base nos dados fornecidos,
        aplicando automaticamente os aliases, filtrando apenas os campos permitidos (fillable)
        e validando os dados de acordo com as regras definidas (se houver). A condição para a atualização
        é definida pelo parâmetro 'where', que deve ser uma tupla no formato (nome_da_coluna, valor).

        Parâmetros:
            data (dict): Dicionário contendo os campos e os respectivos valores que devem ser atualizados.
                        Os dados serão processados pelas funções _apply_aliases e _filter_fillable do modelo.
            where (tuple): Tupla com dois elementos, onde:
                        - O primeiro elemento é o nome da coluna (string) usada para filtrar o registro.
                        - O segundo elemento é o valor que essa coluna deve ter para que o registro seja atualizado.
                        Exemplo: ('id', 110)

        Retorno:
            - Se apenas um registro for atualizado (i.e., updated_rows == 1), retorna a instância atualizada.
            - Caso a atualização afete múltiplos registros, retorna uma lista com todas as instâncias atualizadas.

        Exceções:
            - ValidationError: Se os dados em 'data' não cumprirem as regras definidas no método rules() do modelo.
            - Exception: Qualquer exceção que ocorra durante o processo de atualização resulta em rollback da transação,
                        e a exceção é propagada após a mensagem de erro ser impressa.

        Observações:
            - O método utiliza uma sessão do SQLAlchemy (SessionLocal) para executar a atualização.
            - Após atualizar os registros, o método executa um commit e, em seguida, reconsulta o registro (ou registros)
            atualizado(s) para retorná-los.
            - Em caso de erro durante a operação, a sessão é revertida (rollback) e a exceção é lançada.
        """
        session = SessionLocal()
        update_data = cls._apply_aliases(data)
        update_data = cls._filter_fillable(update_data)

        # Validação automática baseada nas regras do modelo, se definidas
        if hasattr(cls, "rules"):
            from utils.validator import validate_or_fail, ValidationError
            try:
                validate_or_fail(update_data, cls.rules())
            except ValidationError as ve:
                print(f"[VALIDAÇÃO] Erro na atualização: {ve.errors}")
                raise ve

        try:
            # Supondo que 'where' seja uma tupla, ex: ('id', 110)
            filter_column = getattr(cls, where[0])
            if isinstance(where[1], (list, tuple)):
                query = session.query(cls).filter(filter_column.in_(where[1]))
            else:
                query = session.query(cls).filter(filter_column == where[1])
            # query = session.query(cls).filter(filter_column == where[1])
            updated_rows = query.update(update_data, synchronize_session=False)
            session.commit()

            # Se for esperado que apenas um registro seja atualizado,
            # reconsulta para retornar o registro atualizado.
            if updated_rows == 1:
                updated_instance = session.query(cls).filter(filter_column == where[1]).first()
                return updated_instance  # ou, se preferir, updated_instance.to_dict() ou updated_instance.id
            else:
                # Se atualizou mais de um registro, pode-se retornar uma lista ou o número de linhas atualizadas
                return query.all()
        except Exception as e:
            session.rollback()
            print(f"[ERRO BD] Falha ao atualizar {cls.__class__.__name__}: {str(e).splitlines()[0]}")
            raise e
        finally:
            session.close()




    def delete(self):
        """
        Remove o registro atual do banco de dados.
        Exemplo:
          registro.delete()
        """
        session = SessionLocal()
        try:
            session.delete(self)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    
    @classmethod
    def findById(cls, id_value):
        """
        Busca um registro pelo seu ID e o retorna como dicionário.
        Retorna None se nenhum registro for encontrado.
        
        Exemplo:
          registro = Modelo.findById(1)
        """
        session = SessionLocal()
        try:
            # Utiliza session.get() para buscar pela chave primária.
            instance = session.get(cls, id_value)
        finally:
            session.close()
        return instance #.to_dict() if instance else None

    @classmethod
    def query_chain(cls, where=None, or_where=None):
        """
        Retorna um QueryChain para encadeamento de operações.
        Exemplo:
          resultado = Modelo.query_chain().orderBy('id', 'desc').isTrue('ativo').empty('encerrado_em').limit(10).toDict()
        """
        query, session = cls.query(where, or_where)
        return QueryChain(query, session, cls)
