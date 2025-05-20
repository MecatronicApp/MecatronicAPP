import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Visualización de Horarios", layout="wide")

st.title("Visualización de Horarios Académicos 📅")

uploaded_file = st.file_uploader("Sube tu archivo de Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("Vista previa de los datos")
    st.dataframe(df.head())

    columnas_esperadas = {'Día', 'HoraInicio', 'HoraFin', 'Materia', 'Profesor', 'Salón'}
    if columnas_esperadas.issubset(df.columns):
        df['Duración'] = pd.to_datetime(df['HoraFin']) - pd.to_datetime(df['HoraInicio'])
        df['HoraInicio'] = pd.to_datetime(df['HoraInicio']).dt.time
        df['HoraFin'] = pd.to_datetime(df['HoraFin']).dt.time

        st.subheader("Horario por día")

        dias_unicos = df['Día'].unique()
        dia_seleccionado = st.selectbox("Selecciona un día", dias_unicos)

        df_dia = df[df['Día'] == dia_seleccionado]

        fig = px.timeline(
            df_dia,
            x_start=pd.to_datetime(df_dia['HoraInicio'].astype(str)),
            x_end=pd.to_datetime(df_dia['HoraFin'].astype(str)),
            y='Materia',
            color='Profesor',
            title=f"Horario del día: {dia_seleccionado}",
            labels={"Profesor": "Profesor"},
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"El archivo debe contener las siguientes columnas: {', '.join(columnas_esperadas)}")
else:
    st.info("Por favor, sube un archivo de Excel para comenzar.")
