import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# Criar conexão com o banco usando SQLAlchemy 
def conectar_banco():
    engine = create_engine("mysql+mysqlconnector://root:@localhost/sistema_eletrico")
    return engine #sera usado para fazer a busca de dados ao decorrer do cod

# Buscar os dados das barras
def buscar_dadosbarra():
    engine = conectar_banco()
    query = "SELECT Barra, V, Theta FROM dadosbarra"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn).set_index("Barra") 
    return dados

# Buscar os dados das linhas
def buscar_dados_linhas():
    engine = conectar_banco()
    query = "SELECT Barra_Origem, Barra_Destino, R, X, Tap FROM dadoslinha"
    with engine.connect() as conn:
        dados = pd.read_sql(query, conn)
    return dados

# Calcular Gkm
# Fórmula: | gkm = rkm / r²km + x²km |

def calcular_gkm(dados_linhas):
    return dados_linhas["R"] / (dados_linhas["R"]**2 + dados_linhas["X"]**2)

# Executar os cálculos
dadosbarra = buscar_dadosbarra()
dadoslinha = buscar_dados_linhas()

# Substituir TAP = 0 por TAP = 1 para evitar divisão por zero
dadoslinha["Tap"] = dadoslinha["Tap"].replace(0, 1)

# Calcular Gkm
gkm_valores = calcular_gkm(dadoslinha)

# Imprimir os valores de gkm para todas as linhas
"""
Aqui imprime os Gkm de todos separados caso precise para conferir
print("\nValores de Gkm:")
for i, (origem, destino, gkm) in enumerate(zip(dadoslinha["Barra_Origem"], dadoslinha["Barra_Destino"], gkm_valores)):
    print(f"Gkm entre Barra {origem} e Barra {destino}: {gkm:.6f}")
"""

# Construir a função objetiva em uma única equação
equacao_objetiva = []

for i, (origem, destino, tap) in enumerate(zip(dadoslinha["Barra_Origem"], dadoslinha["Barra_Destino"], dadoslinha["Tap"])):
    gkm = gkm_valores[i]
    equacao_objetiva.append(
        f"{gkm:.6f} * (1 / {tap}**2) * (V{origem}**2 + V{destino}**2) - 2 * (1 / {tap}) * V{origem} * V{destino} * cos(Theta{origem} - Theta{destino})"
    )

#Para juntas todas as equações
funcao_objetiva = " + ".join(equacao_objetiva)

# Exibir o resultado final
print("\nFunção Objetiva:\n")
print(funcao_objetiva)