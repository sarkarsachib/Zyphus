"""
DEVmind Fusion PORT System
Protocol Operations Runtime Terminal - Unified interface for all language ports and system connections
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import importlib.util
import tempfile
import threading
import queue
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortType(Enum):
    """Types of PORTs in the Fusion system"""
    LANGUAGE = "language"
    SYSTEM = "system"
    NETWORK = "network"
    QUANTUM = "quantum"
    DEVICE = "device"
    METAVERSE = "metaverse"

class PortStatus(Enum):
    """Status of a PORT"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"

@dataclass
class PortConfig:
    """Configuration for a PORT"""
    name: str
    port_type: PortType
    capabilities: List[str]
    connection_params: Dict[str, Any]
    security_level: str = "standard"
    auto_reconnect: bool = True
    timeout: float = 30.0

@dataclass
class PortMessage:
    """Message structure for PORT communication"""
    id: str
    source_port: str
    target_port: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: int = 1

class BasePORT(ABC):
    """Base class for all PORTs"""
    
    def __init__(self, config: PortConfig):
        self.config = config
        self.status = PortStatus.INACTIVE
        self.connection = None
        self.message_queue = queue.Queue()
        self.event_handlers = {}
        self.metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'uptime': 0,
            'last_activity': None
        }
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the target system"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the target system"""
        pass
    
    @abstractmethod
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Send message through this PORT"""
        pass
    
    @abstractmethod
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive message from this PORT"""
        pass
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event types"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {str(e)}")
    
    def update_metrics(self, metric_type: str, value: Any = None):
        """Update PORT metrics"""
        if metric_type in self.metrics:
            if value is not None:
                self.metrics[metric_type] = value
            else:
                self.metrics[metric_type] += 1
        
        self.metrics['last_activity'] = datetime.now()

class LanguagePORT(BasePORT):
    """PORT for programming language runtime integration"""
    
    def __init__(self, config: PortConfig, language: str, runtime_path: str):
        super().__init__(config)
        self.language = language
        self.runtime_path = runtime_path
        self.process = None
        self.temp_dir = None
    
    async def connect(self) -> bool:
        """Connect to language runtime"""
        try:
            self.status = PortStatus.CONNECTING
            
            # Create temporary directory for code execution
            self.temp_dir = tempfile.mkdtemp(prefix=f"devmind_{self.language}_")
            
            # Initialize language-specific runtime
            if self.language.lower() == 'python':
                await self._init_python_runtime()
            elif self.language.lower() == 'javascript':
                await self._init_javascript_runtime()
            elif self.language.lower() == 'rust':
                await self._init_rust_runtime()
            elif self.language.lower() == 'go':
                await self._init_go_runtime()
            else:
                await self._init_generic_runtime()
            
            self.status = PortStatus.ACTIVE
            self.emit_event('connected', {'language': self.language})
            logger.info(f"Language PORT connected: {self.language}")
            return True
            
        except Exception as e:
            self.status = PortStatus.ERROR
            logger.error(f"Failed to connect Language PORT {self.language}: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from language runtime"""
        try:
            if self.process:
                self.process.terminate()
                self.process = None
            
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
            
            self.status = PortStatus.DISCONNECTED
            self.emit_event('disconnected', {'language': self.language})
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Language PORT {self.language}: {str(e)}")
            return False
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Execute code through language runtime"""
        try:
            payload = message.payload
            code = payload.get('code', '')
            execution_mode = payload.get('mode', 'execute')
            
            if execution_mode == 'execute':
                result = await self._execute_code(code)
            elif execution_mode == 'validate':
                result = await self._validate_code(code)
            elif execution_mode == 'compile':
                result = await self._compile_code(code)
            else:
                result = {'error': f'Unknown execution mode: {execution_mode}'}
            
            self.update_metrics('messages_sent')
            return result
            
        except Exception as e:
            self.update_metrics('errors')
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive message from language runtime"""
        # For language PORTs, this would typically be used for
        # receiving runtime events, errors, or output
        try:
            if not self.message_queue.empty():
                return self.message_queue.get_nowait()
        except queue.Empty:
            pass
        return None
    
    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code in the language runtime"""
        if self.language.lower() == 'python':
            return await self._execute_python(code)
        elif self.language.lower() == 'javascript':
            return await self._execute_javascript(code)
        elif self.language.lower() == 'rust':
            return await self._execute_rust(code)
        elif self.language.lower() == 'go':
            return await self._execute_go(code)
        else:
            return {'error': f'Execution not implemented for {self.language}'}
    
    async def _execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            # Create temporary Python file
            code_file = os.path.join(self.temp_dir, 'temp_code.py')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute Python code
            process = await asyncio.create_subprocess_exec(
                sys.executable, code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'python'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'python'}
    
    async def _execute_javascript(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript code"""
        try:
            # Create temporary JavaScript file
            code_file = os.path.join(self.temp_dir, 'temp_code.js')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute JavaScript code with Node.js
            process = await asyncio.create_subprocess_exec(
                'node', code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'javascript'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'javascript'}
    
    async def _execute_rust(self, code: str) -> Dict[str, Any]:
        """Execute Rust code"""
        try:
            # Create Rust project structure
            src_dir = os.path.join(self.temp_dir, 'src')
            os.makedirs(src_dir, exist_ok=True)
            
            # Create Cargo.toml
            cargo_toml = """[package]
name = "devmind_temp"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
            with open(os.path.join(self.temp_dir, 'Cargo.toml'), 'w') as f:
                f.write(cargo_toml)
            
            # Create main.rs
            with open(os.path.join(src_dir, 'main.rs'), 'w') as f:
                f.write(code)
            
            # Compile and run
            process = await asyncio.create_subprocess_exec(
                'cargo', 'run',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'rust'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'rust'}
    
    async def _execute_go(self, code: str) -> Dict[str, Any]:
        """Execute Go code"""
        try:
            # Create temporary Go file
            code_file = os.path.join(self.temp_dir, 'main.go')
            with open(code_file, 'w') as f:
                f.write(code)
            
            # Execute Go code
            process = await asyncio.create_subprocess_exec(
                'go', 'run', code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'language': 'go'
            }
            
        except Exception as e:
            return {'error': str(e), 'language': 'go'}
    
    async def _init_python_runtime(self):
        """Initialize Python runtime"""
        # Check if Python is available
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Python runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Python runtime: {str(e)}")
    
    async def _init_javascript_runtime(self):
        """Initialize JavaScript runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'node', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Node.js runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize JavaScript runtime: {str(e)}")
    
    async def _init_rust_runtime(self):
        """Initialize Rust runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'cargo', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Rust/Cargo runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Rust runtime: {str(e)}")
    
    async def _init_go_runtime(self):
        """Initialize Go runtime"""
        try:
            process = await asyncio.create_subprocess_exec(
                'go', 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                raise Exception("Go runtime not available")
        except Exception as e:
            raise Exception(f"Failed to initialize Go runtime: {str(e)}")
    
    async def _init_generic_runtime(self):
        """Initialize generic runtime"""
        # For unsupported languages, we'll just mark as connected
        # but execution will return not implemented errors
        pass
    
    async def _validate_code(self, code: str) -> Dict[str, Any]:
        """Validate code syntax"""
        # Implementation would depend on language-specific validators
        return {'valid': True, 'message': 'Validation not implemented'}
    
    async def _compile_code(self, code: str) -> Dict[str, Any]:
        """Compile code (for compiled languages)"""
        # Implementation would depend on language-specific compilers
        return {'compiled': True, 'message': 'Compilation not implemented'}

class SystemPORT(BasePORT):
    """PORT for system-level operations"""
    
    def __init__(self, config: PortConfig):
        super().__init__(config)
        self.os_type = os.name
        self.platform = sys.platform
    
    async def connect(self) -> bool:
        """Connect to system interfaces"""
        try:
            self.status = PortStatus.CONNECTING
            
            # Initialize system connections
            self.connection = {
                'os': self.os_type,
                'platform': self.platform,
                'capabilities': self._get_system_capabilities()
            }
            
            self.status = PortStatus.ACTIVE
            self.emit_event('connected', {'system': self.platform})
            return True
            
        except Exception as e:
            self.status = PortStatus.ERROR
            logger.error(f"Failed to connect System PORT: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from system interfaces"""
        self.status = PortStatus.DISCONNECTED
        self.connection = None
        return True
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Execute system operation"""
        try:
            payload = message.payload
            operation = payload.get('operation', '')
            
            if operation == 'execute_command':
                return await self._execute_command(payload.get('command', ''))
            elif operation == 'file_operation':
                return await self._file_operation(payload)
            elif operation == 'process_management':
                return await self._process_management(payload)
            elif operation == 'system_info':
                return await self._get_system_info()
            else:
                return {'error': f'Unknown system operation: {operation}'}
                
        except Exception as e:
            self.update_metrics('errors')
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive system events"""
        try:
            if not self.message_queue.empty():
                return self.message_queue.get_nowait()
        except queue.Empty:
            pass
        return None
    
    def _get_system_capabilities(self) -> List[str]:
        """Get available system capabilities"""
        capabilities = ['command_execution', 'file_operations', 'system_info']
        
        if self.os_type == 'posix':
            capabilities.extend(['unix_commands', 'shell_access'])
        elif self.os_type == 'nt':
            capabilities.extend(['windows_commands', 'powershell_access'])
        
        return capabilities
    
    async def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute system command"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'command': command
            }
            
        except Exception as e:
            return {'error': str(e), 'command': command}
    
    async def _file_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform file operations"""
        operation = payload.get('file_operation', '')
        path = payload.get('path', '')
        
        try:
            if operation == 'read':
                with open(path, 'r') as f:
                    content = f.read()
                return {'success': True, 'content': content}
            
            elif operation == 'write':
                content = payload.get('content', '')
                with open(path, 'w') as f:
                    f.write(content)
                return {'success': True, 'message': 'File written'}
            
            elif operation == 'exists':
                exists = os.path.exists(path)
                return {'success': True, 'exists': exists}
            
            elif operation == 'list':
                if os.path.isdir(path):
                    files = os.listdir(path)
                    return {'success': True, 'files': files}
                else:
                    return {'error': 'Path is not a directory'}
            
            else:
                return {'error': f'Unknown file operation: {operation}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    async def _process_management(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Manage system processes"""
        # Implementation would include process listing, killing, monitoring
        return {'message': 'Process management not implemented'}
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import platform
        
        return {
            'success': True,
            'system_info': {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            }
        }

class NetworkPORT(BasePORT):
    """PORT for network communications"""
    
    def __init__(self, config: PortConfig):
        super().__init__(config)
        self.session = None
    
    async def connect(self) -> bool:
        """Connect to network interfaces"""
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()
            self.status = PortStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to connect Network PORT: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from network interfaces"""
        if self.session:
            await self.session.close()
        self.status = PortStatus.DISCONNECTED
        return True
    
    async def send_message(self, message: PortMessage) -> Dict[str, Any]:
        """Send network request"""
        try:
            payload = message.payload
            method = payload.get('method', 'GET').upper()
            url = payload.get('url', '')
            headers = payload.get('headers', {})
            data = payload.get('data', {})
            
            if not self.session:
                return {'error': 'Network session not initialized'}
            
            async with self.session.request(method, url, headers=headers, json=data) as response:
                response_data = await response.text()
                
                return {
                    'success': response.status < 400,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'url': url,
                    'method': method
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    async def receive_message(self) -> Optional[PortMessage]:
        """Receive network message"""
        # For network PORTs, this could be used for webhooks or real-time data
        return None

class FusionPORTManager:
    """Manager for all Fusion PORTs"""
    
    def __init__(self):
        self.ports = {}
        self.port_configs = {}
        self.message_router = {}
        self.global_metrics = {
            'total_ports': 0,
            'active_ports': 0,
            'total_messages': 0,
            'total_errors': 0
        }
    
    def register_port(self, port_name: str, port: BasePORT):
        """Register a new PORT"""
        self.ports[port_name] = port
        self.port_configs[port_name] = port.config
        self.global_metrics['total_ports'] += 1
        
        # Register event handlers
        port.register_event_handler('connected', self._on_port_connected)
        port.register_event_handler('disconnected', self._on_port_disconnected)
        port.register_event_handler('error', self._on_port_error)
        
        logger.info(f"PORT registered: {port_name}")
    
    async def connect_port(self, port_name: str) -> bool:
        """Connect a specific PORT"""
        if port_name in self.ports:
            success = await self.ports[port_name].connect()
            if success:
                self.global_metrics['active_ports'] += 1
            return success
        return False
    
    async def disconnect_port(self, port_name: str) -> bool:
        """Disconnect a specific PORT"""
        if port_name in self.ports:
            success = await self.ports[port_name].disconnect()
            if success and self.ports[port_name].status == PortStatus.ACTIVE:
                self.global_metrics['active_ports'] -= 1
            return success
        return False
    
    async def connect_all_ports(self) -> Dict[str, bool]:
        """Connect all registered PORTs"""
        results = {}
        for port_name in self.ports:
            results[port_name] = await self.connect_port(port_name)
        return results
    
    async def disconnect_all_ports(self) -> Dict[str, bool]:
        """Disconnect all PORTs"""
        results = {}
        for port_name in self.ports:
            results[port_name] = await self.disconnect_port(port_name)
        return results
    
    async def send_message(self, port_name: str, message: PortMessage) -> Dict[str, Any]:
        """Send message through specific PORT"""
        if port_name in self.ports:
            port = self.ports[port_name]
            if port.status == PortStatus.ACTIVE:
                result = await port.send_message(message)
                self.global_metrics['total_messages'] += 1
                return result
            else:
                return {'error': f'PORT {port_name} is not active'}
        else:
            return {'error': f'PORT {port_name} not found'}
    
    async def broadcast_message(self, message: PortMessage, port_types: List[PortType] = None) -> Dict[str, Any]:
        """Broadcast message to multiple PORTs"""
        results = {}
        
        for port_name, port in self.ports.items():
            if port_types and port.config.port_type not in port_types:
                continue
            
            if port.status == PortStatus.ACTIVE:
                results[port_name] = await port.send_message(message)
            else:
                results[port_name] = {'error': 'PORT not active'}
        
        return results
    
    def get_port_status(self, port_name: str = None) -> Dict[str, Any]:
        """Get status of specific PORT or all PORTs"""
        if port_name:
            if port_name in self.ports:
                port = self.ports[port_name]
                return {
                    'name': port_name,
                    'type': port.config.port_type.value,
                    'status': port.status.value,
                    'capabilities': port.config.capabilities,
                    'metrics': port.metrics
                }
            else:
                return {'error': f'PORT {port_name} not found'}
        else:
            status = {}
            for name, port in self.ports.items():
                status[name] = {
                    'type': port.config.port_type.value,
                    'status': port.status.value,
                    'capabilities': port.config.capabilities,
                    'metrics': port.metrics
                }
            return status
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global PORT system metrics"""
        return {
            **self.global_metrics,
            'port_details': {name: port.metrics for name, port in self.ports.items()}
        }
    
    def _on_port_connected(self, data: Dict[str, Any]):
        """Handle PORT connected event"""
        logger.info(f"PORT connected: {data}")
    
    def _on_port_disconnected(self, data: Dict[str, Any]):
        """Handle PORT disconnected event"""
        logger.info(f"PORT disconnected: {data}")
    
    def _on_port_error(self, data: Dict[str, Any]):
        """Handle PORT error event"""
        logger.error(f"PORT error: {data}")
        self.global_metrics['total_errors'] += 1

# Global Fusion PORT Manager instance
fusion_port_manager = FusionPORTManager()

# Initialize default PORTs
def initialize_default_ports():
    """Initialize default PORTs for common languages and systems"""
    
    # Language PORTs
    languages = [
        ('python', sys.executable),
        ('javascript', 'node'),
        ('rust', 'cargo'),
        ('go', 'go')
    ]
    
    for lang, runtime in languages:
        config = PortConfig(
            name=f"{lang}_port",
            port_type=PortType.LANGUAGE,
            capabilities=[f"{lang}_execution", "code_validation", "syntax_checking"],
            connection_params={'runtime': runtime}
        )
        port = LanguagePORT(config, lang, runtime)
        fusion_port_manager.register_port(f"{lang}_port", port)
    
    # System PORT
    system_config = PortConfig(
        name="system_port",
        port_type=PortType.SYSTEM,
        capabilities=["command_execution", "file_operations", "process_management"],
        connection_params={}
    )
    system_port = SystemPORT(system_config)
    fusion_port_manager.register_port("system_port", system_port)
    
    # Network PORT
    network_config = PortConfig(
        name="network_port",
        port_type=PortType.NETWORK,
        capabilities=["http_requests", "api_calls", "web_scraping"],
        connection_params={}
    )
    network_port = NetworkPORT(network_config)
    fusion_port_manager.register_port("network_port", network_port)

# Initialize default PORTs when module is imported
initialize_default_ports()

