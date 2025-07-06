# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, join_room, emit
from models import db, Equipo, Partido, SesionApuesta, Apuesta
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apuestas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app)

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    partidos_hoy = Partido.query.filter(db.func.date(Partido.fecha_hora) == date.today(), Partido.finalizado == False).all()
    return render_template('index.html', partidos=partidos_hoy)

@app.route('/crear_sesion', methods=['POST'])
def crear_sesion():
    nombre_sesion = request.form.get('nombre_sesion')
    partido_id = request.form.get('partido_id')
    
    if not nombre_sesion or not partido_id:
        flash('Faltan datos para crear la sesión.', 'danger')
        return redirect(url_for('index'))
        
    nueva_sesion = SesionApuesta(nombre_sesion=nombre_sesion, partido_id=partido_id) #type: ignore
    db.session.add(nueva_sesion)
    db.session.commit()
    
    flash(f"Sesión '{nombre_sesion}' creada. Código de acceso: {nueva_sesion.codigo_acceso}", 'success')
    return redirect(url_for('sesion', codigo_acceso=nueva_sesion.codigo_acceso))

@app.route('/sesion/<codigo_acceso>')
def sesion(codigo_acceso):
    sesion_actual = SesionApuesta.query.filter_by(codigo_acceso=codigo_acceso).first_or_404()
    
    ganadores = None
    # Verificamos SI EL PARTIDO YA TERMINÓ al cargar la página
    if sesion_actual.partido.finalizado:
        partido_final = sesion_actual.partido
        ganadores = [
            apuesta.nombre_usuario for apuesta in sesion_actual.apuestas
            if apuesta.prediccion_local == partido_final.resultado_local and \
               apuesta.prediccion_visitante == partido_final.resultado_visitante
        ]
        
    return render_template('sesion.html', sesion=sesion_actual, ganadores=ganadores)

@app.route('/admin')
def admin():
    equipos = Equipo.query.order_by(Equipo.nombre).all()
    partidos_hoy = Partido.query.filter(db.func.date(Partido.fecha_hora) == date.today()).all()
    return render_template('admin.html', equipos=equipos, partidos=partidos_hoy)

@app.route('/admin/cargar_partido', methods=['POST'])
def cargar_partido():
    local_id = request.form.get('equipo_local')
    visitante_id = request.form.get('equipo_visitante')
    hora_partido = request.form.get('hora_partido') # "HH:MM"

    if local_id == visitante_id:
        flash('Los equipos deben ser diferentes.', 'danger')
        return redirect(url_for('admin'))
        
    fecha_hora_str = f"{date.today().strftime('%Y-%m-%d')} {hora_partido}"
    fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
    
    nuevo_partido = Partido(equipo_local_id=local_id, equipo_visitante_id=visitante_id, fecha_hora=fecha_hora_obj) #type: ignore
    db.session.add(nuevo_partido)
    db.session.commit()
    
    flash('Partido cargado exitosamente.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/actualizar_resultado', methods=['POST'])
def actualizar_resultado():
    partido_id = request.form.get('partido_id')
    res_local = request.form.get('resultado_local')
    res_visitante = request.form.get('resultado_visitante')

    partido = db.session.get(Partido, partido_id)
    if partido and res_local is not None and res_visitante is not None:
        partido.resultado_local = int(res_local)
        partido.resultado_visitante = int(res_visitante)
        partido.finalizado = True
        db.session.commit()
        
        # Notificar a las sesiones de este partido
        sesiones_afectadas = SesionApuesta.query.filter_by(partido_id=partido.id).all()
        for sesion in sesiones_afectadas:
            ganadores = [
                apuesta.nombre_usuario for apuesta in sesion.apuestas 
                if apuesta.prediccion_local == partido.resultado_local and \
                   apuesta.prediccion_visitante == partido.resultado_visitante
            ]
            socketio.emit('partido_finalizado', {'ganadores': ganadores}, room=sesion.codigo_acceso) #type: ignore

        flash('Resultado actualizado.', 'success')
    else:
        flash('Error al actualizar.', 'danger')
        
    return redirect(url_for('admin'))


# --- LÓGICA DE SOCKET.IO PARA TIEMPO REAL ---

@socketio.on('join')
def on_join(data):
    codigo_acceso = data['room']
    join_room(codigo_acceso)
    emit('status', {'msg': 'Te has unido a la sesión.'})

@socketio.on('registrar_apuesta')
def handle_apuesta(data):
    codigo_acceso = data['room']
    sesion_actual = SesionApuesta.query.filter_by(codigo_acceso=codigo_acceso).first()
    
    if sesion_actual and not sesion_actual.partido.finalizado:
        nueva_apuesta = Apuesta(
            nombre_usuario=data['nombre'], #type: ignore
            prediccion_local=int(data['prediccion_local']), #type: ignore
            prediccion_visitante=int(data['prediccion_visitante']), #type: ignore
            sesion_id=sesion_actual.id #type: ignore
        )
        db.session.add(nueva_apuesta)
        db.session.commit()
        
        apuestas_actualizadas = [{
            'nombre': a.nombre_usuario, 
            'prediccion': f"{a.prediccion_local} - {a.prediccion_visitante}"
        } for a in sesion_actual.apuestas]
        
        emit('actualizar_apuestas', {'apuestas': apuestas_actualizadas}, room=codigo_acceso) #type: ignore

# --- INICIALIZACIÓN Y COMANDOS ---
def inicializar_equipos():
    if Equipo.query.count() == 0:
        print("Cargando equipos iniciales...")
        equipos = [
            'Atlético Nacionalpao', 'Millonarios', 'América de Cali', 'Deportivo Cali',
            'Junior de Barranquilla', 'Independiente Santa Fe', 'Once Caldas', 'Deportes Tolima',
            'Real Madrid', 'FC Barcelona', 'Atlético de Madrid', 'Sevilla FC',
            'Manchester United', 'Liverpool FC', 'Chelsea FC', 'Arsenal FC',
            'Bayern München', 'Borussia Dortmund', 'AC Milan', 'Inter Milan','EQUIPO PAOLA']
        for nombre in equipos:
            db.session.add(Equipo(nombre=nombre)) #type: ignore
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        inicializar_equipos()
    socketio.run(app, debug=True)