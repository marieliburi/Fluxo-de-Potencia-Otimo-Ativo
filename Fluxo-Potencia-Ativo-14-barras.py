import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# Criar conexão com o banco usando SQLAlchemy 
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

# Função para calcular a potência ativa Pkm

# Se k é nó inicial:
# Pkm = (gkm (1 / t²km)) * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))

# Se k é nó final:
# Pkm = gkm * V²k - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))

def calcular_potencia_ativa(k, m, gkm, tap, Vk, Vm, theta_km, bkm):
    if k == 1:  # nó inicial
        Pkm = (gkm * (1 / tap**2)) * Vk**2 - (1 / tap) * Vk * Vm * (gkm * np.cos(theta_km) + bkm * np.sin(theta_km))
    else:  # nó final
        Pkm = gkm * Vk**2 - (1 / tap) * Vk * Vm * (gkm * np.cos(theta_km) + bkm * np.sin(theta_km))
    return Pkm

# Função para calcular a potência ativa para ambas as barras (inicial e final)
def calcular_potencia_ativa_total(row, V, theta):
    origem, destino, g, b, bsh, tap = row["Barra_Origem"], row["Barra_Destino"], row["g"], row["b"], row["bsh"], row["tap"]
    Vk = V[origem]
    Vm = V[destino]

    # Calcular as diferenças de ângulo
    theta_km_inicial = theta[origem] - theta[destino]  # Diferença de ângulo para o nó inicial
    theta_km_final = theta[destino] - theta[origem]  # Diferença de ângulo para o nó final
    
    # Calcular a potência ativa para o nó inicial (k = origem)
    Pkm_inicial = calcular_potencia_ativa(origem, destino, g, tap, Vk, Vm, theta_km_inicial, b)

    # Calcular a potência ativa para o nó final (k = destino)
    Pkm_final = calcular_potencia_ativa(destino, origem, g, tap, Vk, Vm, theta_km_final, b)

    return Pkm_inicial, Pkm_final

# Executar os cálculos
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()

# Inicializar a tensão e os ângulos
V = {barra: 1.0 for barra in dadosbarra.index}  # Tensão das barras
theta = {barra: 0.0 for barra in dadosbarra.index}  # Ângulo das barras

# Calcular a potência ativa para cada linha (tanto para o nó inicial quanto final) usando a nova função
for _, row in dadoslinha.iterrows():
    Pkm_inicial, Pkm_final = calcular_potencia_ativa_total(row, V, theta)
    
    # Exibir o resultado da potência ativa para o nó inicial e o nó final
    origem, destino = row["Barra_Origem"], row["Barra_Destino"]
    print(f"Potência ativa entre {origem} e {destino} (Nó Inicial): {Pkm_inicial:.6f}")
    print(f"Potência ativa entre {origem} e {destino} (Nó Final): {Pkm_final:.6f}")
    print()  # Pule uma linha entre os resultados

# Continuação para a primeira restrição
# Pkm − PGk + PC = 0,∀k ∈ G′ ∪ C
print("Restrição 1: Pkm − PGk + PC = 0,∀k ∈ G′ ∪ C")

# Definição da barra slack e dos conjuntos de barras
barra_slack = dadosbarra[dadosbarra["tipo"] == 2].index[0]  
barras_geracao = set(dadosbarra[dadosbarra["tipo"] == 0].index)
barras_carga = set(dadosbarra[dadosbarra["tipo"] == 1].index)  

barras_restricao1 = (barras_geracao | barras_carga) - {barra_slack}  # Barras que entram na restrição

# Criar dicionário para armazenar os valores de Pkm somados por barra
#Como se fosse um vetor, so que adiciona 0 para todos os elementos para nao ser vazio
fluxo_potencia = {k: 0 for k in barras_restricao1}

# Somar os fluxos de potência ativa Pkm para cada barra k
#iterrows() percorre as linhas do DataFrame.
for _, row in dadoslinha.iterrows():
    Pkm_inicial, Pkm_final = calcular_potencia_ativa_total(row, V, theta)

    # Acumular no fluxo de potência das barras envolvidas (se elas estiverem na restrição)
    origem, destino = row["Barra_Origem"], row["Barra_Destino"]
    if origem in fluxo_potencia:
        fluxo_potencia[origem] += Pkm_inicial
    if destino in fluxo_potencia:
        fluxo_potencia[destino] += Pkm_final


# Aplicar a equação da restrição para cada barra
for k in barras_restricao1:
    P_geracao = dadosbarra.at[k, "Pg"]  # Potência ativa gerada
    P_carga = dadosbarra.at[k, "Pc"]  # Potência ativa consumida

    # Resíduo da equação de restrição

    restricao = fluxo_potencia[k] - P_geracao + P_carga
    print(f"Restrição 1 para barra {k}: {restricao:.6f}")
