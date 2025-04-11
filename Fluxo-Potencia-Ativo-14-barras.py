import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# Criar conexão com o banco
def conectar_banco():
    engine = create_engine("mysql+mysqlconnector://root:@localhost/sistema_14barras")
    return engine

# Buscar os dados das barras
def buscar_dadosbarra():
    engine = conectar_banco()
    query = "SELECT Barra, tipo, Pg, Qg, Qmin, Qmax, Pc, Qc, bsh FROM dadosbarra"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn).set_index("Barra")
    return dados

# Buscar os dados das linhas
def buscar_dados_linhas():
    engine = conectar_banco()
    query = "SELECT Barra_Origem, Barra_Destino, g, b, bsh, tap FROM dadoslinha"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn)
    return dados

# ===============================
# INÍCIO DO CÁLCULO
# ===============================

# Dados
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()

# -------------------------------
# Construir a Função Objetiva
# -------------------------------
print("\nFUNÇÃO OBJETIVA:\n")
print("\nFórmula: gkm * (1 / t²km) * Vk² + Vm² - 2 * (1 / tkm) * Vk * Vm * cos(θkm)")

equacao_objetiva = []

for _, row in dadoslinha.iterrows():
    origem = row["Barra_Origem"]
    destino = row["Barra_Destino"]
    origem_int = int(origem)
    destino_int = int(destino)
    gkm = row["g"]

    termo = (
       f"{gkm:.6f} * (1 / (t{origem_int} {destino_int}**2)) * (V{origem}**2 + V{destino}**2) "
       f"- 2 * (1 / t{origem_int} {destino_int}) * V{origem} * V{destino} * cos(θ{origem}{destino})"
    )
    equacao_objetiva.append(termo)

funcao_objetiva = " +\n".join(equacao_objetiva)
print(funcao_objetiva)
print()

# -------------------------------
# Função para calcular PKM
# -------------------------------

def calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial"):
    origem_int = int(origem)
    destino_int = int(destino)

    if tap > 1:
        tap_inv_str = f"(1 / {tap:.4f})"
        tap_inv_quad_str = f"(1 / ({tap:.4f}**2))"
    else:
        tap_inv_str = ""
        tap_inv_quad_str = ""

    if tipo == "inicial":
        return (
            f"({tap_inv_quad_str}{gkm:.6f}) * (V{origem_int}**2) - "
            f"{tap_inv_str}V{origem_int} * V{destino_int} * "
            f"({gkm:.6f} * cos(θ{origem_int} - θ{destino_int}) + ({bkm:.6f}) * sin(θ{origem_int} - θ{destino_int}))"
        )

    elif tipo == "final":
        return (
            f"{gkm:.6f} * (V{destino_int}**2) - "
            f"{tap_inv_str}V{destino_int} * V{origem_int} * "
            f"({gkm:.6f} * cos(θ{destino_int} - θ{origem_int}) + ({bkm:.6f}) * sin(θ{destino_int} - θ{origem_int}))"
        ).replace("*  *", "*").replace("  ", " ").replace("(1 / )", "")


# -------------------------------
# Expressão da Potência Ativa
# -------------------------------
print("EXPRESSÕES DA POTÊNCIA ATIVA (Pkm):\n")
print("INICIAL: Pkm = (gkm * (1 / t²km)) * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))")
print("FINAL:   Pkm = gkm * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))\n")

for _, row in dadoslinha.iterrows():
    origem = row["Barra_Origem"]
    destino = row["Barra_Destino"]
    gkm = row["g"]
    bkm = row["b"]
    tap = row["tap"]

    expressao_pkm_inicial = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial")
    expressao_pkm_final = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="final")

    print(f"Linha {origem} → {destino}:")
    print(f"  Nó Inicial: {expressao_pkm_inicial}")
    print(f"  Nó Final:   {expressao_pkm_final}")
    print()


# -------------------------------
# Restrição 1: Balanço de Potência Ativa
# -------------------------------
print("-----------------------------------------------")
print("RESTRIÇÃO 1: Pkm − PGk + PC = 0, ∀k ∈ G′ ∪ C\n")

# Define a barra slack e os conjuntos de barras para geração e carga
barra_slack = int(dadosbarra[dadosbarra["tipo"] == 2].index[0])
barras_geracao = set(dadosbarra[dadosbarra["tipo"] == 1].index)
barras_carga = set(dadosbarra[dadosbarra["tipo"] == 0].index)

# Conjunto das barras que participam da restrição (todas menos a slack)
barras_restricao1 = (barras_geracao | barras_carga) - {barra_slack}
restricoes = []

# Percorre todas as barras relevantes, convertendo para inteiro para garantir igualdade
for k in sorted(barras_restricao1):
    k_int = int(k)
    termos_fluxo = []

    # Pegando valores reais de Pg e Pc
    Pg = dadosbarra.loc[k_int, "Pg"]
    Pc = dadosbarra.loc[k_int, "Pc"]

    # Percorre cada linha (conexão) e verifica se a barra k está conectada
    for _, row in dadoslinha.iterrows():
        # Converte barras de origem e destino para inteiros
        origem = int(row["Barra_Origem"])
        destino = int(row["Barra_Destino"])
        gkm = row["g"]
        bkm = row["b"]
        tap = row["tap"]

        # ⚠️ Pula o ramo se ele se conecta com a barra slack
        if origem == barra_slack or destino == barra_slack:
            continue

        # Se a barra k é a barra de origem, usa a expressão do nó inicial
        if k_int == origem:
            termo = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial")
            termos_fluxo.append(f"({termo})")
        # Se k for a barra de destino, utiliza a expressão do nó final
        elif k_int == destino:
            termo = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="final")
            termos_fluxo.append(f"({termo})")

    # Constrói a equação simbólica da restrição usando PG e PC literais (não os valores numéricos)
    restricao_k = " +\n ".join(termos_fluxo) + f" - ({Pg}) + ({Pc}) = 0"
    restricoes.append((k_int, restricao_k))

# Exibe as restrições, pulando uma linha entre elas
for k, expressao in restricoes:
    print(f"Restrição para barra {k}:")
    print(expressao)
    print()