import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

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

#Função para conectar na tabela dadosv
def buscar_dadosv():
    engine = conectar_banco()
    query = "SELECT Vmin, Vmax FROM dadosv"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn)
    return dados

#Função para conectar na tabela dadosv
def buscar_dadost():
    engine = conectar_banco()
    query = "SELECT Tmin, Tmax FROM dadost"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn)
    return dados

# -----------------
# INÍCIO DO CÁLCULO
# -----------------
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()
dadosv = buscar_dadosv()
dadost = buscar_dadost()


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
# Construir a Função Objetiva
# -------------------------------
print("\nFUNÇÃO OBJETIVA:\n")
print("\nFórmula: gkm * (1 / t²km) * Vk² + Vm² - 2 * (1 / tkm) * Vk * Vm * cos(θkm)")

equacao_objetiva = []
for _, row in dadoslinha.iterrows():
    origem = row["Origem"]
    destino = row["Destino"]
    gkm = row["gkm"]
    tap = row["tap"]

    # Verifica se o tap > 1 e obtém o nome correto
    tap_nome = obter_nome_tap(tap)
    tap_inv_quad_str = f"(1 / ({tap_nome}**2))" if tap_nome else "1"  # Se não houver tap, usa "1" para manter a multiplicação correta
    tap_inv_str = f"(1 / {tap_nome})" if tap_nome else "1"

    termo = (
        f"{gkm:.6f} * {tap_inv_quad_str} * V{int(origem)}**2 + V{int(destino)}**2 "
        f"- 2 * {tap_inv_str} * V{int(origem)} * V{int(destino)} * cos(theta{int(origem)} - theta{int(destino)})"
    )

    equacao_objetiva.append(termo.replace("* 1 ", ""))  # Remove multiplicações desnecessárias

funcao_objetiva = " +\n".join(equacao_objetiva)
print(funcao_objetiva)
print()

# ----------------------------------------------
# Função para puxar parâmetros do banco de dados
# ----------------------------------------------
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
print("--------------------------------------------")
print("RESTRIÇÃO 1: Pkm − PGk + PC = 0, ∀k ∈ G′ ∪ C")
print("--------------------------------------------")

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



#-----------
#Calculo QG
#-----------
def calcular_qgk(k, dadosbarra, dadoslinha):
    
    #Formula: QGk = QCk − Q_k^sh + ∑{m ∈ k} Qkm
    # Qk^sh = b_k^sh * Vk²
    Qc = dadosbarra.loc[k, "Qc"]
    bsh_k = dadosbarra.loc[k, "bsh"]

    #Cálculo de Q_k^sh
    Qsh_k = f"{bsh_k:.6f} * V{int(k)}**2"

    # Cálculo da soma Σ{m ∈ k} Q_km
    termos_fluxo_q = []
    for _, row in dadoslinha.iterrows():
        origem = int(row["Origem"])
        destino = int(row["Destino"])
        gkm = row["gkm"]
        bkm = row["bkm"]
        tap = row["tap"]
        bsh = row["bsh"]

        # Verifica se o tap > 1 e obtém o nome correto
        tap_nome = obter_nome_tap(tap)
        tap_inv_str = f"(1 / {tap_nome})" if tap_nome else ""

        # Cálculo de Q_km(V, tap, θ)
        if k == origem:
            Qkm = f"-({bkm:.6f} * {tap_inv_str} + {bsh:.6f}) * V{origem}**2 + {tap_inv_str}V{origem} * V{destino} * ({bkm:.6f} * cos(theta{origem}_{destino}) - {gkm:.6f} * sin(theta{origem}_{destino}))"
            termos_fluxo_q.append(f"({Qkm})")
        elif k == destino:
            Qkm = f"-({bkm:.6f} + {bsh:.6f}) * V{destino}**2 + {tap_inv_str}V{destino} * V{origem} * ({bkm:.6f} * cos(theta{destino}_{origem}) - {gkm:.6f} * sin(theta{destino}_{origem}))"
            termos_fluxo_q.append(f"({Qkm})")

    # Retorna a equação final de QGk
    return f"QG{int(k)} = {Qc} - {Qsh_k} + {' + '.join(termos_fluxo_q)}"


# ----------------------------------------
# Restrição 2: Balanço de Potência Reativa
# ----------------------------------------
print("-----------------------------------------------")
print("RESTRIÇÃO 2: Qkm − QGk + QCk − Qshk = 0, ∀k ∈ C")
print("-----------------------------------------------")

restricoes_q = []
for k in sorted(barras_carga):  # Itera sobre as barras de carga
    termos_fluxo_q = []
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

    # Substitui QGk pela equação correta de QGk
    QGk = calcular_qgk(k, dadosbarra, dadoslinha)

    restricao_qk = " +\n ".join(termos_fluxo_q) + f" ({QGk}) + ({Qc}) - ({Qsh}) = 0"
    restricoes_q.append((k, restricao_qk))

# Exibe as restrições corrigidas
for k, expressao in restricoes_q:
    print(f"Restrição de Reativa para barra {k}:")
    print(expressao)
    print()


print("-------------------------------------------")
print("RESTRIÇÃO 3: QminGk ≤ QGk ≤ QmaxGk, ∀k ∈ G")
print("-------------------------------------------")

print("QGk = QCk − Q_k^sh + ∑{m ∈ k} Qkm")
print("Qk^sh = b_k^sh * Vk²\n")

restricoes_qg = []
barras_G = set(dadosbarra[dadosbarra["tipo"].isin([1, 2])].index)  # Filtra barras do tipo 1 e 2

for k in sorted(barras_G):  # Itera sobre as barras do tipo 1 e 2
    Qmin = dadosbarra.loc[k, "Qmin"]
    Qmax = dadosbarra.loc[k, "Qmax"]
    Qc = dadosbarra.loc[k, "Qc"]
    bsh_k = dadosbarra.loc[k, "bsh"]

    # Equação (5.13): Cálculo de Q_k^sh
    Qsh_k = f"{bsh_k:.6f} * V{int(k)}**2"

    # Cálculo da soma Σ_{m ∈ k} Q_km utilizando a função já existente
    termos_fluxo_q = []
    for _, row in dadoslinha.iterrows():
        origem = int(row["Origem"])
        destino = int(row["Destino"])
        gkm = row["gkm"]
        bkm = row["bkm"]
        tap = row["tap"]
        bsh = row["bsh"]

        if k == origem:
            Qkm = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="inicial")
            termos_fluxo_q.append(f"({Qkm})")
        elif k == destino:
            Qkm = calcular_fluxo_q_reativo(origem, destino, gkm, bkm, bsh, tap, tipo="final")
            termos_fluxo_q.append(f"({Qkm})")

    # Monta a equação final de QGk
    equacao_qg = f"{Qc} - {Qsh_k} + {' + '.join(termos_fluxo_q)}"

    # Monta a restrição no formato desejado
    restricao_formatada = f"{Qmin} <= {equacao_qg} <= {Qmax}"

    restricoes_qg.append((k, restricao_formatada))

# Exibe as restrições formatadas corretamente
for k, expressao in restricoes_qg:
    print(f"Restrição para barra {k}:")
    print(expressao)
    print()

    

#------------------------------------------
#Restrição 4: Vmin_k ≤ Vk ≤ Vmax_k, ∀k ∈ B
#------------------------------------------
# Função para inserir valores de Vmin e Vmax no banco
def inserir_valores_vmin_vmax():
    engine = conectar_banco()
    vmin = float(input("Digite o valor de Vmin: "))
    vmax = float(input("Digite o valor de Vmax: "))

    with engine.connect() as conn:
        # Apagar os valores antigos
        delete_query = text("DELETE FROM dadosv")
        conn.execute(delete_query)

        # Inserir os novos valores
        insert_query = text("""
            INSERT INTO dadosv (Vmin, Vmax)
            VALUES (:vmin, :vmax)
        """)
        conn.execute(insert_query, {"vmin": vmin, "vmax": vmax})
        conn.commit()

    
    return vmin, vmax  # Retorna os valores para uso na restrição

# Função para montar as restrições usando os dados já buscados
def montar_restricao_vmin_vmax(dadosbarra, vmin, vmax):
    if not dadosbarra.empty:
        print("\n------------------------------------------")
        print("Restrição 4: Vmin_k ≤ Vk ≤ Vmax_k, ∀k ∈ B:")
        print("------------------------------------------\n")

        for barra in dadosbarra.index:
            print(f"Barra {barra}: {vmin} <= V{barra} <= {vmax}")
    else:
        print("Erro: Nenhum dado encontrado para dadosbarra.")

# -----------------
# Fluxo de execução
# -----------------
vmin, vmax = inserir_valores_vmin_vmax()  
montar_restricao_vmin_vmax(dadosbarra, vmin, vmax)  


#-----------------------------------------------
#Restrição 5: Tmin_km ≤ Tkm ≤ Tmax_km, ∀k, m ∈ T
#-----------------------------------------------

# Função para inserir valores de tmin, tmax no banco
def inserir_valores_tmin_tmax():
    engine = conectar_banco()
    tmin = float(input("\nDigite o valor de tmin para todas as linhas: "))
    tmax = float(input("Digite o valor de tmax para todas as linhas: "))

    with engine.connect() as conn:
        # Apagar os valores antigos antes de inserir novos
        delete_query = text("DELETE FROM dadost")
        conn.execute(delete_query)

        # Inserir os novos valores
        insert_query = text("""
            INSERT INTO dadost (Tmin, Tmax)
            VALUES (:tmin, :tmax)
        """)
        conn.execute(insert_query, {"tmin": tmin, "tmax": tmax})
        conn.commit()

    return tmin, tmax  # Retorna os valores para uso na restrição

# Função para montar a quinta restrição
def montar_restricao_tmin_tmax(dadoslinha, tmin, tmax):
    if not dadoslinha.empty:
        print("\n------------------------------------------------")
        print("Restrição 5: Tmin_km ≤ Tkm ≤ Tmax_km, ∀k, m ∈ T:")
        print("------------------------------------------------\n")

        for _, row in dadoslinha.iterrows():
            origem = int(row["Origem"])  # Convertendo para inteiro
            destino = int(row["Destino"])  # Convertendo para inteiro
            tap = int(row["tap"]) if row["tap"].is_integer() else row["tap"]  # Garantindo que `tap` seja tratado corretamente

            if tap > 1:
                print(f"Linha {origem} → {destino}: {int(tmin) if tmin.is_integer() else tmin} <= t{origem}_{destino} <= {int(tmax) if tmax.is_integer() else tmax}") # o is.integer verifica se o float tem alguma informação depois da virgula, caso tiver ele nao vai cortar
    else:
        print("Erro: Nenhum dado encontrado para dadoslinha.")

# -----------------
# Fluxo de execução
# -----------------
tmin, tmax = inserir_valores_tmin_tmax()  # Primeiro, insere os valores no banco
montar_restricao_tmin_tmax(dadoslinha, tmin, tmax)  # Depois, monta a restrição usando os dados já buscados

print("Valores atribuidos a cada TAP")
print(f"tap1: {tap_vars.get('tap1', 'tap1 não foi registrado')}")
print(f"tap2: {tap_vars.get('tap2', 'tap1 não foi registrado')}")
print(f"tap3: {tap_vars.get('tap3', 'tap1 não foi registrado')}")