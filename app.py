from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key_de_lobby!'
socketio = SocketIO(app)


rooms = {}



def generate_room_code():
    """Gera um código de sala único de 4 letras maiúsculas."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if code not in rooms:
            return code

def analisar_vitoria(j1, j2):
    if j1 == j2:
        return 'Empate!'
    elif (j1 == 'pedra' and j2 == 'tesoura') or \
         (j1 == 'papel' and j2 == 'pedra') or \
         (j1 == 'tesoura' and j2 == 'papel'):
        return 'Jogador 1 venceu!'
    else:
        return 'Jogador 2 venceu!'


@app.route('/')
def index():
    
    return render_template('lobby.html')

@app.route('/create', methods=['POST'])
def create_lobby():
    code = generate_room_code()
   
    rooms[code] = {'players': {}, 'jogadas': {}}
    return redirect(url_for('game_lobby', code=code))

@app.route('/join', methods=['POST'])
def join_lobby():
   
    code = request.form.get('code', '').upper()
    if code in rooms:
        return redirect(url_for('game_lobby', code=code))
    return render_template('lobby.html', error='Lobby não encontrado ou cheio.')

@app.route('/game/<string:code>')
def game_lobby(code):
    
    if code in rooms:
        return render_template('game.html', code=code)
    return redirect(url_for('index'))




@socketio.on('connect')
def handle_connect():
   
    pass

@socketio.on('join_room_request')
def join_game_room(data):
    code = data.get('code')
    
    if code not in rooms:
        emit('error', {'message': 'Sala inexistente.'})
        return

    room_data = rooms[code]
    sid = request.sid

    
    player_role = None
    if 'jogador1' not in room_data['players']:
        player_role = 'jogador1'
    elif 'jogador2' not in room_data['players']:
        player_role = 'jogador2'
    
    
    if player_role:
        
        room_data['players'][player_role] = sid
        join_room(code)
        
        emit('room_joined', {'role': player_role, 'code': code}, room=sid)
        print(f"[{code}] {player_role} ({sid}) entrou na sala.")
        
       
        if len(room_data['players']) == 2:
            emit('start_game', {'message': 'O jogo vai começar!'}, room=code)
    else:
        emit('error', {'message': 'Sala cheia.'}, room=sid)


@socketio.on('escolha')
def receber_escolha(data):
    room_code = data['code']
    jogador = data['jogador']
    escolha = data['escolha']
    
    room = rooms.get(room_code)
    if not room or len(room['players']) < 2:
        return 

    
    room['jogadas'][jogador] = escolha
    
   
    emit('play_registered', {'jogador': jogador, 'message': f'{jogador} jogou!'}, room=room_code)

    if len(room['jogadas']) == 2:
        j1 = room['jogadas'].get('jogador1')
        j2 = room['jogadas'].get('jogador2')
        
        resultado = analisar_vitoria(j1, j2)
        
        
        emit('resultado', {
            'jogador1': j1,
            'jogador2': j2,
            'resultado': resultado
        }, room=room_code)
        
        
        room['jogadas'].clear()

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    
    for code, room_data in list(rooms.items()):
        if room_data['players'].get('jogador1') == sid:
            del room_data['players']['jogador1']
            emit('player_left', {'message': 'Jogador 1 desconectou. O jogo acabou!'}, room=code)
            del rooms[code] 
            print(f"[{code}] Sala removida. Jogador 1 desconectou.")
            return 
        elif room_data['players'].get('jogador2') == sid:
            del room_data['players']['jogador2']
            emit('player_left', {'message': 'Jogador 2 desconectou. O jogo acabou!'}, room=code)
            
            print(f"[{code}] Jogador 2 desconectou.")
            return

if __name__ == '__main__':
    socketio.run(app, debug=True)