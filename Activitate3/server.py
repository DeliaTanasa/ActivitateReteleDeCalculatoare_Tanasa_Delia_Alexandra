import socket
import json
import os
import threading
from datetime import datetime

# Configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
FILES_DIR = 'files'
HISTORY_FILE = 'file_history.json'
DEFAULT_USER = 'student'
DEFAULT_PASSWORD = '1234'


def ensure_files_dir():
    """Ensure files directory exists"""
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"✓ Directory '{FILES_DIR}' created")


def authenticate(username, password):
    """Authenticate user"""
    return username == DEFAULT_USER and password == DEFAULT_PASSWORD


# ==================== HISTORY MANAGEMENT ====================

def load_history():
    """Load file operation history from JSON file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_history(history):
    """Save file operation history to JSON file"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_history_entry(filename, operation, user, details=""):
    """Add an entry to the file operation history"""
    history = load_history()
    if filename not in history:
        history[filename] = []
    
    entry = {
        'operation': operation,
        'user': user,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'details': details
    }
    history[filename].append(entry)
    save_history(history)


def rename_history_entries(old_name, new_name):
    """Transfer history entries when a file is renamed"""
    history = load_history()
    if old_name in history:
        entries = history.pop(old_name)
        if new_name not in history:
            history[new_name] = []
        history[new_name] = entries + history[new_name]
    save_history(history)


# ==================== CLIENT HANDLER ====================

def handle_client(conn, addr):
    """Handle client connection"""
    print(f"\n🔗 Client connected from {addr}")
    authenticated = False
    current_user = None
    
    try:
        while True:
            # Receive request
            request_data = conn.recv(4096).decode('utf-8')
            if not request_data:
                break
            
            try:
                request = json.loads(request_data)
                command = request.get('command')
                
                print(f"📨 Command received: {command}")
                
                # Authentication
                if command == 'login':
                    username = request.get('username')
                    password = request.get('password')
                    
                    if authenticate(username, password):
                        authenticated = True
                        current_user = username
                        response = {'status': 'success', 'message': f'Welcome {username}!'}
                        print(f"✓ User {username} authenticated")
                    else:
                        response = {'status': 'error', 'message': 'Invalid credentials'}
                        print(f"✗ Authentication failed for user {username}")
                
                elif not authenticated:
                    response = {'status': 'error', 'message': 'Not authenticated. Use login first'}
                
                # ==================== EXISTING COMMANDS ====================
                
                elif command == 'create_file':
                    filename = request.get('filename')
                    content = request.get('content', '')
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    
                    add_history_entry(filename, 'CREATE', current_user, f'File created with {len(content)} characters')
                    response = {'status': 'success', 'message': f'File {filename} created on server'}
                    print(f"✓ File created: {filename}")
                
                elif command == 'upload':
                    filename = request.get('filename')
                    content = request.get('content')
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    
                    add_history_entry(filename, 'UPLOAD', current_user, f'File uploaded with {len(content)} characters')
                    response = {'status': 'success', 'message': f'File {filename} uploaded'}
                    print(f"✓ File uploaded: {filename}")
                
                # ==================== STUDENT IMPLEMENTATIONS ====================
                
                elif command == 'rename_file':
                    old_name = request.get('old_name')
                    new_name = request.get('new_name')
                    
                    if not old_name or not new_name:
                        response = {'status': 'error', 'message': 'Old name and new name are required'}
                    else:
                        old_path = os.path.join(FILES_DIR, old_name)
                        new_path = os.path.join(FILES_DIR, new_name)
                        
                        if not os.path.exists(old_path):
                            response = {'status': 'error', 'message': f'File "{old_name}" not found on server'}
                        elif os.path.exists(new_path):
                            response = {'status': 'error', 'message': f'File "{new_name}" already exists on server'}
                        else:
                            os.rename(old_path, new_path)
                            add_history_entry(new_name, 'RENAME', current_user, f'Renamed from "{old_name}" to "{new_name}"')
                            rename_history_entries(old_name, new_name)
                            response = {'status': 'success', 'message': f'File renamed from "{old_name}" to "{new_name}"'}
                            print(f"✓ File renamed: {old_name} → {new_name}")
                
                elif command == 'read_file':
                    filename = request.get('filename')
                    
                    if not filename:
                        response = {'status': 'error', 'message': 'Filename is required'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File "{filename}" not found on server'}
                        else:
                            with open(filepath, 'r') as f:
                                content = f.read()
                            add_history_entry(filename, 'READ', current_user, 'File content read')
                            response = {'status': 'success', 'message': f'Content of "{filename}":', 'content': content}
                            print(f"✓ File read: {filename}")
                
                elif command == 'download':
                    filename = request.get('filename')
                    
                    if not filename:
                        response = {'status': 'error', 'message': 'Filename is required'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File "{filename}" not found on server'}
                        else:
                            with open(filepath, 'r') as f:
                                content = f.read()
                            add_history_entry(filename, 'DOWNLOAD', current_user, f'File downloaded by {current_user}')
                            response = {'status': 'success', 'message': f'File "{filename}" downloaded', 'content': content, 'filename': filename}
                            print(f"✓ File downloaded: {filename}")
                
                elif command == 'edit_file':
                    filename = request.get('filename')
                    new_content = request.get('content')
                    
                    if not filename:
                        response = {'status': 'error', 'message': 'Filename is required'}
                    elif new_content is None:
                        response = {'status': 'error', 'message': 'New content is required'}
                    else:
                        filepath = os.path.join(FILES_DIR, filename)
                        
                        if not os.path.exists(filepath):
                            response = {'status': 'error', 'message': f'File "{filename}" not found on server'}
                        else:
                            with open(filepath, 'w') as f:
                                f.write(new_content)
                            add_history_entry(filename, 'EDIT', current_user, f'File edited, new size: {len(new_content)} characters')
                            response = {'status': 'success', 'message': f'File "{filename}" edited successfully'}
                            print(f"✓ File edited: {filename}")
                
                elif command == 'see_file_operation_history':
                    filename = request.get('filename')
                    
                    if not filename:
                        response = {'status': 'error', 'message': 'Filename is required'}
                    else:
                        history = load_history()
                        file_history = history.get(filename, [])
                        
                        if not file_history:
                            response = {'status': 'success', 'message': f'No history found for "{filename}"', 'history': []}
                        else:
                            response = {'status': 'success', 'message': f'History for "{filename}":', 'history': file_history}
                            print(f"✓ History retrieved for: {filename}")
                
                elif command == 'list_files':
                    files = os.listdir(FILES_DIR)
                    response = {'status': 'success', 'files': files}
                    print(f"✓ Files listed: {len(files)} files found")
                
                elif command == 'logout':
                    authenticated = False
                    current_user = None
                    response = {'status': 'success', 'message': 'Logged out'}
                    print(f"✓ User logged out")
                
                else:
                    response = {'status': 'error', 'message': f'Unknown command: {command}'}
                
            except Exception as e:
                response = {'status': 'error', 'message': str(e)}
                print(f"✗ Error: {str(e)}")
            
            # Send response
            conn.send(json.dumps(response).encode('utf-8'))
    
    except Exception as e:
        print(f"✗ Connection error: {str(e)}")
    finally:
        conn.close()
        print(f"🔌 Client disconnected from {addr}")


def start_server():
    """Start FTP server"""
    ensure_files_dir()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    
    print("=" * 60)
    print("🚀 FTP SERVER STARTED")
    print("=" * 60)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print(f"Files Directory: {FILES_DIR}")
    print(f"Default User: {DEFAULT_USER}")
    print(f"Default Password: {DEFAULT_PASSWORD}")
    print("=" * 60)
    
    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n\n⛔ Server shutting down...")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()