
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

# 1. Configuración de la Base de Datos
# Esto crea el archivo de la base de datos (tareas.db)
ENGINE = create_engine('sqlite:///tareas.db')
Session = sessionmaker(bind=ENGINE)
Base = declarative_base()

# 2. Definición de las Tablas (El Esquema de Datos)

# Tabla 1: Paises (Las 5 filiales)
class Pais(Base):
    __tablename__ = 'paises'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    tareas = relationship("Tarea", back_populates="pais")

# Tabla 2: Bloques de Acción (Los 10 bloques del plan único)
class BloqueAccion(Base):
    __tablename__ = 'bloques_accion'
    id = Column(Integer, primary_key=True)
    fase = Column(String, nullable=False) # FASE A (Compliance) o FASE B (Cultura)
    nombre = Column(String, nullable=False) 
    tareas = relationship("Tarea", back_populates="bloque")

# Tabla 3: Tareas (El registro de lo que hay que hacer por país)
class Tarea(Base):
    __tablename__ = 'tareas'
    id = Column(Integer, primary_key=True)
    
    # Claves foráneas (para saber a qué país y bloque pertenece la tarea)
    pais_id = Column(Integer, ForeignKey('paises.id'))
    bloque_id = Column(Integer, ForeignKey('bloques_accion.id'))
    
    # Detalles de la Tarea
    descripcion = Column(String, nullable=False)
    responsable = Column(String, default="Sin asignar")
    estado = Column(String, default="Pendiente") # Opciones: Pendiente, En Curso, Completado
    documentacion_link = Column(String)
    
    pais = relationship("Pais", back_populates="tareas")
    bloque = relationship("BloqueAccion", back_populates="tareas")

# Tabla 4: Valores Globales (Necesaria para la IA de Consistencia Cultural)
class ValorGlobal(Base):
    __tablename__ = 'valores_globales'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False) 
    definicion = Column(String, nullable=False) 
    
# Función para crear las tablas
def crear_tablas():
    Base.metadata.create_all(ENGINE)
    # print("Tablas de la base de datos creadas exitosamente.")

# Función para cargar los datos iniciales (Países, Bloques y una Tarea Replicada)
def cargar_datos_iniciales(session):
    # Definición de los 5 países
    paises_nombres = ["España", "Italia", "Polonia", "Bélgica", "Chile"]
    paises = [Pais(nombre=nombre) for nombre in paises_nombres]
    
    # Definición de los 10 bloques de acción (idénticos al plan único)
    bloques_data = [
        {"fase": "A", "nombre": "1. Contratación y Onboarding"},
        {"fase": "A", "nombre": "2. Funciones y Responsabilidades"},
        {"fase": "A", "nombre": "3. Salarios y Beneficios"},
        {"fase": "A", "nombre": "4. Jornada y Ausencias"},
        {"fase": "A", "nombre": "5. Seguridad y Salud Laboral"},
        {"fase": "A", "nombre": "6. Protección de Datos (GDPR)"},
        {"fase": "B", "nombre": "7. Diversidad, Igualdad y Ética"},
        {"fase": "B", "nombre": "8. Desarrollo y Talento"},
        {"fase": "B", "nombre": "9. Gobernanza"},
        {"fase": "B", "nombre": "10. Cultura y Clima Laboral"},
    ]
    
    # Cargar datos solo si las tablas están vacías
    if session.query(Pais).count() == 0:
        session.add_all(paises)
        session.add_all([BloqueAccion(**data) for data in bloques_data])

        # Ejemplo de Tarea Maestra para el Bloque 1
        tarea_ejemplo = "Verificar la legalidad de los modelos de contrato locales."
        bloque_1 = session.query(BloqueAccion).filter_by(nombre="1. Contratación y Onboarding").first()
        
        # REPLICACIÓN DE LA TAREA EN LOS 5 PAÍSES
        if bloque_1:
            paises_en_db = session.query(Pais).all()
            for pais in paises_en_db:
                tarea_nueva = Tarea(
                    descripcion=tarea_ejemplo,
                    pais=pais,
                    bloque=bloque_1,
                    responsable=f"Gestor RRHH {pais.nombre}",
                    estado="Pendiente"
                )
                session.add(tarea_nueva)

        # Cargar los Valores Globales (Núcleo de tu Fase B)
        valores = [
            {"nombre": "Integridad", "definicion": "Actuar con honestidad, transparencia y ética inquebrantable en todas las decisiones y relaciones laborales."},
            {"nombre": "Colaboración", "definicion": "Fomentar equipos interfuncionales y transfronterizos, priorizando el éxito colectivo sobre el individual."},
            {"nombre": "Innovación", "definicion": "Buscar constantemente mejores maneras de trabajar y promover la mejora continua en todos los procesos de RRHH."},
        ]
        session.add_all([ValorGlobal(**v) for v in valores])
        
        session.commit()
        print("\n✅ Base de datos (tareas.db) creada y datos iniciales cargados con éxito.")

    else:
        print("\nBase de datos ya existente. Saltando la carga de datos iniciales.")


if __name__ == '__main__':
    # Si ejecutas este archivo, se crean las tablas y se cargan los datos.
    crear_tablas()
    
    session = Session()
    cargar_datos_iniciales(session)
    session.close()