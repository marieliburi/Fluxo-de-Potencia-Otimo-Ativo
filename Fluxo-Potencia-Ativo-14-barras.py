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

# Substituir TAP = 0 por TAP = 1 para evitar divisão por zero
dadoslinha["tap"] = dadoslinha["tap"].replace(0, 1)

# Construir a função objetiva em uma única equação
equacao_objetiva = []

for _, row in dadoslinha.iterrows():
    origem, destino, g, tap = row["Barra_Origem"], row["Barra_Destino"], row["g"], row["tap"]
    equacao_objetiva.append(
        f"{g:.6f} * (1 / {tap}**2) * (V{origem}**2 + V{destino}**2) - 2 * (1 / {tap}) * V{origem} * V{destino} * cos(Theta{origem} - Theta{destino})"
    )

# Unir todas as equações
funcao_objetiva = " + ".join(equacao_objetiva)

# Exibir o resultado final
print("\nFunção Objetiva:\n")
print(funcao_objetiva)

#Agora é o cod para calcular o Pkm

V = {barra: 1.0 for barra in dadosbarra.index}  # Tensão das barras 
theta = {barra: 0.0 for barra in dadosbarra.index}  # Ângulo das barras

# Função para calcular a potência ativa Pkm
def calcular_potencia_ativa(k, m, gkm, tkm, Vk, Vm, theta_km, bkm):
    #print(f"Calculando Pkm: k={k}, m={m}, gkm={gkm}, tkm={tkm}, Vk={Vk}, Vm={Vm}, theta_km={theta_km}, bkm={bkm}")
    
    # Verifica se k é o nó inicial ou final
    #print(f"gkm={gkm}, tkm={tkm}, Vk={Vk}, Vm={Vm}, theta_km={theta_km}, bkm={bkm}") #PARA VERIFICAR OS VALORES

    if k == 1:  # nó inicial
        Pkm = (gkm * 1 / tkm**2) * Vk**2 - (1 /tkm) * Vk * Vm * (gkm * np.cos(theta_km) + bkm * np.sin(theta_km))
    else:  # nó final
        Pkm = gkm * Vk**2 - (1 / tkm) * Vk * Vm * (gkm * np.cos(theta_km) + bkm * np.sin(theta_km))
    
    return Pkm

# Calcular e imprimir a potência ativa para cada linha (tanto para o nó inicial quanto final)
for _, row in dadoslinha.iterrows():
    origem, destino, g, b, bsh, tap = row["Barra_Origem"], row["Barra_Destino"], row["g"], row["b"], row["bsh"], row["tap"]
    Vk = V[origem]
    Vm = V[destino]
    

    # Calcular a potência ativa para o nó inicial (k = origem)
    theta_km_inicial = theta[origem] - theta[destino]  # Diferença de ângulo
    Pkm_inicial = calcular_potencia_ativa(origem, destino, g, tap, Vk, Vm, theta_km_inicial, b)
    
    # Calcular a potência ativa para o nó final (k = destino)
    theta_km_final = theta[destino] - theta[origem]  # Diferença de ângulo
    Pkm_final = calcular_potencia_ativa(destino, origem, g, tap, Vk, Vm, theta_km_final, b)
    
    # Exibir o resultado da potência ativa para o nó inicial e o nó final
    print(f"Potência ativa entre {origem} e {destino} (Nó Inicial): {Pkm_inicial:.6f}")
    print(f"Potência ativa entre {origem} e {destino} (Nó Final): {Pkm_final:.6f}")
    print()  # Pule uma linha entre os resultados
    
