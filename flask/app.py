from flask import Flask, jsonify, request, g
from flask_cors import CORS
from datetime import datetime
import pymysql
import os
import re
from werkzeug.utils import secure_filename
import boto3

app = Flask(__name__)
CORS(app)
app.config['DATABASE'] = 'socks.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1 << 24
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['ALLOWED_MIME_TYPES'] = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}

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
            CREATE TABLE IF NOT EXISTS socks (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
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

        db.execute('''
            CREATE TABLE IF NOT EXISTS wash_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                sock_id INTEGER NOT NULL,
                wash_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sock_id) REFERENCES socks (id)
            )
        ''')

@app.before_request
def before_request():
    init_db()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/api/load', methods=['GET'])
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
            WHERE LOWER(color) LIKE %s OR LOWER(style) LIKE %s OR LOWER(brand) LIKE %s OR %s LIKE ''
            ORDER BY {order}, created_at DESC
            LIMIT %s OFFSET %s
        ''', (query, query, query, query, limit, offset))
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
def get_sock(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT * FROM socks WHERE id = %s', (sock_id,))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)

    sock_dict = dict(sock)
    if sock_dict['photo_name']:
        sock_dict['photo_url'] = img_url(sock_dict['photo_name'])

    return jsonify(sock_dict)


@app.route('/add', methods=['POST'])
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
            INSERT INTO socks (color, color_hex, style, pattern, material, 
                            size, brand, photo_name, clean, created_at, 
                            last_washed, wear_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, 0)
        ''', (sock_data['color'], sock_data['color_hex'], sock_data['style'], sock_data['pattern'], sock_data['material'],
            sock_data['size'], sock_data['brand'], photo_name, current_time, current_time))
    
    return jsonify({
        'success': True,
        'message': 'Носок успешно добавлен!'
    })

@app.route('/edit_sock/<string:sock_id>', methods=['POST'])
def edit_sock(sock_id):
    sock_data, error = validate_sock_form(request.form)
    if error:
        return error

    with get_db().cursor() as db:
        db.execute('SELECT photo_name FROM socks WHERE id = %s', (sock_id,))
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
            WHERE id = %s
        ''', (sock_data['color'], sock_data['color_hex'], sock_data['style'], sock_data['pattern'],
              sock_data['material'], sock_data['size'], sock_data['brand'], photo_name, sock_id))

    return jsonify({
        'success': True,
        'message': 'Носок успешно обновлен!'
    })
    
@app.route('/toggle_clean/<string:sock_id>', methods=['POST'])
def toggle_clean(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT clean, wear_count FROM socks WHERE id = %s', (sock_id,))
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
                WHERE id = %s
            ''', (current_time, sock_id))
            
            db.execute('INSERT INTO wash_history (sock_id) VALUES (%s)', (sock_id,))
            wear_count = sock['wear_count'] + 1
        else:
            db.execute('UPDATE socks SET clean = 0 WHERE id = %s', (sock_id,))
            wear_count = sock['wear_count']
    
    return jsonify({
        'success': True, 
        'new_status': 'clean' if new_clean_status else 'dirty',
        'wear_count': wear_count
    })

@app.route('/delete_sock/<string:sock_id>', methods=['DELETE'])
def delete_sock(sock_id):
    with get_db().cursor() as db:
        db.execute('SELECT photo_name FROM socks WHERE id = %s', (sock_id,))
        sock = db.fetchone()

    if not sock:
        return error_response('Носок не найден', 404)

    if sock['photo_name']:
        delete_img(sock['photo_name'])
    
    with get_db().cursor() as db:
        db.execute('DELETE FROM socks WHERE id = %s', (sock_id,))
        db.execute('DELETE FROM wash_history WHERE sock_id = %s', (sock_id,))
    
    return jsonify({
        'success': True,
        'message': 'Носок успешно удален'
    })

@app.route('/api/stats')
def get_stats():
    with get_db().cursor() as db:
        db.execute('''
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(clean), 0) as clean,
                COUNT(*) - COALESCE(SUM(clean), 0) as dirty,
                AVG(wear_count) as avg_wear_count
            FROM socks
        ''')
        stats = db.fetchone()
    
    return jsonify({
        'success': True,
        'stats': dict(stats),
    })

@app.route('/api/wash_history/<string:sock_id>')
def get_wash_history(sock_id):
    with get_db().cursor() as db:
        db.execute('''
            SELECT wash_date 
            FROM wash_history 
            WHERE sock_id = %s 
            ORDER BY wash_date DESC
        ''', (sock_id,))
        history = db.fetchall()
    
    return jsonify({
        'success': True,
        'history': [row['wash_date'] for row in history]
    })

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', debug=os.environ.get('FLASK_DEBUG') == '1')
