from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

jogadas = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('escolha')
def receber_escolha(data):
    jogador = data['jogador']
    escolha = data['escolha']
    jogadas[jogador] = escolha

    if len(jogadas) == 2:
        resultado = analisar_vitoria(jogadas['jogador1'], jogadas['jogador2'])
        emit('resultado', {
            'jogador1': jogadas['jogador1'],
            'jogador2': jogadas['jogador2'],
            'resultado': resultado
        }, broadcast=True)
        jogadas.clear()  

def analisar_vitoria(j1, j2):
    if j1 == j2:
        return 'Empate!'
    elif (j1 == 'pedra' and j2 == 'tesoura') or \
         (j1 == 'papel' and j2 == 'pedra') or \
         (j1 == 'tesoura' and j2 == 'papel'):
        return 'Jogador 1 venceu!'
    else:
        return 'Jogador 2 venceu!'

if __name__ == '__main__':
    socketio.run(app)
