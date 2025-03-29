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

# Executar os cálculos
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()

# Construir a função objetiva em uma única equação
equacao_objetiva = []

for _, row in dadoslinha.iterrows():
    origem, destino, tap = row["Barra_Origem"], row["Barra_Destino"], row["tap"]
    gkm = row["g"]
    
    equacao_objetiva.append(
        f"{gkm:.6f} * (1 / {tap}**2) * (V{origem}**2 + V{destino}**2) - 2 * (1 / {tap}) * V{origem} * V{destino} * cos(Theta{origem} - Theta{destino})"
    )

# Para juntar todas as equações
funcao_objetiva = " + ".join(equacao_objetiva)

# Exibir o resultado final
print("\nFunção Objetiva:\n")
print(funcao_objetiva)
print()

# Função para calcular a potência ativa Pkm

# Se k é nó inicial:
# Pkm = (gkm (1 / t²km)) * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))

# Se k é nó final:
# Pkm = gkm * V²k - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))


# Inicializar a tensão e os ângulos
V = {barra: 1.0 for barra in dadosbarra.index}  # Tensão das barras
theta = {barra: 0.0 for barra in dadosbarra.index}  # Ângulo das barras

# Calcular a potência ativa para cada linha (tanto para o nó inicial quanto final) usando a nova função
# Gerar expressões da potência ativa para cada linha (tanto para o nó inicial quanto final)

print("INICIAL: Pkm = (gkm (1 / t²km)) * Vk² - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))")
print("\nFINAL: Pkm = gkm * V²k - (1 / tkm) * Vk * Vm * (gkm * cos(θkm) + bkm * sin(θkm))")
print()
for _, row in dadoslinha.iterrows():
    origem, destino = row["Barra_Origem"], row["Barra_Destino"]
    gkm, bkm, tap = row["g"], row["b"], row["tap"]
    
    # Expressões das potências ativas
    expressao_pkm_inicial = (
        f"({gkm:.6f} * (1 / {tap}**2)) * V{origem}² - "
        f"(1 / {tap}) * V{origem} * V{destino} * "
        f"({gkm:.6f} * cos(Theta{origem} - Theta{destino}) + {bkm:.6f} * sin(Theta{origem} - Theta{destino}))"
    )
    
    expressao_pkm_final = (
        f"({gkm:.6f} * V{destino}²) - "
        f"(1 / {tap}) * V{origem} * V{destino} * "
        f"({gkm:.6f} * cos(Theta{destino} - Theta{origem}) + {bkm:.6f} * sin(Theta{destino} - Theta{origem}))"
    )

    # Exibir as expressões simbólicas das potências ativas
    print(f"Expressão da potência ativa entre {origem} e {destino} (Nó Inicial): {expressao_pkm_inicial}")
    print(f"Expressão da potência ativa entre {origem} e {destino} (Nó Final): {expressao_pkm_final}")
    print()  


# Continuação para a primeira restrição
# Pkm − PGk + PC = 0,∀k ∈ G′ ∪ C
print("\nRESTRIÇÃO 1: Pkm − PGk + PC = 0,∀k ∈ G′ ∪ C")

# Definição da barra slack e dos conjuntos de barras
barra_slack = dadosbarra[dadosbarra["tipo"] == 2].index[0]  
barras_geracao = set(dadosbarra[dadosbarra["tipo"] == 1].index)
barras_carga = set(dadosbarra[dadosbarra["tipo"] == 0].index)  

barras_restricao1 = (barras_geracao | barras_carga) - {barra_slack}  # Barras que entram na restrição

# Criar dicionário para armazenar os valores de Pkm somados por barra
#Como se fosse um vetor, so que adiciona 0 para todos os elementos para nao ser vazio
fluxo_potencia = {k: 0 for k in barras_restricao1}
# Construir a restrição de forma simbólica
restricoes = []

for k in barras_restricao1:
    termos_fluxo = []
    
    for _, row in dadoslinha.iterrows():
        origem, destino, tap = row["Barra_Origem"], row["Barra_Destino"], row["tap"]
        
        if origem == k or destino == k:
            gkm = row["g"]
            termos_fluxo.append(
                f"{gkm:.6f} * (1 / {tap}**2) * (V{k}**2) - (1 / {tap}) * V{k} * V{destino} * (gkm * cos(Theta{k} - Theta{destino}))"
            )

    restricao_k = " + ".join(termos_fluxo) + f" - P_G{k} + P_C{k} = 0"
    restricoes.append(restricao_k)

# Exibir todas as restrições
for k, restricao in zip(barras_restricao1, restricoes):
    print(f"Restrição 1 para barra {k}: {restricao}")
    print()
