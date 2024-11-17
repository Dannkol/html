from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    location = Column(String(100), nullable=False)
    longitud = Column(Float, nullable=False)
    latitud = Column(Float, nullable=False)

    # Relación con Usuario
    usuarios = relationship("Usuario_Esp", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name})>"

class Esp(Base):
    __tablename__ = 'esp'

    id = Column(Integer, primary_key=True, autoincrement=True)
    identification = Column(String(50), unique=True, nullable=False)  # MAC o serial único
    json_sensores = Column(JSON, nullable=True)  # Datos de sensores en formato JSON

    # Relación con Usuario
    usuarios = relationship("Usuario_Esp", back_populates="esp")

    def __repr__(self):
        return f"<Esp(id={self.id}, identification={self.identification})>"

class Usuario_Esp(Base):
    __tablename__ = 'usuario_esp'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_user = Column(Integer, ForeignKey('user.id'), nullable=False)
    id_esp = Column(Integer, ForeignKey('esp.id'), nullable=False)

    # Relación con User y Esp
    user = relationship("User", back_populates="usuarios")
    esp = relationship("Esp", back_populates="usuarios")

    def __repr__(self):
        return f"<Usuario_Esp(id={self.id}, id_user={self.id_user}, id_esp={self.id_esp})>"
