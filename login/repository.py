from balanco.entidades.categoria import Categoria
from balanco.services import categoria_service

categorias = [
    ["entrada", "Salário", "#009603", "fa-solid fa-briefcase"],
    ["entrada", "Renda Extra", "#009600", "fa-solid fa-money-bill"],
    ["entrada", "Aporte", "#009600", "fa-solid fa-coins"],
    ["saida", "Alimentação", "#960000", "fa-solid fa-utensils"],
    ["saida", "Casa", "#960000", "fa-solid fa-house-chimney-window"],
    ["saida", "Transporte", "#960000", "fa-solid fa-car"],
    ["saida", "Pessoal", "#960000", "fa-solid fa-person"],
    ["saida", "Educação", "#960000", "fa-solid fa-building-columns"],
    ["saida", "Música", "#960000", "fa-solid fa-music"],
    ["saida", "Social", "#960000", "fa-solid fa-user-group"],
    ["saida", "Lazer", "#960000", "fa-solid fa-film"],
    ["saida", "Tecnologia", "#960000", "fa-solid fa-microchip"],
    ["saida", "Vestuário", "#960000", "fa-solid fa-shirt"],
    ["saida", "Inútil", "#960000", "fa-solid fa-trash-arrow-up"],
    ["saida", "Investimentos", "#960000", "fa-solid fa-chart-line"]
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
