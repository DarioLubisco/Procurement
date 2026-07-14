import pandas as pd
import numpy as np

# 1. Cargar mercado
market = pd.read_csv('test_data/market_offers.csv', dtype={'codbarras': str})
market['codbarras'] = market['codbarras'].str.strip().str.replace('\.0$', '', regex=True)
market['proveedor'] = market['proveedor'].str.strip().str.upper()

# 2. Cargar nuestro pedido
df_ours = pd.read_excel('Pedido_Moleculas_v3.2_30Dias.xlsx')
df_ours['codbarras'] = df_ours['codbarras'].astype(str).str.strip().str.replace('\.0$', '', regex=True)
df_ours['proveedor'] = df_ours['proveedor'].str.strip().str.upper()

# 3. Cargar pedido externo
df_ext = pd.read_excel('pedido_251179.xlsx', skiprows=11)
df_ext = df_ext.dropna(subset=['Barra'])
df_ext['Barra'] = df_ext['Barra'].astype(str).str.strip().str.replace('\.0$', '', regex=True)
df_ext['Proveedor_Externo'] = df_ext['Proveedor'].astype(str).str.strip().str.upper()

# 4. Merge
merged = pd.merge(df_ours, df_ext, left_on='codbarras', right_on='Barra', how='inner', suffixes=('_Nuestro', '_Externo'))

# 5. Análisis de cada diferencia
results = []
for _, row in merged.iterrows():
    cod = row['codbarras']
    desc = row['descripcion']
    prov_nuestro = row['proveedor']
    prov_externo = row['Proveedor_Externo']
    
    if prov_nuestro == prov_externo:
        continue
        
    # Buscar ofertas en el mercado para este codbarras
    ofertas_mercado = market[market['codbarras'] == cod]
    
    # Buscar nuestra oferta en mercado
    nuestra_oferta = ofertas_mercado[ofertas_mercado['proveedor'] == prov_nuestro]
    precio_mercado_nuestro = nuestra_oferta['precio_unitario'].min() if not nuestra_oferta.empty else None
    
    # Buscar oferta externa en mercado
    oferta_ext_en_mercado = ofertas_mercado[ofertas_mercado['proveedor'] == prov_externo]
    precio_mercado_ext = oferta_ext_en_mercado['precio_unitario'].min() if not oferta_ext_en_mercado.empty else None
    
    motivo = ""
    if oferta_ext_en_mercado.empty:
        motivo = f"El proveedor externo ({prov_externo}) NO estaba disponible en nuestro snapshot del mercado para este producto."
    else:
        if precio_mercado_nuestro is not None and precio_mercado_ext is not None:
            if precio_mercado_nuestro <= precio_mercado_ext:
                motivo = f"Nuestro proveedor ({prov_nuestro}) tenía un precio igual o mejor (Bs {precio_mercado_nuestro:.2f}) que el externo (Bs {precio_mercado_ext:.2f}) en el snapshot del mercado."
            else:
                motivo = f"El externo ({prov_externo}) era más barato (Bs {precio_mercado_ext:.2f} vs Bs {precio_mercado_nuestro:.2f}), pero el motor eligió {prov_nuestro} posiblemente por S4 (consolidación) o stock insuficiente."
        else:
            motivo = "Problema con la data de precios en el mercado."
            
    results.append({
        'Codigo Barras': cod,
        'Descripcion': desc,
        'Proveedor Nuestro': prov_nuestro,
        'Precio Nuestro (Bs)': row['precio_unitario'],
        'Proveedor Externo': prov_externo,
        'Precio Externo (Neto USD/ref)': row['Neto'],
        'Externo disponible en nuestro Mercado?': 'SI' if not oferta_ext_en_mercado.empty else 'NO',
        'Precio Externo en nuestro Mercado (Bs)': precio_mercado_ext,
        'Explicacion': motivo,
        'Justificacion Original (Nuestra)': row['justificacion']
    })

df_res = pd.DataFrame(results)
df_res.to_excel('Comparacion_Proveedores.xlsx', index=False)
print(f"Reporte generado con {len(df_res)} diferencias.")
print(df_res['Explicacion'].value_counts())
