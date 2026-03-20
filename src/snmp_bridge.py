"""
SNMP Bridge - Compartilhamento global da MIB entre threads.
Permite que SC e CMC compartilhem a MIB sem SNMP.
"""

# Variável global para armazenar MIB
_global_mib = None


def set_global_mib(mib):
    """Define a MIB globalmente."""
    global _global_mib
    _global_mib = mib


def get_global_mib():
    """Obtém a MIB globalmente."""
    global _global_mib
    return _global_mib
