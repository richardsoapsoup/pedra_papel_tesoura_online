from flask import Flask, render_template, request, redirect, url_for
import threading

app = Flask(__name__)


jogadas = {
    'jogador1': None,
    'jogador2': None
}

lock = threading.Lock()  

def analisar_vitoria(j1, j2):
    if j1 == j2:
        return "Empate!"
    elif (j1 == 'pedra' and j2 == 'tesoura') or \
         (j1 == 'papel' and j2 == 'pedra') or \
         (j1 == 'tesoura' and j2 == 'papel'):
        return "Jogador 1 venceu!"
    else:
        return "Jogador 2 venceu!"

@app.route('/jogar/<jogador>', methods=['GET', 'POST'])
def jogar(jogador):
    if jogador not in ['jogador1', 'jogador2']:
        return "Jogador inválido", 404

    if request.method == 'POST':
        escolha = request.form.get('escolha')
        with lock:
            jogadas[jogador] = escolha

        return redirect(url_for('esperar', jogador=jogador))

    return render_template('jogar.html', jogador=jogador)

@app.route('/esperar/<jogador>')
def esperar(jogador):
    outro = 'jogador1' if jogador == 'jogador2' else 'jogador2'

    if jogadas['jogador1'] and jogadas['jogador2']:
        return redirect(url_for('resultado', jogador=jogador))
    else:
        return render_template('esperar.html')

@app.route('/resultado/<jogador>')
def resultado(jogador):
    j1 = jogadas['jogador1']
    j2 = jogadas['jogador2']
    resultado = analisar_vitoria(j1, j2)

    escolha_propria = j1 if jogador == 'jogador1' else j2
    escolha_adversario = j2 if jogador == 'jogador1' else j1

    return render_template('resultado.html', jogador=jogador,
                           resultado=resultado,
                           sua_escolha=escolha_propria,
                           escolha_adversario=escolha_adversario)

@app.route('/reset')
def reset():
    with lock:
        jogadas['jogador1'] = None
        jogadas['jogador2'] = None
    return redirect(url_for('jogar', jogador='jogador1'))


if __name__ == '__main__':
    app.run(debug=True)

