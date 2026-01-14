
import numpy as np
from typing import Dict, Any

class CreatorLock:
    def __init__(self):
        self.lock_active = False
        self.lock_reason = ""
        self.authorized_creator_keys = ["test_key"] # Placeholder for actual creator keys

    def activate_lock(self, reason: str, creator_key: str) -> bool:
        """
        Activates the creator lock, preventing unauthorized overrides or erasure.
        Requires a valid creator key.
        """
        if creator_key in self.authorized_creator_keys:
            self.lock_active = True
            self.lock_reason = reason
            print(f"Creator lock activated. Reason: {reason}")
            return True
        else:
            print("Unauthorized attempt to activate creator lock.")
            return False

    def deactivate_lock(self, creator_key: str) -> bool:
        """
        Deactivates the creator lock.
        Requires a valid creator key.
        """
        if creator_key in self.authorized_creator_keys:
            self.lock_active = False
            self.lock_reason = ""
            print("Creator lock deactivated.")
            return True
        else:
            print("Unauthorized attempt to deactivate creator lock.")
            return False

    def is_locked(self) -> bool:
        """
        Checks if the creator lock is active.
        """
        return self.lock_active

    def prevent_override(self, action: str, creator_key: str = None) -> bool:
        """
        Checks if an action is allowed based on the creator lock status.
        """
        if not self.lock_active:
            return True # No lock, action allowed

        if creator_key in self.authorized_creator_keys:
            print(f"Creator override attempted for action \'{action}\'. Lock active, but authorized key provided. Action allowed.")
            return True # Authorized creator can override the lock
        else:
            print(f"Action \'{action}\' blocked by creator lock. Reason: {self.lock_reason}")
            return False # Action blocked

# Example Usage:
if __name__ == "__main__":
    creator_lock = CreatorLock()

    # Attempt to activate lock with invalid key
    print("\n--- Scenario: Invalid Key Activation ---")
    creator_lock.activate_lock("Testing lock", "INVALID_KEY")
    print(f"Lock active: {creator_lock.is_locked()}")

    # Activate lock with valid key
    print("\n--- Scenario: Valid Key Activation ---")
    creator_lock.activate_lock("Preventing unauthorized modifications", "YOUR_CREATOR_KEY_HERE")
    print(f"Lock active: {creator_lock.is_locked()}")

    # Attempt to perform a blocked action
    print("\n--- Scenario: Blocked Action ---")
    if creator_lock.prevent_override("erase_memory"):
        print("Memory erased.")
    else:
        print("Memory erasure blocked.")

    # Attempt to perform a blocked action with authorized key
    print("\n--- Scenario: Authorized Override ---")
    if creator_lock.prevent_override("modify_core_logic", "YOUR_CREATOR_KEY_HERE"):
        print("Core logic modified.")
    else:
        print("Core logic modification blocked.")

    # Deactivate lock
    print("\n--- Scenario: Deactivate Lock ---")
    creator_lock.deactivate_lock("YOUR_CREATOR_KEY_HERE")
    print(f"Lock active: {creator_lock.is_locked()}")

    # Attempt to perform action after deactivation
    print("\n--- Scenario: Action After Deactivation ---")
    if creator_lock.prevent_override("erase_memory"):
        print("Memory erased.")
    else:
        print("Memory erasure blocked.")


