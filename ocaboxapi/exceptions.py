class OcaboxServerError(Exception):
    pass

class OcaboxAccessDenied(Exception):
    pass

class CameraBusy(OcaboxServerError):
    """Camera busy with another operation (e.g. acquisition in progress)."""
    pass
