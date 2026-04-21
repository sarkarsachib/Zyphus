"""
Adapter for TypeEvolver compatibility
Wraps TypeEvolverV3 to provide the interface expected by nishkraman/awaken.py
"""
from src.type_evolver_v3 import TypeEvolverV3


class TypeEvolver:
    """Adapter class mapping TypeEvolver -> TypeEvolverV3"""
    
    def __init__(self):
        self._engine = TypeEvolverV3()
        self.initialized = False
    
    async def initialize(self):
        """Initialize the evolution engine"""
        await self._engine.initialize()
        self.initialized = True
        return {"success": True}