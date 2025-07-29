"""
Script to setup MySQL database for AVBook.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avbook.settings')

def setup_mysql():
    """设置MySQL数据库"""
    print("=== AVBook MySQL 数据库设置 ===")
    
    # 检查MySQL连接
    try:
        import pymysql
        print("✅ PyMySQL 已安装")
    except ImportError:
        print("❌ PyMySQL 未安装，请运行: pip install pymysql")
        return False
    
    # 数据库配置信息
    db_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'root-1234',
        'database': 'avbook_py',
        'charset': 'utf8mb4'
    }
    
    print(f"数据库配置:")
    print(f"  主机: {db_config['host']}:{db_config['port']}")
    print(f"  用户: {db_config['user']}")
    print(f"  数据库: {db_config['database']}")
    
    # 测试连接
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            charset=db_config['charset']
        )
        
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 数据库 {db_config['database']} 创建成功")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}")
        print("请确保:")
        print("1. MySQL 服务器正在运行")
        print("2. 用户名和密码正确")
        print("3. 用户有创建数据库的权限")
        return False
    
    print("\n=== 数据库迁移 ===")
    
    # 切换到MySQL配置
    print("切换到MySQL配置...")
    
    # 这里需要手动修改settings.py中的数据库配置
    print("请手动修改 backend/avbook/settings.py 中的数据库配置:")
    print("""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'avbook_py',
        'USER': 'root',
        'PASSWORD': 'root-1234',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
    """)
    
    return True

def migrate_data():
    """迁移数据到MySQL"""
    print("\n=== 数据迁移 ===")
    
    try:
        # 运行迁移
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ 数据库迁移完成")
        
        # 创建超级用户
        print("\n创建超级用户...")
        execute_from_command_line(['manage.py', 'createsuperuser', '--noinput', '--username=admin', '--email=admin@avbook.com'])
        print("✅ 超级用户创建完成 (用户名: admin)")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False
    
    return True

if __name__ == '__main__':
    if setup_mysql():
        print("\n✅ MySQL 设置完成!")
        print("\n下一步:")
        print("1. 修改 settings.py 中的数据库配置")
        print("2. 运行: python manage.py migrate")
        print("3. 运行: python manage.py createsuperuser")
        print("4. 运行爬虫导入数据")
    else:
        print("\n❌ MySQL 设置失败!")
        print("继续使用 SQLite 数据库")
