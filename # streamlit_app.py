# streamlit_app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import itertools
from datetime import datetime

# Funciones auxiliares
def hora_a_minutos(t):
    return t.hour * 60 + t.minute

def color_por_ocupacion(pct):
    if pct < 50:
        return 'green'
    elif pct <= 90:
        return 'gold'
    else:
        return 'red'

def clases_se_solan(c1, c2):
    if c1['Día'] != c2['Día']:
        return False
    ini1, fin1 = hora_a_minutos(c1['Hora Ini']), hora_a_minutos(c1['Hora Fin'])
    ini2, fin2 = hora_a_minutos(c2['Hora Ini']), hora_a_minutos(c2['Hora Fin'])
    return max(ini1, ini2) < min(fin1, fin2)

def combinaciones_validas(opciones_por_materia):
    combinaciones = []
    for combinacion in itertools.product(*opciones_por_materia):
        solapamiento = False
        for i in range(len(combinacion)):
            for j in range(i + 1, len(combinacion)):
                if any(clases_se_solan(c1, c2) for _, c1 in combinacion[i].iterrows() for _, c2 in combinacion[j].iterrows()):
                    solapamiento = True
                    break
            if solapamiento:
                break
        if not solapamiento:
            combinaciones.append(pd.concat(combinacion))
    return combinaciones

def mostrar_calendario(horario_df):
    fig, ax = plt.subplots(figsize=(14, 8))
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    mapa_dias = {dia: i for i, dia in enumerate(dias_semana)}

    for _, row in horario_df.iterrows():
        dia_idx = mapa_dias[row['Día']]
        ini_min = hora_a_minutos(row['Hora Ini'])
        fin_min = hora_a_minutos(row['Hora Fin'])
        duracion = fin_min - ini_min

        rect = patches.Rectangle(
            (dia_idx, ini_min), 0.9, duracion,
            facecolor=color_por_ocupacion(row['% Ocupación']),
            edgecolor='black', alpha=0.8
        )
        ax.add_patch(rect)
        ax.text(
            dia_idx + 0.05, ini_min + duracion / 2,
            f"{row['Asignatura']}\nClase {int(row['Nº Clase'])}",
            fontsize=8, verticalalignment='center'
        )

    ax.set_xlim(0, 6)
    ax.set_ylim(1320, 360)
    ax.set_xticks(range(6))
    ax.set_xticklabels(dias_semana)
    ax.set_yticks(range(360, 1321, 60))
    ax.set_yticklabels([f"{h}:00" for h in range(6, 23)])
    ax.set_title("Horario personalizado")
    ax.set_xlabel("Día")
    ax.set_ylabel("Hora")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    st.pyplot(fig)

# --- APP ---

st.title("📅 Generador de Horarios - Ingeniería Mecatrónica")

uploaded_files = st.file_uploader("Sube uno o varios archivos Excel", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    # Procesar archivos
    frames = []
    for uploaded_file in uploaded_files:
        df_temp = pd.read_excel(uploaded_file, header=2)
        frames.append(df_temp)
    df = pd.concat(frames, ignore_index=True)

    df = df[df['Asignatura'].notna()]
    dias_map = {'Lun': 'Lunes', 'Mar': 'Martes', 'Mier': 'Miércoles', 'Jue': 'Jueves', 'Vier': 'Viernes', 'Sab': 'Sábado'}

    df_largo = df.melt(
        id_vars=['Asignatura', 'Nº Clase', 'Hora Ini', 'Hora Fin', 'Salon', 'Campus', 'Total Inscritos', 'Total Cupos'],
        value_vars=dias_map.keys(), var_name='Día Abrev', value_name='Activo')
    df_largo = df_largo[df_largo['Activo'] == 'Y']
    df_largo['Día'] = df_largo['Día Abrev'].map(dias_map)
    df_largo.drop(columns=['Día Abrev', 'Activo'], inplace=True)

    df_largo['Total Inscritos'] = pd.to_numeric(df_largo['Total Inscritos'], errors='coerce')
    df_largo['Total Cupos'] = pd.to_numeric(df_largo['Total Cupos'], errors='coerce')
    df_largo['% Ocupación'] = (df_largo['Total Inscritos'] / df_largo['Total Cupos']) * 100

    df_largo['Hora Ini'] = pd.to_datetime(df_largo['Hora Ini'].astype(str), format='%H:%M').dt.time
    df_largo['Hora Fin'] = pd.to_datetime(df_largo['Hora Fin'].astype(str), format='%H:%M').dt.time

    materias = sorted(df_largo['Asignatura'].unique())
    seleccionadas = st.multiselect("Selecciona las materias:", materias)
    jornada = st.radio("Selecciona la jornada:", ['Mañana (6:00 - 14:00)', 'Noche (18:00 - 22:00)', 'Mixta (6:00 - 22:00)'])
    sede = st.radio("Selecciona la sede:", ['Todas', 'Chapinero', 'Sur', 'Crisanto Luque'])

    if st.button("🔍 Generar combinaciones de horario"):
        if not seleccionadas:
            st.warning("Selecciona al menos una materia.")
        else:
            df_filtrado = df_largo[
                (df_largo['Asignatura'].isin(seleccionadas)) &
                (df_largo['Total Inscritos'] < df_largo['Total Cupos'])
            ]

            if sede == 'Sur':
                df_filtrado = df_filtrado[df_filtrado['Salon'].str.startswith('SUR', na=False)]
            elif sede == 'Crisanto Luque':
                df_filtrado = df_filtrado[df_filtrado['Salon'].str.contains('SLUQ', na=False)]
            elif sede == 'Chapinero':
                df_filtrado = df_filtrado[
                    ~df_filtrado['Salon'].str.startswith('SUR', na=False) &
                    ~df_filtrado['Salon'].str.contains('SLUQ', na=False)
                ]

            if df_filtrado.empty:
                st.warning("No hay clases disponibles para esta combinación.")
            else:
                if 'Mañana' in jornada:
                    ini_lim, fin_lim = 6*60, 14*60
                elif 'Noche' in jornada:
                    ini_lim, fin_lim = 18*60, 22*60
                else:
                    ini_lim, fin_lim = 6*60, 22*60

                opciones_por_materia = []
                for materia in seleccionadas:
                    clases = df_filtrado[df_filtrado['Asignatura'] == materia]
                    grupos = [g for _, g in clases.groupby('Nº Clase')]
                    if grupos:
                        opciones_por_materia.append(grupos)

                combinaciones = combinaciones_validas(opciones_por_materia)

                combinaciones_filtradas = []
                for comb in combinaciones:
                    if all(ini_lim <= hora_a_minutos(h) <= fin_lim for h in comb['Hora Ini']) and \
                       all(ini_lim <= hora_a_minutos(h) <= fin_lim for h in comb['Hora Fin']):
                        combinaciones_filtradas.append(comb)

                if combinaciones_filtradas:
                    for i, comb in enumerate(combinaciones_filtradas[:5]):
                        st.subheader(f"✅ Opción {i+1}")
                        st.dataframe(comb[['Asignatura', 'Nº Clase', 'Día', 'Hora Ini', 'Hora Fin', 'Salon']])
                        mostrar_calendario(comb)
                else:
                    st.warning("No hay combinaciones que cumplan los filtros de jornada.")

