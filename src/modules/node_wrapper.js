
const fs = require('fs');
const path = require('path');

class ModuleExecutor {
    constructor() {
        this.loadedModules = {};
    }
    
    async loadModule(modulePath) {
        try {
            delete require.cache[require.resolve(modulePath)];
            const module = require(modulePath);
            this.loadedModules[path.basename(modulePath, '.js')] = module;
            return { success: true, module: module };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async executeFunction(moduleName, functionName, args = []) {
        try {
            const module = this.loadedModules[moduleName];
            if (!module) {
                return { success: false, error: 'Module not loaded' };
            }
            
            const func = module[functionName];
            if (typeof func !== 'function') {
                return { success: false, error: 'Function not found' };
            }
            
            const result = await func(...args);
            return { success: true, result: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    getModuleInfo(moduleName) {
        const module = this.loadedModules[moduleName];
        if (!module) {
            return { success: false, error: 'Module not loaded' };
        }
        
        return {
            success: true,
            exports: Object.keys(module),
            type: typeof module
        };
    }
}

// Handle process communication
process.on('message', async (message) => {
    const executor = new ModuleExecutor();
    
    try {
        const { action, data } = message;
        let result;
        
        switch (action) {
            case 'load':
                result = await executor.loadModule(data.path);
                break;
            case 'execute':
                result = await executor.executeFunction(data.module, data.function, data.args);
                break;
            case 'info':
                result = executor.getModuleInfo(data.module);
                break;
            default:
                result = { success: false, error: 'Unknown action' };
        }
        
        process.send({ id: message.id, result: result });
    } catch (error) {
        process.send({ id: message.id, result: { success: false, error: error.message } });
    }
});

console.log('Node.js module executor ready');
