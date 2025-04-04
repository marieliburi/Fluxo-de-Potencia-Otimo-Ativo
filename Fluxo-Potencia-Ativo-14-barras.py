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
print("\n Fórmula: gkm * (1 / t²km) * Vk² + Vm² - 2 * (1 / tkm) * Vk * Vm * cos(θkm)")

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
    tap = f"t{origem}{destino}"  # Notação simbólica

    origem_int = int(origem)
    destino_int = int(destino)

    expressao_pkm_inicial = (
        f"({gkm:.6f} * (1 / (t{origem_int} {destino_int}**2))) * (V{origem_int}**2) - "
        f"(1 / t{origem_int} {destino_int}) * V{origem_int} * V{destino_int} * "
        f"({gkm:.6f} * cos(θ{origem_int} {destino_int}) + {bkm:.6f} * sin(θ{origem_int} {destino_int}))"
    )
    expressao_pkm_final = (
        f"{gkm:.6f} * (V{destino_int}**2) - "
        f"(1 / t{origem_int} {destino_int}) * V{destino_int} * V{origem_int} * "
        f"({gkm:.6f} * cos(θ{destino_int} {origem_int}) + {bkm:.6f} * sin(θ{destino_int} {origem_int}))"
    )

    print(f"Linha {origem} → {destino}:")
    print(f"  Nó Inicial: {expressao_pkm_inicial}")
    print(f"  Nó Final:   {expressao_pkm_final}")
    print()

# -------------------------------
# Restrição 1: Balanço de Potência Ativa
# -------------------------------
print("-----------------------------------------------")
print("RESTRIÇÃO 1: Pkm − PGk + PC = 0, ∀k ∈ G′ ∪ C\n")


barra_slack = dadosbarra[dadosbarra["tipo"] == 2].index[0]
barras_geracao = set(dadosbarra[dadosbarra["tipo"] == 1].index)
barras_carga = set(dadosbarra[dadosbarra["tipo"] == 0].index)

barras_restricao1 = (barras_geracao | barras_carga) - {barra_slack}
restricoes = []

for k in barras_restricao1:
    termos_fluxo = []

    for _, row in dadoslinha.iterrows():
        origem = row["Barra_Origem"]
        destino = row["Barra_Destino"]
        gkm = row["g"]
        tap = f"t{origem}{destino}"

        origem_int = int(origem)
        destino_int = int(destino)

        if origem == k:
            termos_fluxo.append(
                f"{gkm:.6f} * (1 / (t{origem_int}{destino_int}**2)) * (V{k}**2) - "
                f"(1 / t {origem_int} {destino_int}) * V{k} * V{destino} * (gkm * cos(θ{k}{destino}))"
        )
        elif destino == k:
            termos_fluxo.append(
                f"{gkm:.6f} * (V{k}**2) - "
                f"(1 / t {origem_int} {destino_int}) * V{k} * V{origem} * (gkm * cos(θ{k}{origem}))"
            )

    restricao_k = " + ".join(termos_fluxo) + f" - P_G{k} + P_C{k} = 0"
    restricoes.append((k, restricao_k))

# Exibir as restrições
for k, expressao in restricoes:
    print(f"Restrição para barra {k}:")
    print(expressao)
    print()
