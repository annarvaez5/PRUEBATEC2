# models.py
from flask_sqlalchemy import SQLAlchemy
import string
import random

db = SQLAlchemy()

def generar_codigo_acceso(longitud=6):
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

class Partido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo_local_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    equipo_visitante_id = db.Column(db.Integer, db.ForeignKey('equipo.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    resultado_local = db.Column(db.Integer, default=None)
    resultado_visitante = db.Column(db.Integer, default=None)
    finalizado = db.Column(db.Boolean, default=False)

    equipo_local = db.relationship('Equipo', foreign_keys=[equipo_local_id])
    equipo_visitante = db.relationship('Equipo', foreign_keys=[equipo_visitante_id])

class SesionApuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_sesion = db.Column(db.String(100), nullable=False)
    codigo_acceso = db.Column(db.String(6), unique=True, nullable=False, default=generar_codigo_acceso)
    partido_id = db.Column(db.Integer, db.ForeignKey('partido.id'), nullable=False)

    partido = db.relationship('Partido')
    apuestas = db.relationship('Apuesta', backref='sesion', lazy=True, cascade="all, delete-orphan")

class Apuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(80), nullable=False)
    prediccion_local = db.Column(db.Integer, nullable=False)
    prediccion_visitante = db.Column(db.Integer, nullable=False)
    sesion_id = db.Column(db.Integer, db.ForeignKey('sesion_apuesta.id'), nullable=False)