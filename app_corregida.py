
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime
import io
import itertools

dias_map = {
    'Lun': 'Lunes',
    'Mar': 'Martes',
    'Mier': 'Miércoles',
    'Jue': 'Jueves',
    'Vier': 'Viernes',
    'Sab': 'Sábado'
}
dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
mapa_dias = {dia: i for i, dia in enumerate(dias_semana)}

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
    for _, row in horario_df.iterrows():
        dia_idx = mapa_dias[row['Día']]
        ini_min = hora_a_minutos(row['Hora Ini'])
        fin_min = hora_a_minutos(row['Hora Fin'])
        duracion = fin_min - ini_min
        rect = patches.Rectangle(
            (dia_idx, ini_min),
            width=0.9,
            height=duracion,
            facecolor=color_por_ocupacion(row['% Ocupación']),
            edgecolor='black',
            alpha=0.8
        )
        ax.add_patch(rect)
        ax.text(
            dia_idx + 0.05, ini_min + duracion / 2,
            f"{row['Asignatura']}\nClase #{int(row['Nº Clase'])}\n{row['Hora Ini'].strftime('%H:%M')} - {row['Hora Fin'].strftime('%H:%M')}",
            fontsize=8,
            verticalalignment='center',
            color='black'
        )
    ax.set_xlim(0, len(dias_semana))
    ax.set_ylim(1320, 360)
    ax.set_xticks(range(len(dias_semana)))
    ax.set_xticklabels(dias_semana)
    ax.set_yticks(range(360, 1321, 60))
    ax.set_yticklabels([f"{h}:00" for h in range(6, 23)])
    ax.set_xlabel("Día")
    ax.set_ylabel("Hora")
    ax.set_title("🗓️ Horario personalizado del estudiante")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    return fig

# Estado global de combinaciones
global_state = {"combinaciones": [], "indice": 0, "seleccionadas": []}

def cargar_archivos(files):
    if not files:
        return "⚠️ Por favor carga al menos un archivo Excel.", gr.update(choices=[])
    frames = []
    for f in files:
        df_temp = pd.read_excel(f.name, header=2)
        frames.append(df_temp)
    df = pd.concat(frames, ignore_index=True)
    df = df[df['Asignatura'].notna()]
    df_largo = df.melt(
        id_vars=['Asignatura', 'Nº Clase', 'Hora Ini', 'Hora Fin', 'Salon', 'Campus', 'Total Inscritos', 'Total Cupos'],
        value_vars=dias_map.keys(),
        var_name='Día Abrev',
        value_name='Activo'
    )
    df_largo = df_largo[df_largo['Activo'] == 'Y']
    df_largo['Día'] = df_largo['Día Abrev'].map(dias_map)
    df_largo = df_largo.drop(columns=['Día Abrev', 'Activo'])
    df_largo['Total Inscritos'] = pd.to_numeric(df_largo['Total Inscritos'], errors='coerce')
    df_largo['Total Cupos'] = pd.to_numeric(df_largo['Total Cupos'], errors='coerce')
    df_largo['% Ocupación'] = (df_largo['Total Inscritos'] / df_largo['Total Cupos']) * 100
    df_largo['Hora Ini'] = pd.to_datetime(df_largo['Hora Ini'].astype(str), format='%H:%M').dt.time
    df_largo['Hora Fin'] = pd.to_datetime(df_largo['Hora Fin'].astype(str), format='%H:%M').dt.time
    global_state['df'] = df_largo
    materias = sorted(df_largo['Asignatura'].unique())
    return "✅ Archivos cargados correctamente.", gr.update(choices=materias)

def generar_combinaciones(materias, jornada, sede):
    df = global_state['df']
    df_filtrado = df[df['Asignatura'].isin(materias) & (df['Total Inscritos'] < df['Total Cupos'])]
    if sede == 'Sur':
        df_filtrado = df_filtrado[df_filtrado['Salon'].str.startswith('SUR', na=False)]
    elif sede == 'Crisanto Luque':
        df_filtrado = df_filtrado[df_filtrado['Salon'].str.contains('SLUQ', na=False)]
    elif sede == 'Chapinero':
        df_filtrado = df_filtrado[
            ~df_filtrado['Salon'].str.startswith('SUR', na=False) &
            ~df_filtrado['Salon'].str.contains('SLUQ', na=False)
        ]

    if 'Mañana' in jornada:
        hora_ini_limite = 6 * 60
        hora_fin_limite = 14 * 60
    elif 'Noche' in jornada:
        hora_ini_limite = 18 * 60
        hora_fin_limite = 22 * 60
    else:
        hora_ini_limite = 6 * 60
        hora_fin_limite = 22 * 60

    opciones_por_materia = []
    for materia in materias:
        clases = df_filtrado[df_filtrado['Asignatura'] == materia]
        clases_por_num = [grupo for _, grupo in clases.groupby('Nº Clase')]
        if clases_por_num:
            opciones_por_materia.append(clases_por_num)

    combinaciones = combinaciones_validas(opciones_por_materia)
    combinaciones_filtradas = []
    for comb in combinaciones:
        if all(hora_ini_limite <= hora_a_minutos(h) <= hora_fin_limite for h in comb['Hora Ini']) and            all(hora_ini_limite <= hora_a_minutos(h) <= hora_fin_limite for h in comb['Hora Fin']):
            combinaciones_filtradas.append(comb)

    if not combinaciones_filtradas:
        return "⚠️ No se encontraron combinaciones válidas.", None

    global_state['combinaciones'] = combinaciones_filtradas
    global_state['indice'] = 0
    return mostrar_combinacion()

def mostrar_combinacion():
    if not global_state['combinaciones']:
        return "⚠️ No hay combinaciones generadas.", None
    comb = global_state['combinaciones'][global_state['indice']]
    tabla = comb[['Asignatura', 'Nº Clase', 'Día', 'Hora Ini', 'Hora Fin', 'Salon']]
    fig = mostrar_calendario(comb)
    return tabla, fig

def siguiente():
    if global_state['combinaciones']:
        global_state['indice'] = (global_state['indice'] + 1) % len(global_state['combinaciones'])
    return mostrar_combinacion()

def anterior():
    if global_state['combinaciones']:
        global_state['indice'] = (global_state['indice'] - 1) % len(global_state['combinaciones'])
    return mostrar_combinacion()

with gr.Blocks() as demo:
    gr.Markdown("## 📚 Generador de Horarios para Estudiantes - Ingeniería Mecatrónica")
    archivos = gr.File(file_types=['.xls', '.xlsx'], file_count="multiple", label="Sube archivos Excel")
    estado_archivo = gr.Textbox(label="Estado de carga", interactive=False)
    materias = gr.CheckboxGroup(label="Materias disponibles")
    jornada = gr.Radio(["Mañana (6:00 - 14:00)", "Noche (18:00 - 22:00)", "Mixta (6:00 - 22:00)"], label="Jornada")
    sede = gr.Radio(["Todas", "Chapinero", "Sur", "Crisanto Luque"], label="Sede")
    boton_cargar = gr.Button("📂 Cargar archivos")
    boton_generar = gr.Button("✅ Generar combinaciones")
    tabla = gr.Dataframe()
    grafico = gr.Plot()
    botones_nav = gr.Row([gr.Button("⬅️ Anterior"), gr.Button("➡️ Siguiente")])

    boton_cargar.click(cargar_archivos, inputs=[archivos], outputs=[estado_archivo, materias])
    boton_generar.click(generar_combinaciones, inputs=[materias, jornada, sede], outputs=[tabla, grafico])
    boton_anterior.click(anterior, outputs=[tabla, grafico])
    boton_siguiente.click(siguiente, outputs=[tabla, grafico])

demo.launch()
