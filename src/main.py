import os
import sys
import asyncio
import logging
from datetime import datetime
import click

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import core systems
from src.nrx_interpreter import nrx_interpreter
from src.custom_kernel import devmind_kernel
from src.custom_terminal import devmind_terminal
from src.js_module_bridge_fixed import js_bridge

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Utility Functions ---

def run_async(coro):
    """Helper function to run async functions in a synchronous context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def initialize_systems():
    """Initialize all core DEVmind systems"""
    logger.info("Initializing core DEVmind systems...")
    
    # Database initialization (requires app context, which we simulate here)
    # Since we removed Flask, we need to manually handle the DB setup if needed.
    # For a pure CLI, we can skip the Flask-SQLAlchemy part and just ensure the DB file exists.
    # For now, we'll assume the DB file is handled by the core components if they need it.
    
    nrx_result = run_async(nrx_interpreter.initialize())
    kernel_result = run_async(devmind_kernel.initialize())
    terminal_result = run_async(devmind_terminal.initialize())
    js_bridge_result = run_async(js_bridge.initialize())
    
    if all([nrx_result['success'], kernel_result['success'], terminal_result['success'], js_bridge_result['success']]):
        logger.info("All core systems initialized successfully.")
        return True
    else:
        logger.error("Failed to initialize all core systems.")
        logger.error(f"NRX: {nrx_result}")
        logger.error(f"Kernel: {kernel_result}")
        logger.error(f"Terminal: {terminal_result}")
        logger.error(f"JS Bridge: {js_bridge_result}")
        return False

# --- CLI Implementation with Click ---

@click.group()
def cli():
    """DEVmind Fusion Engine CLI"""
    pass

@cli.command()
def init():
    """Initializes all core DEVmind systems."""
    if initialize_systems():
        click.echo(click.style("DEVmind Fusion Engine initialized and ready.", fg='green'))
    else:
        click.echo(click.style("DEVmind Fusion Engine initialization failed. Check logs for details.", fg='red'))

@cli.command()
def status():
    """Checks the status of the core DEVmind systems."""
    click.echo(click.style("--- DEVmind Fusion Engine Status ---", fg='cyan'))
    click.echo(f"Version: 2.0.0")
    click.echo(f"Timestamp: {datetime.now().isoformat()}")
    
    # Ensure systems are initialized before checking health
    if not initialize_systems():
        click.echo(click.style("Warning: Systems may not be fully initialized", fg='yellow'))
    
    # Run a quick health check
    health_status = run_async(health_check_core())
    
    click.echo(click.style("\n--- Component Health Check ---", fg='cyan'))
    for component, status in health_status['component_health'].items():
        color = 'green' if status else 'red'
        click.echo(f"{component:<20}: {click.style('OK' if status else 'FAIL', fg=color)}")
    
    overall_color = 'green' if health_status['overall_health'] else 'red'
    click.echo(f"\nOverall Health: {click.style('HEALTHY' if health_status['overall_health'] else 'UNHEALTHY', fg=overall_color)}")

@cli.command()
@click.argument('nrx_code')
def execute(nrx_code):
    """Executes a single line of NRX code."""
    click.echo(f"Executing NRX code: {nrx_code}")
    result = run_async(nrx_interpreter.execute_nrx_code(nrx_code))
    
    if result['success']:
        click.echo(click.style("Execution Successful:", fg='green'))
        click.echo(f"Result: {result.get('result', 'None')}")
    else:
        click.echo(click.style("Execution Failed:", fg='red'))
        click.echo(f"Error: {result.get('error', 'Unknown Error')}")

# Helper function for health check logic (extracted from old main.py)
async def health_check_core():
    """Comprehensive health check of all systems (async)."""
    health_status = {
        'nrx_interpreter': False,
        'custom_kernel': False,
        'custom_terminal': False,
        'js_modules_bridge': False
    }
    
    # Test basic functionality
    try:
        nrx_test = await nrx_interpreter.execute_nrx_code('print("Health check")')
        health_status['nrx_interpreter'] = nrx_test['success']
    except Exception as e:
        logger.error(f"NRX Health Check Failed: {e}")
        health_status['nrx_interpreter'] = False
    
    try:
        kernel_test = await devmind_kernel.execute_command('get_status')
        # Assuming execute_command returns a truthy value on success
        health_status['custom_kernel'] = True
    except Exception as e:
        logger.error(f"Kernel Health Check Failed: {e}")
        health_status['custom_kernel'] = False
    
    try:
        terminal_test = await devmind_terminal.execute_command('echo "Health check"')
        health_status['custom_terminal'] = terminal_test.success
    except Exception as e:
        logger.error(f"Terminal Health Check Failed: {e}")
        health_status['custom_terminal'] = False
    
    try:
        js_test = await js_bridge.test_module('smart_terminal')
        health_status['js_modules_bridge'] = js_test['test_success']
    except Exception as e:
        logger.error(f"JS Bridge Health Check Failed: {e}")
        health_status['js_modules_bridge'] = False
    
    overall_health = all(health_status.values())
    
    return {
        'overall_health': overall_health,
        'component_health': health_status,
        'healthy_components': sum(health_status.values()),
        'total_components': len(health_status),
    }

if __name__ == '__main__':
    cli()
