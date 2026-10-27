"""Compatibility layer for ASTRO's optional crytic-compile XBlock config."""

try:
    from crytic_compile.localize import config as _project_config
except ModuleNotFoundError as error:
    if error.name not in {"crytic_compile.localize", "crytic_compile.localize.config"}:
        raise
    _project_config = None


_UNSUPPORTED_XBLOCK = (
    "XBlock mode requires the project-specific crytic_compile.localize extension; "
    "install the ASTRO-compatible crytic-compile fork to use -xblock."
)


def get_xblock():
    if _project_config is None:
        return False
    return _project_config.get_xblock()


def use_xblock():
    if _project_config is None:
        raise RuntimeError(_UNSUPPORTED_XBLOCK)
    return _project_config.use_xblock()


def set_xblock_json(data):
    if _project_config is None:
        raise RuntimeError(_UNSUPPORTED_XBLOCK)
    return _project_config.set_xblock_json(data)
