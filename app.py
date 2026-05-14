from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sistema_vendas_2026"

def get_db():
    conn = sqlite3.connect('vendas.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER DEFAULT 0)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY, customer_id INTEGER, date TEXT, total REAL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY, sale_id INTEGER, product_id INTEGER, 
                    quantity INTEGER, price REAL)''')
    
    # Criar admin
    if cur.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password) VALUES (?,?)", 
                    ('admin', hashlib.sha256('admin'.encode()).hexdigest()))
        print("✅ Usuário admin criado!")
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado!")

# ===================== ROTAS =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db()
    user = conn.execute("SELECT username FROM users WHERE username=? AND password=?", 
                        (username, hashlib.sha256(password.encode()).hexdigest())).fetchone()
    conn.close()
    
    if user:
        session['user'] = username
        return redirect(url_for('menu'))
    flash('Usuário ou senha incorretos!')
    return redirect(url_for('index'))

@app.route('/menu')
def menu():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('menu.html', usuario=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ===================== CLIENTES =====================
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if 'user' not in session: return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        conn = get_db()
        conn.execute("INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)", (nome, email, phone))
        conn.commit()
        conn.close()
        
        flash('✅ Cliente cadastrado com sucesso!')
        return redirect(url_for('listar_clientes'))
    return render_template('clientes.html')

# ===================== PRODUTOS =====================
@app.route('/produtos', methods=['GET', 'POST'])
def produtos():
    if 'user' not in session: return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        preco = float(request.form.get('preco'))
        estoque = int(request.form.get('estoque'))
        
        conn = get_db()
        conn.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (nome, preco, estoque))
        conn.commit()
        conn.close()
        
        flash('✅ Produto cadastrado com sucesso!')
        return redirect(url_for('listar_produtos'))
    return render_template('produtos.html')

# ===================== LISTAGENS =====================
@app.route('/listar-clientes')
def listar_clientes():
    if 'user' not in session: return redirect(url_for('index'))
    conn = get_db()
    clientes = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return render_template('listar-clientes.html', clientes=clientes)

@app.route('/listar-produtos')
def listar_produtos():
    if 'user' not in session: return redirect(url_for('index'))
    conn = get_db()
    produtos = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    return render_template('listar-produtos.html', produtos=produtos)

# ===================== NOVA VENDA =====================
@app.route('/nova-venda', methods=['GET', 'POST'])
def nova_venda():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    conn = get_db()
    clientes = conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()
    produtos = conn.execute("SELECT id, name, price, stock FROM products WHERE stock > 0 ORDER BY name").fetchall()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 0))
        
        if not customer_id or not product_id or quantity <= 0:
            flash('Preencha todos os campos!', 'error')
            conn.close()
            return redirect(url_for('nova_venda'))
        
        produto = conn.execute("SELECT price, stock FROM products WHERE id = ?", (product_id,)).fetchone()
        
        if not produto or produto['stock'] < quantity:
            flash('Estoque insuficiente!', 'error')
            conn.close()
            return redirect(url_for('nova_venda'))
        
        total = produto['price'] * quantity
        
        cur = conn.cursor()
        cur.execute("INSERT INTO sales (customer_id, date, total) VALUES (?, ?, ?)", 
                    (customer_id, datetime.now().strftime("%Y-%m-%d %H:%M"), total))
        sale_id = cur.lastrowid
        
        cur.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (sale_id, product_id, quantity, produto['price']))
        
        cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        
        conn.commit()
        conn.close()
        
        flash(f'✅ Venda realizada! Total: R$ {total:.2f}', 'success')
        return redirect(url_for('menu'))
    
    conn.close()
    return render_template('nova-venda.html', clientes=clientes, produtos=produtos)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)