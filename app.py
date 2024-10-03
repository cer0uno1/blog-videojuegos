from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="proyectofinal"
)

@app.route('/', methods=['GET', 'POST'])
def index():
    juegos = []
    if request.method == 'POST':
        search_query = request.form['search']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM videojuegos WHERE nombre LIKE %s", (f"%{search_query}%",))
        juegos = cursor.fetchall()
        cursor.close()
    return render_template('index.html', juegos=juegos)

@app.route('/game/<int:idvideojuego>', methods=['GET', 'POST'])
def detallesJuego(idvideojuego):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM videojuegos WHERE idvideojuegos = %s", (idvideojuego,))
    videojuego = cursor.fetchone()
    
    cursor.execute("SELECT * FROM reseña WHERE videojuegoreseñado = %s", (idvideojuego,))
    reseñas = cursor.fetchall()
    cursor.close()
    
    if request.method == 'POST':
        creador = request.form['creador']
        texto = request.form['contenido']
        cursor = db.cursor()
        cursor.execute("INSERT INTO reseña (videojuegoreseñado, creador, contenido) VALUES (%s, %s, %s)", (idvideojuego, creador, texto))
        db.commit()
        cursor.close()
        return redirect(url_for('detallesJuego', idvideojuego=idvideojuego))
    
    return render_template('juego.html', videojuego=videojuego, reseñas=reseñas)

if __name__ == '__main__':
    app.run(debug=True)
