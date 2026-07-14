import pandas as pd
import numpy as np

# Load our order
df_ours = pd.read_excel('Pedido_Moleculas_v3.2_30Dias.xlsx')
df_ours['codbarras'] = df_ours['codbarras'].astype(str).str.strip().str.replace('\.0$', '', regex=True)

# Load external order
df_ext = pd.read_excel('pedido_251179.xlsx', skiprows=11)
df_ext = df_ext.dropna(subset=['Barra'])
df_ext['Barra'] = df_ext['Barra'].astype(str).str.strip().str.replace('\.0$', '', regex=True)

# Merge
merged = pd.merge(df_ours, df_ext, left_on='codbarras', right_on='Barra', how='inner', suffixes=('_Nuestro', '_Externo'))

differences = merged[merged['proveedor'] != merged['Proveedor']]

print(f"Total lineas en nuestro pedido: {len(df_ours)}")
print(f"Total lineas en pedido externo: {len(df_ext)}")
print(f"Coincidencias por código de barras: {len(merged)}")
print(f"Diferencias en proveedor: {len(differences)}")
print("\nEjemplos de diferencias:")
for _, row in differences.head(10).iterrows():
    print(f"Cod: {row['codbarras']} | Desc: {row['descripcion']}")
    print(f"  Nuestro: {row['proveedor']} (Precio: {row['precio_unitario']}, Cant: {row['cantidad']})")
    print(f"  Externo: {row['Proveedor']} (Precio: {row['Neto']}, Cant: {row['Cantidad']})")
    print(f"  Justificación nuestra: {row['justificacion']}")
    print("---")
