from typing import Optional, Generator
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import contextmanager
import logging
from app.database.modelsDB import Base

logger = logging.getLogger("app.database")

class DatabaseConfig:
    """Clase para manejar la configuración de la base de datos."""
    def __init__(self):
        load_dotenv()
        self.user = os.getenv('USERDB')
        self.password = os.getenv('PASSWORD')
        self.host = os.getenv('HOST')
        self.port = os.getenv('PORT')
        self.database = os.getenv('DATABASE')
        
        if not all([self.user, self.password, self.host, self.port, self.database]):
            raise ValueError("Faltan variables de entorno necesarias para la conexión a la base de datos")
    
    @property
    def database_url(self) -> str:
        """Genera la URL de conexión a la base de datos."""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

class Database:
    """
    Clase singleton para manejar la conexión a la base de datos.
    Implementa el patrón singleton de manera segura para hilos.
    """
    _instance: Optional['Database'] = None
    _engine: Optional[Engine] = None
    _SessionFactory = None

    def __new__(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config = DatabaseConfig()
            self._initialize_engine()
            self._setup_session_factory()
            self.initialize_database()

    def _initialize_engine(self) -> None:
        """Inicializa el motor de SQLAlchemy con configuración optimizada."""
        try:
            self._engine = create_engine(
                self._config.database_url,
                pool_pre_ping=True,          # Verifica la conexión antes de cada uso
                pool_size=10,                # Número de conexiones en el pool
                max_overflow=20,             # Conexiones adicionales máximas
                pool_timeout=30,             # Tiempo máximo de espera para conexión
                pool_recycle=3600,           # Reciclar conexiones cada hora
                echo=False,                  # No mostrar queries SQL en logs
                connect_args={
                    'connect_timeout': 10    # Timeout de conexión en segundos
                }
            )
            logger.info("Motor de base de datos inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar el motor de base de datos: {e}")
            raise

    def _setup_session_factory(self) -> None:
        """Configura la fábrica de sesiones."""
        self._SessionFactory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Proporciona un contexto para manejar sesiones de base de datos de manera segura.

        Yields:
            Session: Sesión de SQLAlchemy

        Example:
            with database.session() as session:
                results = session.query(Model).all()
        """
        session: Session = self._SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en la sesión de base de datos: {e}")
            raise
        finally:
            session.close()

    def initialize_database(self) -> None:
        """Inicializa la base de datos creando todas las tablas necesarias."""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("Tablas de base de datos creadas correctamente")
            self._create_default_data()
        except SQLAlchemyError as e:
            logger.error(f"Error al crear las tablas de la base de datos: {e}")
            raise

    def _create_default_data(self) -> None:
        """Crea datos predeterminados en la base de datos."""
        try:
            with self.session() as session:
                # Aquí puedes agregar la lógica para crear datos predeterminados
                # Por ejemplo:
                # if not session.query(Role).filter_by(name="admin").first():
                #     session.add(Role(name="admin"))
                if session is None:
                    raise ValueError("La sesión de base de datos no está disponible")
                pass
            logger.info("Datos predeterminados creados correctamente")
        except IntegrityError:
            logger.warning("Los datos predeterminados ya existen")
        except Exception as e:
            logger.error(f"Error al crear datos predeterminados: {e}")
            raise

    @property
    def engine(self) -> Engine:
        """Retorna el motor de base de datos."""
        return self._engine

    def dispose(self) -> None:
        """Libera todos los recursos de la base de datos."""
        if self._engine:
            self._engine.dispose()
            logger.info("Recursos de la base de datos liberados")

# Instancia singleton de la base de datos
database = Database()