import os
import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

def get_database_type(db):
    """
    获取数据库类型 (postgresql, sqlite, mysql等)
    """
    try:
        return db.engine.name
    except:
        return "unknown"

def check_column_exists(db, table_name, column_name):
    """
    检查指定表的列是否存在
    """
    try:
        inspector = inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"检查列是否存在时出错: {str(e)}")
        return False

def add_column_if_not_exists(db, table_name, column_name, column_type, default_value=None):
    """
    添加列到表中（如果该列不存在）
    支持PostgreSQL和SQLite
    """
    if check_column_exists(db, table_name, column_name):
        return False  # 列已存在，无需添加

    db_type = get_database_type(db)
    
    try:
        # 基于数据库类型使用不同的SQL语法
        if db_type == 'postgresql':
            # PostgreSQL语法
            sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
            if default_value is not None:
                sql += f" DEFAULT {default_value}"
        elif db_type == 'sqlite':
            # SQLite不支持ALTER TABLE ADD COLUMN IF NOT EXISTS，需要检查后再添加
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                sql += f" DEFAULT {default_value}"
        else:
            # 其他数据库的通用语法（可能需要针对特定数据库调整）
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                sql += f" DEFAULT {default_value}"
        
        # 执行SQL
        db.session.execute(text(sql))
        db.session.commit()
        logger.info(f"已添加列 {column_name} 到表 {table_name}")
        return True
    except OperationalError as e:
        # SQLite在添加已存在的列时会出错，但这对我们来说是可接受的
        if "duplicate column name" in str(e).lower():
            logger.info(f"列 {column_name} 已存在于表 {table_name}")
            return False
        logger.error(f"添加列时出错: {str(e)}")
        db.session.rollback()
        return False
    except ProgrammingError as e:
        # PostgreSQL在使用IF NOT EXISTS时，如果列已存在不会报错
        logger.error(f"添加列时出错: {str(e)}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"添加列时出错: {str(e)}")
        db.session.rollback()
        return False

def get_date_format_function(db, format_string):
    """
    根据数据库类型返回适当的日期格式化函数
    
    Args:
        db: SQLAlchemy数据库实例
        format_string: 日期格式字符串
        
    Returns:
        适用于当前数据库类型的函数名称
    """
    db_type = get_database_type(db)
    
    if db_type == 'postgresql':
        return 'to_char'  # PostgreSQL使用to_char
    elif db_type == 'sqlite':
        return 'strftime'  # SQLite使用strftime
    else:
        # 默认返回strftime，可以根据需要添加其他数据库的支持
        return 'strftime'

def format_date(db, column, format_string):
    """
    以数据库无关的方式格式化日期
    
    Args:
        db: SQLAlchemy数据库实例
        column: 要格式化的列
        format_string: 格式字符串
        
    Returns:
        格式化后的SQL表达式
    """
    from sqlalchemy.sql import func
    
    db_type = get_database_type(db)
    
    if db_type == 'postgresql':
        # PostgreSQL使用to_char
        if format_string == '%H':
            pg_format = 'HH24'
        elif format_string == '%Y-%m-%d':
            pg_format = 'YYYY-MM-DD'
        elif format_string == '%Y-%m':
            pg_format = 'YYYY-MM'
        elif format_string == '%m-%d':
            pg_format = 'MM-DD'
        else:
            pg_format = format_string.replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD').replace('%H', 'HH24')
        
        return func.to_char(column, pg_format)
    
    elif db_type == 'sqlite':
        # SQLite使用strftime
        return func.strftime(format_string, column)
    
    else:
        # 默认使用SQLite格式，可以根据需要添加其他数据库支持
        return func.strftime(format_string, column)

def perform_database_migrations(db):
    """
    执行数据库迁移，自动添加新列
    """
    try:
        logger.info("开始数据库迁移")
        
        # 添加LicenseKey表的新列
        add_column_if_not_exists(db, 'license_key', 'calculation_type', 'VARCHAR(20)', "'fixed'")
        add_column_if_not_exists(db, 'license_key', 'calculation_value', 'FLOAT', "1.0")
        add_column_if_not_exists(db, 'license_key', 'meta_info', 'TEXT', 'NULL')
        
        logger.info("数据库迁移完成")
        return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False