import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# Configuración de página minimalista
st.set_page_config(page_title="Consumo de Fleje", layout="centered")

# --- ENCABEZADO ---
st.markdown("<h1 style='text-align: center;'>Consumo de fleje</h1>", unsafe_allow_html=True)

# --- TEXTO INTRODUCTORIO (JUSTIFICADO) ---
st.markdown("""
<div style="text-align: justify;">
Esta aplicación sirve para sumar el peso del fleje consumido por máquina en cada turno. Tú lo único que tienes que hacer es:
<br><br>
1. Coger los partes de los desbobinadores y asegurarte que en TODAS las páginas sea legible la máquina a la que se le corresponde el parte, que está marcada la casilla del turno de mañana, de tarde o de noche y que también esté escrita y sea legible la fecha.
<br><br>
2. Cuando tengas todos los partes preparados de la forma que se indica, lo que tienes que hacer es escanearlos, todos juntos. Ojo, recuerda indicarle a la impresora multifunción que te escanée los partes por las dos caras, que si no se nos puede quedar información por el medio.
<br><br>
3. El .pdf que has obtenido, adjúntalo en el cuadro que aparece aquí abajo, sin más.
<br><br>
Con todo esto, al final te devolveré una tabla en el que te hago la suma de todo el fleje metido a máquina por máquina y por turno.
</div>
""", unsafe_allow_html=True)

st.write("---")

# --- BOTÓN DE CARGA DE ARCHIVO ---
uploaded_file = st.file_uploader("Arrastra o busca tu archivo PDF", type="pdf")

def extract_data(pdf_file):
    all_rows = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            # 1a) Identificar Máquina (L11, L12...)
            maquina_match = re.search(r"L\d{2}", text)
            maquina = maquina_match.group(0) if maquina_match else "Desconocida"
            
            # 1b) Identificar Fecha (Buscamos patrón DD/MM/AAAA)
            fecha_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
            fecha = fecha_match.group(0) if fecha_match else "S/F"
            
            # 1c) Identificar Turno
            # Esto busca la palabra que tenga una marca cerca o esté en el texto
            turno = "Desconocido"
            if "Mañana" in text: turno = "Mañana"
            elif "Tarde" in text: turno = "Tarde"
            elif "Noche" in text: turno = "Noche"
            
            # 2, 3, 4, 5) Analizar Tabla de datos
            table = page.extract_table()
            if table:
                last_etiqueta = 0
                last_gancho = 0
                
                for row in table:
                    # Filtramos filas que parezcan contener datos numéricos o comillas
                    # Ajustar índices [0] y [1] según la posición real en tu PDF
                    raw_e = row[0] if len(row) > 0 else None
                    raw_g = row[1] if len(row) > 1 else None
                    
                    # Lógica de recursividad (Comillas)
                    if raw_e == '"' or raw_e == "''":
                        val_e = last_etiqueta
                    else:
                        try:
                            val_e = float(str(raw_e).replace(',', '.'))
                            last_etiqueta = val_e
                        except: val_e = 0
                        
                    if raw_g == '"' or raw_g == "''":
                        val_g = last_gancho
                    elif not raw_g or raw_g.strip() == "":
                        val_g = 0
                    else:
                        try:
                            val_g = float(str(raw_g).replace(',', '.'))
                            last_gancho = val_g
                        except: val_g = 0
                    
                    if val_e > 0 or val_g > 0:
                        all_data = {
                            "Fecha": fecha,
                            "Turno": turno,
                            "Maquina": maquina,
                            "Peso Etiqueta": val_e,
                            "Peso Gancho": val_g
                        }
                        all_rows.append(all_data)
                        
    return pd.DataFrame(all_rows)

if uploaded_file:
    with st.spinner('Procesando PDF y sumando fleje...'):
        df = extract_data(uploaded_file)
        
        if not df.empty:
            # Agrupar y pivotar para el formato pedido
            pivot_df = df.pivot_table(
                index=['Fecha', 'Turno'],
                columns='Maquina',
                values=['Peso Etiqueta', 'Peso Gancho'],
                aggfunc='sum'
            ).fillna(0)
            
            # Reordenar niveles de columnas para que coincida con el diseño
            pivot_df = pivot_df.swaplevel(0, 1, axis=1).sort_index(axis=1)
            
            st.success("¡Procesamiento completado!")
            st.dataframe(pivot_df)
            
            # Exportar a Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                pivot_df.to_excel(writer, sheet_name='Resumen')
            
            st.download_button(
                label="Descargar Excel",
                data=buffer.getvalue(),
                file_name="resumen_consumo_fleje.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se detectaron datos válidos en el PDF.")