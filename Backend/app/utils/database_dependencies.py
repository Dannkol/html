from typing import Generator
from sqlalchemy.orm import Session
from app.database.database import database

# Dependency para obtener una sesión de base de datos
def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener una sesión de base de datos.
    
    Yields:
        Session: Sesión activa de SQLAlchemy
    """
    session = database._SessionFactory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Dependency para obtener una sesión con transacciones manuales
def get_transactional_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener una sesión de base de datos con manejo manual de transacciones.
    
    Yields:
        Session: Sesión activa de SQLAlchemy
    """
    session = database._SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
