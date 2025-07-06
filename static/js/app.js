// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const roomCode = document.body.dataset.roomCode;

    socket.on('connect', () => {
        socket.emit('join', { room: roomCode });
    });

    socket.on('status', (data) => {
        console.log(data.msg);
    });

    const formApuesta = document.getElementById('form-apuesta');
    formApuesta.addEventListener('submit', (e) => {
        e.preventDefault();
        const nombre = document.getElementById('nombre_usuario').value;
        const predLocal = document.getElementById('prediccion_local').value;
        const predVisitante = document.getElementById('prediccion_visitante').value;

        if(nombre && predLocal && predVisitante) {
            socket.emit('registrar_apuesta', {
                room: roomCode,
                nombre: nombre,
                prediccion_local: predLocal,
                prediccion_visitante: predVisitante
            });
            formApuesta.reset();
        }
    });

    socket.on('actualizar_apuestas', (data) => {
        const lista = document.getElementById('lista-apuestas');
        lista.innerHTML = ''; // Limpiar lista
        data.apuestas.forEach(apuesta => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = `${apuesta.nombre}: ${apuesta.prediccion}`;
            lista.appendChild(li);
        });
    });

    socket.on('partido_finalizado', (data) => {
        const divGanadores = document.getElementById('ganadores');
        divGanadores.innerHTML = `<h3>Partido Finalizado!</h3>`;
        if (data.ganadores.length > 0) {
            divGanadores.innerHTML += `<p class="alert alert-success">Ganador(es): ${data.ganadores.join(', ')}</p>`;
        } else {
            divGanadores.innerHTML += `<p class="alert alert-warning">No hubo ganadores.</p>`;
        }
        document.getElementById('form-apuesta').style.display = 'none';
    });
});