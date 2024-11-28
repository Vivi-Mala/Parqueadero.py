import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime

# Crear base de datos y tablas si no existen
def crear_base_datos():
    conn = sqlite3.connect("parqueadero.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carros (
            placa TEXT PRIMARY KEY,
            hora_entrada TEXT,  
            hora_salida TEXT,
            total_pago REAL,
            puesto INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS puestos (
            numero INTEGER PRIMARY KEY,
            ocupado INTEGER
        )
    ''')
    for i in range(1, 41):
        cursor.execute('INSERT OR IGNORE INTO puestos (numero, ocupado) VALUES (?, ?)', (i, 0))
    conn.commit()
    conn.close()

# Función para registrar un carro con hora de entrada
def registrar_carro():
    placa = simpledialog.askstring("Registrar Carro", "Ingrese la placa del carro:")
    if not placa:
        return

    hora_entrada = simpledialog.askstring("Hora de Entrada", "Ingrese la hora de entrada (HH:MM):")
    if not hora_entrada:
        return

    try:
        datetime.strptime(hora_entrada, "%H:%M")  # Verifica si el formato de hora es correcto
    except ValueError:
        messagebox.showerror("Error de formato", "La hora debe tener el formato HH:MM.")
        return

    conn = sqlite3.connect("parqueadero.db")
    cursor = conn.cursor()

    # Buscar un puesto disponible
    cursor.execute("SELECT numero FROM puestos WHERE ocupado = 0 LIMIT 1")
    puesto = cursor.fetchone()

    if puesto:
        puesto_numero = puesto[0]
        try:
            cursor.execute("INSERT INTO carros (placa, hora_entrada, puesto) VALUES (?, ?, ?)", (placa, hora_entrada, puesto_numero))
            cursor.execute("UPDATE puestos SET ocupado = 1 WHERE numero = ?", (puesto_numero,))
            conn.commit()
            messagebox.showinfo("Registro Exitoso", f"Carro {placa} registrado en el puesto {puesto_numero}. Hora de entrada: {hora_entrada}.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "La placa ya está registrada.")
    else:
        messagebox.showwarning("Sin Espacio", "No hay puestos disponibles.")

    conn.close()

# Función para ver datos con protección de contraseña
def mostrar_datos():
    clave = simpledialog.askstring("Contraseña", "Ingrese la contraseña de administrador:", show="*")
    if clave != "admin123":
        messagebox.showerror("Acceso Denegado", "Contraseña incorrecta.")
        return

    conn = sqlite3.connect("parqueadero.db")
    cursor = conn.cursor()

    # Consulta de carros registrados
    cursor.execute("SELECT * FROM carros")
    carros = cursor.fetchall()

    # Consulta de puestos actualizados
    cursor.execute("SELECT * FROM puestos ORDER BY numero ASC")
    puestos = cursor.fetchall()

    # Crear una ventana para mostrar los datos
    ventana_datos = tk.Toplevel()
    ventana_datos.title("Datos del Parqueadero")
    ventana_datos.geometry("600x400")

    texto = tk.Text(ventana_datos, wrap="word", width=80, height=20, font=("Arial", 10), bg="#f4f4f4", bd=2, relief="sunken")
    texto.pack(padx=10, pady=10)

    texto.insert("end", "Tabla de Carros Registrados:\n")
    texto.insert("end", "Placa\tHora Entrada\tHora Salida\tTotal Pago\tPuesto\n")
    texto.insert("end", "-" * 60 + "\n")
    for carro in carros:
        texto.insert("end", f"{carro[0]}\t{carro[1]}\t{carro[2] if carro[2] else 'N/A'}\t{carro[3] if carro[3] else 'N/A'}\t{carro[4]}\n")

    texto.insert("end", "\n")

    texto.insert("end", "Estado de los Puestos:\n")
    texto.insert("end", "Número\tOcupado\n")
    texto.insert("end", "-" * 40 + "\n")
    for puesto in puestos:
        estado = "Ocupado" if puesto[1] == 1 else "Disponible"
        texto.insert("end", f"{puesto[0]}\t{estado}\n")

    conn.close()

# Función para calcular el cobro y generar factura
def cobrar_salida():
    placa = simpledialog.askstring("Cobrar Salida", "Ingrese la placa del carro:")
    if not placa:
        return

    conn = sqlite3.connect("parqueadero.db")
    cursor = conn.cursor()

    # Verificar si el carro está registrado
    cursor.execute("SELECT * FROM carros WHERE placa = ?", (placa,))
    carro = cursor.fetchone()

    if not carro:
        messagebox.showwarning("Carro No Encontrado", "El carro con esa placa no está registrado en el parqueadero.")
        conn.close()
        return

    if carro[2]:  # Si la columna `hora_salida` no es NULL
        messagebox.showinfo("Salida Ya Registrada", "El carro ya salió del parqueadero.")
        conn.close()
        return

    hora_salida = simpledialog.askstring("Hora de Salida", "Ingrese la hora de salida (HH:MM):")
    if not hora_salida:
        return

    try:
        hora_salida = datetime.strptime(hora_salida, "%H:%M")  # Verifica si el formato de hora es correcto
    except ValueError:
        messagebox.showerror("Error de formato", "La hora debe tener el formato HH:MM.")
        return

    hora_entrada = datetime.strptime(carro[1], "%H:%M")
    tiempo_estacionado = (hora_salida - hora_entrada).total_seconds() / 3600  # Tiempo en horas

    if tiempo_estacionado < 0:
        messagebox.showerror("Error", "La hora de salida no puede ser antes de la hora de entrada.")
        conn.close()
        return

    tarifa = 5000  # Definir tarifa por hora
    total_pago = round(tiempo_estacionado) * tarifa

    cursor.execute("UPDATE carros SET hora_salida = ?, total_pago = ? WHERE placa = ?", (hora_salida.strftime("%H:%M"), total_pago, placa))

    # Liberar el puesto ocupado
    cursor.execute("UPDATE puestos SET ocupado = 0 WHERE numero = ?", (carro[4],))
    conn.commit()

    factura = f"""
    --------------------------------------
    Factura de Salida - Parqueadero YESYU
    --------------------------------------
    Placa del Carro: {placa}
    Hora de Entrada: {carro[1]}
    Hora de Salida: {hora_salida.strftime("%H:%M")}
    Tiempo Estacionado: {round(tiempo_estacionado)} horas
    Total a Pagar: {total_pago} COP
    --------------------------------------
    ¡Gracias por usar nuestro parqueadero!
    """

    messagebox.showinfo("Factura Generada", factura)
    conn.close()

# Función para ver los ingresos totales
def ver_ingresos_totales():
    clave = simpledialog.askstring("Contraseña", "Ingrese la contraseña de administrador:", show="*")
    if clave != "admin123":
        messagebox.showerror("Acceso Denegado", "Contraseña incorrecta.")
        return

    conn = sqlite3.connect("parqueadero.db")
    cursor = conn.cursor()

    # Consultar la suma de los ingresos totales
    cursor.execute("SELECT SUM(total_pago) FROM carros WHERE total_pago IS NOT NULL")
    total_ingresos = cursor.fetchone()[0]  # Devuelve el valor de la suma, o None si no hay registros

    conn.close()

    if total_ingresos is None:  # Si no hay ingresos registrados
        total_ingresos = 0

    messagebox.showinfo("Ingresos Totales", f"Los ingresos totales del parqueadero son: {total_ingresos} COP")

# Crear la base de datos y las tablas al iniciar
crear_base_datos()

# Interfaz gráfica principal
root = tk.Tk()
root.title("Administración de Parqueadero YESYU")
root.geometry("400x400")
root.config(bg="#b0e0e6")

# Títulos y etiquetas
label_titulo = tk.Label(root, text="Sistema de Parqueadero YESYU", font=("Arial", 16, "bold"), bg="#b0e0e6", fg="#333")
label_titulo.grid(row=0, column=0, columnspan=3, pady=20)

# Botones para las funcionalidades
btn_registrar = tk.Button(root, text="Registrar Carro", command=registrar_carro, font=("Arial", 12), bg="#4CAF50", fg="white", relief="raised", bd=5)
btn_registrar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

btn_ver_datos = tk.Button(root, text="Ver Datos Guardados", command=mostrar_datos, font=("Arial", 12), bg="#2196F3", fg="white", relief="raised", bd=5)
btn_ver_datos.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

btn_cobrar = tk.Button(root, text="Cobrar Salida", command=cobrar_salida, font=("Arial", 12), bg="#FF5722", fg="white", relief="raised", bd=5)
btn_cobrar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

btn_ingresos = tk.Button(root, text="Ver Ingresos Totales", command=ver_ingresos_totales, font=("Arial", 12), bg="#FFC107", fg="black", relief="raised", bd=5)
btn_ingresos.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

# Iniciar la aplicación
root.mainloop()
