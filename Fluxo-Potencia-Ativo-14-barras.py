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
    query = "SELECT Barra_Origem AS Origem, Barra_Destino AS Destino, g AS gkm, b AS bkm, bsh, tap FROM dadoslinha"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn)
    return dados

# ===============================
# INÍCIO DO CÁLCULO
# ===============================
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()

# -------------------------------
# Construir a Função Objetiva
# -------------------------------
print("\nFUNÇÃO OBJETIVA:\n")
print("\nFórmula: gkm * (1 / t²km) * Vk² + Vm² - 2 * (1 / tkm) * Vk * Vm * cos(θkm)")

equacao_objetiva = []
for _, row in dadoslinha.iterrows():
    origem = row["Origem"]
    destino = row["Destino"]
    gkm = row["gkm"]

    termo = (
        f"{gkm:.6f} * (1 / (t{origem}{destino}**2)) * (V{origem}**2 + V{destino}**2) "
        f"- 2 * (1 / t{origem}{destino}) * V{origem} * V{destino} * cos(θ{origem}{destino})"
    )
    equacao_objetiva.append(termo)

funcao_objetiva = " +\n".join(equacao_objetiva)
print(funcao_objetiva)
print()

# -------------------------------
# Função para formatar o TAP
# -------------------------------
def formatar_tap(tap):
    if tap > 1:
        tap_inv_str = f"(1 / {tap:.4f})"
        tap_inv_quad_str = f"(1 / ({tap:.4f}**2))"
    else:
        tap_inv_str = ""
        tap_inv_quad_str = ""
    return tap_inv_str, tap_inv_quad_str

# -------------------------------
# Função para puxar parametros do banco de dados
# -------------------------------
def extrair_parametros_linha(row):
    return row['Origem'], row['Destino'], row['gkm'], row['bkm'], row['tap'], row['bsh']

# -------------------------------
# Função para calcular PKM
# -------------------------------
def calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial"):
    tap_inv_str, tap_inv_quad_str = formatar_tap(tap)
    if tipo == "inicial":
        return (
            f"({tap_inv_quad_str}{gkm:.6f}) * (V{origem}**2) - "
            f"{tap_inv_str}V{origem} * V{destino} * "
            f"({gkm:.6f} * cos(θ{origem} - θ{destino}) + ({bkm:.6f}) * sin(θ{origem} - θ{destino}))"
        )
    elif tipo == "final":
        return (
            f"{gkm:.6f} * (V{destino}**2) - "
            f"{tap_inv_str}V{destino} * V{origem} * "
            f"({gkm:.6f} * cos(θ{destino} - θ{origem}) + ({bkm:.6f}) * sin(θ{destino} - θ{origem}))"
        ).replace("*  *", "*").replace("  ", " ").replace("(1 / )", "")

# -------------------------------
# Expressão da Potência Ativa
# -------------------------------
print("EXPRESSÕES DA POTÊNCIA ATIVA (Pkm):\n")
print("INICIAL: Pkm = (gkm * (1 / t²km)) * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))")
print("FINAL:   Pkm = gkm * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))\n")

for _, row in dadoslinha.iterrows():
    origem, destino, gkm, bkm, tap, bsh = extrair_parametros_linha(row)
    pkm_inicial = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial")
    pkm_final = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="final")

    #print(f"Linha {origem} → {destino}:")
    #print(f"  Nó Inicial: {pkm_inicial}")
    #print(f"  Nó Final:   {pkm_final}")
    #print()

# -------------------------------
# Restrição 1: Balanço de Potência Ativa
# -------------------------------
print("-----------------------------------------------")
print("RESTRIÇÃO 1: Pkm − PGk + PC = 0, ∀k ∈ G′ ∪ C\n")

barra_slack = int(dadosbarra[dadosbarra["tipo"] == 2].index[0])
barras_geracao = set(dadosbarra[dadosbarra["tipo"] == 1].index)
barras_carga = set(dadosbarra[dadosbarra["tipo"] == 0].index)
barras_restricao1 = (barras_geracao | barras_carga) - {barra_slack}

restricoes = []
for k in sorted(barras_restricao1):
    termos_fluxo = []
    Pg = dadosbarra.loc[k, "Pg"]
    Pc = dadosbarra.loc[k, "Pc"]

    for _, row in dadoslinha.iterrows():
        origem, destino, gkm, bkm, tap, bsh = extrair_parametros_linha(row)
        if origem == barra_slack or destino == barra_slack:
            continue
        if k == origem:
            termo = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial")
            termos_fluxo.append(f"({termo})")
        elif k == destino:
            termo = calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="final")
            termos_fluxo.append(f"({termo})")

    restricao_k = " +\n ".join(termos_fluxo) + f" - ({Pg}) + ({Pc}) = 0"
    restricoes.append((k, restricao_k))

for k, expressao in restricoes:
    print(f"Restrição para barra {k}:")
    print(expressao)
    print()

# -------------------------------
# Função para calcular QKM
# -------------------------------
def calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="inicial"):
    tap_inv_str, tap_inv_quad_str = formatar_tap(tap)
    if tipo == "inicial":
        return (
            f"-({tap_inv_quad_str}{bkm:.6f}) * (V{origem}**2) - "
            f"{tap_inv_str}V{origem} * V{destino} * "
            f"({gkm:.6f} * sin(θ{origem} - θ{destino}) - ({bkm:.6f}) * cos(θ{origem} - θ{destino})) + "
            f"{bsh / 2:.6f} * (V{origem}**2)"
        )
    elif tipo == "final":
        return (
            f"-{bkm:.6f} * (V{destino}**2) - "
            f"{tap_inv_str}V{destino} * V{origem} * "
            f"({gkm:.6f} * sin(θ{destino} - θ{origem}) - ({bkm:.6f}) * cos(θ{destino} - θ{origem})) + "
            f"{bsh / 2:.6f} * (V{destino}**2)"
        ).replace("*  *", "*").replace("  ", " ").replace("(1 / )", "")

# ----------------------------------------
# Restrição 2: Balanço de Potência Reativa
# ----------------------------------------
print("-----------------------------------------------")
print("RESTRIÇÃO 2: Qkm − QGk + QCk − Qshk = 0, ∀k ∈ C\n")

restricoes_q = []
for k in sorted(barras_carga):
    termos_fluxo_q = []
    Qg = dadosbarra.loc[k, "Qg"]
    Qc = dadosbarra.loc[k, "Qc"]
    Qsh = dadosbarra.loc[k, "bsh"]

    for _, row in dadoslinha.iterrows():
        origem, destino, gkm, bkm, tap, bsh = extrair_parametros_linha(row)
        if origem == barra_slack or destino == barra_slack:
            continue
        if k == origem:
            termo = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="inicial")
            termos_fluxo_q.append(f"({termo})")
        elif k == destino:
            termo = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="final")
            termos_fluxo_q.append(f"({termo})")

    restricao_qk = " +\n ".join(termos_fluxo_q) + f" - ({Qg}) + ({Qc}) - ({Qsh}) = 0"
    restricoes_q.append((k, restricao_qk))

for k, expressao in restricoes_q:
    print(f"Restrição de Reativa para barra {k}:")
    print(expressao)
    print()
