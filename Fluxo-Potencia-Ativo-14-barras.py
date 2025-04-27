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
        f"{gkm:.6f} * (1 / (t{int(origem)}{int(destino)}**2)) * (V{int(origem)}**2 + V{int(destino)}**2) "
        f"- 2 * (1 / t{int(origem)}{int(destino)}) * V{int(origem)} * V{int(destino)} * cos(θ{int(origem)}{int(destino)})"
    )

    equacao_objetiva.append(termo)

funcao_objetiva = " +\n".join(equacao_objetiva)
print(funcao_objetiva)
print()

# Inicializar o dicionário global para os valores de tap maiores que 1
tap_vars = {}
tap_counter = 1  # Para numerar as variáveis tap1, tap2, etc.

# -------------------------------
# Função para registrar taps > 1
# -------------------------------
def registrar_taps(dadoslinha):
    global tap_counter, tap_vars
    for _, row in dadoslinha.iterrows():
        tap = row['tap']
        if tap > 1:
            # Verifica se o valor já foi registrado
            if tap not in tap_vars.values():
                tap_vars[f"tap{tap_counter}"] = tap  # Atribui um nome ao tap
                tap_counter += 1

# Registrar os taps uma única vez
registrar_taps(dadoslinha)

# -------------------------------
# Função para formatar o TAP
# -------------------------------
def obter_nome_tap(tap):
    # Retorna o nome da variável tap, ou vazio se tap <= 1
    for nome, valor in tap_vars.items():
        if tap == valor:
            return nome
    return ""  # Caso o tap não seja maior que 1




# -------------------------------
# Função para puxar parâmetros do banco de dados
# -------------------------------
def extrair_parametros_linha(row):
    return row['Origem'], row['Destino'], row['gkm'], row['bkm'], row['tap'], row['bsh']


# -------------------------------
# Função para calcular PKM
# -------------------------------
def calcular_fluxo_p_ativo(origem, destino, gkm, bkm, tap, tipo="inicial"):
    tap_nome = obter_nome_tap(tap)  # Nome da variável do tap
    if tap_nome:
        tap_inv_quad_str = f"(1 / ({tap_nome}**2))"
        tap_inv_str = f"(1 / {tap_nome})"
    else:
        tap_inv_quad_str = ""
        tap_inv_str = ""

    if tipo == "inicial":
        return (
            f"({tap_inv_quad_str}{gkm:.6f}) * (V{int(origem)}**2) - "
            f"{tap_inv_str}V{int(origem)} * V{int(destino)} * "
            f"({gkm:.6f} * cos(theta{int(origem)} - theta{int(destino)}) + ({bkm:.6f}) * sin(theta{int(origem)} - theta{int(destino)}))"
        )
    elif tipo == "final":
        return (
            f"{gkm:.6f} * (V{int(destino)}**2) - "
            f"{tap_inv_str}V{int(destino)} * V{int(origem)} * "
            f"({gkm:.6f} * cos(theta{int(destino)} - theta{int(origem)}) + ({bkm:.6f}) * sin(theta{int(destino)} - theta{int(origem)}))"
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
            termo = calcular_fluxo_p_ativo(int(origem), int(destino), gkm, bkm, tap, tipo="inicial")
            termos_fluxo.append(f"({termo})")
        elif k == destino:
            termo = calcular_fluxo_p_ativo(int(origem), int(destino), gkm, bkm, tap, tipo="final")
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
    tap_nome = obter_nome_tap(tap)  # Nome da variável do tap
    if tap_nome:
        tap_inv_quad_str = f"(1 / ({tap_nome}**2))"
        tap_inv_str = f"(1 / {tap_nome})"
    else:
        tap_inv_quad_str = ""
        tap_inv_str = ""

    if tipo == "inicial":
        return (
            f"-(({bkm:.6f} * {tap_inv_quad_str}) + {bsh:.6f}) * (V{int(origem)}**2) + "
            f"{tap_inv_str}V{int(origem)} * V{int(destino)} * "
            f"({bkm:.6f} * cos(theta{int(origem)} - theta{int(destino)}) - {gkm:.6f} * sin(theta{int(origem)} - theta{int(destino)}))"
        )
    
    elif tipo == "final":
        return (
            f"-({bkm:.6f} + {bsh:.6f}) * (V{int(destino)}**2) + "
            f"{tap_inv_str}V{int(destino)} * V{int(origem)} * "
            f"({bkm:.6f} * cos(theta{int(destino)} - theta{int(origem)}) - {gkm:.6f} * sin(theta{int(destino)} - theta{int(origem)}))"
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
            termo = calcular_fluxo_q_reativo(int(origem), int(destino), gkm, bkm, bsh, tap, tipo="inicial")
            termos_fluxo_q.append(f"({termo})")
        elif k == destino:
            termo = calcular_fluxo_q_reativo(int(origem), int(destino), gkm, bkm, bsh, tap, tipo="final")
            termos_fluxo_q.append(f"({termo})")

    restricao_qk = " +\n ".join(termos_fluxo_q) + f" ({Qg}) + ({Qc}) - ({Qsh}) = 0"
    restricoes_q.append((k, restricao_qk))

for k, expressao in restricoes_q:
    print(f"Restrição de Reativa para barra {k}:")
    print(expressao)
    print()


# -------------------------------
# Impressão dos Fluxos Reativos Qkm
# -------------------------------
print("-----------------------------------------------")
print("FLUXOS DE POTÊNCIA REATIVA (Qkm):\n")
print("INICIAL: Qkm = -(bkm * (1/tap²) + b^sh_km) * Vk² + (1/tap) * Vk * Vm * (bkm * cos(θk - θm) - gkm * sin(θk - θm))")
print("FINAL:   Qkm = -(bkm + bsh) * Vm² + (1/tap) * Vm * Vk * (bkm * cos(θm - θk) - gkm * sin(θm - θk))")


for _, row in dadoslinha.iterrows():
    origem, destino, gkm, bkm, tap, bsh = extrair_parametros_linha(row)
    qkm_inicial = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="inicial")
    qkm_final = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="final")

    #print(f"Linha {origem} → {destino}:")
    #print(f"  Qkm Inicial: {qkm_inicial}")
    #print(f"  Qkm Final:   {qkm_final}")
    #print()

