import logging

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import bcrypt


class Database:
    TOKEN = 'TOKEN'

    def __init__(self, dbname, user, password, host):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)

    def authenticate_user(self, login, password):
        # Проверка в таблице граждан
        query_citizen = sql.SQL("""
                    SELECT c.*, r.name as role_name
                    FROM citizen c
                    JOIN role r ON c.role_id = r.role_id
                    WHERE c.username = %s
                """)
        self.cur.execute(query_citizen, (login,))
        user_citizen = self.cur.fetchone()

        if user_citizen and bcrypt.checkpw(password.encode('utf-8'), user_citizen['password_hash'].encode('utf-8')):
            user_citizen['is_admin'] = user_citizen['role_name'] == 'Administrator'
            logging.info(f"Пользователь аутентифицирован как гражданин: {user_citizen}")
            return user_citizen

        # Проверка в таблице администраторов
        query_admin = sql.SQL("""
                    SELECT a.*, r.name as role_name
                    FROM administrator a
                    JOIN role r ON a.role_id = r.role_id
                    WHERE a.username = %s
                """)
        self.cur.execute(query_admin, (login,))
        user_admin = self.cur.fetchone()

        if user_admin and bcrypt.checkpw(password.encode('utf-8'), user_admin['password_hash'].encode('utf-8')):
            user_admin['is_admin'] = user_admin['role_name'] == 'Administrator'
            logging.info(f"Пользователь аутентифицирован как администратор: {user_admin}")
            return user_admin

        logging.warning(f"Аутентификация не удалась для пользователя: {login}")
        return None

    def view_all_data(self):
        query = sql.SQL("SELECT citizen_id, last_name, first_name FROM citizen")
        self.cur.execute(query)
        data = self.cur.fetchall()
        return "\n".join([f"{row['citizen_id']}, {row['last_name']}, {row['first_name']}" for row in data])

    def register_user(self, first_name, last_name, patronymic, date_of_birth, passport_number, address, username,
                      password, gender):
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = """
            INSERT INTO citizen (first_name, last_name, patronymic, date_of_birth, passport_number, address, role_id, username, password_hash, gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cur.execute(query, (
            first_name, last_name, patronymic, date_of_birth, passport_number, address, 1, username, password_hash,
            gender))
        self.conn.commit()

    def update_data(self, citizen_id, field_name, new_value):
        query = sql.SQL("UPDATE citizen SET {} = %s WHERE citizen_id = %s").format(sql.Identifier(field_name))
        self.cur.execute(query, (new_value, citizen_id))
        self.conn.commit()

    def get_personal_data(self, citizen_id):
        query = sql.SQL("SELECT * FROM citizen WHERE citizen_id = %s")
        self.cur.execute(query, (citizen_id,))
        personal_data = self.cur.fetchone()
        return personal_data

    def get_scan_results(self, citizen_id):
        query = sql.SQL("""
            SELECT irisscan.*, organization.*
            FROM irisscan
            JOIN organization ON irisscan.organization_id = organization.organization_id
            WHERE irisscan.citizen_id = %s
        """)
        self.cur.execute(query, (citizen_id,))
        scan_results = self.cur.fetchall()
        return scan_results

    def create_user(self, first_name, last_name, patronymic, date_of_birth, passport_number, address, username,
                    password):
        self.register_user(first_name, last_name, patronymic, date_of_birth, passport_number, address, username,
                           password)

    def get_user(self, citizen_id):
        query = sql.SQL("SELECT * FROM citizen WHERE citizen_id = %s")
        self.cur.execute(query, (citizen_id,))
        user = self.cur.fetchone()
        return user

    def get_all_users(self):
        return self.view_all_data()

    def update_user(self, citizen_id, field_name, new_value):
        self.update_data(citizen_id, field_name, new_value)


    def view_table_data(self, table_name):
        valid_tables = ["role", "citizen", "organization", "document", "irisscan", "consent", "administrator", "application"]
        if table_name.lower() not in valid_tables:
            return None
        try:
            query = sql.SQL('SELECT * FROM {}').format(sql.Identifier(table_name))
            self.cur.execute(query)
            return [dict(row) for row in self.cur.fetchall()]
        except Exception as e:
            self.conn.rollback()  # Сброс транзакции
            print(f"Ошибка при выполнении запроса: {e}")
            return None

    def execute_query(self, query, *params):
        try:
            self.cur.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            self.conn.rollback()
            return False

