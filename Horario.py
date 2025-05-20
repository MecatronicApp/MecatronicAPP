# 📚 Importar librerías
import pandas as pd
import io
from IPython.display import display, clear_output
import ipywidgets as widgets
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime
import itertools

# 📂 Paso 1: Subir archivos Excel (fuera de Colab)
upload_widget = widgets.FileUpload(
    accept='.xlsx',
    multiple=True
)
display(widgets.HTML("<h3>⬆️ Carga tus archivos Excel (.xlsx)</h3>"))
display(upload_widget)

# Función para leer los archivos cargados en memoria
def leer_archivos_excel(uploaded_files):
    frames = []
    for nombre_archivo in uploaded_files:
        contenido = uploaded_files[nombre_archivo]['content']
        df_temp = pd.read_excel(io.BytesIO(contenido), header=2)
        frames.append(df_temp)
    return pd.concat(frames, ignore_index=True)

# Esperar hasta que se suban archivos
print("Esperando archivos...")
while not upload_widget.value:
    pass

df = leer_archivos_excel(upload_widget.value)

# 🧹 Paso 2: Limpiar y transformar los datos
df = df[df['Asignatura'].notna()]

dias_map = {
    'Lun': 'Lunes',
    'Mar': 'Martes',
    'Mier': 'Miércoles',
    'Jue': 'Jueves',
    'Vier': 'Viernes',
    'Sab': 'Sábado'
}

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

# 📋 Paso 3: Mostrar resumen general de materias
resumen = df_largo.groupby(['Asignatura', 'Nº Clase']).agg({
    'Día': lambda x: ', '.join(sorted(x.unique())),
    'Hora Ini': lambda x: min(x).strftime('%H:%M'),
    'Hora Fin': lambda x: max(x).strftime('%H:%M'),
    'Total Inscritos': 'first',
    'Total Cupos': 'first',
    '% Ocupación': 'first'
}).reset_index()

print("\U0001F4CB Oferta académica disponible:")
display(resumen)

# ✅ Paso 4: Widgets de selección con filtro de materias
materias = sorted(df_largo['Asignatura'].unique())

busqueda_materias = widgets.Text(
    description='Buscar:',
    placeholder='Escribe para filtrar materias',
    layout=widgets.Layout(width='50%')
)

selector_materias = widgets.SelectMultiple(
    options=materias,
    description='Materias:',
    layout=widgets.Layout(width='50%'),
    rows=12
)

def filtrar_materias_por_texto(cambio):
    texto = cambio['new'].lower()
    opciones_filtradas = [m for m in materias if texto in m.lower()]
    selector_materias.options = opciones_filtradas

busqueda_materias.observe(filtrar_materias_por_texto, names='value')

selector_jornada = widgets.RadioButtons(
    options=['Mañana (6:00 - 14:00)', 'Noche (18:00 - 22:00)', 'Mixta (6:00 - 22:00)'],
    description='Jornada:',
    layout=widgets.Layout(width='50%'),
    style={'description_width': 'initial'}
)

selector_sede = widgets.RadioButtons(
    options=['Todas', 'Chapinero', 'Sur', 'Crisanto Luque'],
    description='Sede:',
    layout=widgets.Layout(width='50%'),
    style={'description_width': 'initial'}
)

boton_generar = widgets.Button(description="Generar horario", button_style='success')
boton_anterior = widgets.Button(description="Anterior", button_style='info')
boton_siguiente = widgets.Button(description="Siguiente", button_style='info')
output = widgets.Output()
nav_box = widgets.HBox([boton_anterior, boton_siguiente])

# 🗓️ Visualización
def hora_a_minutos(t):
    return t.hour * 60 + t.minute

def color_por_ocupacion(pct):
    if pct < 50:
        return 'green'
    elif pct <= 90:
        return 'gold'
    else:
        return 'red'

dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
mapa_dias = {dia: i for i, dia in enumerate(dias_semana)}

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
    ax.set_title("\U0001F5D3️ Horario personalizado del estudiante")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

# Auxiliares
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

# ▶️ Paso 6: Generar combinaciones
combinaciones_filtradas = []
indice_actual = 0

def on_boton_generar_clicked(b):
    global combinaciones_filtradas, indice_actual
    with output:
        clear_output(wait=True)
        seleccion = list(selector_materias.value)
        jornada = selector_jornada.value
        sede = selector_sede.value

        if not seleccion:
            print("⚠️ Por favor selecciona al menos una materia.")
            return

        df_filtrado = df_largo[
            (df_largo['Asignatura'].isin(seleccion)) &
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

        materias_disponibles = df_filtrado['Asignatura'].unique()
        materias_no_disponibles = [m for m in seleccion if m not in materias_disponibles]

        if materias_no_disponibles:
            print(f"⚠️ No hay opciones disponibles para: {', '.join(materias_no_disponibles)}")
            return

        if df_filtrado.empty:
            print("⚠️ No hay clases disponibles con los filtros seleccionados.")
            return

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
        for materia in seleccion:
            clases = df_filtrado[df_filtrado['Asignatura'] == materia]
            clases_por_num = [grupo for _, grupo in clases.groupby('Nº Clase')]
            if clases_por_num:
                opciones_por_materia.append(clases_por_num)

        if not opciones_por_materia:
            print("⚠️ No hay opciones válidas para generar combinaciones.")
            return

        combinaciones = combinaciones_validas(opciones_por_materia)

        combinaciones_filtradas = []
        for comb in combinaciones:
            if all(hora_ini_limite <= hora_a_minutos(h) <= hora_fin_limite for h in comb['Hora Ini']) and \
               all(hora_ini_limite <= hora_a_minutos(h) <= hora_fin_limite for h in comb['Hora Fin']):
                combinaciones_filtradas.append(comb)

        if not combinaciones_filtradas:
            print("⚠️ No hay opciones para esta jornada.")
            return

        indice_actual = 0
        mostrar_combinacion_actual()

def mostrar_combinacion_actual():
    with output:
        clear_output(wait=True)
        print(f"✅ Mostrando combinación #{indice_actual + 1} de {len(combinaciones_filtradas)}")
        comb = combinaciones_filtradas[indice_actual]
        display(comb[['Asignatura', 'Nº Clase', 'Día', 'Hora Ini', 'Hora Fin', 'Salon']])
        mostrar_calendario(comb)

def on_boton_anterior_clicked(b):
    global indice_actual
    if combinaciones_filtradas:
        indice_actual = (indice_actual - 1) % len(combinaciones_filtradas)
        mostrar_combinacion_actual()

def on_boton_siguiente_clicked(b):
    global indice_actual
    if combinaciones_filtradas:
        indice_actual = (indice_actual + 1) % len(combinaciones_filtradas)
        mostrar_combinacion_actual()

# ▶️ Conectar eventos
boton_generar.on_click(on_boton_generar_clicked)
boton_anterior.on_click(on_boton_anterior_clicked)
boton_siguiente.on_click(on_boton_siguiente_clicked)

# ▶️ Mostrar UI
display(widgets.VBox([
    busqueda_materias,
    selector_materias,
    selector_jornada,
    selector_sede,
    boton_generar,
    nav_box,
    output
]))
