from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

app = Flask(__name__)

username = 'cer0uno'
password = 'sebakpo1'
host = 'cer0uno.mysql.pythonanywhere-services.com'
database = 'cer0uno$rese-ador'

connection_string = f'mysql+mysqldb://{username}:{password}@{host}/{database}'

engine = create_engine(connection_string)
Session = sessionmaker(bind=engine)
session = Session()


Base = declarative_base()


class Videojuego(Base):
    __tablename__ = 'videojuegos'

    idvideojuegos = Column(Integer, primary_key=True)
    nombre = Column(String)
    añolanzamiento = Column(Integer)
    descripcion = Column(String)
    caratulalink = Column(String)
    screenshotlink = Column(String)

class Reseña(Base):
    __tablename__ = 'reseña'

    idreseña = Column(Integer, primary_key=True)
    videojuegoreseñado = Column(Integer, ForeignKey('videojuegos.idvideojuegos'))
    creador = Column(String)
    contenido = Column(String)
    fechacreado = Column(DateTime, default=datetime.utcnow)

    videojuego = relationship("Videojuego")

@app.route('/', methods=['GET', 'POST'])
def index():
    juegos = []
    if request.method == 'POST':
        search_query = request.form['search']
        juegos = session.query(Videojuego).filter(Videojuego.nombre.like(f"%{search_query}%")).all()
    return render_template('index.html', juegos=juegos)

@app.route('/game/<int:idvideojuego>', methods=['GET', 'POST'])
def detallesJuego(idvideojuego):
    videojuego = session.query(Videojuego).filter(Videojuego.idvideojuegos == idvideojuego).first()
    reseñas = session.query(Reseña).filter(Reseña.videojuegoreseñado == idvideojuego).all()

    if request.method == 'POST':
        creador = request.form['creador']
        texto = request.form['contenido']
        nueva_reseña = Reseña(videojuegoreseñado=idvideojuego, creador=creador, contenido=texto)
        session.add(nueva_reseña)
        session.commit()
        return redirect(url_for('detallesJuego', idvideojuego=idvideojuego))

    return render_template('juego.html', videojuego=videojuego, reseñas=reseñas)

@app.route('/agregar', methods=['GET', 'POST'])
def agregarVideojuego():
    if request.method == 'POST':
        nombre = request.form['nombre']
        añolanzamiento = request.form['añolanzamiento']
        descripcion = request.form['descripcion']
        caratulalink = request.form['caratulalink']
        screenshotlink = request.form['screenshotlink']

        nuevo_videojuego = Videojuego(nombre=nombre, añolanzamiento=añolanzamiento, descripcion=descripcion, caratulalink=caratulalink, screenshotlink=screenshotlink)
        session.add(nuevo_videojuego)
        session.commit()

        return redirect(url_for('index'))

    return render_template('agregarjuego.html')

@app.route('/acercade', methods=['GET'])
def contacto():

    return render_template('acercade.html')

@app.route('/videojuegos')
def listar_videojuegos():
    videojuegos = session.query(Videojuego).all()
    return render_template('listar.html', videojuegos=videojuegos)


if __name__ == '__main__':
    app.run(debug=True)
