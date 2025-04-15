import re

class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Erro de validação")

    def __str__(self):
        return f"Erro de validação: {self.errors}"

def validate_or_fail(data: dict, rules: dict):
    """
    Valida os dados com base nas regras fornecidas.

    Regras disponíveis:
      - 'required'      → campo obrigatório
      - 'string'        → deve ser string
      - 'integer'       → deve ser inteiro
      - 'float'         → deve ser decimal
      - 'boolean'       → deve ser booleano
      - 'email'         → deve ser e-mail válido
      - 'datetime'      → string representando data/hora
      - 'min:<n>'       → mínimo de caracteres ou valor
      - 'max:<n>'       → máximo de caracteres ou valor
      - 'regex:<exp>'   → valida com regex
      - 'in:[a,b,c]'    → valor deve estar nessa lista
      - 'not_in:[x,y]'  → valor **não** pode estar nessa lista
    """
    errors = {}

    for field, constraints in rules.items():
        value = data.get(field)

        for rule in constraints:
            if rule == "required":
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.setdefault(field, []).append("Este campo é obrigatório.")

            elif rule == "string" and value is not None:
                if not isinstance(value, str):
                    errors.setdefault(field, []).append("Deve ser uma string.")

            elif rule == "integer" and value is not None:
                if not isinstance(value, int):
                    errors.setdefault(field, []).append("Deve ser um número inteiro.")

            elif rule == "float" and value is not None:
                if not isinstance(value, float):
                    errors.setdefault(field, []).append("Deve ser um número decimal.")

            elif rule == "boolean" and value is not None:
                if not isinstance(value, bool):
                    errors.setdefault(field, []).append("Deve ser verdadeiro ou falso.")

            elif rule == "email" and value is not None:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", str(value)):
                    errors.setdefault(field, []).append("Formato de e-mail inválido.")

            elif rule == "datetime" and value is not None:
                if not isinstance(value, str):
                    errors.setdefault(field, []).append("Data/hora deve ser string (use formato ISO ou similar).")

            elif rule.startswith("min:") and value is not None:
                try:
                    min_val = int(rule.split(":")[1])
                    if isinstance(value, (str, list)) and len(value) < min_val:
                        errors.setdefault(field, []).append(f"Mínimo de {min_val} caracteres.")
                    elif isinstance(value, (int, float)) and value < min_val:
                        errors.setdefault(field, []).append(f"Valor mínimo permitido é {min_val}.")
                except:
                    pass

            elif rule.startswith("max:") and value is not None:
                try:
                    max_val = int(rule.split(":")[1])
                    if isinstance(value, (str, list)) and len(value) > max_val:
                        errors.setdefault(field, []).append(f"Máximo de {max_val} caracteres.")
                    elif isinstance(value, (int, float)) and value > max_val:
                        errors.setdefault(field, []).append(f"Valor máximo permitido é {max_val}.")
                except:
                    pass

            elif rule.startswith("regex:") and value is not None:
                pattern = rule.split(":", 1)[1]
                if not re.match(pattern, str(value)):
                    errors.setdefault(field, []).append("Formato inválido.")

            elif rule.startswith("in:[") and value is not None:
                try:
                    allowed = eval(rule.split(":", 1)[1])
                    if value not in allowed:
                        errors.setdefault(field, []).append(f"Valor deve ser um dos permitidos: {allowed}")
                except:
                    pass

            elif rule.startswith("not_in:[") and value is not None:
                try:
                    blocked = eval(rule.split(":", 1)[1])
                    if value in blocked:
                        errors.setdefault(field, []).append(f"Valor não permitido: {value}")
                except:
                    pass

    if errors:
        raise ValidationError(errors)
