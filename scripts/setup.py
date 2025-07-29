#!/usr/bin/env python3
"""
AVBook Python版本项目设置脚本
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """运行命令"""
    print(f"运行命令: {command}")
    if isinstance(command, str):
        command = command.split()
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def check_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 9):
        print("❌ Python版本需要3.9或更高")
        sys.exit(1)
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查pip
    try:
        subprocess.run(["pip", "--version"], check=True, capture_output=True)
        print("✅ pip已安装")
    except subprocess.CalledProcessError:
        print("❌ pip未安装")
        sys.exit(1)
    
    # 检查Node.js
    try:
        result = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True)
        node_version = result.stdout.strip()
        print(f"✅ Node.js版本: {node_version}")
    except subprocess.CalledProcessError:
        print("❌ Node.js未安装，请安装Node.js 16+")
        sys.exit(1)
    
    # 检查npm
    try:
        result = subprocess.run(["npm", "--version"], check=True, capture_output=True, text=True)
        npm_version = result.stdout.strip()
        print(f"✅ npm版本: {npm_version}")
    except subprocess.CalledProcessError:
        print("❌ npm未安装")
        sys.exit(1)


def setup_backend():
    """设置后端环境"""
    print("\n🐍 设置Django后端...")
    
    backend_dir = Path("backend")
    
    # 创建虚拟环境
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print("创建虚拟环境...")
        run_command(f"python -m venv {venv_dir}")
    
    # 激活虚拟环境的pip路径
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip"
        python_path = venv_dir / "Scripts" / "python"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # 安装依赖
    print("安装Python依赖...")
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt", cwd=backend_dir)
    
    # 创建环境变量文件
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print("创建环境变量文件...")
        env_content = """# Django设置
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库设置
DB_NAME=avbook_py
DB_USER=root
DB_PASSWORD=root-1234
DB_HOST=127.0.0.1
DB_PORT=3306

# Redis设置
REDIS_URL=redis://localhost:6379/0

# Celery设置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"""
        env_file.write_text(env_content)
    
    # 创建日志目录
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Django后端设置完成")


def setup_crawler():
    """设置爬虫环境"""
    print("\n🕷️ 设置Scrapy爬虫...")
    
    crawler_dir = Path("crawler")
    
    # 创建虚拟环境
    venv_dir = crawler_dir / "venv"
    if not venv_dir.exists():
        print("创建爬虫虚拟环境...")
        run_command(f"python -m venv {venv_dir}")
    
    # 激活虚拟环境的pip路径
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip"
    else:
        pip_path = venv_dir / "bin" / "pip"
    
    # 安装依赖
    print("安装爬虫依赖...")
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt", cwd=crawler_dir)
    
    # 创建输出目录
    output_dir = crawler_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    logs_dir = crawler_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Scrapy爬虫设置完成")


def setup_frontend():
    """设置前端环境"""
    print("\n⚛️ 设置React前端...")
    
    frontend_dir = Path("frontend")
    
    # 安装依赖
    print("安装前端依赖...")
    run_command("npm install", cwd=frontend_dir)
    
    # 创建环境变量文件
    env_file = frontend_dir / ".env"
    if not env_file.exists():
        print("创建前端环境变量文件...")
        env_content = """REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_TITLE=AVBook
REACT_APP_VERSION=1.0.0
"""
        env_file.write_text(env_content)
    
    print("✅ React前端设置完成")


def setup_database():
    """设置数据库"""
    print("\n🗄️ 设置数据库...")
    
    # 创建数据库初始化脚本
    db_script = Path("scripts") / "init_database.sql"
    if not db_script.exists():
        print("创建数据库初始化脚本...")
        db_content = """-- 创建数据库
CREATE DATABASE IF NOT EXISTS avbook_py CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（如果需要）
-- CREATE USER 'avbook'@'localhost' IDENTIFIED BY 'avbook_password';
-- GRANT ALL PRIVILEGES ON avbook_py.* TO 'avbook'@'localhost';
-- FLUSH PRIVILEGES;

USE avbook_py;

-- 数据库已创建，Django迁移将创建表结构
SELECT 'Database avbook_py created successfully' AS message;
"""
        db_script.write_text(db_content)
    
    print("✅ 数据库脚本已创建")
    print("📝 请手动执行以下步骤:")
    print("   1. 确保MySQL服务正在运行")
    print("   2. 使用root用户连接MySQL")
    print(f"   3. 执行脚本: mysql -u root -p < {db_script}")


def create_start_scripts():
    """创建启动脚本"""
    print("\n📜 创建启动脚本...")
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    # Windows启动脚本
    if platform.system() == "Windows":
        start_script = scripts_dir / "start.bat"
        start_content = """@echo off
echo Starting AVBook services...

echo Starting Django backend...
start "Django" cmd /k "cd backend && venv\\Scripts\\activate && python manage.py runserver"

echo Starting Celery worker...
start "Celery" cmd /k "cd backend && venv\\Scripts\\activate && celery -A avbook worker -l info"

echo Starting React frontend...
start "React" cmd /k "cd frontend && npm start"

echo All services started!
pause
"""
        start_script.write_text(start_content)
    
    # Unix启动脚本
    else:
        start_script = scripts_dir / "start.sh"
        start_content = """#!/bin/bash
echo "Starting AVBook services..."

echo "Starting Django backend..."
cd backend
source venv/bin/activate
python manage.py runserver &
DJANGO_PID=$!

echo "Starting Celery worker..."
celery -A avbook worker -l info &
CELERY_PID=$!

echo "Starting React frontend..."
cd ../frontend
npm start &
REACT_PID=$!

echo "All services started!"
echo "Django PID: $DJANGO_PID"
echo "Celery PID: $CELERY_PID"
echo "React PID: $REACT_PID"

# 等待用户输入停止服务
read -p "Press Enter to stop all services..."

echo "Stopping services..."
kill $DJANGO_PID $CELERY_PID $REACT_PID
echo "All services stopped."
"""
        start_script.write_text(start_content)
        start_script.chmod(0o755)
    
    print(f"✅ 启动脚本已创建: {start_script}")


def main():
    """主函数"""
    print("🚀 AVBook Python版本项目设置")
    print("=" * 50)
    
    # 检查当前目录
    if not Path("backend").exists() or not Path("frontend").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    try:
        check_requirements()
        setup_backend()
        setup_crawler()
        setup_frontend()
        setup_database()
        create_start_scripts()
        
        print("\n🎉 项目设置完成!")
        print("\n📋 下一步操作:")
        print("1. 启动MySQL和Redis服务")
        print("2. 执行数据库初始化脚本")
        print("3. 运行Django迁移: cd backend && python manage.py migrate")
        print("4. 创建超级用户: cd backend && python manage.py createsuperuser")
        print("5. 使用启动脚本启动所有服务")
        
    except KeyboardInterrupt:
        print("\n❌ 设置被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 设置过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
