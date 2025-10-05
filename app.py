from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    """Analisa a jogada e retorna 'jogador1', 'jogador2' ou 'Empate'."""
    if j1 == j2:
        return 'Empate'
    elif (j1 == 'pedra' and j2 == 'tesoura') or \
         (j1 == 'papel' and j2 == 'pedra') or \
         (j1 == 'tesoura' and j2 == 'papel'):
        return 'jogador1'
    else:
        return 'jogador2'



@app.route('/')
def index():
    
    return render_template('lobby.html')

@app.route('/create', methods=['POST'])
def create_lobby():
    
    nome = request.form.get('nome', '').strip() or 'Jogador 1'

    is_private = request.form.get('is_private') is not None
    
    
    code = generate_room_code()

    session['nome_temp'] = nome
    
    rooms[code] = {
        'players': {}, 
        'jogadas': {}, 
        'nomes': {}, 
        'is_private': is_private, 
        'youtube_queue': [], 
        'youtube_play_time': 0,
     
        'score': {
            'jogador1': {'vitorias': 0, 'derrotas': 0},
            'jogador2': {'vitorias': 0, 'derrotas': 0}
        }
    }
   
    return redirect(url_for('game_lobby', code=code))

@app.route('/join', methods=['POST'])
def join_lobby():
    
    code = request.form.get('code', '').upper()
    
    nome = request.form.get('nome', '').strip() or 'Convidado' 
    
    if code in rooms:
        session['nome_temp'] = nome 
        return redirect(url_for('game_lobby', code=code))
    return render_template('lobby.html', error='Lobby não encontrado ou cheio.')

@app.route('/lobbies')
def list_lobbies_page():
   
    
    available = []
    
   
    for code, data in rooms.items():

        if data.get('is_private', False):
            continue

        players_count = len(data['players'])
        
     
        if players_count < 2:
            
          
            player1_name = data['nomes'].get('jogador1', 'Aguardando Nome')

            available.append({
                'code': code,
                'players': players_count,
                'host_name': player1_name
            })

   
    return render_template('lobbies.html', lobbies=available)

@app.route('/set_name', methods=['POST'])
def set_name():
    
    
   
    nome = request.form.get('nome', '').strip() or 'Convidado'
    
    
    code = session.pop('room_code_temp', None)
    
    if code and code in rooms:
       
        session['nome_temp'] = nome
       
        return redirect(url_for('game_lobby', code=code))
        
   
    return redirect(url_for('index'))

@app.route('/nome_prompt')
def nome_prompt():
   
    
    if 'room_code_temp' in session:
        return render_template('nome_prompt.html')
    
    return redirect(url_for('index'))

@app.route('/game/<string:code>')
def game_lobby(code):
   
    nome = session.pop('nome_temp', None) 
    
    if code in rooms:
        
        
        if nome is None:
           
            session['room_code_temp'] = code
            return redirect(url_for('nome_prompt'))
        
      
        return render_template('game.html', code=code, nome=nome)
    
   
    return redirect(url_for('index'))




@socketio.on('connect')
def handle_connect():
    pass



@socketio.on('join_room_request')
def handle_join_request(data):
    room_code = data['code']
    nome = data['nome']

    if room_code not in rooms:
        emit('error', {'message': 'Sala não encontrada.'})
        return

    room = rooms[room_code]
    
    
    if 'jogador1' not in room['players']:
        JOGADOR_ID = 'jogador1'
    elif 'jogador2' not in room['players']:
        JOGADOR_ID = 'jogador2'
    else:
        emit('error', {'message': 'Sala cheia.'})
        return

    room['players'][JOGADOR_ID] = request.sid
    room['nomes'][JOGADOR_ID] = nome
    join_room(room_code)
    
    emit('room_joined', {'role': JOGADOR_ID, 'nome': nome})

    
    if 'jogador1' in room['players'] and 'jogador2' in room['players']:
        j1_nome = room['nomes']['jogador1']
        j2_nome = room['nomes']['jogador2']
        
        
        emit('start_game', {'j1_nome': j1_nome, 'j2_nome': j2_nome}, room=room_code)
        
        
        emit('receive_message', {'nome': 'Sistema', 'message': f'{j2_nome} entrou na sala! O jogo começou.'}, room=room_code)
    else:
        
        emit('receive_message', {'nome': 'Sistema', 'message': f'{nome} entrou na sala. Aguardando outro jogador...'}, room=room_code)
        
    
    current_queue = room.get('youtube_queue', [])
    
    if current_queue:
       
        emit('queue_updated', {'queue': current_queue}, room=request.sid)
        
       
        current_time = room.get('youtube_play_time', 0) 
        
        
        current_video_id = current_queue[0]['id']
        emit('play_next_video', {'youtube_id': current_video_id, 'start_time': current_time}, room=request.sid)

    print(f"{nome} ({JOGADOR_ID}) juntou-se à sala {room_code}")

@socketio.on('send_message')
def handle_chat_message(data):
    room_code = data['code']
    jogador_id = data['jogador']
    message = data['message']
    
    room = rooms.get(room_code)
    if not room:
        return
        
   
    nome_remetente = room['nomes'].get(jogador_id, 'Desconhecido')
    
    
    nome_j1 = room['nomes'].get('jogador1', 'Jogador 1')
    nome_j2 = room['nomes'].get('jogador2', 'Jogador 2')
    
    if nome_j1.lower() == nome_j2.lower():
        if jogador_id == 'jogador1':
            nome_remetente = f"{nome_remetente} (1)"
        elif jogador_id == 'jogador2':
            nome_remetente = f"{nome_remetente} (2)"

   
    emit('receive_message', {
        'nome': nome_remetente,
        'message': message
    }, room=room_code)
    
    print(f"[{room_code}] Chat - {nome_remetente}: {message}")


@socketio.on('add_to_queue')
def add_video_to_queue(data):
    room_code = data['code']
    youtube_id = data['youtube_id']
    title = data['title']
    jogador_id = data['jogador']
    
    room = rooms.get(room_code)
    if not room:
        return

    nome_solicitante = room['nomes'].get(jogador_id, 'Convidado')
    
    video_info = {
        'id': youtube_id,
        'title': title,
        'added_by': nome_solicitante
    }
    
    room['youtube_queue'].append(video_info)
    
  
    emit('queue_updated', {'queue': room['youtube_queue']}, room=room_code)
    
   
    if len(room['youtube_queue']) == 1:
        emit('play_next_video', {'youtube_id': youtube_id}, room=room_code)
    
    print(f"[{room_code}] Vídeo adicionado: {title} por {nome_solicitante}")

@socketio.on('video_ended')
def handle_video_ended(data):
    room_code = data['code']
    room = rooms.get(room_code)
    if not room:
        return
    
   
    if room['youtube_queue']:
      
        room['youtube_queue'].pop(0) 
        
       
        emit('queue_updated', {'queue': room['youtube_queue']}, room=room_code)
        
     
        if room['youtube_queue']:
            next_video_id = room['youtube_queue'][0]['id']
           
            emit('play_next_video', {'youtube_id': next_video_id}, room=room_code)


@socketio.on('video_error')
def handle_video_error(data):
    room_code = data['code']
    room = rooms.get(room_code)
    if not room:
        return

   
    if room['youtube_queue']:
        
     
        problematic_video = room['youtube_queue'][0].get('title', 'Vídeo Desconhecido')
        print(f"[{room_code}] ERRO DE REPRODUÇÃO: O vídeo '{problematic_video}' será removido da fila e o próximo será reproduzido.")

        room['youtube_queue'].pop(0) 

     
        emit('queue_updated', {'queue': room['youtube_queue']}, room=room_code)

     
        if room['youtube_queue']:

            
            next_video_id = room['youtube_queue'][0]['id']
            room['youtube_play_time'] = 0 
            emit('play_next_video', {'youtube_id': next_video_id, 'start_time': 0}, room=room_code)
        else:
            print(f"[{room_code}] Fila de reprodução vazia.")


@socketio.on('sync_play_pause')
def sync_play_pause(data):
    room_code = data['code']
    state = data['state'] 
    current_time = data['time']
    
    room = rooms.get(room_code)
    if not room:
        return
        
    
    room['youtube_play_time'] = current_time
    
    
    emit('player_sync_command', {'state': state, 'time': current_time}, room=room_code, include_self=False)
    
    print(f"[{room_code}] Sincronização: {state.upper()} no tempo {current_time:.2f}s.")                                        


@socketio.on('escolha')
def receber_escolha(data):
    room_code = data['code']
    jogador = data['jogador'] 
    escolha = data['escolha']
    
    room = rooms.get(room_code)
    if not room or len(room['players']) < 2:
        return 
    
    nome_jogador = room['nomes'].get(jogador, jogador)

    room['jogadas'][jogador] = escolha
    
    
    emit('play_registered', {'jogador_id': jogador, 'nome': nome_jogador, 'message': f'{nome_jogador} jogou!'}, room=room_code)

    if len(room['jogadas']) == 2:
        j1_escolha = room['jogadas'].get('jogador1')
        j2_escolha = room['jogadas'].get('jogador2')
        
        vencedor_id = analisar_vitoria(j1_escolha, j2_escolha) 
        nome_j1 = room['nomes'].get('jogador1', 'Jogador 1')
        nome_j2 = room['nomes'].get('jogador2', 'Jogador 2')
        
        nomes_sao_iguais = nome_j1.lower() == nome_j2.lower()
        
        if nomes_sao_iguais:
            nome_j1_display = f"{nome_j1} (1)"
            nome_j2_display = f"{nome_j2} (2)"
        else:
            nome_j1_display = nome_j1
            nome_j2_display = nome_j2
            
        
       
        if vencedor_id == 'jogador1':
            room['score']['jogador1']['vitorias'] += 1
            room['score']['jogador2']['derrotas'] += 1
            mensagem_resultado = f"{nome_j1_display} venceu!"
        elif vencedor_id == 'jogador2':
            room['score']['jogador2']['vitorias'] += 1
            room['score']['jogador1']['derrotas'] += 1
            mensagem_resultado = f"{nome_j2_display} venceu!"
        else:
            mensagem_resultado = 'Empate!'
      

        
        emit('resultado', {
            
            'jogador1_nome': nome_j1_display, 
            'jogador2_nome': nome_j2_display, 
            'j1_escolha': j1_escolha,
            'j2_escolha': j2_escolha,
            'resultado': mensagem_resultado, 
            'score': room['score']          
        }, room=room_code)
        
        room['jogadas'].clear()

@socketio.on('leave_room_request')
def handle_leave_request(data):
    
    room_code = data.get('code')
    
    
    leave_room(room_code)
    
  
    socketio.disconnect(sid=request.sid, silent=False) 
    
    print(f"[{room_code}] Usuário ({request.sid}) saiu da sala manualmente.")

       

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    
    for code, room_data in list(rooms.items()):
        
       
        if room_data['players'].get('jogador1') == sid:
            nome_j1 = room_data['nomes'].get('jogador1', 'Jogador 1')
            
            
            emit('player_left', {'message': f'{nome_j1} (Anfitrião) desconectou. O jogo e a sala acabaram!'}, room=code)
            
            del rooms[code] 
            print(f"[{code}] Sala removida. {nome_j1} desconectou.")
            return 
        
      
        elif room_data['players'].get('jogador2') == sid:
            nome_j2 = room_data['nomes'].get('jogador2', 'Jogador 2')
            
           
            if 'jogador2' in room_data['players']:
                 del room_data['players']['jogador2']
            if 'jogador2' in room_data['nomes']:
                 del room_data['nomes']['jogador2']
            if 'jogador2' in room_data['jogadas']:
                 del room_data['jogadas']['jogador2']
                 
          
            emit('opponent_disconnected', {
                'message': f'{nome_j2} desconectou. Você está aguardando um novo oponente.',
                'opponent_name': 'Aguardando...'
            }, room=room_data['players'].get('jogador1'))
            
            print(f"[{code}] {nome_j2} desconectou. Jogo esperando novo J2.")
            return

if __name__ == '__main__':
    
    socketio.run(app, debug=True, host='0.0.0.0')