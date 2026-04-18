import streamlit as st
import pandas as pd
import pytesseract
from pdf2image import convert_from_bytes
import re
import io

st.set_page_config(page_title="Consumo de Fleje", layout="centered")

st.markdown("<h1 style='text-align: center;'>Consumo de fleje</h1>", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: justify;">
Esta aplicación sirve para sumar el peso del fleje consumido por máquina en cada turno... [Instrucciones simplificadas para el código]
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Adjunta el PDF escaneado", type="pdf")

def procesar_pdf(file_bytes):
    # Convertimos el PDF en imágenes (una por página)
    images = convert_from_bytes(file_bytes.read())
    all_data = []
    
    # Variables para recordar el valor anterior (Recursividad de comillas)
    last_e = 0.0
    last_g = 0.0

    for i, img in enumerate(images):
        # OCR: Extraemos el texto de la imagen de la página
        text = pytesseract.image_to_string(img, lang='spa')
        
        # 1. Identificar Máquina (L11, L12...)
        maquina = re.search(r"L\d{2}", text)
        maquina = maquina.group(0) if maquina else "L??"
        
        # 2. Identificar Fecha
        fecha = re.search(r"\d{2}/\d{2}/\d{4}", text)
        fecha = fecha.group(0) if fecha else "S/Fecha"
        
        # 3. Identificar Turno
        turno = "Mañana"
        if "Tarde" in text or "[X] Tarde" in text: turno = "Tarde"
        elif "Noche" in text or "[X] Noche" in text: turno = "Noche"

        # 4. Extraer números de las columnas (Peso Etiqueta y Peso Gancho)
        # Buscamos líneas que tengan números o comillas
        lines = text.split('\n')
        for line in lines:
            # Buscamos números decimales o el símbolo de comillas
            parts = re.findall(r'(\d+[\.,]\d+|"|' + "''" + ')', line)
            
            if parts:
                raw_e = parts[0]
                raw_g = parts[1] if len(parts) > 1 else "0"

                # Lógica Peso Etiqueta + Comillas
                if raw_e in ['"', "''"]:
                    val_e = last_e
                else:
                    try:
                        val_e = float(raw_e.replace(',', '.'))
                        last_e = val_e
                    except: val_e = 0.0

                # Lógica Peso Gancho + Comillas + Vacío
                if raw_g in ['"', "''"]:
                    val_g = last_g
                else:
                    try:
                        val_g = float(raw_g.replace(',', '.'))
                        last_g = val_g
                    except: val_g = 0.0
                
                if val_e > 0 or val_g > 0:
                    all_data.append({
                        "Fecha": fecha,
                        "Turno": turno,
                        "Maquina": maquina,
                        "Peso etiqueta": val_e,
                        "Peso gancho": val_g
                    })

    return pd.DataFrame(all_data)

if uploaded_file:
    with st.spinner('Leyendo manuscritos y procesando...'):
        df_final = procesar_pdf(uploaded_file)
        
        if not df_final.empty:
            # Crear la tabla pivote con el formato exacto solicitado
            tabla_pivote = df_final.pivot_table(
                index=['Fecha', 'Turno'],
                columns='Maquina',
                values=['Peso etiqueta', 'Peso gancho'],
                aggfunc='sum'
            ).fillna(0)
            
            # Ajustar orden de columnas
            tabla_pivote = tabla_pivote.swaplevel(0, 1, axis=1).sort_index(axis=1)
            
            st.success("Datos extraídos correctamente")
            st.table(tabla_pivote) # st.table es más minimalista
            
            # Botón de exportar
            towrite = io.BytesIO()
            tabla_pivote.to_excel(towrite, index=True, header=True)
            st.download_button(label="📥 Descargar Excel", data=towrite.getvalue(), file_name="consumo.xlsx")
        else:
            st.warning("No se encontraron datos. Asegúrate de que el encabezado (L11, L12...) y los números sean legibles.")
