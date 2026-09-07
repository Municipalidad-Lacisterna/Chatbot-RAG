import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Create data
data = {
    'Adopcion_Pct': [0.10, 0.20, 0.30],
    'Vecinos': [10315, 20630, 30947],
    'Mensajes_RAG': [20630, 41260, 61894],
    'Costo_USD': [412, 825, 1237]
}
df = pd.DataFrame(data)

output_dir = "/home/aspen/Alcaldia_Practica/docs/attachments"
os.makedirs(output_dir, exist_ok=True)

# 1. df.info() -> Representar visualmente o guardar texto
with open(os.path.join(output_dir, "Pasted image 1.txt"), "w") as f:
    df.info(buf=f)

# 2. Matriz de correlación
vars_numericas = ['Adopcion_Pct', 'Vecinos', 'Mensajes_RAG', 'Costo_USD']
matriz_corr = df[vars_numericas].corr()
plt.figure(figsize=(8, 6))
sns.heatmap(matriz_corr, annot=True, cmap='coolwarm', fmt=".2f")
plt.title("Matriz de Correlación")
plt.savefig(os.path.join(output_dir, "Pasted image 2.png"))
plt.close()

# 3. Ajuste del modelo
tarifa_servicio_chile = 0.02
df['Prediccion_Costo'] = df['Mensajes_RAG'] * tarifa_servicio_chile
with open(os.path.join(output_dir, "Pasted image 3.txt"), "w") as f:
    f.write("Modelo de facturación aplicado exitosamente.\n")
    f.write(df[['Mensajes_RAG', 'Costo_USD', 'Prediccion_Costo']].to_string())

# 4. Dashboard (Plot de costo vs adopción)
plt.figure(figsize=(10, 6))
sns.lineplot(data=df, x='Adopcion_Pct', y='Costo_USD', marker='o')
plt.title("Proyección de Costos por Adopción")
plt.savefig(os.path.join(output_dir, "dashboard_lacisterna_problema_1.png"))
plt.savefig(os.path.join(output_dir, "Pasted image 4.png"))
plt.close()

print("Imágenes y datos generados en", output_dir)
