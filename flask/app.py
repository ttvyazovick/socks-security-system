from flask import Flask, jsonify, request, g, session
from flask_cors import CORS
from datetime import datetime
import pymysql
import os
import re
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import boto3

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '').lower() == 'true'
CORS(app, supports_credentials=True)
app.config['DATABASE'] = 'socks.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1 << 24
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['ALLOWED_MIME_TYPES'] = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}
AUTH_VALUE_PATTERN = re.compile(r'^[A-Za-z_]{4,16}$')

COLOR_OPTIONS = {
    'Черные': '#2c3e50',
    'Белые': '#ecf0f1',
    'Серые': '#7f8c8d',
    'Синие': '#3498db',
    'Зеленые': '#27ae60',
    'Красные': '#e74c3c',
    'Желтые': '#f1c40f',
    'Фиолетовые': '#9b59b6',
    'Розовые': '#e84393',
    'Оранжевые': '#e67e22',
    'Голубые': '#00cec9',
    'Коричневые': '#a1887f',
    'Бежевые': '#f5deb3',
    'Бирюзовые': '#1abc9c',
    'Мятные': '#98ff98',
}
STYLE_OPTIONS = {'Спортивные', 'Повседневные', 'Домашние', 'Бизнес', 'Короткие', 'Термо', 'Вязаные', 'Смешные', 'Праздничные'}
PATTERN_OPTIONS = {'Однотонные', 'Полоска', 'Горошек', 'Клетка', 'Геометрия', 'Принт', 'Логотип'}
MATERIAL_OPTIONS = {'Хлопок', 'Шерсть', 'Синтетика', 'Шелк', 'Бамбук', 'Лен'}
SIZE_OPTIONS = {'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL'}
BRAND_OPTIONS = {'Nike', 'Puma', 'Reebok', 'Uniqlo', 'H&M', 'Wilson', 'Funny Socks', 'Unknown'}

BUCKET_NAME = os.environ.get('BUCKET_NAME')
if BUCKET_NAME:
    s3_client = boto3.client(
        's3',
        endpoint_url=os.environ['BUCKET_ENDPOINT'],
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name=os.environ['BUCKET_REGION']
    )

def error_response(message, status=400):
    return jsonify({'success': False, 'message': message}), status

def validate_auth_value(value):
    return isinstance(value, str) and AUTH_VALUE_PATTERN.fullmatch(value) is not None

def auth_validation_message(field):
    return f'{field} должен быть длиной от 4 до 16 символов и состоять только из латинских букв и нижнего подчеркивания'

def current_user_id():
    return session.get('user_id')

def login_required(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            return error_response('Авторизуйтесь, пожалуйста', 401)
        return route(*args, **kwargs)
    return wrapped

def attach_orphan_socks(user_id):
    with get_db().cursor() as db:
        db.execute('UPDATE socks SET user_id = %s WHERE user_id IS NULL', (user_id,))

def attach_orphan_socks_to_first_user(db):
    db.execute('SELECT id FROM users ORDER BY created_at ASC, id ASC LIMIT 1')
    first_user = db.fetchone()
    if first_user:
        db.execute('UPDATE socks SET user_id = %s WHERE user_id IS NULL', (first_user['id'],))

def allowed_file(file):
    filename = file.filename
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'] and \
           file.mimetype in app.config['ALLOWED_MIME_TYPES']

def parse_int_arg(name, default, min_value=0, max_value=None):
    value = request.args.get(name, str(default))
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'Параметр {name} должен быть числом')

    if value < min_value:
        raise ValueError(f'Параметр {name} не может быть меньше {min_value}')
    if max_value is not None:
        value = min(value, max_value)
    return value

def format_datetime(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%d.%m.%Y')
    return datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')

def validate_sock_form(form):
    color_name = form.get('color')
    color_hex = form.get('color_hex')
    style = form.get('style')
    pattern = form.get('pattern')
    material = form.get('material')
    size = form.get('size')
    brand = form.get('brand')

    if not all([color_name, color_hex, style, pattern, material, size, brand]):
        return None, error_response('Заполните все обязательные поля')
    if color_name not in COLOR_OPTIONS:
        return None, error_response('Некорректный цвет')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color_hex) or COLOR_OPTIONS[color_name].lower() != color_hex.lower():
        return None, error_response('Некорректный код цвета')
    if style not in STYLE_OPTIONS:
        return None, error_response('Некорректный стиль')
    if pattern not in PATTERN_OPTIONS:
        return None, error_response('Некорректный узор')
    if material not in MATERIAL_OPTIONS:
        return None, error_response('Некорректный материал')
    if size not in SIZE_OPTIONS:
        return None, error_response('Некорректный размер')
    if brand not in BRAND_OPTIONS:
        return None, error_response('Некорректный бренд')

    return {
        'color': color_name,
        'color_hex': color_hex,
        'style': style,
        'pattern': pattern,
        'material': material,
        'size': size,
        'brand': brand,
    }, None

def img_url(filename):
    if BUCKET_NAME:
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': filename},
            ExpiresIn=604800
        )
    else:
        return f"/{os.path.join(app.config['UPLOAD_FOLDER'], filename)}"

def save_img(file):
    filename = secure_filename(file.filename)
    if BUCKET_NAME:
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={'ContentType': file.content_type}
        )
    else:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(local_path, 'wb') as f:
            f.write(file.read())
                  
    return filename

def delete_img(photo_name):
    if BUCKET_NAME:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=photo_name)
    else:
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_name)
        if os.path.exists(local_path):
            os.remove(local_path)

def get_db():
    db_url = os.environ.get('MYSQL_URL')
    
    if db_url and db_url.startswith('mysql://'):
        from urllib.parse import urlparse
        url = urlparse(db_url)
        conn = pymysql.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path.lstrip('/'),
            port=url.port or 3306,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    else:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='user',
            password='123',
            database='sss',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    return conn

def init_db():
    with get_db().cursor() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(16) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS socks (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                color VARCHAR(10) NOT NULL,
                color_hex VARCHAR(7) NOT NULL,
                style VARCHAR(12) NOT NULL,
                pattern TEXT NOT NULL,
                material TEXT NOT NULL,
                size TEXT NOT NULL,
                brand TEXT NOT NULL,
                photo_name TEXT,
                clean BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_washed TIMESTAMP,
                wear_count INTEGER DEFAULT 0
            )
        ''')

        db.execute("SHOW COLUMNS FROM socks LIKE 'user_id'")
        if not db.fetchone():
            db.execute('ALTER TABLE socks ADD COLUMN user_id INT NULL AFTER id')

        db.execute("SHOW INDEX FROM socks WHERE Key_name = 'idx_socks_user_id'")
        if not db.fetchone():
            db.execute('CREATE INDEX idx_socks_user_id ON socks (user_id)')

        db.execute('''
            CREATE TABLE IF NOT EXISTS wash_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                sock_id INTEGER NOT NULL,
                wash_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sock_id) REFERENCES socks (id)
            )
        ''')

        attach_orphan_socks_to_first_user(db)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not validate_auth_value(username):
        return error_response(auth_validation_message('Логин'))
    if not validate_auth_value(password):
        return error_response(auth_validation_message('Пароль'))

    with get_db().cursor() as db:
        db.execute('SELECT COUNT(*) AS count FROM users')
        users_count = db.fetchone()['count']

        db.execute('SELECT id FROM users WHERE username = %s', (username,))
        if db.fetchone():
            return error_response('Пользователь с таким логином уже существует', 409)

        db.execute(
            'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
            (username, generate_password_hash(password))
        )
        user_id = db.lastrowid

    if users_count == 0:
        attach_orphan_socks(user_id)

    session.clear()
    session['user_id'] = user_id
    session['username'] = username

    return jsonify({
        'success': True,
        'user': {'id': user_id, 'username': username},
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not validate_auth_value(username) or not validate_auth_value(password):
        return error_response('Неверный логин или пароль', 401)

    with get_db().cursor() as db:
        db.execute('SELECT id, username, password_hash FROM users WHERE username = %s', (username,))
        user = db.fetchone()

    if not user or not check_password_hash(user['password_hash'], password):
        return error_response('Неверный логин или пароль', 401)

    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'success': True,
        'user': {'id': user['id'], 'username': user['username']},
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def me():
    user_id = current_user_id()
    if not user_id:
        return jsonify({'success': True, 'user': None})

    with get_db().cursor() as db:
        db.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
        user = db.fetchone()

    if not user:
        session.clear()
        return jsonify({'success': True, 'user': None})

    return jsonify({'success': True, 'user': dict(user)})

@app.route('/api/load', methods=['GET'])
@login_required
def load_socks():
    query = '%' + request.args.get('query', '').lower()[:100] + '%'
    try:
        offset = parse_int_arg('offset', 0)
        limit = parse_int_arg('limit', 5, min_value=1, max_value=50)
    except ValueError as error:
        return error_response(str(error))

    priority = request.args.get('priority', 'clean')
    order = {
        'clean': 'clean DESC',
        'dirty': 'clean ASC',
        'frequent': 'wear_count DESC'
    }.get(priority)
    if order is None:
        return error_response('Некорректный параметр priority')

    with get_db().cursor() as db:
        db.execute(f'''
            SELECT * FROM socks
            WHERE user_id = %s
              AND (LOWER(color) LIKE %s OR LOWER(style) LIKE %s OR LOWER(brand) LIKE %s OR %s LIKE '')
            ORDER BY {order}, created_at DESC
            LIMIT %s OFFSET %s
        ''', (current_user_id(), query, query, query, query, limit, offset))
        socks = db.fetchall()
    
    socks_list = []
    for sock in socks:
        sock_dict = dict(sock)

        sock_dict['created_at_formatted'] = format_datetime(sock_dict['created_at'])
        sock_dict['last_washed_formatted'] = format_datetime(sock_dict['last_washed'])

        if sock_dict['photo_name']:
            sock_dict['photo_url'] = img_url(sock_dict['photo_name'])
        
        socks_list.append(sock_dict)
    
    return jsonify(socks_list)

@app.route('/api/sock/<string:sock_id>', methods=['GET'])
@login_required
def get_sock(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT * FROM socks WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)

    sock_dict = dict(sock)
    if sock_dict['photo_name']:
        sock_dict['photo_url'] = img_url(sock_dict['photo_name'])

    return jsonify(sock_dict)


@app.route('/add', methods=['POST'])
@login_required
def add_sock():
    sock_data, error = validate_sock_form(request.form)
    if error:
        return error
    
    photo_name = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            if not allowed_file(file):
                return error_response('Можно загрузить только PNG, JPG или WEBP изображение')
            file.filename = secure_filename(file.filename)
            photo_name = save_img(file)
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db().cursor() as db:
        db.execute('''
            INSERT INTO socks (user_id, color, color_hex, style, pattern, material,
                            size, brand, photo_name, clean, created_at, 
                            last_washed, wear_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, 0)
        ''', (current_user_id(), sock_data['color'], sock_data['color_hex'], sock_data['style'], sock_data['pattern'], sock_data['material'],
            sock_data['size'], sock_data['brand'], photo_name, current_time, current_time))
    
    return jsonify({
        'success': True,
        'message': 'Носок успешно добавлен!'
    })

@app.route('/edit_sock/<string:sock_id>', methods=['POST'])
@login_required
def edit_sock(sock_id):
    sock_data, error = validate_sock_form(request.form)
    if error:
        return error

    with get_db().cursor() as db:
        db.execute('SELECT photo_name FROM socks WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)

    photo_name = sock['photo_name']
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            if not allowed_file(file):
                return error_response('Можно загрузить только PNG, JPG или WEBP изображение')
            if photo_name:
                delete_img(photo_name)
            file.filename = secure_filename(file.filename)
            photo_name = save_img(file)

    with get_db().cursor() as db:
        db.execute('''
            UPDATE socks
            SET color = %s, color_hex = %s, style = %s, pattern = %s,
                material = %s, size = %s, brand = %s, photo_name = %s
            WHERE id = %s AND user_id = %s
        ''', (sock_data['color'], sock_data['color_hex'], sock_data['style'], sock_data['pattern'],
              sock_data['material'], sock_data['size'], sock_data['brand'], photo_name, sock_id, current_user_id()))

    return jsonify({
        'success': True,
        'message': 'Носок успешно обновлен!'
    })
    
@app.route('/toggle_clean/<string:sock_id>', methods=['POST'])
@login_required
def toggle_clean(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT clean, wear_count FROM socks WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)
    
    new_clean_status = not sock['clean']
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db().cursor() as db:
        if new_clean_status:
            db.execute('''
                UPDATE socks 
                SET clean = 1, last_washed = %s, wear_count = wear_count + 1 
                WHERE id = %s AND user_id = %s
            ''', (current_time, sock_id, current_user_id()))
            
            db.execute('INSERT INTO wash_history (sock_id) VALUES (%s)', (sock_id,))
            wear_count = sock['wear_count'] + 1
        else:
            db.execute('UPDATE socks SET clean = 0 WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
            wear_count = sock['wear_count']
    
    return jsonify({
        'success': True, 
        'new_status': 'clean' if new_clean_status else 'dirty',
        'wear_count': wear_count
    })

@app.route('/delete_sock/<string:sock_id>', methods=['DELETE'])
@login_required
def delete_sock(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT photo_name FROM socks WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)

    if sock['photo_name']:
        delete_img(sock['photo_name'])
    
    with get_db().cursor() as db:
        db.execute('DELETE FROM wash_history WHERE sock_id = %s', (sock_id,))
        db.execute('DELETE FROM socks WHERE id = %s AND user_id = %s', (sock_id, current_user_id()))
    
    return jsonify({
        'success': True,
        'message': 'Носок успешно удален'
    })

@app.route('/api/stats')
@login_required
def get_stats():
    with get_db().cursor() as db:
        db.execute('''
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(clean), 0) as clean,
                COUNT(*) - COALESCE(SUM(clean), 0) as dirty,
                AVG(wear_count) as avg_wear_count
            FROM socks
            WHERE user_id = %s
        ''', (current_user_id(),))
        stats = db.fetchone()
    
    return jsonify({
        'success': True,
        'stats': dict(stats),
    })

@app.route('/api/wash_history/<string:sock_id>')
@login_required
def get_wash_history(sock_id):
    with get_db().cursor() as db:
        db.execute('''
            SELECT wash_history.wash_date
            FROM wash_history
            JOIN socks ON socks.id = wash_history.sock_id
            WHERE wash_history.sock_id = %s AND socks.user_id = %s
            ORDER BY wash_history.wash_date DESC
        ''', (sock_id, current_user_id()))
        history = db.fetchall()
    
    return jsonify({
        'success': True,
        'history': [row['wash_date'] for row in history]
    })

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=os.environ.get('FLASK_DEBUG') == '1')
