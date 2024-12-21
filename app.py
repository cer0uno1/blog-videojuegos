from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from functools import wraps
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# Crea la aplicación web utilizando Flask.
app = Flask(__name__)

#
app.secret_key = 'cer0uno'

# Credenciales de la base de datos.
username = 'root'
password = 'root'
host = 'localhost'
database = 'pfinal'

# Utilizamos las credenciales para conectarnos a la base de datos.
connection_string = f'mysql+mysqldb://{username}:{password}@{host}/{database}'
engine = create_engine(connection_string)
Session = sessionmaker(bind=engine)
db_session = Session()

# Base declarativa, utilizada para definir tablas y modelos.
Base = declarative_base()

# Utilizando la base, creamos una clase para cada tabla. Esta clase utilizará la estructura de su respectiva tabla
class Genero(Base):
    __tablename__ = 'generos'
    idgeneros = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)

class Dispositivo(Base):
    __tablename__ = 'dispositivos'
    iddispositivos = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)

# Tabla intermedia utilizada para relacionar cada videojuego con sus géneros.
videojuego_genero = Table('videojuegos_genero', Base.metadata,
    Column('id_videojuego', Integer, ForeignKey('videojuegos.idvideojuegos')),
    Column('id_genero', Integer, ForeignKey('generos.idgeneros'))
)

# Tabla intermedia utilizada para relacionar cada videojeugos con los dispositivos donde están disponible.
videojuego_dispositivo = Table('videojuegos_dispositivo', Base.metadata,
    Column('id_videojuego', Integer, ForeignKey('videojuegos.idvideojuegos')),
    Column('id_dispositivo', Integer, ForeignKey('dispositivos.iddispositivos'))
)

class Videojuego(Base):
    __tablename__ = 'videojuegos'
    idvideojuegos = Column(Integer, primary_key=True)
    nombre = Column(String)
    añolanzamiento = Column(Integer)
    descripcion = Column(String)
    caratulalink = Column(String)
    screenshotlink = Column(String)
    aprobado = Column(Integer, default=0) # Se utiliza un valor booleano para definir cuales videojuegos mostrar.

    # Relación muchos a muchos entre 'videojuego' y 'genero' usando la tabla intermedia 'videojuego_genero'.
    generos = relationship('Genero', secondary=videojuego_genero, backref='videojuegos')
    # Relación muchos a muchos entre 'videojuego' y 'dispositivo' usando la tabla intermedia 'videojuego_dispositivo'.
    dispositivos = relationship('Dispositivo', secondary=videojuego_dispositivo, backref='videojuegos')

class Discusion(Base):
    __tablename__ = 'discusiones'
    iddiscusiones = Column(Integer, primary_key=True)
    videojuegodiscutido = Column(Integer, ForeignKey('videojuegos.idvideojuegos'))
    creador = Column(Integer, ForeignKey('usuario.username'))
    contenido = Column(String)
    fechacreado = Column(DateTime, default=datetime.utcnow)
    aprobado = Column(Integer, default=0) # Se utiliza un valor booleano para definir cuales discusiones mostrar.

    # Relación con la tabla 'Videojuego' para acceder al videojuego asociado a la discusión.
    videojuego = relationship("Videojuego", backref="discusiones")
    # Relación con la tabla 'Respuesta' para mostrar únicamente las respuestas aprobadas.
    respuestas = relationship(
        "Respuesta",
        back_populates="discusion",
        primaryjoin="and_(Respuesta.discusionid == Discusion.iddiscusiones, Respuesta.aprobado == 1)",
    )

class Respuesta(Base):
    __tablename__ = 'respuestas'
    idrespuestas = Column(Integer, primary_key=True)
    discusionid = Column(Integer, ForeignKey('discusiones.iddiscusiones'))
    creador = Column(String)
    contenido = Column(String)
    fechacreado = Column(DateTime, default=datetime.utcnow)
    aprobado = Column(Integer, default=0) # Se utiliza un valor booleano para definir cuales respuestas mostrar.

    # Relación con la tabla 'Discusion', para acceder a la discusión asociada a la respuesta.
    discusion = relationship("Discusion", back_populates="respuestas")
    
# Todos los valores booleanos utilizados tiene como valor por defecto 0, indicando que no deben ser mostrados.
    
class Usuario(Base):
    __tablename__ = 'usuario'
    idusuario = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    bio = Column(String, nullable=False)
    fotoperfil = Column(String)
    esAdmin = Column(Integer, default=0) # Valor booleano que indica si el usuario es administrador.
    baneado = Column(Integer, default=0) # Valor booleano que indica si el usuario está baneado.
    favoritos = relationship(
        "Videojuego", 
        secondary="usuario_juegos_favoritos", 
        backref="usuario_favoritos",
        primaryjoin="Usuario.idusuario == usuario_juegos_favoritos.c.idusuario",
        secondaryjoin="Videojuego.idvideojuegos == usuario_juegos_favoritos.c.idvideojuego"
    )

# Relación muchos a muchos entre 'usuario' y 'videojuego', utilizando la tabla intermedia 'usuario_juegos_favoritos'.
usuario_juegos_favoritos = Table('usuario_juegos_favoritos', Base.metadata,
    Column('idusuario', Integer, ForeignKey('usuario.idusuario')),
    Column('idvideojuego', Integer, ForeignKey('videojuegos.idvideojuegos'))
)

UPLOAD_FOLDER = 'static/uploads' # Se define la carpeta donde se guardarán los archivos subidos por los usuarios.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'} # Se define los tipos de archivos permitidos para subir.

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # Indica la carpeta de subida a la aplicación.
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Crea la carpeta de carga si esta no existe.

# Función usada para verificar que el archivo subido esté permitido.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS # Verifica si el archivo tiene una extensión y si es una de las permitidas.

# Función que protege las funciones que requieran de estar logueado.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login')) # Verifica si 'user_id' está en la sesión. Si no, redirige a la página de login.
        return f(*args, **kwargs) # Si está logueado, prosigue con su funcionamiento normal.
    return decorated_function

# Función que protege las funciones que requieren de ser administrador.
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'esAdmin' not in session or not session['esAdmin']:
            flash('Acceso denegado: no tienes permisos de administrador.', 'error') # Si el usuario no es administrador, se le avisa en un mensaje, y se vuelve al inicio.
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Define la ruta de inicio de la aplicación
@app.route('/', methods=['GET', 'POST'])
def index():
    juegos = [] # Inicia la lista de juegos vacía
    if request.method == 'POST':
        search_query = request.form['search']
        juegos = db_session.query(Videojuego).filter(Videojuego.nombre.like(f"%{search_query}%"), Videojuego.aprobado==1).all() 
        # Realiza una busqueda de los juegos cuyos nombres sean similares a la búsqueda ingresada por el usuario.
        # Selecciona solo los juegos aprobados, luego llena la lista 'juegos' con estos valores.
    return render_template('index.html', juegos=juegos) # Renderiza la plantilla 'index.html' pasando la lista de juegos como contexto.

# Ruta para ver los detalles de un videojuego en especifico.
# La ruta usa el valor dinámico 'idvideojuego', para definir de cual videojuego debe obtener sus datos.
@app.route('/game/<int:idvideojuego>', methods=['GET', 'POST'])
def detallesJuego(idvideojuego):
    # Consulta en la base de datos para obtener el videojuego con el ID proporcionado.
    videojuego = db_session.query(Videojuego).filter(Videojuego.idvideojuegos == idvideojuego).first()
    
    # Consulta para obtener solo las discusiones aprobadas acerca de este videojuego.
    discusiones = db_session.query(Discusion).filter_by(videojuegodiscutido=idvideojuego, aprobado=1).all()
    
    # Obtiene tantos los géneros como los dispositivos asociados al videojuego.
    generos = videojuego.generos
    dispositivos = videojuego.dispositivos
    
    # Al cargar una discusión nueva, se verifica primero que el usuario esté logueado.
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Debes estar logueado para agregar una discusión.', 'warning')
            return redirect(url_for('login'))
        # Si no está logueado, se avisa con un mensaje, y se redirige al ingreso de usuarios.

        # Recupera el nombre de usuario del creador y el contenido de la nueva discusión desde el formulario.
        creador = session['username']
        contenido = request.form['contenido']

        # Crea una nueva instancia de Discusion con los datos proporcionados.
        nueva_discusion = Discusion(
            videojuegodiscutido=idvideojuego, 
            creador=creador, 
            contenido=contenido, 
            aprobado=0
        )
        # Agrega la nueva discusión a la base de datos y confirma los cambios.
        db_session.add(nueva_discusion)
        db_session.commit()

        flash('Tu discusión fue enviada correctamente y está pendiente de aprobación.', 'info')
        return redirect(url_for('detallesJuego', idvideojuego=idvideojuego))
        # Se le avisa al usuario que la nueva discusión está pendiente de aprobación, y se redirige a la página del videojuego

# Renderiza la plantilla 'juego.html' con todos los datos anteriormente mencionados.
    return render_template('juego.html', videojuego=videojuego, discusiones=discusiones, generos=generos, dispositivos=dispositivos)

# Ruta para responder a una discusión específica.
# La URL incluye un parámetro dinámico 'iddiscusion', que identifica la discusión.
@app.route('/discusiones/<int:iddiscusion>/responder', methods=['POST'])
def responder(iddiscusion):
    # Consulta en la base de datos para obtener la discusión con el ID proporcionado.
    discusion = db_session.query(Discusion).filter(Discusion.iddiscusiones == iddiscusion).first()
    
    # Si no se encuentra la discusión, muestra un mensaje de error y redirige al inicio.
    if not discusion:
        flash('La discusión no existe.', 'error')
        return redirect(url_for('index'))

    # Verifica que el usuario esté logueado. Si no lo está, se redirige al ingreso de usuarios.
    if 'user_id' not in session:
        flash('Debes estar logueado para responder a esta discusión.', 'warning')
        return redirect(url_for('login'))

    # Recupera el nombre de usuario del creador y el contenido de la respuesta desde el formulario.
    creador = session['username']
    contenido = request.form['contenido']

    # Crea una nueva instancia de Respuesta con los datos proporcionados.
    nueva_respuesta = Respuesta(
        discusion=discusion, 
        creador=creador, 
        contenido=contenido, 
        aprobado=0
    )
    
    # Agrega la nueva respuesta a la base de datos y confirma los cambios.
    db_session.add(nueva_respuesta)
    db_session.commit()

    # Muestra un mensaje al usuario indicando que la respuesta está pendiente de aprobación.
    flash('Tu respuesta ha sido enviada y está pendiente de aprobación.', 'info')
    
    # Redirige al usuario a la página de detalles del videojuego.
    return redirect(url_for('detallesJuego', idvideojuego=discusion.videojuegodiscutido))

# Ruta para el registro de nuevos usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Recupera el nombre de usuario y la contraseña ingresados en el formulario.
        username = request.form['username']
        password = request.form['password']
        
        # Verifica si el nombre de usuario ya existe en la base de datos.
        usuario_existente = db_session.query(Usuario).filter_by(username=username).first()
        if usuario_existente:
            # Si ya existe, muestra un mensaje de error, y redirige nuevamente al registro
            flash('El nombre de usuario ya está en uso. Por favor, usa otro', 'error')
            return redirect(url_for('register'))

    # Agrega el nuevo usuario a la base de datos y confirma los cambios.
        new_user = Usuario(username=username, password=password)
        db_session.add(new_user)
        db_session.commit()
        
        # Muestra un mensaje indicando que el registro fue exitoso, y que ya puede iniciar sesión.
        flash("Registro exitoso, ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))
    
    return render_template('login.html') # Renderiza la plantilla de login.

# Ruta para el inicio de sesión de usuarios.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Recupera el nombre de usuario y la contraseña ingresados en el formulario.
        username = request.form['username']
        password = request.form['password']

        # Consulta en la base de datos para encontrar un usuario con el nombre de usuario ingresado.
        user = db_session.query(Usuario).filter_by(username=username).first()
        
        if user:
            if user.baneado == 1:  # Verifica si el usuario está baneado
                flash('Tu cuenta ha sido baneada. Por favor, contacta con administración.', 'error')
                return redirect(url_for('login'))  # Redirige al login si está baneado

        # Compara las credenciales del usuario a las obtenidas de la base de datos.
        if user and user.password == password:
            session['user_id'] = user.idusuario
            session['username'] = user.username
            session['esAdmin'] = user.esAdmin
            # Si coinciden, guarda esos datos como la sesión del usuario.
            flash('Bienvenido!', 'success')
            #Se redirige a la página de perfil
            if user.esAdmin:
                return redirect(url_for('profile'))
            else:
                return redirect(url_for('profile'))
        else:
            flash('Usuario o contraseña incorrectos', 'error') # Si no coinciden, se genera un error

    return render_template('login.html') # Renderiza la plantilla de login

# Ruta para editar el perfil del usuario.
@app.route('/perfil', methods=['GET', 'POST'])
@login_required # Requiere que la sesión del usuario haya sido iniciada
def profile():
    user_id = session.get('user_id') # Obtiene el ID del usuario almacenado en la sesión.
    user = db_session.query(Usuario).filter_by(idusuario=user_id).first() # Recupera los datos del usuario desde la base de datos.

    # Si el usuario no existe, muestra un mensaje de error y redirige al inicio.
    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('index'))
    
    # Recupera los videojuegos favoritos del usuario.
    # Relación secundaria a través de la tabla 'usuario_juegos_favoritos'.
    juegos_favoritos = db_session.query(Videojuego).join(usuario_juegos_favoritos).filter(usuario_juegos_favoritos.c.idusuario == user.idusuario).all()
    # Alternativamente, accede a los favoritos directamente desde la relación en el modelo de usuario.
    juegos_favoritos = user.favoritos if user.favoritos else []
    # Recupera todos los videojuegos disponibles en la base de datos.
    all_games = db_session.query(Videojuego).all()

    # Si el usuario envió un formulario para actualizar su perfil.
    if request.method == 'POST':
        # Verifica si el formulario incluye un archivo llamado 'foto'.
        if 'foto' in request.files and request.files['foto']:
            foto = request.files['foto']
            # Valida que el archivo cargado sea una imagen permitida.
            if foto and allowed_file(foto.filename):
                # Genera dinámicamente un nombre para la foto del usuario.
                filename = secure_filename(f"{user.username}_profile.{foto.filename.rsplit('.', 1)[1].lower()}")
                # Se agrega el nuevo nombre de la foto a la ruta del archivo
                foto_path = os.path.join('static', 'uploads', filename)

                # Guarda el archivo en el directorio especificado.
                foto.save(foto_path)

                # Actualiza el valor de la ruta de la foto de perfil al de la nueva imagen
                user.fotoperfil = f'static/uploads/{filename}' 
                db_session.commit()
            else:
                # Si el archivo no es válido, muestra un mensaje de error.
                flash('El archivo no es una imagen válida.', 'error')
        else:
            # Si no se seleccionó ningún archivo, muestra un mensaje de advertencia.
            flash('No se ha seleccionado ninguna foto.', 'warning')

    # Renderiza la plantilla del perfil con los datos del usuario y sus juegos favoritos.
    return render_template('perfil.html', user=user, juegos_favoritos=juegos_favoritos, all_games=all_games)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user_id = session.get('user_id')
    user = db_session.query(Usuario).filter_by(idusuario=user_id).first()

    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('profile'))

    bio = request.form.get('bio')

    user.bio = bio

    db_session.commit()
    flash('Tu perfil ha sido actualizado.', 'success')
    return redirect(url_for('profile'))

# Ruta para actualizar los juegos favoritos del usuario
@app.route('/update_favorites', methods=['POST'])
@login_required # Requiere tener la sesión iniciada
def update_favorites():
    user_id = session.get('user_id') # Obtiene el ID del usuario almacenado en la sesión.
    user = db_session.query(Usuario).filter_by(idusuario=user_id).first() # Recupera el usuario correspondiente desde la base de datos.

    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('profile')) # Si el usuario no existe, muestra un mensaje de error y redirige al perfil.

    # Obtiene la lista de videojuegos seleccionados desde el formulario enviado.
    selected_games = request.form.getlist('favorite_games')

    # Recorre los videojuegos favoritos actuales del usuario.
    # Si un videojuego ya no está en la lista seleccionada, lo elimina de los favoritos.
    for game in user.favoritos:
        if str(game.idvideojuegos) not in selected_games:
            user.favoritos.remove(game)

    # Recorre los IDs de los videojuegos seleccionados.
    # Si un videojuego no está en la lista de favoritos actual, lo añade.
    for game_id in selected_games:
        videojuego = db_session.query(Videojuego).filter_by(idvideojuegos=game_id).first()
        if videojuego and videojuego not in user.favoritos:
            user.favoritos.append(videojuego)

    # Guarda los cambios en la base de datos.
    db_session.commit()
    # Muestra un mensaje de éxito en la acción, y regresa al perfil.
    flash('Tus favoritos han sido actualizados.', 'success')
    return redirect(url_for('profile'))

# Ruta para mostrar el perfil público de un usuario específico basado en su nombre de usuario.
@app.route('/usuario/<username>') # Utiliza el valor dinámico 'username' para referirse a un usuario en especifico.
def perfilusuario(username):
    # Busca al usuario en la base de datos usando el nombre de usuario proporcionado en la URL.
    user = db_session.query(Usuario).filter_by(username=username).first()
    # Si el usuario no existe, muestra un mensaje de error y redirige a la página principal.
    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('index'))
    
    # Renderiza la plantilla del perfil público del usuario con los datos del usuario encontrado.
    return render_template('perfilusuario.html', user=user)

# Ruta para agregar un nuevo videojuego a la base de datos.
@app.route('/agregar', methods=['GET', 'POST'])
def agregarVideojuego():
    # Verifica si el usuario está logueado antes de permitir el acceso a la funcionalidad.
    if 'user_id' not in session:
        flash('Debes estar logueado para poder agregar juegos nuevos', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Obtiene los datos enviados por el usuario desde el formulario.
        nombre = request.form['nombre']
        añolanzamiento = request.form['añolanzamiento']
        descripcion = request.form['descripcion']
        generos_ids = request.form.getlist('generos[]')  # Lista de IDs de géneros seleccionados
        dispositivos_ids = request.form.getlist('dispositivos[]')  # Lista de IDs de dispositivos seleccionados

        
        # Verifica si ya existe un videojuego con el mismo nombre.
        videojuego_existente = db_session.query(Videojuego).filter_by(nombre=nombre).first()
        if videojuego_existente:
            flash('Ya existe un videojuego con este nombre. Por favor, utiliza otro nombre.', 'danger')
            return redirect(url_for('agregarVideojuego'))

        # Variables para almacenar las rutas de los archivos de carátula y captura de pantalla.
        caratula_path = None
        screenshot_path = None

         # Verifica y procesa el archivo de carátula si fue proporcionado.
        if 'caratula' in request.files:
            caratula = request.files['caratula']
            if caratula and allowed_file(caratula.filename):
                # Cambia dinámicamente el nombre de la foto de cáratula, y guarda el archivo.
                filename_caratula = secure_filename(f"{nombre.replace(' ', '_')}-Caratula.{caratula.filename.rsplit('.', 1)[1].lower()}")
                caratula_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_caratula)
                caratula.save(caratula_path)

        # Verifica y procesa el archivo de captura de pantalla si fue proporcionado.
        if 'screenshot' in request.files:
            screenshot = request.files['screenshot']
            if screenshot and allowed_file(screenshot.filename):
                # Cambia dinámicamente el nombre de la foto de captura de pantalla, y guarda el archivo.
                filename_screenshot = secure_filename(f"{nombre.replace(' ', '_')}-Screenshot.{screenshot.filename.rsplit('.', 1)[1].lower()}")
                screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_screenshot)
                screenshot.save(screenshot_path)

        # Crea un nuevo objeto Videojuego con los datos proporcionados por el usuario.
        nuevo_videojuego = Videojuego(
            nombre=nombre,
            añolanzamiento=añolanzamiento,
            descripcion=descripcion,
            caratulalink=caratula_path,
            screenshotlink=screenshot_path
        )
        
        for genero_id in generos_ids:
            genero = db_session.query(Genero).get(genero_id)
            if genero:
                nuevo_videojuego.generos.append(genero)  # Suponiendo una relación many-to-many

        for dispositivo_id in dispositivos_ids:
            dispositivo = db_session.query(Dispositivo).get(dispositivo_id)
            if dispositivo:
                nuevo_videojuego.dispositivos.append(dispositivo)  # Suponiendo una relación many-to-many
        
        # Guarda todos los datos en la base de datos.
        db_session.add(nuevo_videojuego)
        db_session.commit()
        
        # Muestra un mensaje de éxito indicando que el videojuego está pendiente de aprobación.
        flash('El videojuego fue cargado correctamente y está pendiente de aprobación.', 'success')

        return redirect(url_for('index')) # Redirige al usuario a la página principal.

    # Obtiene la lista de géneros y dispositivos para mostrarlos en el formulario.
    generos = db_session.query(Genero).all()
    dispositivos = db_session.query(Dispositivo).all()

    # Renderiza la plantilla del formulario para agregar un nuevo videojuego.
    return render_template('agregarjuego.html', generos=generos, dispositivos=dispositivos)

# Ruta para la página "Acerca de"
@app.route('/acercade', methods=['GET'])
def contacto():
    return render_template('acercade.html')

# Ruta para listar todos los videojuegos aprobados.
@app.route('/videojuegos')
def listar_videojuegos():
    # Consulta todos los videojuegos que han sido aprobados.
    videojuegos = db_session.query(Videojuego).filter_by(aprobado=1).all()
    # Renderiza la plantilla que muestra la lista de videojuegos aprobados.
    return render_template('listar.html', videojuegos=videojuegos)

# Ruta para mostrar el panel de administración, solo accesible para administradores.
@app.route('/admin_dashboard')
@admin_required # Asegura que solo puedan acceder los administradores
def admin_dashboard():
    # Consulta todos los videojuegos, discusiones y respuestas de la base de datos.
    videojuegos = db_session.query(Videojuego).all()
    discusiones = db_session.query(Discusion).all()
    respuestas = db_session.query(Respuesta).all()
    # Renderiza la plantilla del panel de administración, pasando los datos de juegos, discusiones y respuestas.
    return render_template('admin_dashboard.html', juegos=videojuegos, discusiones=discusiones, respuestas=respuestas)
     
# Ruta para cerrar la sesión del usuario o administrador.
@app.route('/logout')
def logout():
    # Elimina las claves de sesión relacionadas con el usuario y el administrador.
    session.pop('admin_logged_in', None)
    session.pop('user_id', None)
    
    # Muestra un mensaje de éxito indicando que la sesión ha sido cerrada.
    flash("Sesión cerrada correctamente", 'success')
    # Redirige al usuario a la página principal después de cerrar sesión.
    return redirect(url_for('index'))

# Ruta para cambiar estado de aprobación
@app.route('/cambiar_estado/<tipo>/<int:id>/<int:estado>', methods=['POST'])
def cambiar_estado(tipo, id, estado):
    # Dependiendo del tipo, obtenemos el elemento correspondiente de la base de datos.
    if tipo == 'videojuego':
        item = db_session.query(Videojuego).filter_by(idvideojuegos=id).first()
    elif tipo == 'discusion':
        item = db_session.query(Discusion).filter_by(iddiscusiones=id).first()
    elif tipo == 'respuesta':
        item = db_session.query(Respuesta).filter_by(idrespuestas=id).first()
    else:
        return redirect(url_for('admin_dashboard')) # Si el tipo no es válido, regresa al panel de control.
    
    # Si se encuentra el elemento correspondiente, cambiamos su estado (aprobado) y guardamos los cambios.
    if item:
        item.aprobado = estado # Establece el nuevo estado (1 para habilitar, 0 para deshabilitar).
        # Guarda los cambios y muestra un mensaje de éxito.
        db_session.commit()
        flash('Habilitado / Deshabilitado con éxito', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('admin_dashboard')) # Si no se encuentra el item, regresa al panel de control.
    
# Ruta de edición de datos de videojuegos. Utiliza el valor dinámico 'idvideojuego' para saber a cual videojuego se refiere.
@app.route('/editar_videojuego/<int:idvideojuego>', methods=['GET', 'POST'])
def editar_videojuego(idvideojuego):
    # Busca el videojuego con el ID proporcionado.
    videojuego = db_session.query(Videojuego).filter(Videojuego.idvideojuegos == idvideojuego).first()
    
    if not videojuego:
        return redirect(url_for('admin_dashboard')) # Si no se encuentra el videojuego, regresa al panel de control.

    # Actualizar los datos del videojuego con los valores del formulario.
    if request.method == 'POST':
        videojuego.nombre = request.form['nombre']
        videojuego.añolanzamiento = request.form['añolanzamiento']
        videojuego.descripcion = request.form['descripcion']

        # Si se sube una nueva cáratula, se la procesa
        if 'caratula' in request.files:
            caratula_file = request.files['caratula']
            if caratula_file and allowed_file(caratula_file.filename):
                filename_caratula = secure_filename(f"{videojuego.nombre.replace(' ', '_')}-Caratula.{caratula_file.filename.rsplit('.', 1)[1].lower()}")
                caratula_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_caratula)
                caratula_file.save(caratula_path)
                videojuego.caratulalink = caratula_path

        # Si se sube una nueva captura de pantalla, se la procesa
        if 'screenshot' in request.files:
            screenshot_file = request.files['screenshot']
            if screenshot_file and allowed_file(screenshot_file.filename):
                filename_screenshot = secure_filename(f"{videojuego.nombre.replace(' ', '_')}-Screenshot.{screenshot_file.filename.rsplit('.', 1)[1].lower()}")
                screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_screenshot)
                screenshot_file.save(screenshot_path)
                videojuego.screenshotlink = screenshot_path

        # Actualizar los géneros y dispositivos seleccionados para el videojuego.
        generos_ids = request.form.getlist('generos')
        dispositivos_ids = request.form.getlist('dispositivos')
        videojuego.generos = db_session.query(Genero).filter(Genero.idgeneros.in_(generos_ids)).all()
        videojuego.dispositivos = db_session.query(Dispositivo).filter(Dispositivo.iddispositivos.in_(dispositivos_ids)).all()

        # Guardar todos los datos, mostrar mensaje de éxito, regresar al panel de control.
        db_session.commit()
        flash('Datos actualizados con éxito', 'success')
        return redirect(url_for('admin_dashboard'))
    # Obtener la lista de géneros y dispositivos disponibles, y los géneros y dispositivos seleccionados por el videojuego.
    generos = db_session.query(Genero).all()
    dispositivos = db_session.query(Dispositivo).all()
    generos_seleccionados = [g.idgeneros for g in videojuego.generos]
    dispositivos_seleccionados = [d.iddispositivos for d in videojuego.dispositivos]

    # Renderizar la plantilla para editar el videojuego.
    return render_template(
        'editarjuego.html',
        videojuego=videojuego,
        generos=generos,
        dispositivos=dispositivos,
        generos_seleccionados=generos_seleccionados,
        dispositivos_seleccionados=dispositivos_seleccionados
    )
    
# Ruta para gestionar usuarios, solo accesible para administradores.
@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required  # Asegura acceso solo a administradores.
def manejousuarios():
    # Consulta todos los usuarios de la base de datos.
    usuarios = db_session.query(Usuario).all()

    if request.method == 'POST':
        idusuario= request.form['user_id']  # ID del usuario a modificar.
        action = request.form['action']  # Acción a realizar 

        # Busca al usuario en la base de datos.
        usuario = db_session.query(Usuario).filter_by(idusuario=idusuario).first()
        if not usuario:
            flash('Usuario no encontrado.', 'danger')
            return redirect(url_for('manejousuarios'))

        # Realiza la acción seleccionada.
        if action == 'ban':
            usuario.baneado = not usuario.baneado  # Alterna el estado de baneado.
            estado = "baneado" if usuario.baneado else "desbaneado"
            flash(f'El usuario {usuario.username} ha sido {estado}.', 'success')
        elif action == 'make_admin':
            usuario.esAdmin = True  # Promueve al usuario a administrador.
            flash(f'El usuario {usuario.username} ahora es administrador.', 'success')
        else:
            flash('Acción no válida.', 'danger')

        # Guarda los cambios en la base de datos.
        db_session.commit()
        return redirect(url_for('manejousuarios'))

    # Renderiza la plantilla de gestión de usuarios.
    return render_template('manejousuarios.html', usuarios=usuarios)

if __name__ == '__main__':
    app.run(debug=True)
