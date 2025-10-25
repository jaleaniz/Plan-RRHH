import os
import sys

# ----------------------------------------------------
# FIX CRÍTICO: Configurar la codificación a UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
# ----------------------------------------------------

import json
from flask import Flask, jsonify, request, send_file
# ... (resto del código) ...
import os
import json
from flask import Flask, jsonify, request, send_file # Añadido send_file
from flask_cors import CORS # Necesario para que el navegador lea el JSON
from dotenv import load_dotenv
from google import genai

# Importa las clases y funciones que definiste en database.py
from database import Session, Pais, BloqueAccion, Tarea, ValorGlobal, crear_tablas, cargar_datos_iniciales

# ===============================================
# 1. CONFIGURACIÓN DE LA APP Y LA IA
# ===============================================

# Cargar la clave de la IA de forma segura desde el archivo .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = 'gemini-2.5-flash' 

if not API_KEY:
    raise ValueError("ERROR: La clave API (GEMINI_API_KEY) no está cargada desde el archivo .env.")

# Inicializar el cliente de la API de Gemini
client = genai.Client(api_key=API_KEY)

# Inicializar la aplicación web Flask
app = Flask(__name__)
CORS(app) # <<<< CORRECCIÓN FINAL: HABILITAR CORS

# ===============================================
# 2. LÓGICA DE NEGOCIO (Scorecards E y F)
# ===============================================

def calcular_scorecards(session):
    """Calcula el Scorecard de Compliance y el Índice de Alineación Cultural (IAC) para cada país."""
    
    bloques_fase_a = session.query(BloqueAccion).filter_by(fase='A').all()
    bloques_fase_b = session.query(BloqueAccion).filter_by(fase='B').all()
    
    paises = session.query(Pais).all()
    
    resultados = {}
    
    for pais in paises:
        tareas_a_totales = session.query(Tarea).filter(
            Tarea.pais_id == pais.id,
            Tarea.bloque_id.in_([b.id for b in bloques_fase_a])
        ).count()
        tareas_b_totales = session.query(Tarea).filter(
            Tarea.pais_id == pais.id,
            Tarea.bloque_id.in_([b.id for b in bloques_fase_b])
        ).count()
        
        tareas_a_completadas = session.query(Tarea).filter(
            Tarea.pais_id == pais.id,
            Tarea.bloque_id.in_([b.id for b in bloques_fase_a]),
            Tarea.estado == 'Completado'
        ).count()
        tareas_b_completadas = session.query(Tarea).filter(
            Tarea.pais_id == pais.id,
            Tarea.bloque_id.in_([b.id for b in bloques_fase_b]),
            Tarea.estado == 'Completado'
        ).count()
        
        scorecard_compliance = (tareas_a_completadas / tareas_a_totales) * 100 if tareas_a_totales > 0 else 0
        indice_cultural = (tareas_b_completadas / tareas_b_totales) * 100 if tareas_b_totales > 0 else 0
        
        resultados[pais.nombre] = {
            'compliance': round(scorecard_compliance, 1),
            'cultura': round(indice_cultural, 1),
            'total_a': tareas_a_totales,
            'total_b': tareas_b_totales
        }
        
    return resultados

# ===============================================
# 3. LÓGICA DE LA IA (Funcionalidades I y J)
# ===============================================

@app.route('/api/ia/consistencia', methods=['POST'])
def asistente_consistencia_cultural():
    """Funcionalidad J: Compara un plan local (texto) con los Valores Globales (texto)."""
    
    data = request.json
    plan_local = data.get('plan_local', '')
    pais_nombre = data.get('pais', 'General')
    
    if not plan_local:
        return jsonify({"error": "Se requiere el texto del plan local."}), 400

    session = Session()
    valores_maestros = session.query(ValorGlobal).all()
    session.close()

    contexto_valores = "DOCUMENTO MAESTRO DE VALORES GLOBALES:\n"
    for valor in valores_maestros:
        contexto_valores += f"- {valor.nombre}: {valor.definicion}\n"
    
    prompt_ia = f"""
    Eres un auditor experto en Cultura Organizacional Global. Tu tarea es analizar el 'Plan de Acción Local' proporcionado y compararlo estrictamente con el 'DOCUMENTO MAESTRO DE VALORES GLOBALES'.
    
    Instrucciones:
    1. Genera un 'Índice de Coherencia Semántica' (un porcentaje del 0 al 100%) que indique qué tan alineado está el plan con los valores maestros.
    2. Identifica cualquier palabra, frase o concepto en el plan local que pueda interpretarse como una 'desviación', 'inconsistencia' o 'conflicto' con la definición maestra.
    3. Proporciona sugerencias prácticas para reescribir las secciones problemáticas y asegurar una alineación perfecta con la cultura única del grupo.
    
    ---
    {contexto_valores}
    ---
    
    Plan de Acción Local a auditar ({pais_nombre}):
    {plan_local}
    
    Tu respuesta debe estar en formato JSON con las claves: 'coherencia_porcentaje', 'inconsistencias', y 'sugerencias'.
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_ia]
        )
        
        ia_response_text = response.text.strip()
        ia_json = json.loads(ia_response_text)
        
        return jsonify(ia_json)

    except Exception as e:
        return jsonify({
            "error": "Error al procesar la respuesta de la IA. Intenta con un prompt más claro.",
            "detalle_tecnico": str(e),
            "texto_bruto_ia": response.text if 'response' in locals() else None
        }), 500


@app.route('/api/ia/informe', methods=['GET'])
def generador_informe_ejecutivo():
    """Funcionalidad I: Genera un informe ejecutivo usando los Scorecards."""
    
    session = Session()
    metricas = calcular_scorecards(session)
    session.close()

    metricas_json_str = json.dumps(metricas, indent=2)

    prompt_ia = f"""
    Eres un Analista Estratégico de Recursos Humanos. Genera un informe ejecutivo de alto nivel, conciso y profesional, basado en las métricas de Scorecards proporcionadas (Compliance y Cultura) para 5 filiales globales.
    
    Instrucciones:
    1. Título: "Informe Ejecutivo de Despliegue Global de RRHH (FASE: [Indicar el foco principal])"
    2. Resumen Ejecutivo (1 párrafo): Destaca el progreso promedio y el mayor riesgo/oportunidad.
    3. Benchmarking de Compliance (FASE A):
        - Identifica el país con MEJOR y PEOR Scorecard de Compliance.
        - Analiza las implicaciones del PEOR caso (ej. "Riesgo legal alto en [País]").
    4. Benchmarking Cultural (FASE B):
        - Identifica el país con la MÁXIMA y MÍNIMA Alineación Cultural (IAC).
        - Sugiere una acción estratégica clave para el país con la MÍNIMA alineación, enfocada en la uniformidad cultural.
    5. Conclusión y Próximos Pasos (1 punto): Recomendación principal para la Dirección.

    Métricas de Scorecards de los 5 Países (en JSON):
    {metricas_json_str}
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_ia]
        )
        
        return jsonify({"informe_ejecutivo": response.text})

    except Exception as e:
        return jsonify({"error": f"Error al generar el informe: {str(e)}", "detalle": metricas}), 500

# ===============================================
# 4. API DE DATOS (Para que el Front-end pida la información)
# ===============================================

@app.route('/', methods=['GET'])
def index():
    """Ruta principal que sirve el archivo HTML del dashboard."""
    return send_file('index.html') 

@app.route('/api/tareas', methods=['GET'])
def obtener_tareas():
    """API para obtener todas las tareas de todos los países (Funcionalidad A)."""
    session = Session()
    tareas_data = []
    
    for tarea in session.query(Tarea).all():
        tareas_data.append({
            'id': tarea.id,
            'pais': tarea.pais.nombre,
            'bloque': tarea.bloque.nombre,
            'fase': tarea.bloque.fase,
            'descripcion': tarea.descripcion,
            'responsable': tarea.responsable,
            'estado': tarea.estado
        })
    
    session.close()
    return jsonify(tareas_data)

@app.route('/api/metricas', methods=['GET'])
def obtener_metricas():
    """API para obtener los Scorecards (Funcionalidades D, E, F)."""
    session = Session()
    metricas = calcular_scorecards(session)
    session.close()
    return jsonify(metricas)


if __name__ == '__main__':
    # Asegurar que la base de datos y los datos iniciales existan al iniciar la app
    crear_tablas()
    session = Session()
    cargar_datos_iniciales(session)
    session.close()
    
    print("\n\n#####################################################")
    print("  ¡APLICACIÓN DE BACKEND DE RRHH INICIADA! ")
    print("  Abre tu navegador y ve a: http://127.0.0.1:5000/")
    print("  Rutas de API disponibles:")
    print("  - Tareas: /api/tareas")
    print("  - Métricas: /api/metricas")
    print("  - Generador de Informe (IA): /api/ia/informe (GET)")
    print("#####################################################\n")
    
    # COMANDO FINAL DE EJECUCIÓN DEL SERVIDOR
    app.run(debug=True)