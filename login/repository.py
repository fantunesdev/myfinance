from balanco.entidades.antecipation import Antecipation
from balanco.entidades.categoria import Categoria
from balanco.services import categoria_service, antecipation_service

categorias = [
    ["saida", "Alimentação", "#960000", "fa-solid fa-utensils"],
    ["entrada", "Aporte", "#009600", "fa-solid fa-coins"],
    ["saida", "Casa", "#960000", "fa-solid fa-house-chimney-window"],
    ["saida", "Educação", "#960000", "fa-solid fa-building-columns"],
    ["saida", "Investimentos", "#960000", "fa-solid fa-chart-line"],
    ["saida", "Lazer", "#960000", "fa-solid fa-film"],
    ["saida", "Música", "#960000", "fa-solid fa-music"],
    ["saida", "Pessoal", "#960000", "fa-solid fa-person"],
    ["entrada", "Renda Extra", "#009600", "fa-solid fa-money-bill"],
    ["entrada", "Salário", "#009603", "fa-solid fa-briefcase"],
    ["saida", "Social", "#960000", "fa-solid fa-user-group"],
    ["saida", "Transporte", "#960000", "fa-solid fa-car"]
]


def cadastrar_categorias(usuario):
    for i in categorias:
        categoria = Categoria(
            tipo=i[0],
            descricao=i[1],
            cor=i[2],
            icone=i[3],
            usuario=usuario
        )
        categoria_service.cadastrar_categoria(categoria)


def create_antecipation(user):
    antecipation = Antecipation(
        day=1,
        antecipate=False,
        user=user
    )
    antecipation_service.create_antecipation(antecipation)
