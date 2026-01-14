"""
DEVmind Unified Language Integration System
Provides seamless integration between all programming languages, APIs, and system components
through the .nrx language and Fusion PORT architecture
"""

import asyncio
import json
import logging
import importlib
import sys
import os
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid
import threading
import queue
import time

from .fusion_api import fusion_gateway, APIProtocol, RequestType
from .fusion_port import fusion_port_manager, PortMessage, PortType, BasePORT, PortConfig, PortStatus
from .nrx_interpreter import nrx_interpreter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationType(Enum):
    """Types of integrations supported"""
    LANGUAGE_TO_LANGUAGE = "language_to_language"
    LANGUAGE_TO_API = "language_to_api"
    API_TO_LANGUAGE = "api_to_language"
    SYSTEM_TO_LANGUAGE = "system_to_language"
    NRX_TO_ALL = "nrx_to_all"
    ALL_TO_NRX = "all_to_nrx"

class IntegrationMode(Enum):
    """Integration execution modes"""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    PIPELINE = "pipeline"
    BROADCAST = "broadcast"
    CHAIN = "chain"

@dataclass
class IntegrationRequest:
    """Request for unified integration"""
    id: str
    integration_type: IntegrationType
    mode: IntegrationMode
    source: str
    target: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    priority: int = 1

@dataclass
class IntegrationResponse:
    """Response from unified integration"""
    request_id: str
    success: bool
    results: List[Dict[str, Any]]
    errors: List[str]
    execution_time: float
    integration_path: List[str]
    timestamp: datetime

class LanguageBridge:
    """Bridge for cross-language communication"""
    
    def __init__(self):
        self.language_mappings = {}
        self.type_converters = {}
        self.serializers = {}
        
    def register_language_mapping(self, from_lang: str, to_lang: str, converter: Callable):
        """Register a language-to-language converter"""
        key = f"{from_lang}_to_{to_lang}"
        self.language_mappings[key] = converter
        logger.info(f"Language mapping registered: {key}")
    
    def register_type_converter(self, from_type: str, to_type: str, converter: Callable):
        """Register a type converter"""
        key = f"{from_type}_to_{to_type}"
        self.type_converters[key] = converter
        logger.info(f"Type converter registered: {key}")
    
    async def convert_between_languages(self, source_lang: str, target_lang: str, 
                                      code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert code from one language to another"""
        try:
            mapping_key = f"{source_lang}_to_{target_lang}"
            
            if mapping_key in self.language_mappings:
                # Use registered converter
                converter = self.language_mappings[mapping_key]
                result = await converter(code, context or {})
                return {
                    'success': True,
                    'converted_code': result,
                    'source_language': source_lang,
                    'target_language': target_lang
                }
            else:
                # Use AI-powered conversion through .nrx
                nrx_code = f"""
define AI CodeConverter:
    brain use fusion
    emotion set "analytical"

convert code:
    from: "{source_lang}"
    to: "{target_lang}"
    source: "{code}"
    context: {json.dumps(context or {})}
"""
                
                result = await nrx_interpreter.execute(nrx_code)
                
                if result['success']:
                    return {
                        'success': True,
                        'converted_code': result.get('results', [{}])[0].get('converted_code', ''),
                        'source_language': source_lang,
                        'target_language': target_lang,
                        'ai_converted': True
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'Conversion failed'),
                        'source_language': source_lang,
                        'target_language': target_lang
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source_language': source_lang,
                'target_language': target_lang
            }
    
    def convert_data_types(self, data: Any, from_type: str, to_type: str) -> Any:
        """Convert data between different type systems"""
        converter_key = f"{from_type}_to_{to_type}"
        
        if converter_key in self.type_converters:
            converter = self.type_converters[converter_key]
            return converter(data)
        
        # Default conversions
        if from_type == 'python' and to_type == 'javascript':
            return self._python_to_javascript(data)
        elif from_type == 'javascript' and to_type == 'python':
            return self._javascript_to_python(data)
        elif from_type == 'json' and to_type == 'python':
            return json.loads(data) if isinstance(data, str) else data
        elif from_type == 'python' and to_type == 'json':
            return json.dumps(data)
        else:
            return data
    
    def _python_to_javascript(self, data: Any) -> Any:
        """Convert Python data to JavaScript-compatible format"""
        if isinstance(data, dict):
            return {k: self._python_to_javascript(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._python_to_javascript(item) for item in data]
        elif isinstance(data, tuple):
            return [self._python_to_javascript(item) for item in data]
        elif data is None:
            return None
        elif isinstance(data, bool):
            return data
        elif isinstance(data, (int, float, str)):
            return data
        else:
            return str(data)
    
    def _javascript_to_python(self, data: Any) -> Any:
        """Convert JavaScript data to Python-compatible format"""
        # Similar conversion logic but in reverse
        return data

class APIBridge:
    """Bridge for API integration and communication"""
    
    def __init__(self):
        self.api_mappings = {}
        self.protocol_converters = {}
        
    def register_api_mapping(self, api_name: str, config: Dict[str, Any]):
        """Register an API mapping"""
        self.api_mappings[api_name] = config
        logger.info(f"API mapping registered: {api_name}")
    
    async def call_api_from_language(self, language: str, api_name: str, 
                                   method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call API from a specific language context"""
        try:
            # Get API configuration
            if api_name not in self.api_mappings:
                return {'success': False, 'error': f'API {api_name} not registered'}
            
            api_config = self.api_mappings[api_name]
            
            # Convert language-specific data to API format
            converted_data = self._convert_language_data_to_api(language, data, api_config)
            
            # Make API call through Fusion API
            request_data = {
                'endpoint': api_config.get('endpoint', '/api/default'),
                'method': method,
                'data': converted_data,
                'headers': api_config.get('headers', {})
            }
            
            response = await fusion_gateway.process_request(request_data, APIProtocol.REST)
            
            # Convert API response back to language format
            converted_response = self._convert_api_response_to_language(language, response.data, api_config)
            
            return {
                'success': response.success,
                'data': converted_response,
                'api_name': api_name,
                'language': language,
                'execution_time': response.execution_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'api_name': api_name,
                'language': language
            }
    
    def _convert_language_data_to_api(self, language: str, data: Dict[str, Any], 
                                    api_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert language-specific data to API format"""
        # Apply language-specific conversions
        if language == 'python':
            # Python data is usually already in the right format
            return data
        elif language == 'javascript':
            # Convert JavaScript data structures
            return self._normalize_javascript_data(data)
        elif language == 'rust':
            # Convert Rust data structures
            return self._normalize_rust_data(data)
        else:
            return data
    
    def _convert_api_response_to_language(self, language: str, response_data: Dict[str, Any], 
                                        api_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API response to language-specific format"""
        # Apply language-specific response formatting
        if language == 'python':
            return response_data
        elif language == 'javascript':
            return self._format_for_javascript(response_data)
        elif language == 'rust':
            return self._format_for_rust(response_data)
        else:
            return response_data
    
    def _normalize_javascript_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize JavaScript data for API consumption"""
        return data
    
    def _normalize_rust_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Rust data for API consumption"""
        return data
    
    def _format_for_javascript(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format response data for JavaScript consumption"""
        return data
    
    def _format_for_rust(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format response data for Rust consumption"""
        return data

class SystemBridge:
    """Bridge for system-level integration"""
    
    def __init__(self):
        self.system_hooks = {}
        self.event_listeners = {}
        
    def register_system_hook(self, hook_name: str, handler: Callable):
        """Register a system hook"""
        self.system_hooks[hook_name] = handler
        logger.info(f"System hook registered: {hook_name}")
    
    def register_event_listener(self, event_type: str, listener: Callable):
        """Register an event listener"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(listener)
        logger.info(f"Event listener registered for: {event_type}")
    
    async def execute_system_integration(self, operation: str, 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system-level integration"""
        try:
            if operation in self.system_hooks:
                handler = self.system_hooks[operation]
                result = await handler(context)
                return {
                    'success': True,
                    'result': result,
                    'operation': operation
                }
            else:
                # Use system PORT for operation
                message = PortMessage(
                    id=str(uuid.uuid4()),
                    source_port='integration_system',
                    target_port='system_port',
                    message_type='system_operation',
                    payload={'operation': operation, **context},
                    timestamp=datetime.now()
                )
                
                result = await fusion_port_manager.send_message('system_port', message)
                
                return {
                    'success': 'error' not in result,
                    'result': result,
                    'operation': operation
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation': operation
            }
    
    def emit_system_event(self, event_type: str, data: Dict[str, Any]):
        """Emit system event to all listeners"""
        if event_type in self.event_listeners:
            for listener in self.event_listeners[event_type]:
                try:
                    listener(data)
                except Exception as e:
                    logger.error(f"Event listener error: {str(e)}")

class UnifiedIntegrationEngine:
    """Main engine for unified language and system integration"""
    
    def __init__(self):
        self.language_bridge = LanguageBridge()
        self.api_bridge = APIBridge()
        self.system_bridge = SystemBridge()
        self.integration_history = []
        self.active_integrations = {}
        self.integration_metrics = {
            'total_integrations': 0,
            'successful_integrations': 0,
            'failed_integrations': 0,
            'average_execution_time': 0.0
        }
        
        # Initialize default integrations
        self._initialize_default_integrations()
    
    def _initialize_default_integrations(self):
        """Initialize default integration mappings"""
        
        # Register default language converters
        self.language_bridge.register_language_mapping(
            'python', 'javascript', self._python_to_javascript_converter
        )
        self.language_bridge.register_language_mapping(
            'javascript', 'python', self._javascript_to_python_converter
        )
        
        # Register default API mappings
        self.api_bridge.register_api_mapping('devmind_core', {
            'endpoint': '/api/fusion',
            'headers': {'Content-Type': 'application/json'},
            'auth_required': False
        })
        
        # Register default system hooks
        self.system_bridge.register_system_hook('file_sync', self._file_sync_handler)
        self.system_bridge.register_system_hook('process_monitor', self._process_monitor_handler)
        
        logger.info("Default integrations initialized")
    
    async def process_integration_request(self, request: IntegrationRequest) -> IntegrationResponse:
        """Process a unified integration request"""
        start_time = time.time()
        
        try:
            self.active_integrations[request.id] = request
            
            # Route to appropriate integration handler
            if request.integration_type == IntegrationType.LANGUAGE_TO_LANGUAGE:
                results = await self._handle_language_to_language(request)
            elif request.integration_type == IntegrationType.LANGUAGE_TO_API:
                results = await self._handle_language_to_api(request)
            elif request.integration_type == IntegrationType.API_TO_LANGUAGE:
                results = await self._handle_api_to_language(request)
            elif request.integration_type == IntegrationType.SYSTEM_TO_LANGUAGE:
                results = await self._handle_system_to_language(request)
            elif request.integration_type == IntegrationType.NRX_TO_ALL:
                results = await self._handle_nrx_to_all(request)
            elif request.integration_type == IntegrationType.ALL_TO_NRX:
                results = await self._handle_all_to_nrx(request)
            else:
                results = [{'error': f'Unknown integration type: {request.integration_type}'}]
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Determine success
            success = all('error' not in result for result in results)
            errors = [result.get('error', '') for result in results if 'error' in result]
            
            # Create response
            response = IntegrationResponse(
                request_id=request.id,
                success=success,
                results=results,
                errors=errors,
                execution_time=execution_time,
                integration_path=self._build_integration_path(request),
                timestamp=datetime.now()
            )
            
            # Update metrics
            self._update_metrics(success, execution_time)
            
            # Store in history
            self.integration_history.append({
                'request': asdict(request),
                'response': asdict(response)
            })
            
            # Clean up
            if request.id in self.active_integrations:
                del self.active_integrations[request.id]
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            response = IntegrationResponse(
                request_id=request.id,
                success=False,
                results=[],
                errors=[str(e)],
                execution_time=execution_time,
                integration_path=[],
                timestamp=datetime.now()
            )
            
            self._update_metrics(False, execution_time)
            
            if request.id in self.active_integrations:
                del self.active_integrations[request.id]
            
            return response
    
    async def _handle_language_to_language(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle language-to-language integration"""
        source_lang = request.source
        target_lang = request.target
        code = request.payload.get('code', '')
        context = request.payload.get('context', {})
        
        result = await self.language_bridge.convert_between_languages(
            source_lang, target_lang, code, context
        )
        
        return [result]
    
    async def _handle_language_to_api(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle language-to-API integration"""
        language = request.source
        api_name = request.target
        method = request.payload.get('method', 'POST')
        data = request.payload.get('data', {})
        
        result = await self.api_bridge.call_api_from_language(
            language, api_name, method, data
        )
        
        return [result]
    
    async def _handle_api_to_language(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle API-to-language integration"""
        api_name = request.source
        language = request.target
        
        # This would involve calling an API and then formatting the response for a specific language
        # For now, we'll simulate this
        result = {
            'success': True,
            'message': f'API {api_name} response formatted for {language}',
            'data': request.payload
        }
        
        return [result]
    
    async def _handle_system_to_language(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle system-to-language integration"""
        operation = request.source
        language = request.target
        context = request.payload
        
        # Execute system operation
        system_result = await self.system_bridge.execute_system_integration(operation, context)
        
        # Format result for target language
        if system_result['success']:
            formatted_result = self.language_bridge.convert_data_types(
                system_result['result'], 'system', language
            )
            
            return [{
                'success': True,
                'system_operation': operation,
                'target_language': language,
                'result': formatted_result
            }]
        else:
            return [system_result]
    
    async def _handle_nrx_to_all(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle .nrx to all systems integration"""
        nrx_code = request.payload.get('nrx_code', '')
        targets = request.payload.get('targets', ['python', 'javascript', 'system'])
        
        # Execute .nrx code
        nrx_result = await nrx_interpreter.execute(nrx_code)
        
        if not nrx_result['success']:
            return [nrx_result]
        
        results = []
        
        # Distribute results to all targets
        for target in targets:
            if target in ['python', 'javascript', 'rust', 'go']:
                # Send to language PORT
                message = PortMessage(
                    id=str(uuid.uuid4()),
                    source_port='nrx_integration',
                    target_port=f'{target}_port',
                    message_type='nrx_result',
                    payload={
                        'nrx_result': nrx_result,
                        'target_language': target
                    },
                    timestamp=datetime.now()
                )
                
                port_result = await fusion_port_manager.send_message(f'{target}_port', message)
                results.append({
                    'target': target,
                    'type': 'language',
                    'result': port_result
                })
                
            elif target == 'system':
                # Send to system PORT
                message = PortMessage(
                    id=str(uuid.uuid4()),
                    source_port='nrx_integration',
                    target_port='system_port',
                    message_type='nrx_result',
                    payload={'nrx_result': nrx_result},
                    timestamp=datetime.now()
                )
                
                system_result = await fusion_port_manager.send_message('system_port', message)
                results.append({
                    'target': target,
                    'type': 'system',
                    'result': system_result
                })
        
        return results
    
    async def _handle_all_to_nrx(self, request: IntegrationRequest) -> List[Dict[str, Any]]:
        """Handle all systems to .nrx integration"""
        sources = request.payload.get('sources', {})
        
        # Collect data from all sources
        collected_data = {}
        
        for source_name, source_config in sources.items():
            if source_config.get('type') == 'language':
                # Get data from language PORT
                message = PortMessage(
                    id=str(uuid.uuid4()),
                    source_port='integration_collector',
                    target_port=f"{source_name}_port",
                    message_type='data_request',
                    payload=source_config.get('request', {}),
                    timestamp=datetime.now()
                )
                
                result = await fusion_port_manager.send_message(f"{source_name}_port", message)
                collected_data[source_name] = result
                
            elif source_config.get('type') == 'system':
                # Get data from system PORT
                message = PortMessage(
                    id=str(uuid.uuid4()),
                    source_port='integration_collector',
                    target_port='system_port',
                    message_type='data_request',
                    payload=source_config.get('request', {}),
                    timestamp=datetime.now()
                )
                
                result = await fusion_port_manager.send_message('system_port', message)
                collected_data[source_name] = result
        
        # Generate .nrx code from collected data
        nrx_code = self._generate_nrx_from_data(collected_data)
        
        # Execute generated .nrx code
        nrx_result = await nrx_interpreter.execute(nrx_code)
        
        return [{
            'success': True,
            'collected_data': collected_data,
            'generated_nrx': nrx_code,
            'nrx_result': nrx_result
        }]
    
    def _generate_nrx_from_data(self, data: Dict[str, Any]) -> str:
        """Generate .nrx code from collected data"""
        # This is a simplified example - in a real implementation,
        # this would use AI to generate appropriate .nrx code
        
        nrx_lines = [
            "# Generated .nrx code from integrated data",
            "define AI DataProcessor:",
            "    brain use fusion",
            "    emotion set \"analytical\"",
            ""
        ]
        
        for source, source_data in data.items():
            nrx_lines.append(f"process {source}:")
            nrx_lines.append(f"    data: {json.dumps(source_data)}")
            nrx_lines.append("")
        
        return "\n".join(nrx_lines)
    
    def _build_integration_path(self, request: IntegrationRequest) -> List[str]:
        """Build integration execution path"""
        path = [request.source]
        
        if request.mode == IntegrationMode.CHAIN:
            # For chain mode, add intermediate steps
            path.extend(['nrx_interpreter', 'fusion_api'])
        elif request.mode == IntegrationMode.PIPELINE:
            # For pipeline mode, add processing steps
            path.extend(['data_converter', 'format_adapter'])
        
        path.append(request.target)
        return path
    
    def _update_metrics(self, success: bool, execution_time: float):
        """Update integration metrics"""
        self.integration_metrics['total_integrations'] += 1
        
        if success:
            self.integration_metrics['successful_integrations'] += 1
        else:
            self.integration_metrics['failed_integrations'] += 1
        
        # Update average execution time
        total = self.integration_metrics['total_integrations']
        current_avg = self.integration_metrics['average_execution_time']
        self.integration_metrics['average_execution_time'] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    # Default converter implementations
    async def _python_to_javascript_converter(self, code: str, context: Dict[str, Any]) -> str:
        """Convert Python code to JavaScript"""
        # This is a simplified converter - in reality, this would be much more sophisticated
        js_code = code.replace('print(', 'console.log(')
        js_code = js_code.replace('def ', 'function ')
        js_code = js_code.replace(':', ' {')
        js_code = js_code.replace('    ', '  ')  # Adjust indentation
        return js_code + '\n}'  # Close function
    
    async def _javascript_to_python_converter(self, code: str, context: Dict[str, Any]) -> str:
        """Convert JavaScript code to Python"""
        # This is a simplified converter
        py_code = code.replace('console.log(', 'print(')
        py_code = py_code.replace('function ', 'def ')
        py_code = py_code.replace(' {', ':')
        py_code = py_code.replace('}', '')  # Remove closing braces
        return py_code
    
    async def _file_sync_handler(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file synchronization"""
        return {
            'operation': 'file_sync',
            'status': 'completed',
            'files_synced': context.get('files', [])
        }
    
    async def _process_monitor_handler(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process monitoring"""
        return {
            'operation': 'process_monitor',
            'status': 'active',
            'processes': context.get('processes', [])
        }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration system status"""
        return {
            'active_integrations': len(self.active_integrations),
            'total_history': len(self.integration_history),
            'metrics': self.integration_metrics,
            'language_mappings': len(self.language_bridge.language_mappings),
            'api_mappings': len(self.api_bridge.api_mappings),
            'system_hooks': len(self.system_bridge.system_hooks),
            'timestamp': datetime.now().isoformat()
        }

# Global unified integration engine instance
unified_integration_engine = UnifiedIntegrationEngine()

